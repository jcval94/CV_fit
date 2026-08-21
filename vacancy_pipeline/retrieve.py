from __future__ import annotations

import argparse
import json
from pathlib import Path

from vacancy_pipeline.index import retrieve


def main() -> int:
    parser = argparse.ArgumentParser(description="Lexically retrieve vacancy chunks from the incremental index.")
    parser.add_argument("query")
    parser.add_argument("--state-dir", default="vacancy_state")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--include-source-fit",
        action="store_true",
        help="include source-provided fit opinions; excluded from matching by default",
    )
    args = parser.parse_args()
    index_path = Path(args.state_dir) / "lexical_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    hits = retrieve(index, args.query, args.top_k, include_source_fit=args.include_source_fit)
    print(json.dumps([hit.to_dict() for hit in hits], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
