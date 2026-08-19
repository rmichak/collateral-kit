"""Scaffold a campaign file from the shipped example.

Usage:  python3 scripts/new_campaign.py <slug> [--title "Care Plan"] [--from example-retainer]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from kit import CAMPAIGNS_DIR, KitError


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--title")
    ap.add_argument("--source", default="example-retainer")
    args = ap.parse_args()

    dest = CAMPAIGNS_DIR / args.slug
    if (dest / "campaign.yaml").exists():
        raise KitError(f"{dest / 'campaign.yaml'} already exists")
    src = CAMPAIGNS_DIR / args.source / "campaign.yaml"
    if not src.exists():
        raise KitError(f"no source campaign at {src}")

    dest.mkdir(parents=True, exist_ok=True)
    title = args.title or args.slug.replace("-", " ").title()
    text = src.read_text(encoding="utf-8")
    text = text.replace(f"slug: {args.source}", f"slug: {args.slug}")
    text = text.replace("title: Website Care Plan", f"title: {title}")
    # Social cards are named explicitly in the source; carrying those names over
    # would collide with the original in the index. Drop them and let the
    # compositor derive names from this campaign's slug.
    text = "\n".join(line for line in text.splitlines()
                     if not re.match(r"^\s{4}name:\s", line))
    (dest / "campaign.yaml").write_text(text, encoding="utf-8")
    (dest / "assets").mkdir(exist_ok=True)

    print(f"created campaigns/{args.slug}/campaign.yaml (copied from {args.source})")
    print("\nRewrite it top to bottom — the example's words are placeholders.")
    print(f"Then:  make campaign SLUG={args.slug} BRAND=<your-brand>")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
