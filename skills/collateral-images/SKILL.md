---
name: collateral-images
description: Use when generating, replacing, or troubleshooting the imagery on collateral — brochure covers, feature figures, social card backgrounds. Triggers on "generate the images", "the picture is wrong", "regenerate the cover", "different photo", "make the image match", "no stock photos".
---

# Imagery

```bash
make images SLUG=<slug> BRAND=<brand>
python3 scripts/gen_images.py <slug> --brand <brand> --only cover --force
```

## Providers

Tried in order when `images.provider: auto`:

1. **higgsfield** — the `higgsfield` CLI, if installed and logged in. Uses
   `gpt_image_2` at 2k; override with `COLLATERAL_HF_MODEL` / `COLLATERAL_HF_RESOLUTION`.
2. **openai** — `OPENAI_API_KEY`, `gpt-image-1`.
3. **replicate** — `REPLICATE_API_TOKEN`, FLUX by default; override with
   `REPLICATE_IMAGE_MODEL`.
4. **placeholder** — a flat brand panel so the layout renders before art exists.

Set `images.provider: manual` in `brand.yaml` to skip generation entirely and
drop files into `campaigns/<slug>/assets/` yourself.

**Placeholders must never ship.** `verify.py` fails the build when `CREDITS.txt`
still lists placeholder art. That is deliberate.

## Writing prompts

Each prompt is joined with the brand's `images.style` clause and `images.negative`
list, so the campaign prompt describes only *what is happening*.

The rule that makes these look like a campaign rather than a stock library:

> **The picture shows what the offer actually does, in the reader's own world.**

Not "business success". A florist's counter at 6am. Hands editing a site at a
workbench. Two people leaning over one laptop in a shop back room.

Practical constraints:

- **Leave room for text.** Covers need a dark or empty lower third for the
  headline scrim. Social squares need an empty upper half for the wordmark.
- **No readable text in the image.** Generators cannot spell, and a garbled sign
  is the first thing a reader notices.
- **No faces you will need again.** Consistent people across a campaign is a
  different problem; prefer over-the-shoulder, hands, and empty rooms.
- **Aspect matters**: `2:3` covers, `3:2` figures, `1:1` Facebook, `16:9` X.

## Sizes

Generated at the destination's requirement: 2048px square for Facebook, 2400px
long edge for print figures. `verify.py` fails a hard upscale and warns on a
mild one.

## When an image is wrong

1. **Wrong crop** — do not regenerate. Adjust `hero.focal`
   (`center 25%` … `center 60%`) or the social entry's `focal`.
2. **Too bright behind the headline** — regenerate with "generous empty space in
   the lower third, darker toward the bottom" added to the prompt.
3. **Right idea, wrong feel** — change the brand's `images.style` clause, which
   fixes every image at once, rather than patching one prompt.
4. **Content is wrong** — rewrite the campaign prompt to name the specific scene.
   Vague prompts produce stock-looking results.

Always `--force` to overwrite, and always look at the result before rebuilding.
Every generation appends provider and prompt to `assets/CREDITS.txt`.
