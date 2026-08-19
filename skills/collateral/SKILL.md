---
name: collateral
description: Use when the user wants marketing collateral for any brand — a one-pager, a print brochure, a Facebook or X/Twitter post, or a whole campaign for an offer. Triggers on "make a one-pager", "build a brochure", "campaign for <offer>", "flyer", "leave-behind", "social card", "FB post for this offer", "sales sheet". Routes to the right sub-skill and enforces the quality gates.
---

# Collateral

Turn one offer into a coherent set of pieces — brochure, one-pager, social cards
and captions — that all say the same thing and use the same art.

## First: is the kit ready?

```bash
make doctor BRAND=<brand>
```

If it reports missing pieces, fix those before anything else. If the user has no
brand pack yet, go to **collateral-brand** first — nothing else can run without one.

## The shape of the work

Two files drive everything. Nothing else needs editing.

| File | What it holds | How often it changes |
|---|---|---|
| `brands/<brand>/brand.yaml` | colours, fonts, wordmarks, CTA URLs, voice rules | once per brand |
| `campaigns/<slug>/campaign.yaml` | headline, features, price, image prompts, captions | once per offer |

Then one command builds every piece:

```bash
make campaign SLUG=<slug> BRAND=<brand>
```

which runs, in order: generate images → build HTML → render PDFs → composite
social cards → rasterise proofs → rebuild the index and review board → verify.

## Routing

| The user wants | Go to |
|---|---|
| a brand set up, colours or fonts changed | **collateral-brand** |
| the words for a new offer | **collateral-campaign** |
| a single leave-behind sheet | **collateral-onepager** |
| a multi-page print piece | **collateral-brochure** |
| Facebook / X / Instagram posts | **collateral-social** |
| imagery generated or replaced | **collateral-images** |
| to approve, reject or revise pieces | **collateral-review** |

## The rules that make the output good

These are not style preferences. Each one exists because skipping it produced a
piece that had to be rebuilt.

1. **One campaign, one set of images.** The hero on the brochure is the hero on
   the one-pager. The social card uses art from the same shoot. A campaign whose
   print and social look unrelated reads as two campaigns.
2. **Generated, never stock.** The picture must show what the offer actually
   does. A generic smiling-handshake photo tells the reader nothing and signals
   that nobody cared.
3. **Look at every proof before shipping.** `make proof` writes a PNG per page.
   `verify.py` catches mechanical faults; only your eyes catch a bad crop, a
   weak scrim, or a headline that reads wrong at a glance.
4. **Never print a QR to a URL that does not resolve.** Run
   `make verify` with `--check-urls` before anything goes to a printer. A wrong
   web page can be fixed in a minute; a wrong QR on 500 sheets cannot.
5. **Log every asset.** `assets/CREDITS.txt` records provider and prompt for
   each image. Six months later this is the only record of how a piece was made.
6. **Price honestly or not at all.** `price.mode` is `card`, `negotiable`, or
   `none`. Do not invent a number, and do not hedge with "starting at".
7. **Never claim a result that has not happened.** No named clients, no
   testimonials, no metrics unless the user supplies them.

## When something fails

- `jinja2.UndefinedError` on a template variable → a typo in a template, not the
  campaign. Optional campaign fields are safe to omit.
- Fonts render at the wrong weight on social cards → the family is a Google
  *variable* font; re-run `make fonts BRAND=<brand>`, which pins static instances.
- PDF is tiny or blank → an asset failed to load; `render_pdf.mjs` prints which.
- A page reads half-empty → give it an `image:` key, or merge it into its
  neighbour. Do not pad with filler copy.
