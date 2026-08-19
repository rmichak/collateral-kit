---
name: collateral-campaign
description: Use when writing or revising the copy for an offer's collateral — headline, features, price, CTA, page structure. Triggers on "write the campaign for", "what should the brochure say", "draft the copy", "new offer", "rewrite the headline", "the copy is too generic".
---

# Writing a campaign

`campaigns/<slug>/campaign.yaml` holds every word that appears on every piece.
Write it once; brochure, one-pager and social all read from it.

```bash
python3 scripts/new_campaign.py <slug> --title "<Offer name>"
```

Then rewrite it completely. The example's words are placeholders, not a template
to lightly edit — copy that has been half-edited reads worse than copy written
from scratch.

## Before writing, get four answers

Ask the user; do not invent them.

1. **Who is this for**, specifically? Not "small businesses" — "florists and
   DJs who answer their own phone".
2. **What does it replace?** The hour they lose, the task they dread, the thing
   that keeps not getting done. This is the headline.
3. **What does it cost**, and is that number public?
4. **What happens next?** The exact URL the reader goes to.

## Structure

```yaml
hero:
  chip: SHORT UPPERCASE LABEL
  headline: The first clause
  headline_accent: the second clause, in the accent colour
  sub: One sentence, plain, no adjectives.
  image: cover
```

Splitting the headline is what gives it the two-tone look. Put the *turn* in the
accent half — the surprise, the promise, the relief.

`features` are the spine. Four for the one-pager, more for the brochure. Each is
a `kicker` (two or three words, mono, uppercase), a `title`, and one `body`
sentence. **One idea per row.** If a row needs a semicolon it is two rows.

`pages` are the brochure interior, each with a `layout`:

| Layout | For |
|---|---|
| `feature-spread` | four points in two columns |
| `steps` | a numbered sequence: how it works, what happens next |
| `price` | the price card with what is and is not included |
| `proof` | a pull quote plus supporting points |
| `gallery` | two captioned images |

Any page may carry an `image:` key; the figure grows to fill whatever height is
left, so a short page does not read empty.

## Writing rules

Beyond the brand's own voice rules:

- **Lead with the problem.** The reader recognises their own week in the first
  line, or they stop reading.
- **Concrete over abstract.** "The quote that went quiet" beats "improved
  follow-up efficiency".
- **Say the number.** Hedged pricing reads as expensive. If it genuinely varies,
  use `price.mode: negotiable` and say what drives it.
- **Never claim what has not happened.** No invented testimonials, client names,
  or metrics. If the user has none yet, use a `steps` page instead of `proof`.
- **Mark accents with asterisks.** `title: One number, *no surprises.*` renders
  the starred run in the accent colour. Use it once per heading, never mid-word.

## Length

The layout shrinks a headline to fit, but a headline that has to shrink was too
long. Aim for: hero headline under 60 characters, sub under 160, feature body
under 200. If it does not fit, the idea is not sharp yet.
