"""Generate the campaign's imagery through whichever provider is available.

The standing rule this kit encodes: imagery is generated for the piece and shows
what the offer actually does — never stock, never a smiling handshake. The same
file is then reused across brochure, one-pager and social so the campaign reads
as one thing.

Providers, tried in order when images.provider is `auto`:
  higgsfield   the `higgsfield` CLI, if installed and logged in
  openai       OPENAI_API_KEY, gpt-image-1
  replicate    REPLICATE_API_TOKEN, a FLUX endpoint
  placeholder  a branded gradient panel, so the layout renders before art exists

Usage:
  python3 scripts/gen_images.py <campaign> --brand <brand> [--only cover,fb]
                                [--provider auto|higgsfield|openai|replicate|placeholder]
                                [--force]
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from kit import KitError, credit, hex_to_rgb, load_brand, load_campaign

# Target pixels per aspect. Social surfaces set the ceiling: a Facebook square
# is served at 2048, so anything smaller is visibly upscaled in the feed.
ASPECT_PX = {
    "1:1":  (2048, 2048),
    "3:2":  (2400, 1600),
    "2:3":  (1600, 2400),
    "16:9": (1920, 1080),
    "4:5":  (1600, 2000),
}


def full_prompt(brand, spec: dict) -> str:
    """Campaign intent + brand style clause + brand negatives, in that order."""
    img = brand.data.get("images", {}) or {}
    parts = [spec["prompt"].strip()]
    if img.get("style"):
        parts.append(img["style"].strip())
    if img.get("negative"):
        parts.append(f"Avoid: {img['negative'].strip()}")
    return ". ".join(p.rstrip(".") for p in parts if p) + "."


# --------------------------------------------------------------------------- providers

def have_higgsfield() -> bool:
    from shutil import which
    if not which("higgsfield"):
        return False
    try:
        res = subprocess.run(["higgsfield", "account", "status"],
                             capture_output=True, timeout=25, text=True)
        return res.returncode == 0
    except Exception:
        return False


# `higgsfield model get <job_type>` lists a model's params. GPT Image 2 takes
# aspect_ratio / resolution / quality and is the strongest text-and-layout
# renderer; override with COLLATERAL_HF_MODEL if you prefer another.
HF_MODEL = os.environ.get("COLLATERAL_HF_MODEL", "gpt_image_2")
HF_ASPECTS = {"1:1", "4:3", "3:4", "16:9", "9:16", "3:2", "2:3"}


def gen_higgsfield(prompt: str, out: Path, aspect: str) -> bool:
    cmd = ["higgsfield", "--json", "generate", "create", HF_MODEL,
           "--prompt", prompt,
           "--aspect_ratio", aspect if aspect in HF_ASPECTS else "3:2",
           "--resolution", os.environ.get("COLLATERAL_HF_RESOLUTION", "2k"),
           "--quality", "high",
           "--wait", "--wait-timeout", "15m"]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=1000)
    if res.returncode != 0:
        print(f"    higgsfield failed: {(res.stderr or res.stdout).strip()[:300]}")
        return False

    url = first_media_url(res.stdout)
    if not url:
        print(f"    higgsfield returned no media url: {res.stdout.strip()[:300]}")
        return False
    with urllib.request.urlopen(url, timeout=300) as resp:
        out.write_bytes(resp.read())
    return True


def first_media_url(blob: str) -> str | None:
    """Walk whatever JSON the CLI printed and return the first image URL in it."""
    import re

    candidates: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, str) and value.startswith("http") and (
                        key in {"url", "raw", "min", "image_url", "output"}
                        or re.search(r"\.(jpe?g|png|webp)(\?|$)", value, re.I)):
                    candidates.append(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for line in blob.splitlines():
        line = line.strip()
        if not line or line[0] not in "{[":
            continue
        try:
            walk(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not candidates:
        try:
            walk(json.loads(blob))
        except json.JSONDecodeError:
            pass
    if not candidates:  # last resort: a bare URL printed as text
        found = re.findall(r"https?://\S+\.(?:jpe?g|png|webp)", blob, re.I)
        candidates = found
    return candidates[0] if candidates else None


def gen_openai(prompt: str, out: Path, aspect: str) -> bool:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return False
    w, h = ASPECT_PX.get(aspect, ASPECT_PX["3:2"])
    # gpt-image-1 accepts a fixed set of sizes; pick the nearest orientation.
    size = "1024x1024" if w == h else ("1536x1024" if w > h else "1024x1536")
    body = json.dumps({"model": "gpt-image-1", "prompt": prompt,
                       "size": size, "quality": "high", "n": 1}).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/images/generations", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        payload = json.loads(resp.read())
    out.write_bytes(base64.b64decode(payload["data"][0]["b64_json"]))
    return True


def gen_replicate(prompt: str, out: Path, aspect: str) -> bool:
    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        return False
    model = os.environ.get("REPLICATE_IMAGE_MODEL", "black-forest-labs/flux-1.1-pro")
    body = json.dumps({"input": {"prompt": prompt, "aspect_ratio": aspect,
                                 "output_format": "jpg"}}).encode()
    req = urllib.request.Request(
        f"https://api.replicate.com/v1/models/{model}/predictions", data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "Prefer": "wait"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        payload = json.loads(resp.read())
    url = payload.get("output")
    if isinstance(url, list):
        url = url[0] if url else None
    if not url:
        print(f"    replicate returned no output: {payload.get('error') or payload.get('status')}")
        return False
    with urllib.request.urlopen(url, timeout=300) as resp:
        out.write_bytes(resp.read())
    return True


def gen_placeholder(brand, prompt: str, out: Path, aspect: str, label: str) -> bool:
    """A brand-coloured panel that is obviously not final art."""
    from PIL import Image, ImageDraw

    w, h = ASPECT_PX.get(aspect, ASPECT_PX["3:2"])
    top, bottom = hex_to_rgb(brand.colors["dark"]), hex_to_rgb(brand.colors["dark2"])
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        draw.line([(0, y), (w, y)],
                  fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    accent = hex_to_rgb(brand.colors["accent"])
    step = max(w, h) // 14
    for i in range(-h, w, step):                      # faint diagonal rule pattern
        draw.line([(i, 0), (i + h, h)], fill=tuple(int(c * 0.22 + 30) for c in accent), width=2)
    draw.rectangle([(0, h - 96), (w, h)], fill=hex_to_rgb(brand.colors["dark"]))
    draw.text((40, h - 62), f"PLACEHOLDER — {label}", fill=accent)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)
    return True


PROVIDER_ORDER = ["higgsfield", "openai", "replicate", "placeholder"]


def choose(requested: str) -> list[str]:
    if requested and requested not in ("auto", "manual"):
        return [requested]
    if requested == "manual":
        return []
    order = []
    if have_higgsfield():
        order.append("higgsfield")
    if os.environ.get("OPENAI_API_KEY"):
        order.append("openai")
    if os.environ.get("REPLICATE_API_TOKEN"):
        order.append("replicate")
    order.append("placeholder")
    return order


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("campaign")
    ap.add_argument("--brand", required=True)
    ap.add_argument("--provider", default=None)
    ap.add_argument("--only", help="comma-separated image keys")
    ap.add_argument("--force", action="store_true", help="regenerate files that already exist")
    args = ap.parse_args()

    brand = load_brand(args.brand)
    campaign = load_campaign(args.campaign)
    campaign.assets_dir.mkdir(parents=True, exist_ok=True)

    requested = args.provider or (brand.data.get("images", {}) or {}).get("provider", "auto")
    order = choose(requested)
    if not order:
        print("provider is 'manual' — drop your files into "
              f"{campaign.assets_dir} and log them in CREDITS.txt")
        return 0
    print(f"image providers, in order: {' -> '.join(order)}")

    # A real provider can fail transiently (a 5xx, a dropped connection). Retry
    # it a couple of times before falling through, so one blip does not quietly
    # demote an image to a placeholder.
    ATTEMPTS = {"higgsfield": 3, "openai": 3, "replicate": 3, "placeholder": 1}
    real_providers = [p for p in order if p != "placeholder"]

    wanted = set(args.only.split(",")) if args.only else None
    images = campaign.data.get("images") or {}
    made = 0
    fell_back = []
    for key, spec in images.items():
        if wanted and key not in wanted:
            continue
        out = campaign.assets_dir / spec["file"]
        if out.exists() and not args.force:
            print(f"  = {key}: {out.name} exists (use --force to regenerate)")
            continue
        if not spec.get("prompt"):
            print(f"  ! {key}: no prompt and no file — supply one or add a prompt")
            continue

        prompt = full_prompt(brand, spec)
        aspect = spec.get("aspect", "3:2")
        winner = None
        for provider in order:
            for attempt in range(1, ATTEMPTS[provider] + 1):
                suffix = f"  (retry {attempt - 1})" if attempt > 1 else ""
                print(f"  > {key} via {provider} ({aspect}){suffix}")
                try:
                    ok = (gen_placeholder(brand, prompt, out, aspect, key) if provider == "placeholder"
                          else {"higgsfield": gen_higgsfield, "openai": gen_openai,
                                "replicate": gen_replicate}[provider](prompt, out, aspect))
                except Exception as exc:
                    print(f"    {provider} error: {exc}")
                    ok = False
                if ok:
                    winner = provider
                    break
                if attempt < ATTEMPTS[provider]:
                    time.sleep(2 * attempt)
            if winner:
                break
        if winner:
            credit(campaign, f"{spec['file']}  {winner}  prompt: {prompt}")
            print(f"    wrote {out.name}")
            made += 1
            if winner == "placeholder" and real_providers:
                fell_back.append(key)
        else:
            print(f"  ! {key}: every provider failed")

    print(f"done: {made} image(s). Look at each one before you ship it.")
    if fell_back:
        print()
        print(f"  WARNING: {len(fell_back)} image(s) fell back to a branded placeholder "
              f"because {' / '.join(real_providers)} failed: {', '.join(fell_back)}")
        print( "  These are blank panels, not real art. Re-run once the provider is back,"
               " e.g. `gen_images.py <campaign> --brand <brand> --only "
              f"{','.join(fell_back)} --force`.")
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
