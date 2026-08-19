"""Turn brand.yaml + campaign.yaml into print-ready HTML.

The campaign directory is made self-contained: brand fonts, wordmarks and
generated QR codes are staged into assets/brand/, and every path in the HTML is
relative. The folder can be zipped and opened anywhere, which is what makes the
review board and the hand-off to a printer work.

Usage:
  python3 scripts/build_page.py <campaign> --brand <brand> [--kind onepager|brochure|both]
"""
from __future__ import annotations

import argparse
import html
import re
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from kit import (TEMPLATE_DIR, Brand, Campaign, KitError, credit, load_brand,
                 load_campaign, slugify, soft)
from make_qr import write_qr

BRAND_STAGE = "assets/brand"   # relative to the campaign dir


def accent(text: str | None) -> str:
    """*starred* runs render in the accent colour. Everything else is escaped."""
    if not text:
        return ""
    parts = re.split(r"\*([^*]+)\*", text)
    out = []
    for i, part in enumerate(parts):
        esc = html.escape(part)
        out.append(f'<span class="ac">{esc}</span>' if i % 2 else esc)
    return "".join(out)


def stage_brand_assets(brand: Brand, campaign: Campaign) -> dict:
    """Copy fonts and wordmarks into the campaign so nothing points outside it."""
    dest = campaign.out_dir / BRAND_STAGE
    (dest / "fonts").mkdir(parents=True, exist_ok=True)

    fonts = {}
    for role in ("display", "mono"):
        spec = brand.font(role)
        files = []
        for face in brand.font_files(role):
            target = dest / "fonts" / face["path"].name
            shutil.copy2(face["path"], target)
            files.append({"weight": face["weight"], "href": f"{BRAND_STAGE}/fonts/{target.name}"})
        if not files:
            print(f"  ! no local {role} faces for '{spec['family']}' — "
                  f"run scripts/fetch_fonts.py {brand.slug} (falling back to {spec['stack']})")
        fonts[role] = {"family": spec["family"], "stack": spec["stack"], "files": files}

    lockups = {}
    for key in ("lockup_light", "lockup_dark"):
        src = brand.asset(key)
        if src:
            shutil.copy2(src, dest / src.name)
            lockups[key] = f"{BRAND_STAGE}/{src.name}"
        else:
            lockups[key] = None
    return {"fonts": fonts, **lockups}


def build_qrs(brand: Brand, campaign: Campaign) -> list[dict]:
    out = []
    for spec in campaign.data.get("qr", []) or []:
        target = brand.cta(spec["target"])
        url = spec.get("url") or target["url"]
        name = f"qr-{slugify(spec['target'])}.png"
        write_qr(url, campaign.out_dir / BRAND_STAGE / name)
        out.append({
            "href": f"{BRAND_STAGE}/{name}",
            "url": url,
            "caption": spec.get("caption") or target["label"],
        })
    return out


def credits_line(brand: Brand, campaign: Campaign) -> str:
    """One-line provenance for the printed page. The full ledger is CREDITS.txt."""
    images = campaign.data.get("images") or {}
    generated = [k for k, v in images.items() if v.get("prompt")]
    if not generated:
        return ""
    prefix = (brand.data.get("legal") or {}).get("credits_prefix", "Imagery:")
    return f"{prefix} original imagery generated for {brand.name}. Not stock."


def make_env(brand: Brand, campaign: Campaign) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        undefined=StrictUndefined,
        autoescape=False,   # templates escape deliberately via |e or accent()
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["accent"] = accent

    def resolve_image(key: str) -> str:
        spec = campaign.image(key)
        if not spec["path"].exists():
            print(f"  ! image '{key}' missing: {spec['path']}")
        return f"assets/{spec['file']}"

    def image_alt(key: str) -> str:
        return html.escape((campaign.image(key) or {}).get("alt", ""))

    env.globals.update(resolve_image=resolve_image, image_alt=image_alt)
    return env


def base_context(brand: Brand, campaign: Campaign, staged: dict, qrs: list[dict]) -> dict:
    data = campaign.data
    hero = data.get("hero", {})
    hero_img = campaign.image(hero.get("image"))
    cta_name = (data.get("cta") or {}).get("target") or next(iter(brand.data.get("cta", {})), None)
    return soft({
        "brand": {**brand.data, "name": brand.name},
        "campaign": {
            "title": data["title"],
            "hero": hero,
            "features": data.get("features", []),
            "price": data.get("price", {}),
            "aside": data.get("aside"),
            "cta": data.get("cta", {}),
        },
        "colors": brand.colors,
        "fonts": staged["fonts"],
        "lockup_light": staged["lockup_light"],
        "lockup_dark": staged["lockup_dark"],
        "hero_image": f"assets/{hero_img['file']}" if hero_img else None,
        "hero_alt": html.escape(hero_img.get("alt", "")) if hero_img else "",
        "hero_focal": hero.get("focal", "center 35%"),
        "qrs": qrs,
        "cta_target": brand.cta(cta_name) if cta_name else {"label": "", "url": "", "display": ""},
        "credits": credits_line(brand, campaign),
        "draft_marker": bool(data.get("draft_marker")),
    })


def build_onepager(env, ctx, campaign) -> Path:
    out = campaign.out_dir / f"{campaign.slug}-onepager.html"
    out.write_text(env.get_template("onepager/page.html.j2").render(**ctx), encoding="utf-8")
    print(f"  built {out.name}")
    return out


def build_brochure(env, ctx, campaign) -> Path:
    pages = campaign.data.get("pages") or []
    if not pages:
        print("  ! campaign has no pages: — brochure will be cover + closing only")
    closing = campaign.data.get("cta", {})
    ctx = {
        **ctx,
        "pages": soft(pages),
        "hero_height": "11in",
        "closing": {
            "eyebrow": closing.get("eyebrow", "Next step"),
            "headline": closing.get("headline") or ctx["cta_target"].get("label", ""),
            "sub": closing.get("sub", ""),
        },
    }
    out = campaign.out_dir / f"{campaign.slug}-brochure.html"
    out.write_text(env.get_template("brochure/document.html.j2").render(**ctx), encoding="utf-8")
    print(f"  built {out.name}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("campaign")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--kind", default="both", choices=["onepager", "brochure", "both"])
    args = ap.parse_args()

    brand = load_brand(args.brand)
    campaign = load_campaign(args.campaign)
    campaign.out_dir.mkdir(parents=True, exist_ok=True)
    campaign.assets_dir.mkdir(parents=True, exist_ok=True)

    print(f"building {campaign.slug} with brand {brand.name}")
    staged = stage_brand_assets(brand, campaign)
    qrs = build_qrs(brand, campaign)
    for q in qrs:
        credit(campaign, f"{Path(q['href']).name}  QR -> {q['url']}")

    env = make_env(brand, campaign)
    ctx = base_context(brand, campaign, staged, qrs)

    if args.kind in ("onepager", "both"):
        build_onepager(env, ctx, campaign)
    if args.kind in ("brochure", "both"):
        build_brochure(env, dict(ctx), campaign)
    print(f"  output: {campaign.out_dir}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
