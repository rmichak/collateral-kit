"""Composite the campaign's social cards and write their captions.

Social is where a campaign usually falls apart: a different image, a different
headline, a different promise from the print piece. So the card is built from
the *same* generated image and the *same* brand tokens as the brochure, and the
caption ships beside it in the same folder.

Surfaces:  fb_square 2048x2048   x_wide 1600x900   ig_portrait 1080x1350

Usage:  python3 scripts/social_card.py <campaign> --brand <brand> [--only name]
"""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from kit import (SOCIAL_SPECS, Brand, Campaign, KitError, credit, hex_to_rgb,
                 load_brand, load_campaign, slugify, social_name)


def load_font(brand: Brand, role: str, weight: int, size: int) -> ImageFont.FreeTypeFont:
    stem = slugify(brand.font(role)["family"])
    fonts = brand.root / "assets" / "fonts"
    for candidate in (weight, 700, 600, 500, 400):
        path = fonts / f"{stem}-{candidate}.ttf"
        if path.exists():
            return ImageFont.truetype(str(path), size)
    for fallback in ("/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(fallback).exists():
            return ImageFont.truetype(fallback, size)
    raise KitError(f"no TTF for {role}; run scripts/fetch_fonts.py {brand.slug}")


def cover_fit(img: Image.Image, size: tuple[int, int], focal: float = 0.4) -> Image.Image:
    """Scale to cover, then crop around a focal point given as a fraction of height."""
    tw, th = size
    scale = max(tw / img.width, th / img.height)
    resized = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))),
                         Image.LANCZOS)
    left = (resized.width - tw) // 2
    top = min(max(0, round(resized.height * focal - th / 2)), resized.height - th)
    return resized.crop((left, top, left + tw, top + th))


def gradient_scrim(size: tuple[int, int], color: tuple[int, int, int],
                   stops: list[tuple[float, float]]) -> Image.Image:
    """Vertical scrim. stops are (position 0-1, opacity 0-1), interpolated linearly."""
    w, h = size
    scrim = Image.new("RGBA", (1, h))
    px = scrim.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        prev, nxt = stops[0], stops[-1]
        for i in range(len(stops) - 1):
            if stops[i][0] <= t <= stops[i + 1][0]:
                prev, nxt = stops[i], stops[i + 1]
                break
        span = (nxt[0] - prev[0]) or 1
        alpha = prev[1] + (nxt[1] - prev[1]) * ((t - prev[0]) / span)
        px[0, y] = (*color, int(max(0.0, min(1.0, alpha)) * 255))
    return scrim.resize((w, h))


def wrap_to_width(draw, text: str, font, max_width: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit_headline(draw, text: str, brand: Brand, max_width: int, max_height: int,
                 start: int, min_size: int) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
    """Shrink the display face until the headline fits its box. Never let it overflow."""
    size = start
    while size > min_size:
        font = load_font(brand, "display", 700, size)
        lines = wrap_to_width(draw, text, font, max_width)
        leading = int(size * 1.08)
        if len(lines) * leading <= max_height:
            return font, lines, leading
        size -= max(2, size // 24)
    font = load_font(brand, "display", 700, min_size)
    return font, wrap_to_width(draw, text, font, max_width), int(min_size * 1.08)


def build_card(brand: Brand, campaign: Campaign, spec: dict, index: int) -> Path:
    kind = spec["kind"]
    surface = SOCIAL_SPECS[kind]
    W, H = surface["size"]
    pad = round(W * 0.072)

    image = campaign.image(spec["image"])
    if not image["path"].exists():
        raise KitError(f"social card needs {image['path']} — run gen_images.py first")

    base = cover_fit(Image.open(image["path"]).convert("RGB"), (W, H),
                     focal=float(spec.get("focal", 0.42)))
    canvas = base.convert("RGBA")

    # Scrim: light at the top so the wordmark sits on texture, heavy at the
    # bottom so the headline always clears its background.
    dark = hex_to_rgb(brand.colors["dark"])
    canvas.alpha_composite(gradient_scrim((W, H), dark,
                                          [(0.0, 0.55), (0.28, 0.20), (0.58, 0.55), (1.0, 0.94)]))
    draw = ImageDraw.Draw(canvas)

    # top band: wordmark
    lockup_path = brand.asset("lockup_light")
    if lockup_path:
        lock = Image.open(lockup_path).convert("RGBA")
        target_h = round(H * 0.042)
        lock = lock.resize((round(lock.width * target_h / lock.height), target_h), Image.LANCZOS)
        canvas.alpha_composite(lock, (pad, pad))

    # The bottom stack is measured first, then drawn upward from the baseline
    # padding, so nothing can run off the edge however long the headline is.
    kicker = spec.get("kicker")
    headline = spec.get("headline", "")
    body_w = W - pad * 2

    max_head_h = round(H * (0.34 if kind == "x_wide" else 0.42))
    hfont, hlines, leading = fit_headline(
        draw, headline, brand, body_w, max_head_h,
        start=round(H * (0.105 if kind == "x_wide" else 0.082)),
        min_size=round(H * 0.036))

    rule_h = max(3, round(H * 0.005))
    rule_gap = round(H * 0.030)
    chip_gap = round(H * 0.028)

    kfont = box = chip_h = None
    if kicker:
        kfont = load_font(brand, "mono", 500, round(H * 0.021))
        box = draw.textbbox((0, 0), kicker.upper(), font=kfont)
        chip_h = (box[3] - box[1]) + round(H * 0.009) * 2

    stack_h = rule_h + rule_gap + (chip_h + chip_gap if kicker else 0) + len(hlines) * leading
    y = H - pad - stack_h

    # accent rule
    draw.rectangle([(pad, y), (pad + round(W * 0.12), y + rule_h)],
                   fill=hex_to_rgb(brand.colors["accent"]))
    y += rule_h + rule_gap

    # kicker chip
    if kicker:
        text = kicker.upper()
        chip_pad_x, chip_pad_y = round(H * 0.014), round(H * 0.009)
        tw = draw.textlength(text, font=kfont)
        draw.rounded_rectangle([(pad, y), (pad + tw + chip_pad_x * 2, y + chip_h)],
                               radius=round(chip_h * 0.22),
                               fill=hex_to_rgb(brand.colors["highlight"]))
        draw.text((pad + chip_pad_x, y + chip_pad_y - box[1]), text,
                  font=kfont, fill=hex_to_rgb(brand.colors["dark"]))
        y += chip_h + chip_gap

    # headline
    for line in hlines:
        draw.text((pad, y), line, font=hfont, fill=(255, 255, 255, 255))
        y += leading

    out = campaign.out_dir / "social" / f"{social_name(campaign.slug, spec, index)}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out, quality=90, subsampling=0)
    return out


def write_caption(campaign: Campaign, spec: dict, card: Path) -> Path | None:
    caption = spec.get("caption")
    if not caption:
        return None
    limit = SOCIAL_SPECS[spec["kind"]]["limit"]
    text = caption.strip()
    if len(text) > limit:
        print(f"  ! caption for {card.stem} is {len(text)} chars; "
              f"{SOCIAL_SPECS[spec['kind']]['label']} allows {limit}")
    out = card.with_suffix(".txt")
    out.write_text(text + "\n", encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("campaign")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--only", help="build just this card name")
    args = ap.parse_args()

    brand = load_brand(args.brand)
    campaign = load_campaign(args.campaign)
    specs = campaign.data.get("social") or []
    if not specs:
        print("campaign defines no social: entries")
        return 0

    print(f"compositing social for {campaign.slug}")
    for i, spec in enumerate(specs):
        if args.only and spec.get("name") != args.only:
            continue
        card = build_card(brand, campaign, spec, i)
        w, h = SOCIAL_SPECS[spec["kind"]]["size"]
        print(f"  {card.relative_to(campaign.out_dir)}  {w}x{h}")
        credit(campaign, f"social/{card.name}  composited from {spec['image']}")
        caption = write_caption(campaign, spec, card)
        if caption:
            print(f"  {caption.relative_to(campaign.out_dir)}  "
                  f"{len(caption.read_text(encoding='utf-8').strip())} chars")
    print("  look at each card before posting.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
