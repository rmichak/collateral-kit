---
name: collateral-brochure
description: Use when the user wants a multi-page print brochure, booklet, or long-form PDF for an offer. Triggers on "brochure", "print piece", "booklet", "multi-page", "the full version", "something to mail", "printed handout".
---

# Brochures

Full-bleed letter pages: a cover that is one image and one promise, interior
pages that each make a single argument, and a closing page that is nothing but
the next step and its QR codes.

```bash
make build SLUG=<slug> BRAND=<brand>
make pdf   SLUG=<slug>
make proof SLUG=<slug>      # one PNG per page — look at all of them
```

## Page order that works

1. **Cover** — automatic. The image and the headline, nothing else.
2. **What you get** — `feature-spread`, four points in two columns, plus an image.
3. **How it works** — `steps`, three or four numbered stages. This is the page
   that removes the reader's fear of starting.
4. **What it costs** — `price`, with what is included and what is quoted separately.
5. **Proof or gallery** — only if there is something real to show.
6. **Closing** — automatic. The next step, the QRs, the wordmark.

Six pages is the natural length. Fewer than four and it should have been a
one-pager; more than eight and nobody finishes it.

## Layouts

Set `layout:` per page. Every layout also accepts an `image:` key, and the figure
expands to absorb whatever height is left over — that is the fix for a page that
reads half-empty.

- `feature-spread` — two-column grid of kicker + title + body
- `steps` — auto-numbered sequence, `01 02 03`
- `price` — feature list beside the price card and aside
- `proof` — a large pull quote on a dark panel, plus optional supporting points
- `gallery` — two captioned images

## Copy discipline across pages

Each page gets **one** job. The most common failure is a brochure where pages 2,
3 and 4 all argue the same thing in different words. Read the page titles in
sequence: they should form a sentence that moves.

The `intro` paragraph under each title is where the argument lives; the grid
below it is evidence. If the intro is missing, the page is a list with no point.

## Before it goes to a printer

```bash
make verify SLUG=<slug> BRAND=<brand>
python3 scripts/verify.py <slug> --brand <brand> --check-urls
```

`--check-urls` requests every CTA and QR target. Do this every time. A QR
printed to a 404 is the one defect that cannot be fixed after the fact.

Also confirm on the proofs: no text within 0.4in of a trim edge, the cover
headline readable at thumbnail size, and page numbers continuous.
