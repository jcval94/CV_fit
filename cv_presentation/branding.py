from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator


HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
FontToken = Literal["system_sans", "humanist_sans", "classic_serif", "modern_serif"]
BrandSourceKind = Literal["verified_manual", "verified_official", "fallback"]

FONT_STACKS: dict[FontToken, str] = {
    "system_sans": "Arial, Helvetica, sans-serif",
    "humanist_sans": '"Trebuchet MS", Arial, Helvetica, sans-serif',
    "classic_serif": '"Times New Roman", Times, serif',
    "modern_serif": 'Georgia, "Times New Roman", serif',
}


class BrandProfile(BaseModel):
    company: str
    source_kind: BrandSourceKind = "fallback"
    source_url: str | None = None
    verified: bool = False
    primary: str = "#1F2937"
    secondary: str = "#4B5563"
    accent: str = "#2563EB"
    surface: str = "#FFFFFF"
    text: str = "#111827"
    muted: str = "#4B5563"
    heading_font: FontToken = "system_sans"
    body_font: FontToken = "system_sans"
    notes: list[str] = Field(default_factory=list)

    @field_validator("primary", "secondary", "accent", "surface", "text", "muted")
    @classmethod
    def _valid_hex(cls, value: str) -> str:
        value = value.upper()
        if not HEX_RE.match(value):
            raise ValueError(f"expected 6-digit hex color, got {value!r}")
        return value


class DesignTokens(BaseModel):
    company: str
    brand_verified: bool
    brand_source_kind: BrandSourceKind
    brand_source_url: str | None = None
    primary: str
    secondary: str
    accent: str
    surface: str
    text: str
    muted: str
    heading_font_stack: str
    body_font_stack: str
    notes: list[str] = Field(default_factory=list)


class ContrastCheck(BaseModel):
    foreground: str
    background: str
    ratio: float
    threshold: float
    passed: bool
    use: str


class DesignValidation(BaseModel):
    passed: bool
    checks: list[ContrastCheck]
    reasons: list[str] = Field(default_factory=list)


def company_slug(company: str) -> str:
    normalized = unicodedata.normalize("NFKD", company).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "company"


def _rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


def _channel(value: int) -> float:
    scaled = value / 255.0
    return scaled / 12.92 if scaled <= 0.04045 else ((scaled + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    r, g, b = _rgb(hex_color)
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(a: str, b: str) -> float:
    l1, l2 = sorted((relative_luminance(a), relative_luminance(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def tokens_from_brand(profile: BrandProfile) -> DesignTokens:
    return DesignTokens(
        company=profile.company,
        brand_verified=profile.verified,
        brand_source_kind=profile.source_kind,
        brand_source_url=profile.source_url,
        primary=profile.primary,
        secondary=profile.secondary,
        accent=profile.accent,
        surface=profile.surface,
        text=profile.text,
        muted=profile.muted,
        heading_font_stack=FONT_STACKS[profile.heading_font],
        body_font_stack=FONT_STACKS[profile.body_font],
        notes=list(profile.notes),
    )


def validate_design_tokens(tokens: DesignTokens) -> DesignValidation:
    specs = [
        (tokens.text, tokens.surface, 4.5, "body text on surface"),
        (tokens.primary, tokens.surface, 4.5, "primary headings on surface"),
        (tokens.muted, tokens.surface, 4.5, "muted text on surface"),
        (tokens.surface, tokens.primary, 4.5, "light text on primary areas"),
        (tokens.surface, tokens.secondary, 4.5, "light text on secondary areas"),
        (tokens.accent, tokens.surface, 3.0, "large/accent graphics on surface"),
    ]
    checks = []
    for fg, bg, threshold, use in specs:
        ratio = round(contrast_ratio(fg, bg), 2)
        checks.append(ContrastCheck(
            foreground=fg,
            background=bg,
            ratio=ratio,
            threshold=threshold,
            passed=ratio >= threshold,
            use=use,
        ))
    reasons = [f"contrast_failed:{item.use}:{item.ratio}<{item.threshold}" for item in checks if not item.passed]
    if not tokens.brand_verified:
        reasons.append("brand_unverified: neutral/fallback styling must not be described as official institutional branding")
    return DesignValidation(passed=all(item.passed for item in checks), checks=checks, reasons=reasons)


def fallback_brand(company: str) -> BrandProfile:
    return BrandProfile(
        company=company,
        source_kind="fallback",
        verified=False,
        notes=["No verified company brand profile was supplied; use neutral ATS-safe styling."],
    )


def load_brand_profile(path: Path | None, *, company: str) -> BrandProfile:
    if path is None:
        return fallback_brand(company)
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    profile = BrandProfile.model_validate(payload)
    if profile.company.casefold().strip() != company.casefold().strip():
        raise ValueError(f"brand profile company {profile.company!r} does not match vacancy company {company!r}")
    if profile.source_kind != "fallback" and (not profile.verified or not profile.source_url):
        raise ValueError("verified brand profiles require verified=true and a source_url")
    return profile


def resolve_brand_profile(
    *,
    company: str,
    explicit_path: Path | None = None,
    profiles_dir: Path | None = None,
) -> BrandProfile:
    if explicit_path is not None:
        return load_brand_profile(explicit_path, company=company)
    if profiles_dir is not None:
        candidate = profiles_dir / f"{company_slug(company)}.yaml"
        if candidate.exists():
            return load_brand_profile(candidate, company=company)
    return fallback_brand(company)
