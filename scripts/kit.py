"""Shared plumbing for collateral-kit: config loading, validation, path resolution.

Everything downstream (HTML build, PDF render, social compositor, index) reads
its inputs through here so a brand pack and a campaign file are interpreted
exactly one way.
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "schema"
TEMPLATE_DIR = ROOT / "templates"
BRANDS_DIR = ROOT / "brands"
CAMPAIGNS_DIR = ROOT / "campaigns"

# Semantic tokens every template may reference. A brand pack that omits one
# gets the fallback, so a minimal brand.yaml (six colours) still renders.
COLOR_FALLBACKS = {
    "ink": "#131C28",
    "body": "#2C3541",
    "muted": "#616C7A",
    "paper": "#FAF9F6",
    "paper2": "#F3F1EA",
    "rule": "#E3DFD5",
    "dark": "#0a0f1a",
    "dark2": "#141d2b",
    "dark3": "#1e2a3a",
    "onDark": "#E6ECF4",
    "onDarkDim": "#96A3B5",
    "accent": "#00d4ff",
    "accentInk": "#0e7490",
    "accentDeep": "#0a5567",
    "accentTint": "#e4f2f7",
    "highlight": "#f59e0b",
}

# Pixel dimensions per social surface. Kept here rather than in the templates
# because both the compositor and the caption linter need them.
SOCIAL_SPECS = {
    "fb_square":    {"size": (2048, 2048), "limit": 63206, "label": "Facebook square"},
    "x_wide":       {"size": (1600, 900),  "limit": 280,   "label": "X / Twitter card"},
    "ig_portrait":  {"size": (1080, 1350), "limit": 2200,  "label": "Instagram portrait"},
    "li_square":    {"size": (1200, 1200), "limit": 3000,  "label": "LinkedIn square"},
    "li_landscape": {"size": (1200, 627),  "limit": 3000,  "label": "LinkedIn landscape"},
}


class Blank:
    """A falsy stand-in for an absent optional field.

    Templates run under StrictUndefined so a mistyped *template* variable still
    fails loudly. Optional *campaign* fields are different: a campaign with no
    aside, no intro and no image is perfectly valid, and `{% if p.intro %}`
    should simply be false. Blank absorbs any attribute or key access, renders
    as an empty string, and iterates as empty.
    """

    __slots__ = ()

    def __getattr__(self, _name): return self
    def __getitem__(self, _key): return self
    def __call__(self, *_a, **_k): return self
    def __iter__(self): return iter(())
    def __len__(self): return 0
    def __bool__(self): return False
    def __str__(self): return ""
    def __repr__(self): return "''"
    def __eq__(self, other): return other in (None, "", False) or isinstance(other, Blank)
    def __hash__(self): return hash("")


BLANK = Blank()


class Soft(dict):
    """A dict whose missing keys are BLANK, applied recursively on load."""

    def __missing__(self, _key):
        return BLANK

    def __getattr__(self, name):
        return self[name]


def soft(value):
    """Recursively wrap mappings so optional fields are safe to reference."""
    if isinstance(value, dict):
        return Soft({k: soft(v) for k, v in value.items()})
    if isinstance(value, list):
        return [soft(v) for v in value]
    return value


class KitError(RuntimeError):
    """A problem the user can fix: bad config, missing asset, absent dependency."""


def die(msg: str) -> "None":
    raise KitError(msg)


def load_yaml(path: Path) -> dict:
    if not path.exists():
        die(f"missing file: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        die(f"{path} must contain a YAML mapping at the top level")
    return data


def validate(data: dict, schema_name: str, label: str) -> None:
    """Validate against JSON Schema when jsonschema is installed; skip loudly if not."""
    try:
        import jsonschema
    except ImportError:  # pragma: no cover - optional dependency
        print(f"  ! jsonschema not installed; skipping {label} validation", file=sys.stderr)
        return
    schema = json.loads((SCHEMA_DIR / schema_name).read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        lines = [f"{label} is invalid:"]
        for err in errors[:12]:
            where = "/".join(str(p) for p in err.path) or "(root)"
            lines.append(f"  - {where}: {err.message}")
        die("\n".join(lines))


@dataclass
class Brand:
    root: Path
    data: dict
    colors: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.data["brand"]["name"]

    @property
    def slug(self) -> str:
        return self.root.name

    def font(self, role: str) -> dict:
        spec = dict(self.data.get("fonts", {}).get(role, {}))
        spec.setdefault("weights", [400, 700] if role == "display" else [400, 500])
        spec.setdefault(
            "stack",
            "'Helvetica Neue', Arial, sans-serif" if role == "display" else "Menlo, monospace",
        )
        return spec

    def font_files(self, role: str) -> list[dict]:
        """Local woff2 faces for a role, as {weight, path}. Empty until fetch_fonts runs."""
        spec = self.font(role)
        stem = slugify(spec.get("family", role))
        out = []
        for weight in spec["weights"]:
            path = self.root / "assets" / "fonts" / f"{stem}-{weight}.woff2"
            if path.exists():
                out.append({"weight": weight, "path": path})
        return out

    def asset(self, key: str) -> Path | None:
        rel = self.data.get("assets", {}).get(key)
        if not rel:
            return None
        path = (self.root / rel).resolve()
        return path if path.exists() else None

    def cta(self, name: str) -> dict:
        entry = self.data.get("cta", {}).get(name)
        if not entry:
            available = ", ".join(self.data.get("cta", {})) or "(none defined)"
            die(f"brand '{self.name}' has no cta named '{name}'. Defined: {available}")
        return entry


def load_brand(ref: str) -> Brand:
    """Accept a brand name under brands/, or a path to a brand directory or brand.yaml."""
    candidates = [Path(ref), Path(ref) / "brand.yaml", BRANDS_DIR / ref / "brand.yaml"]
    path = next((c for c in candidates if c.is_file()), None)
    if path is None:
        known = sorted(p.name for p in BRANDS_DIR.iterdir() if (p / "brand.yaml").exists()) if BRANDS_DIR.exists() else []
        die(f"no brand pack at '{ref}'. Known brands: {', '.join(known) or '(none)'}")
    data = load_yaml(path)
    validate(data, "brand.schema.json", f"brand pack {path}")
    colors = {**COLOR_FALLBACKS, **(data.get("colors") or {})}
    return Brand(root=path.parent.resolve(), data=data, colors=colors)


@dataclass
class Campaign:
    path: Path
    data: dict

    @property
    def slug(self) -> str:
        return self.data["slug"]

    @property
    def out_dir(self) -> Path:
        return CAMPAIGNS_DIR / self.slug

    @property
    def assets_dir(self) -> Path:
        return self.out_dir / "assets"

    def image(self, key: str | None) -> dict | None:
        if not key:
            return None
        spec = (self.data.get("images") or {}).get(key)
        if spec is None:
            die(f"campaign '{self.slug}' references image '{key}' which is not defined under images:")
        return {**spec, "key": key, "path": self.assets_dir / spec["file"]}


def load_campaign(ref: str) -> Campaign:
    candidates = [Path(ref), Path(ref) / "campaign.yaml", CAMPAIGNS_DIR / ref / "campaign.yaml"]
    path = next((c for c in candidates if c.is_file()), None)
    if path is None:
        die(f"no campaign file at '{ref}' (looked for campaign.yaml)")
    data = load_yaml(path)
    validate(data, "campaign.schema.json", f"campaign {path}")
    return Campaign(path=path.resolve(), data=data)


def social_name(campaign_slug: str, spec: dict, index: int) -> str:
    """The filename stem for a social card. Defined once so the compositor and
    the index never disagree about what a card is called."""
    return spec.get("name") or f"{campaign_slug}-{spec['kind'].replace('_', '-')}-{index + 1}"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    def channel(c: float) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    l1, l2 = relative_luminance(hex_to_rgb(fg)), relative_luminance(hex_to_rgb(bg))
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def credit(campaign: Campaign, entry: str) -> None:
    """Append a line to the campaign's CREDITS.txt. Every asset gets one."""
    campaign.assets_dir.mkdir(parents=True, exist_ok=True)
    path = campaign.assets_dir / "CREDITS.txt"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if entry in existing:
        return
    with path.open("a", encoding="utf-8") as fh:
        if not existing:
            fh.write(f"# Asset provenance for {campaign.slug}\n")
        fh.write(entry.rstrip() + "\n")


def which(cmd: str) -> str | None:
    from shutil import which as _which
    return _which(cmd)


def chrome_executable() -> str:
    """Find a Chrome/Chromium binary for PDF rendering."""
    env = os.environ.get("CHROME_PATH") or os.environ.get("PUPPETEER_EXECUTABLE_PATH")
    if env and Path(env).exists():
        return env
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    for name in ("google-chrome", "chromium", "chrome"):
        found = which(name)
        if found:
            return found
    die("no Chrome/Chromium found. Install Chrome, or set CHROME_PATH.")
