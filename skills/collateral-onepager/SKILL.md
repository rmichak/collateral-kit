---
name: collateral-onepager
description: Use when the user wants a single-page leave-behind, sales sheet, flyer, or one-pager PDF for an offer. Triggers on "one-pager", "leave-behind", "sales sheet", "one page version", "something to hand out", "flyer for".
---

# One-pagers

One letter page: hero with the headline over the image, four feature rows, a
price card and callout down the right, a CTA bar with QR codes at the foot.

```bash
make build SLUG=<slug> BRAND=<brand>   # HTML
make pdf   SLUG=<slug>                 # PDF
make proof SLUG=<slug>                 # PNG to actually look at
```

## What it is for

Handed over at the end of a conversation, or attached to a follow-up email. The
reader already knows who you are; this answers "what does it cost and what do I
do next". It is not a brochure with pages removed — it carries less argument and
more decision.

## What lands on the page

Only the **first four** `features` from `campaign.yaml`. Order them so the
strongest is first; a reader scans two rows and the price.

The right column takes `price` and `aside`. The aside is the highest-value block
on the sheet — use it for what the offer *replaces*, in the reader's own terms,
not for a feature you could not fit elsewhere.

## Checks specific to this piece

- The hero image must survive a heavy bottom scrim. Bright, busy photographs
  fight the headline. Prefer a scene with dark or empty space in its lower half.
- `hero.focal` moves the crop (`center 35%` is the default). If a face or the
  subject is being cut, adjust it rather than regenerating the image.
- If the left column ends well above the credits line, you have three features'
  worth of content in a four-feature layout. Cut to three strong rows rather
  than padding a weak fourth.

## If it does not fit

The page does not scroll. When content overflows:

1. Shorten the feature bodies — one sentence each, no exceptions.
2. Drop the fourth feature.
3. Move detail to the brochure and leave the sheet as the decision page.

Never reduce the type size to make copy fit. The size is the design.
