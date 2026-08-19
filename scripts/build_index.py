"""Build the campaign index and the review board for a brand.

The index answers "what have we made and where does it live". The board is how
a decision gets made about each piece: approve, refresh, reject, retire, plus a
note, then one digest pasted back into the chat. Both are static HTML that work
straight off the filesystem — no server, nothing uploaded.

Usage:  python3 scripts/build_index.py --brand <brand> [--campaigns a,b] [--out <dir>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from kit import (CAMPAIGNS_DIR, TEMPLATE_DIR, KitError, load_brand,
                 load_campaign, social_name, soft)


def rel(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        import os
        return os.path.relpath(path, base)


def fingerprint(paths: list[Path]) -> str:
    """Changes when any listed file changes, so the board can reset stale verdicts."""
    h = hashlib.sha256()
    for p in sorted(paths):
        if p.exists():
            stat = p.stat()
            h.update(f"{p.name}:{stat.st_size}:{int(stat.st_mtime)}".encode())
    return h.hexdigest()[:12]


def collect(campaign, out_base: Path) -> list[dict]:
    """Every shippable artefact of one campaign, with the two facts a reviewer needs."""
    data = campaign.data
    purpose = data.get("purpose") or "—"
    audience = data.get("audience") or "—"
    assets: list[dict] = []
    proof_dir = campaign.out_dir / "proof"

    for kind, stem in (("one-pager", "onepager"), ("brochure", "brochure")):
        pdf = campaign.out_dir / f"{campaign.slug}-{stem}.pdf"
        if not pdf.exists():
            continue
        thumb = proof_dir / f"{campaign.slug}-{stem}-p01.png"
        assets.append({
            "id": f"{campaign.slug}:{stem}",
            "campaign": data["title"],
            "name": f"{data['title']} — {kind}",
            "kind": "pdf",
            "href": rel(pdf, out_base),
            "thumb": rel(thumb, out_base) if thumb.exists() else None,
            "purpose": purpose,
            "audience": audience,
            "rebuilt": True,
        })

    for index, spec in enumerate(data.get("social") or []):
        name = social_name(campaign.slug, spec, index)
        card = campaign.out_dir / "social" / f"{name}.jpg"
        if not card.exists():
            continue
        caption = card.with_suffix(".txt")
        assets.append({
            "id": f"{campaign.slug}:social:{name}",
            "campaign": data["title"],
            "name": name,
            "kind": spec["kind"].replace("_", " "),
            "href": rel(card, out_base),
            "thumb": rel(card, out_base),
            "purpose": purpose,
            "audience": audience,
            "caption_href": rel(caption, out_base) if caption.exists() else None,
            "rebuilt": True,
        })
    return assets


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--campaigns", help="comma-separated slugs; default is every built campaign")
    ap.add_argument("--out", default=None, help="output dir; default campaigns/_index")
    args = ap.parse_args()

    brand = load_brand(args.brand)
    out_base = Path(args.out).resolve() if args.out else (CAMPAIGNS_DIR / "_index")
    out_base.mkdir(parents=True, exist_ok=True)

    slugs = (args.campaigns.split(",") if args.campaigns else
             sorted(p.name for p in CAMPAIGNS_DIR.iterdir()
                    if (p / "campaign.yaml").exists()))
    if not slugs:
        raise KitError("no campaigns found — build one first")

    campaigns, all_assets, files = [], [], []
    for slug in slugs:
        campaign = load_campaign(slug)
        assets = collect(campaign, out_base)
        if not assets:
            print(f"  ! {slug}: nothing built yet, skipping")
            continue
        files.extend((out_base / a["href"]) for a in assets)
        all_assets.extend(assets)
        campaigns.append({
            "slug": slug,
            "title": campaign.data["title"],
            "status": campaign.data.get("status", "draft"),
            "purpose": campaign.data.get("purpose", ""),
            "assets": assets,
        })

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)),
                      trim_blocks=True, lstrip_blocks=True)
    ctx = {
        "brand": soft({**brand.data, "name": brand.name, "slug": brand.slug}),
        "colors": brand.colors,
        "campaigns": campaigns,
        "assets": all_assets,
        "assets_json": json.dumps(all_assets),
        "built": date.today().isoformat(),
        "storage_key": f"collateral-review-{brand.slug}",
        "migration_key": fingerprint(files),
    }

    for template, name in (("index/campaign-kit.html.j2", "campaign-kit.html"),
                           ("index/review-board.html.j2", "review-board.html")):
        path = out_base / name
        path.write_text(env.get_template(template).render(**ctx), encoding="utf-8")
        print(f"  built {rel(path, Path.cwd())}")

    print(f"  {len(all_assets)} asset(s) across {len(campaigns)} campaign(s)")
    print(f"  open: file://{out_base / 'review-board.html'}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
