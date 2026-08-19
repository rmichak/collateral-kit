---
name: collateral-social
description: Use when the user wants social posts for an offer — Facebook squares, X/Twitter cards, Instagram portraits, and the captions to go with them. Triggers on "facebook post", "FB square", "twitter post", "X post", "social card", "post for this campaign", "caption for".
---

# Social cards

Cards are composited in PIL from the **same** generated image and the **same**
brand tokens as the print pieces, so the campaign reads as one thing across
print and feed.

```bash
make social SLUG=<slug> BRAND=<brand>
```

Writes `campaigns/<slug>/social/<name>.jpg` and `<name>.txt` side by side.

## Surfaces

| `kind` | Pixels | Caption limit |
|---|---|---|
| `fb_square` | 2048 × 2048 | 63,206 |
| `x_wide` | 1600 × 900 | 280 |
| `ig_portrait` | 1080 × 1350 | 2,200 |
| `li_square` | 1200 × 1200 | 3,000 |
| `li_landscape` | 1200 × 627 | 3,000 |

LinkedIn favours the square in-feed; the landscape matches its link-preview size.

`verify.py` fails the build on a caption over its limit — X in particular.

## Card anatomy

Wordmark top-left; accent rule, eyebrow chip and headline stacked up from the
bottom. The whole stack is measured before it is drawn, so a long headline
shrinks to fit rather than running off the edge.

```yaml
social:
  - kind: fb_square
    name: care-plan-fb-1
    image: social_square      # a key from images:
    kicker: Website care plan
    headline: Your site should not be your problem to babysit.
    caption: |
      ...
```

Give social its own image with **empty space in the upper half** — the top of a
square is where the wordmark sits and where feed UI crops. Reusing the print
cover usually puts the subject exactly where the headline needs to go.

## Writing captions

The card carries the hook; the caption carries the argument. They must not be
the same sentence.

- **Facebook** — open with the reader's situation in one line, then a blank
  line. Three or four short paragraphs. Price and terms plainly. End with the
  single next step. Links in the first comment if the user prefers, but the
  caption should still name the destination.
- **X** — under 280 including the URL. One idea. No thread unless asked.
- **Instagram** — front-load the first 125 characters; the rest is truncated.

Do not write a caption in a different voice from the brochure. If the print
piece says "we look at your site together", the caption does not say "let's
unlock your digital potential".

## Before posting

Look at every card. `verify.py` cannot tell you that the headline sits over a
busy patch of the photograph or that the crop cut something in half.
