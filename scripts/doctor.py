"""Check every dependency and print exactly how to install what is missing.

Run this first on a new machine. Nothing here is guessed: each entry is a thing
the kit actually calls.

Usage:  python3 scripts/doctor.py [--brand <brand>]
"""
from __future__ import annotations

import argparse
import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

from kit import ROOT

OK, WARN, BAD = "  ok  ", " warn ", " MISS "


def line(status: str, name: str, detail: str = "") -> None:
    print(f"{status}  {name:<26} {detail}")


def check_python() -> int:
    v = sys.version_info
    if (v.major, v.minor) >= (3, 10):
        line(OK, "python", f"{v.major}.{v.minor}.{v.micro}")
        return 0
    line(BAD, "python", f"{v.major}.{v.minor} — need 3.10+")
    return 1


def check_modules() -> int:
    needed = {
        "jinja2": "templating the print HTML",
        "yaml": "reading brand.yaml and campaign.yaml",
        "PIL": "compositing social cards",
        "fontTools": "converting webfonts for the compositor",
        "qrcode": "QR codes for print CTAs",
        "jsonschema": "validating config before it renders",
    }
    missing = []
    for module, why in needed.items():
        try:
            importlib.import_module(module)
            line(OK, module, why)
        except ImportError:
            line(BAD, module, why)
            missing.append(module)
    try:
        importlib.import_module("brotli")
        line(OK, "brotli", "decompressing woff2 fonts")
    except ImportError:
        line(WARN, "brotli", "woff2 -> TTF will fail; social cards lose the brand font")
        missing.append("brotli")
    if missing:
        print(f"\n    fix:  uv pip install -r requirements.txt"
              f"\n      or:  python3 -m pip install -r requirements.txt")
    return len(missing)


def check_node() -> int:
    node = shutil.which("node")
    if not node:
        line(BAD, "node", "needed for HTML -> PDF")
        print("\n    fix:  brew install node   (or https://nodejs.org)")
        return 1
    version = subprocess.run([node, "-v"], capture_output=True, text=True).stdout.strip()
    major = int(version.lstrip("v").split(".")[0]) if version.startswith("v") else 0
    if major < 20:
        line(WARN, "node", f"{version} — 20+ recommended")
    else:
        line(OK, "node", version)

    if (ROOT / "node_modules" / "puppeteer-core").exists():
        line(OK, "puppeteer-core", "installed")
        return 0
    line(BAD, "puppeteer-core", "not installed")
    print("\n    fix:  npm install")
    return 1


def check_chrome() -> int:
    candidates = [
        os.environ.get("CHROME_PATH"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    ]
    for candidate in filter(None, candidates):
        if Path(candidate).exists():
            line(OK, "chrome", candidate)
            return 0
    line(BAD, "chrome", "no Chrome/Chromium found — this is the PDF engine")
    print("\n    fix:  install Google Chrome, or export CHROME_PATH=/path/to/chromium")
    return 1


def check_image_providers() -> int:
    found = []
    if shutil.which("higgsfield"):
        try:
            res = subprocess.run(["higgsfield", "account", "status"],
                                 capture_output=True, timeout=20, text=True)
            if res.returncode == 0:
                line(OK, "higgsfield", "CLI logged in")
                found.append("higgsfield")
            else:
                line(WARN, "higgsfield", "CLI present but not logged in — run: higgsfield auth login")
        except Exception:
            line(WARN, "higgsfield", "CLI present but did not respond")
    if os.environ.get("OPENAI_API_KEY"):
        line(OK, "openai", "OPENAI_API_KEY set (gpt-image-1)")
        found.append("openai")
    if os.environ.get("REPLICATE_API_TOKEN"):
        line(OK, "replicate", "REPLICATE_API_TOKEN set")
        found.append("replicate")

    if not found:
        line(WARN, "image provider", "none configured — placeholders only")
        print("\n    Collateral still builds; the art will be flat brand panels and"
              "\n    verify.py will refuse to pass them. Configure one of:"
              "\n      export OPENAI_API_KEY=...           gpt-image-1"
              "\n      export REPLICATE_API_TOKEN=...      FLUX and friends"
              "\n      higgsfield auth login               if you have an account"
              "\n    or set images.provider: manual in brand.yaml and supply files yourself.")
    return 0


def check_brand(ref: str) -> int:
    from kit import KitError, load_brand
    try:
        brand = load_brand(ref)
    except KitError as exc:
        line(BAD, f"brand {ref}", str(exc).splitlines()[0])
        return 1
    line(OK, f"brand {brand.slug}", brand.name)

    problems = 0
    for role in ("display", "mono"):
        files = brand.font_files(role)
        ttfs = [f for f in files if f["path"].with_suffix(".ttf").exists()]
        if not files:
            line(BAD, f"  {role} font", f"no local faces — run: make fonts BRAND={brand.slug}")
            problems += 1
        elif not ttfs:
            line(WARN, f"  {role} font", "woff2 only; social cards need the TTFs")
        else:
            line(OK, f"  {role} font", f"{len(files)} face(s)")
    for key in ("lockup_light", "lockup_dark"):
        if brand.asset(key):
            line(OK, f"  {key}", "present")
        else:
            line(WARN, f"  {key}", f"missing — run: make lockup BRAND={brand.slug}")
    if not brand.data.get("cta"):
        line(WARN, "  cta targets", "none defined; QRs and CTA panels will be empty")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", help="also check a brand pack")
    args = ap.parse_args()

    print("collateral-kit doctor\n")
    problems = check_python() + check_modules() + check_node() + check_chrome()
    check_image_providers()
    if args.brand:
        print()
        problems += check_brand(args.brand)

    print()
    if problems:
        print(f"{problems} thing(s) need fixing. Follow the fix lines above.")
        return 1
    print("Everything the kit needs is present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
