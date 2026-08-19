"""Generate light and dark wordmark PNGs for a brand that has no logo file.

A real logo always wins — point brand.yaml assets.lockup_* at it instead. This
exists so a brand pack is renderable the moment it is created.

Usage:  python3 scripts/make_lockup.py <brand> [--text "Northwind Studio"]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from kit import KitError, hex_to_rgb, load_brand, slugify

HEIGHT = 220          # generous, so it stays crisp scaled down to ~0.3in in print
PAD_X, PAD_Y = 26, 34


def pick_font(brand, size: int) -> ImageFont.FreeTypeFont:
    stem = slugify(brand.font("display")["family"])
    fonts = brand.root / "assets" / "fonts"
    for weight in (700, 600, 500, 400):
        candidate = fonts / f"{stem}-{weight}.ttf"
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    for fallback in ("/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if Path(fallback).exists():
            return ImageFont.truetype(fallback, size)
    raise KitError("no usable TTF found — run scripts/fetch_fonts.py first")


def render(brand, text: str, fg: str, accent: str, out: Path) -> None:
    font = pick_font(brand, HEIGHT - PAD_Y * 2)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    box = probe.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]

    dot = int(HEIGHT * 0.13)
    gap = int(HEIGHT * 0.16)
    img = Image.new("RGBA", (tw + PAD_X * 2 + dot + gap, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cy = HEIGHT // 2
    draw.ellipse([(PAD_X, cy - dot // 2), (PAD_X + dot, cy + dot // 2)], fill=hex_to_rgb(accent))
    draw.text((PAD_X + dot + gap - box[0], cy - th // 2 - box[1]), text, font=font, fill=hex_to_rgb(fg))

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"  wrote {out.relative_to(brand.root)} ({img.width}x{img.height})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("brand")
    ap.add_argument("--text", help="wordmark text; defaults to the brand name")
    args = ap.parse_args()

    brand = load_brand(args.brand)
    text = args.text or brand.name
    print(f"generating wordmarks for {brand.name}")
    render(brand, text, "#FFFFFF", brand.colors["accent"], brand.root / "assets" / "lockup-light.png")
    render(brand, text, brand.colors["ink"], brand.colors["accentInk"], brand.root / "assets" / "lockup-dark.png")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
