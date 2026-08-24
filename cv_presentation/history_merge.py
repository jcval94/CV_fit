from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from cv_presentation.budget_dashboard import attach_navigation
from cv_presentation.feed_enhancements import enhance_feed_index
from cv_presentation.manual_send_status import apply_manual_send_status
from cv_presentation.p0_decision_ux import apply_p0_decision_ux


_POST_RE = re.compile(r'(<article class="feed-post"[^>]*>.*?</article>)', re.DOTALL)
_VACANCY_RE = re.compile(r'data-vacancy="([^"]+)"')


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _snapshot_date(site_dir: Path) -> date | None:
    raw = str(_read_json(site_dir / "showcase.json", {}).get("date") or "")[:10]
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _feed_posts(index_html: str) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for match in _POST_RE.finditer(index_html):
        html = match.group(1)
        vacancy = _VACANCY_RE.search(html)
        if vacancy:
            result.append((vacancy.group(1), html))
    return result


def _post_has_cv(post_html: str) -> bool:
    return "cv_primary.html" in post_html or "cv_alternate.html" in post_html


def _copy_missing_tree(source: Path, destination: Path) -> None:
    if not source.exists():
        return
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.rglob("*"):
        if not item.is_file():
            continue
        relative = item.relative_to(source)
        target = destination / relative
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def _replace_posts(index_html: str, posts: list[str]) -> str:
    matches = list(_POST_RE.finditer(index_html))
    if not matches:
        raise ValueError("latest showcase contains no feed-post markup")
    start = matches[0].start()
    end = matches[-1].end()
    return index_html[:start] + "\n".join(posts) + index_html[end:]


def _replace_count(html: str, label: str, value: int) -> str:
    pattern = re.compile(rf'<span class="top-stat">\d+ {re.escape(label)}</span>')
    return pattern.sub(f'<span class="top-stat">{value} {label}</span>', html, count=1)


def _replace_filter_count(html: str, filter_name: str, label: str, value: int) -> str:
    pattern = re.compile(
        rf'(<button class="filter[^>]*" data-filter="{re.escape(filter_name)}">){re.escape(label)} \(\d+\)(</button>)'
    )
    return pattern.sub(rf'\g<1>{label} ({value})\g<2>', html, count=1)


def _normalize_review_round_display(site_dir: Path) -> None:
    """Do not render a hard-coded /5 denominator after production moved to an adaptive cap."""
    index_path = site_dir / "index.html"
    text = index_path.read_text(encoding="utf-8")
    text = text.replace(
        "metric('Review rounds',rounds?`${rounds}/5`:'n/a')",
        "metric('Review rounds',rounds?String(rounds):'n/a')",
    )
    index_path.write_text(text, encoding="utf-8")


def merge_showcase_history(
    *,
    sites_root: Path,
    site_dir: Path,
    history_days: int = 7,
    generation_manifest: Path = Path("generation_state/manifest.json"),
) -> dict[str, Any]:
    if history_days < 1:
        raise ValueError("history_days must be >= 1")

    snapshots: list[tuple[Path, date]] = []
    for candidate in sorted(path for path in sites_root.iterdir() if path.is_dir()):
        snapshot_date = _snapshot_date(candidate)
        if snapshot_date and (candidate / "index.html").exists():
            snapshots.append((candidate, snapshot_date))
    if not snapshots:
        raise ValueError("no valid daily showcase snapshots were found")

    end_date = max(item[1] for item in snapshots)
    start_date = end_date - timedelta(days=history_days - 1)
    eligible = [(path, day) for path, day in snapshots if start_date <= day <= end_date]
    if not eligible:
        raise ValueError("no showcase snapshots fall inside the requested history window")

    # Directory prefixes supplied by the workflow encode newest-first run order.
    eligible.sort(key=lambda item: (item[1], item[0].name), reverse=True)
    latest_site = eligible[0][0]
    if site_dir.exists():
        shutil.rmtree(site_dir)
    shutil.copytree(latest_site, site_dir)

    selected_posts: dict[str, tuple[str, date, bool]] = {}
    selected_rows: dict[str, dict[str, Any]] = {}

    for snapshot, snapshot_day in eligible:
        index_html = (snapshot / "index.html").read_text(encoding="utf-8")
        for vacancy_id, post_html in _feed_posts(index_html):
            generated = _post_has_cv(post_html)
            existing = selected_posts.get(vacancy_id)
            if existing is None or (generated and not existing[2]):
                selected_posts[vacancy_id] = (post_html, snapshot_day, generated)

        payload = _read_json(snapshot / "showcase.json", {"vacancies": []})
        for raw in payload.get("vacancies", []):
            vacancy_id = str(raw.get("vacancy_id") or "")
            if not vacancy_id:
                continue
            row = dict(raw)
            row["source_date"] = snapshot_day.isoformat()
            existing_row = selected_rows.get(vacancy_id)
            current_generated = bool(row.get("has_technical_modern_html") or row.get("has_harvard_html"))
            existing_generated = bool(
                existing_row
                and (existing_row.get("has_technical_modern_html") or existing_row.get("has_harvard_html"))
            )
            if existing_row is None or (current_generated and not existing_generated):
                selected_rows[vacancy_id] = row

        source_vacancies = snapshot / "vacancies"
        if source_vacancies.exists():
            for vacancy_dir in source_vacancies.iterdir():
                if vacancy_dir.is_dir():
                    _copy_missing_tree(vacancy_dir, site_dir / "vacancies" / vacancy_dir.name)

    ordered_ids = sorted(
        selected_posts,
        key=lambda vacancy_id: (
            selected_posts[vacancy_id][1],
            float(selected_rows.get(vacancy_id, {}).get("fit_score") or 0),
            vacancy_id,
        ),
        reverse=True,
    )
    combined_posts = [selected_posts[vacancy_id][0] for vacancy_id in ordered_ids]

    index_path = site_dir / "index.html"
    index_html = _replace_posts(index_path.read_text(encoding="utf-8"), combined_posts)
    generated_count = sum(1 for vacancy_id in ordered_ids if selected_posts[vacancy_id][2])
    ready_count = sum(1 for vacancy_id in ordered_ids if selected_rows.get(vacancy_id, {}).get("ready_to_send") is True)
    review_count = len(ordered_ids) - ready_count

    index_html = index_html.replace("Today's vacancies and generated CVs", "Vacancies from the last 7 days")
    index_html = re.sub(
        r'<div class="feed-intro"><h2>Vacancies from the last 7 days</h2><p>.*?</p></div>',
        '<div class="feed-intro"><h2>Vacancies from the last 7 days</h2>'
        f'<p>History window {start_date.isoformat()} → {end_date.isoformat()}. '
        'Each post keeps the original vacancy link and the newest available public CV bundle.</p></div>',
        index_html,
        count=1,
        flags=re.DOTALL,
    )
    index_html = re.sub(
        r'<small>[^<]*· vacancy-to-CV pipeline</small>',
        f'<small>{start_date.isoformat()} → {end_date.isoformat()} · 7-day vacancy history</small>',
        index_html,
        count=1,
    )
    index_html = _replace_count(index_html, "vacancies", len(ordered_ids))
    index_html = _replace_count(index_html, "generated", generated_count)
    index_html = _replace_count(index_html, "ready", ready_count)
    index_html = _replace_filter_count(index_html, "all", "All", len(ordered_ids))
    index_html = _replace_filter_count(index_html, "ready", "Ready", ready_count)
    index_html = _replace_filter_count(index_html, "review", "Review", review_count)
    index_path.write_text(index_html, encoding="utf-8")

    combined_rows = [selected_rows[vacancy_id] for vacancy_id in ordered_ids if vacancy_id in selected_rows]
    (site_dir / "showcase.json").write_text(
        json.dumps(
            {
                "schema_version": 3,
                "view": "vacancy_cv_feed_7d",
                "date": end_date.isoformat(),
                "history_days": history_days,
                "window_start": start_date.isoformat(),
                "window_end": end_date.isoformat(),
                "vacancies": combined_rows,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    # Rebuild client-side enhancements from current versioned metrics without any model calls.
    process_metrics = site_dir / "process_metrics.json"
    if process_metrics.exists():
        process_metrics.unlink()
    enhance_feed_index(site_dir, generation_manifest_path=generation_manifest)
    _normalize_review_round_display(site_dir)
    apply_p0_decision_ux(site_dir)
    apply_manual_send_status(site_dir)
    attach_navigation(site_dir)

    return {
        "history_days": history_days,
        "window_start": start_date.isoformat(),
        "window_end": end_date.isoformat(),
        "snapshot_count": len(eligible),
        "vacancy_count": len(ordered_ids),
        "generated_count": generated_count,
        "ready_count": ready_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge recent daily-showcase artifacts into a seven-day GitHub Pages history feed.")
    parser.add_argument("--sites-root", required=True)
    parser.add_argument("--site-dir", default="_site")
    parser.add_argument("--history-days", type=int, default=7)
    parser.add_argument("--generation-manifest", default="generation_state/manifest.json")
    args = parser.parse_args()
    report = merge_showcase_history(
        sites_root=Path(args.sites_root),
        site_dir=Path(args.site_dir),
        history_days=args.history_days,
        generation_manifest=Path(args.generation_manifest),
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
