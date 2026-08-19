"""Pre-ship checks. Fails loudly on the mistakes that are expensive to find late.

Nothing here is a matter of taste. Each check corresponds to something that has
actually gone wrong on a real campaign: a placeholder that shipped, an image
used on print at web resolution, a caption over the platform limit, a QR
pointing at a page that does not exist, a headline that cannot be read against
its own scrim.

Usage:  python3 scripts/verify.py <campaign> --brand <brand> [--check-urls]
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

from kit import (SOCIAL_SPECS, Campaign, KitError, contrast_ratio, load_brand,
                 load_campaign, social_name)

# 150 dpi is the floor for a letter page; below it the image visibly softens.
MIN_PRINT_PX = {"cover": 1400, "default": 1100}


class Report:
    def __init__(self) -> None:
        self.problems: list[str] = []
        self.warnings: list[str] = []
        self.passes = 0

    def fail(self, msg: str) -> None:
        self.problems.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def ok(self, _msg: str = "") -> None:
        self.passes += 1


def usage_map(campaign: Campaign) -> tuple[set, set]:
    """Which image keys land on print, and which land on social."""
    social = {s.get("image") for s in (campaign.data.get("social") or [])} - {None}
    print_used = {campaign.data.get("hero", {}).get("image")}
    for page in campaign.data.get("pages") or []:
        print_used.add(page.get("image"))
        for item in page.get("items") or []:
            print_used.add(item.get("image"))
    return print_used - {None}, social


def check_images(campaign: Campaign, rep: Report) -> None:
    from PIL import Image

    images = campaign.data.get("images") or {}
    if not images:
        rep.warn("campaign defines no images — the pieces will be flat colour")
    print_used, social_used = usage_map(campaign)

    for key, spec in images.items():
        path = campaign.assets_dir / spec["file"]
        if not path.exists():
            rep.fail(f"image '{key}' missing: {path.name}. Run gen_images.py.")
            continue
        with Image.open(path) as img:
            w, h = img.size

        # Print and social have different floors, and an image can be both.
        floors = []
        if key in print_used:
            floors.append((MIN_PRINT_PX["cover" if key == "cover" else "default"], "print"))
        for spec_social in campaign.data.get("social") or []:
            if spec_social.get("image") == key:
                sw, sh = SOCIAL_SPECS[spec_social["kind"]]["size"]
                floors.append((max(sw, sh), SOCIAL_SPECS[spec_social["kind"]]["label"]))
        if not floors:
            continue
        floor, why = max(floors, key=lambda f: f[0])
        long_edge = max(w, h)
        if long_edge < floor * 0.6:
            rep.fail(f"image '{key}' is {w}x{h}; {why} wants {floor}px on the long edge. "
                     f"That is a hard upscale and it will show.")
        elif long_edge < floor:
            rep.warn(f"image '{key}' is {w}x{h}; {why} wants {floor}px. "
                     f"Mild upscale — acceptable, but regenerate if you can.")
        else:
            rep.ok()

    credits = campaign.assets_dir / "CREDITS.txt"
    if not credits.exists():
        rep.fail("no CREDITS.txt — every asset must record where it came from")
    else:
        text = credits.read_text(encoding="utf-8")
        for key, spec in images.items():
            if spec["file"] not in text:
                rep.warn(f"image '{key}' is not logged in CREDITS.txt")
        if "placeholder" in text:
            rep.fail("CREDITS.txt lists placeholder art — generate real imagery before shipping")
        rep.ok()


def check_reuse(campaign: Campaign, rep: Report) -> None:
    """Every generated image should be doing a job somewhere."""
    images = set((campaign.data.get("images") or {}).keys())
    used_print, used_social = usage_map(campaign)
    unused = images - (used_social | used_print)
    for key in sorted(unused):
        rep.warn(f"image '{key}' is generated but never placed on a piece")
    if not used_print:
        rep.fail("no image is used on any print piece")
    else:
        rep.ok()


def check_contrast(brand, rep: Report) -> None:
    """Headline and body colours must clear WCAG AA against their backgrounds."""
    pairs = [
        ("#FFFFFF", brand.colors["dark"], "hero headline on the dark panel", 4.5),
        (brand.colors["onDark"], brand.colors["dark"], "body copy on the dark panel", 4.5),
        (brand.colors["ink"], brand.colors["paper"], "headline on paper", 4.5),
        (brand.colors["body"], brand.colors["paper"], "body copy on paper", 4.5),
        (brand.colors["accentInk"], brand.colors["paper"], "accent text on paper", 4.5),
        (brand.colors["accentDeep"], brand.colors["accentTint"], "aside text on its tint", 4.5),
        (brand.colors["accent"], brand.colors["dark"], "accent text on the dark panel", 3.0),
        (brand.colors["dark"], brand.colors["highlight"], "chip text on the highlight chip", 4.5),
    ]
    for fg, bg, label, floor in pairs:
        ratio = contrast_ratio(fg, bg)
        if ratio < floor:
            rep.fail(f"contrast {ratio:.1f}:1 for {label} (needs {floor}:1) — adjust the brand tokens")
        else:
            rep.ok()


def check_captions(campaign: Campaign, rep: Report) -> None:
    for index, spec in enumerate(campaign.data.get("social") or []):
        caption = (spec.get("caption") or "").strip()
        surface = SOCIAL_SPECS[spec["kind"]]
        name = social_name(campaign.slug, spec, index)
        if not caption:
            rep.warn(f"social card '{name}' has no caption")
            continue
        if len(caption) > surface["limit"]:
            rep.fail(f"caption for '{name}' is {len(caption)} chars; "
                     f"{surface['label']} allows {surface['limit']}")
        else:
            rep.ok()
        headline = (spec.get("headline") or "").strip()
        if headline and len(headline) > 90:
            rep.warn(f"headline on '{name}' is {len(headline)} chars — it will shrink to fit")


def check_outputs(campaign: Campaign, rep: Report) -> None:
    expected = [
        campaign.out_dir / f"{campaign.slug}-onepager.pdf",
        campaign.out_dir / f"{campaign.slug}-brochure.pdf",
    ]
    for path in expected:
        if not path.exists():
            rep.warn(f"not built yet: {path.name}")
        elif path.stat().st_size < 20_000:
            rep.fail(f"{path.name} is only {path.stat().st_size} bytes — the render probably failed")
        else:
            rep.ok()
    for index, spec in enumerate(campaign.data.get("social") or []):
        name = social_name(campaign.slug, spec, index)
        if not (campaign.out_dir / "social" / f"{name}.jpg").exists():
            rep.warn(f"social card not built: {name}.jpg")


def check_urls(brand, campaign: Campaign, rep: Report) -> None:
    """A QR pointing at a 404 is the worst possible print defect: unfixable."""
    targets = {}
    for spec in campaign.data.get("qr") or []:
        entry = brand.cta(spec["target"])
        targets[spec["target"]] = spec.get("url") or entry["url"]
    cta_name = (campaign.data.get("cta") or {}).get("target")
    if cta_name:
        targets[cta_name] = brand.cta(cta_name)["url"]

    for name, url in targets.items():
        try:
            req = urllib.request.Request(url, method="HEAD",
                                         headers={"User-Agent": "collateral-kit/verify"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                code = resp.status
        except Exception as exc:
            rep.fail(f"cta '{name}' -> {url} is unreachable ({exc}). "
                     "Do not print a QR to a URL that does not resolve.")
            continue
        if code >= 400:
            rep.fail(f"cta '{name}' -> {url} returned {code}")
        else:
            rep.ok()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("campaign")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--check-urls", action="store_true",
                    help="HEAD every CTA and QR target; do this before anything goes to print")
    args = ap.parse_args()

    brand = load_brand(args.brand)
    campaign = load_campaign(args.campaign)
    rep = Report()

    print(f"verifying {campaign.slug} ({brand.name})")
    check_images(campaign, rep)
    check_reuse(campaign, rep)
    check_contrast(brand, rep)
    check_captions(campaign, rep)
    check_outputs(campaign, rep)
    if args.check_urls:
        check_urls(brand, campaign, rep)

    for msg in rep.warnings:
        print(f"  warn  {msg}")
    for msg in rep.problems:
        print(f"  FAIL  {msg}")
    print(f"  {rep.passes} checks passed, {len(rep.warnings)} warnings, {len(rep.problems)} failures")
    if rep.problems:
        print("\nNot ready to ship. Fix the failures above.")
        return 1
    print("\nMechanically clean. Now look at every proof image before you ship it —"
          "\nnothing here can tell you whether the picture is any good.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
