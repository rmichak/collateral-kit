---
name: collateral-brand
description: Use when setting up a brand for collateral, or changing its colours, fonts, logo, CTA links, or voice rules. Triggers on "set up a brand", "new client brand", "change the brand colours", "use these fonts", "add a booking link", "brand pack", "make it match our brand".
---

# Brand packs

A brand pack is the only file that differs between one company's collateral and
another's. Get it right once and every campaign inherits it.

## Creating one

```bash
make brand BRAND=<slug>        # copies the annotated example
make fonts BRAND=<slug>        # pulls the faces named in brand.yaml
make lockup BRAND=<slug>       # generates a wordmark, if there is no real logo
make doctor BRAND=<slug>       # confirms the pack is complete
```

## What to ask the user

Ask only for what you cannot infer. If they have a website, read its colours and
fonts first and confirm rather than interrogate.

1. **Colours** — at minimum a dark panel colour, a paper colour, and one accent.
   The other tokens have sensible fallbacks.
2. **Fonts** — a display face and a mono face. Google Fonts names work directly.
3. **Logo** — a PNG with transparency, light version. Without one the kit
   generates a wordmark.
4. **Links** — where does the reader go? A booking page, a payment link, a
   contact form. Each gets a name and becomes available to every campaign.
5. **Voice** — how they write. This is what stops the copy sounding generic.

## The colour tokens

They are semantic, not literal, so a template never mentions "navy":

| Token | Used for |
|---|---|
| `dark`, `dark2`, `dark3` | hero panels, CTA bars, price cards |
| `onDark`, `onDarkDim` | copy on those panels |
| `paper`, `paper2`, `rule` | page background, alternate bands, hairlines |
| `ink`, `body`, `muted` | headlines, body copy, fine print |
| `accent` | the bright accent — used on dark only |
| `accentInk` | the same accent, darkened enough to read on paper |
| `accentDeep`, `accentTint` | the pale callout block and its text |
| `highlight` | the eyebrow chip |

**`accent` and `accentInk` are different colours on purpose.** A bright accent
that sings on a dark panel usually fails contrast on white. `make verify` checks
all eight pairings against WCAG AA and tells you which one is short.

## CTA targets

```yaml
cta:
  primary: { label: "Book a call", url: "https://...", display: "acme.com/book" }
  buy:     { label: "Start today", url: "https://buy.stripe.com/...", display: "acme.com/start" }
```

Any URL works — payment link, booking page, form. Campaigns reference these by
name, so changing a link updates every piece that points at it.

`display` is how the URL reads in print; use a short human form, not the raw
tracking URL.

## Voice rules

Written into `brand.yaml` and followed when drafting copy. Be specific:

```yaml
voice:
  rules:
    - Lead with the reader's problem, not the offer's name.
    - Concrete nouns over adjectives. Name the actual task being removed.
  avoid:
    - leverage, unlock, seamless, cutting-edge
    - claims about clients or results that have not happened
```

Vague rules ("professional but friendly") change nothing. Rules that name banned
words and required structures change the output.
