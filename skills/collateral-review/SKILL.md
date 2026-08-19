---
name: collateral-review
description: Use when the user wants to review, approve, reject or revise collateral, or hands back a review digest. Triggers on "review the pieces", "let me look at these", "review board", "here's my digest", "approve", "these need another pass", "what have we built".
---

# Review and revision

Two static pages, rebuilt from whatever is currently built:

```bash
make index BRAND=<brand>
```

- `campaigns/_index/campaign-kit.html` — what exists, what each piece is for, where it lives.
- `campaigns/_index/review-board.html` — the decision surface.

Open the board with `file://` — no server needed.

## How the board works

Every asset gets a card showing the piece, its **purpose** and its **audience**
(both from `campaign.yaml`), four statuses — approve / refresh / reject / retire —
a notes box, and **⤢ Larger** for a full-screen look. Clicking a status again
unsets it.

Notes save to `localStorage` as they are typed. Nothing is uploaded.

**Copy digest for Claude** puts a markdown summary on the clipboard. That is
what the user pastes back into the chat.

When a piece is rebuilt, the board notices the file changed and clears its
verdict on next open — but keeps the note that prompted the rebuild. A stale
approval on a changed file is worse than no approval.

## Processing a digest

When the user pastes one back, work through it in this order:

1. **Refresh** — apply each note. Ask a follow-up if a note is ambiguous rather
   than guessing; a wrong interpretation costs a whole rebuild cycle.
2. **Reject** — delete the files. A rejected piece left on disk gets shipped by
   accident six weeks later.
3. **Retire** — move to `campaigns/<slug>/retired/`. Keep it, stop showing it.
4. **Approve** — set `status: approved` in that campaign's `campaign.yaml`.
5. Rebuild, then `make index BRAND=<brand>` so the board matches reality.
6. Tell the user plainly what changed, what was deleted, and what still needs an
   answer.

Never mark something approved that the user did not approve, and never quietly
skip a refresh note because it was hard to interpret. Say so instead.

## Purpose and audience

These come from the campaign's `purpose:` and `audience:` fields. Fill them in
when the campaign is written — a card with `—` in both slots gives the reviewer
nothing to judge against, and they end up reviewing the design instead of the
decision.
