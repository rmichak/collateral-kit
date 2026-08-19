# collateral-kit

Repeatable, brand-agnostic marketing collateral: print brochures, one-pagers,
Facebook / X / Instagram cards and their captions — generated from two YAML
files and rendered by headless Chrome.

Built as a Claude Code plugin, so the skills, scripts and templates travel
together and install with one command. The scripts also run standalone if you
would rather use the `make` targets directly.

---

## What it produces

For one offer, one command produces:

- a multi-page full-bleed **brochure** PDF
- a single-page **one-pager** PDF
- **social cards** at 2048², 1600×900 or 1080×1350, with captions beside them
- **QR codes** pointing at whatever URLs the brand defines
- a **proof sheet** — one PNG per page, for looking at before shipping
- a **campaign index** and a **review board** with approve / refresh / reject / retire

Everything lands in `campaigns/<slug>/`, self-contained: fonts, images and QRs
are staged inside the folder, so it can be zipped and sent to a printer as-is.

---

## Install

### As a Claude Code plugin

```
/plugin marketplace add rmichak/collateral-kit
/plugin install collateral-kit
```

Then just ask: *"make me a one-pager for the care plan offer"*.

### Standalone

```bash
git clone git@github.com:rmichak/collateral-kit.git
cd collateral-kit
make setup                    # venv + python deps + puppeteer-core
make doctor BRAND=_example    # tells you exactly what is missing, if anything
make demo                     # fetches fonts, builds the shipped example end to end
```

`make demo` finishes with one deliberate failure — it builds with placeholder
imagery, and `verify.py` refuses to pass placeholder art. That is the gate
working. Configure an image provider, or supply your own files, and it clears.

**Fonts are fetched, not committed.** A licensed typeface is not ours to
redistribute, so `brands/*/assets/fonts/` is gitignored and
`make fonts BRAND=<brand>` pulls the faces named in `brand.yaml` from Google
Fonts on first use.

---

## What has to be installed

`make doctor` checks every one of these and prints the fix for anything missing.

| Requirement | Why | Install |
|---|---|---|
| Python 3.10+ | the builders | preinstalled on macOS/Linux |
| jinja2, PyYAML, Pillow, fontTools, brotli, qrcode, jsonschema | templating, compositing, fonts, QRs, validation | `make setup` |
| Node 20+ | drives headless Chrome | `brew install node` |
| puppeteer-core | HTML → PDF and page rasters | `make setup` |
| **Chrome or Chromium** | the actual PDF engine | Google Chrome, or set `CHROME_PATH` |

No paid service is needed to produce a brochure. One is only needed to
**generate imagery**, and even that is optional:

| Provider | Set | Notes |
|---|---|---|
| Higgsfield | `higgsfield auth login` | uses `gpt_image_2` at 2k |
| OpenAI | `OPENAI_API_KEY` | `gpt-image-1` |
| Replicate | `REPLICATE_API_TOKEN` | FLUX by default |
| manual | `images.provider: manual` | you supply the files |

Tried in that order when `images.provider: auto`. With none configured the kit
renders flat brand-coloured placeholders — enough to check a layout, and
`verify.py` refuses to let one ship.

---

## The two files

Everything else is machinery. These are the only files you edit.

### `brands/<brand>/brand.yaml` — once per brand

Colours as **semantic tokens** (`dark`, `paper`, `accent`, `accentInk`…), fonts
by Google Fonts name, wordmark paths, named CTA URLs, and voice rules. A rebrand
is this file and nothing else.

```yaml
colors:
  dark: "#0B1A14"
  paper: "#FBFAF7"
  accent: "#4ADE9B"      # bright — used on dark panels
  accentInk: "#0F7A52"   # the same accent, dark enough to read on paper
cta:
  primary: { label: "Book a call", url: "https://acme.com/book", display: "acme.com/book" }
```

### `campaigns/<slug>/campaign.yaml` — once per offer

Headline, feature rows, price block, brochure page structure, image prompts,
social cards and captions.

```yaml
hero:
  headline: Your site should not be
  headline_accent: your problem to babysit.
price:
  mode: card              # card | negotiable | none
  amount: "$185"
  label: per month
```

---

## Commands

```bash
make setup                          # once per machine
make doctor BRAND=acme              # check the install and a brand pack
make brand  BRAND=acme              # scaffold a new brand pack
make fonts  BRAND=acme              # pull its Google Fonts, pin static instances
make lockup BRAND=acme              # generate a wordmark if there is no logo

python3 scripts/new_campaign.py care-plan --title "Care Plan"

make campaign SLUG=care-plan BRAND=acme    # the whole pipeline
make index    BRAND=acme                   # rebuild the index and review board
```

`make campaign` runs: images → HTML → PDF → social → proofs → index → verify.

Individual steps: `make images`, `build`, `pdf`, `social`, `proof`, `verify`.

---

## The quality gates

`scripts/verify.py` fails the build on things that are expensive to catch late:

- an image below the resolution its destination needs
- placeholder art still listed in `CREDITS.txt`
- an asset with no provenance entry
- a caption over the platform's character limit
- any of eight brand colour pairings below WCAG AA contrast
- a PDF small enough that the render clearly failed
- with `--check-urls`: **any CTA or QR target that does not resolve**

That last one matters most. A wrong web page is a one-minute fix; a wrong QR on
500 printed sheets is not.

Nothing automated can tell you whether the picture is any good. `make proof`
writes a PNG per page precisely so that looking at them is cheap enough to
actually do.

---

## Design decisions worth knowing

**Semantic colour tokens, not literal names.** Templates never say "navy". They
say `--dark`. That is what makes a brand swap a config change.

**`accent` and `accentInk` are separate.** A bright accent that works on a dark
panel almost never passes contrast on white. Keeping both, and checking both,
prevents the most common rebrand failure.

**Variable fonts are pinned.** Google increasingly serves one variable file for
every requested weight. Browsers resolve the axis; PIL does not, so every social
headline would silently render at 400. `fetch_fonts.py` instantiates real static
TTFs at each weight.

**Campaign folders are self-contained.** Fonts, wordmarks, images and QRs are
staged inside `campaigns/<slug>/`, and every path in the HTML is relative.

**Optional fields are safe to omit.** Templates run under `StrictUndefined` so a
mistyped *template* variable fails loudly, while absent *campaign* fields
resolve to a falsy blank.

---

## Repository layout

```
.claude-plugin/     plugin + marketplace manifests
skills/             the eight skills (router, brand, campaign, onepager,
                    brochure, social, images, review)
scripts/            kit.py, build_page, render_pdf, social_card, gen_images,
                    verify, build_index, fetch_fonts, make_lockup, doctor
templates/          jinja2 print templates + index/review-board
schema/             JSON Schema for brand.yaml and campaign.yaml
brands/_example/    a fictional brand, so the repo is self-testing
campaigns/          output (gitignored, except the shipped example)
```

## Your brands stay yours

`.gitignore` excludes `brands/*` and `campaigns/*` by default — only the
fictional `_example` brand and its demo campaign are tracked. Client palettes,
logos, prices, URLs and artwork stay on your machine unless you deliberately
add them. Keep it that way: a brand pack holds a client's pricing and links.

## Licence

MIT. See [LICENSE](LICENSE).

Bundled dependencies keep their own licences: puppeteer-core (Apache-2.0),
Jinja2 / Pillow / fontTools / PyYAML / qrcode / jsonschema (BSD- or
MIT-style). Fonts are downloaded at build time from Google Fonts under their
own terms and are never redistributed by this repository.
