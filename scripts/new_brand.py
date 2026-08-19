"""Scaffold a new brand pack from the example, then fetch its fonts.

A brand pack is the only thing that differs between one company's collateral
and another's. This copies the annotated example so you edit values rather
than invent structure.

Usage:  python3 scripts/new_brand.py <slug> [--name "Acme Co"] [--from _example]
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from kit import BRANDS_DIR, KitError


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", help="directory name under brands/")
    ap.add_argument("--name", help="display name; defaults to a title-cased slug")
    ap.add_argument("--source", default="_example", help="brand pack to copy")
    args = ap.parse_args()

    dest = BRANDS_DIR / args.slug
    if dest.exists():
        raise KitError(f"{dest} already exists")
    src = BRANDS_DIR / args.source
    if not (src / "brand.yaml").exists():
        raise KitError(f"no source brand pack at {src}")

    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("fonts", "*.ttf", "*.woff2"))
    (dest / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    for stale in ("lockup-light.png", "lockup-dark.png"):
        (dest / "assets" / stale).unlink(missing_ok=True)

    name = args.name or args.slug.replace("-", " ").title()
    path = dest / "brand.yaml"
    text = path.read_text(encoding="utf-8")
    text = text.replace("Northwind Studio", name).replace("northwind.example",
                                                          f"{args.slug}.example")
    path.write_text(text, encoding="utf-8")

    print(f"created brands/{args.slug}/")
    print("\nNow, in order:")
    print(f"  1. edit brands/{args.slug}/brand.yaml — colours, fonts, cta URLs, voice")
    print(f"  2. make fonts BRAND={args.slug}      — pull the faces you named")
    print(f"  3. drop a real logo at brands/{args.slug}/assets/lockup-light.png")
    print(f"     (or run: make lockup BRAND={args.slug} to generate a wordmark)")
    print(f"  4. make doctor BRAND={args.slug}     — confirm the pack is complete")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
