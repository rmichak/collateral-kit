"""Pull a brand's display and mono faces from Google Fonts into the brand pack.

Print output must not depend on the network at render time, and the PIL social
compositor needs TTFs (it cannot read woff2), so each face is stored twice:
  assets/fonts/<family>-<weight>.woff2   embedded by the HTML templates
  assets/fonts/<family>-<weight>.ttf     used by the social compositor

Usage:  python3 scripts/fetch_fonts.py <brand>
"""
from __future__ import annotations

import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from kit import KitError, load_brand, slugify

# Google serves woff2 only to user agents it believes support it.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def css_for(family: str, weights: list[int]) -> str:
    spec = f"{urllib.parse.quote(family)}:wght@{';'.join(str(w) for w in sorted(weights))}"
    url = f"https://fonts.googleapis.com/css2?family={spec}&display=swap"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def faces_from_css(css: str) -> dict[int, str]:
    """Map weight -> woff2 url, keeping the latin subset (the last block wins in Google's CSS)."""
    out: dict[int, str] = {}
    for block in css.split("@font-face"):
        weight = re.search(r"font-weight:\s*(\d+)", block)
        src = re.search(r"url\((https://[^)]+\.woff2)\)", block)
        if weight and src:
            out[int(weight.group(1))] = src.group(1)
    return out


def to_static(woff2: Path, ttf: Path, weight: int) -> bool:
    """Write a static TTF at `weight`.

    Google Fonts increasingly serves one *variable* file for every requested
    weight, so figtree-400.woff2 and figtree-700.woff2 are the same bytes. A
    browser resolves the axis; PIL does not, and every social headline would
    silently render at 400. When the face has an fvar table we pin the weight
    axis to produce a genuine static instance.
    """
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        print("  ! fontTools not installed; skipping TTF conversion (social cards need it)")
        return False
    try:
        font = TTFont(str(woff2))
        if "fvar" in font:
            from fontTools.varLib import instancer
            axes = {a.axisTag: weight for a in font["fvar"].axes if a.axisTag == "wght"}
            if axes:
                font = instancer.instantiateVariableFont(font, axes, updateFontNames=False)
        font.flavor = None
        font.save(str(ttf))
        return True
    except Exception as exc:  # brotli missing, or an unusual face
        print(f"  ! could not convert {woff2.name} to TTF: {exc}")
        return False


def is_variable(path: Path) -> bool:
    try:
        from fontTools.ttLib import TTFont
        return "fvar" in TTFont(str(path))
    except Exception:
        return False


def variable_range(path: Path) -> tuple[int, int] | None:
    """The wght axis min/max of a variable face, for the CSS @font-face range."""
    try:
        from fontTools.ttLib import TTFont
        font = TTFont(str(path))
        for axis in font.get("fvar").axes if "fvar" in font else []:
            if axis.axisTag == "wght":
                return int(axis.minValue), int(axis.maxValue)
    except Exception:
        pass
    return None


def fetch_role(brand, role: str) -> int:
    spec = brand.font(role)
    family = spec.get("google") or spec.get("family")
    if not spec.get("google"):
        print(f"  {role}: '{family}' has no google: key — assuming self-hosted, skipping")
        return 0
    stem = slugify(spec["family"])
    dest = brand.root / "assets" / "fonts"
    dest.mkdir(parents=True, exist_ok=True)

    faces = faces_from_css(css_for(family, spec["weights"]))
    count = 0
    for weight in spec["weights"]:
        url = faces.get(weight)
        if not url:
            print(f"  ! {family} has no weight {weight} on Google Fonts")
            continue
        woff2 = dest / f"{stem}-{weight}.woff2"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as resp:
            woff2.write_bytes(resp.read())
        to_static(woff2, dest / f"{stem}-{weight}.ttf", weight)
        note = " (variable, pinned for TTF)" if is_variable(woff2) else ""
        print(f"  {family} {weight} -> {woff2.name}{note}")
        count += 1
    return count


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    brand = load_brand(sys.argv[1])
    print(f"fetching fonts for {brand.name}")
    total = sum(fetch_role(brand, role) for role in ("display", "mono"))
    print(f"done: {total} faces in {brand.root / 'assets' / 'fonts'}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
