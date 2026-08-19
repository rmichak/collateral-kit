# collateral-kit — one command per step, and one that does all of them.
#
#   make setup                      once per machine
#   make doctor BRAND=_example      check everything is installed
#   make brand BRAND=acme           scaffold a new brand pack
#   make campaign SLUG=x BRAND=y    images -> HTML -> PDF -> social -> proofs -> verify
#   make index BRAND=y              rebuild the campaign index and review board

PY      := .venv/bin/python
RUN     := PYTHONPATH=scripts $(PY)
BRAND   ?= _example
SLUG    ?= example-retainer
PROVIDER?=            # e.g. PROVIDER=placeholder to skip the image API

.PHONY: setup doctor brand fonts lockup images build pdf social proof verify index campaign demo clean help

help:
	@sed -n '2,8p' Makefile | sed 's/^# \{0,1\}//'

setup:
	@command -v uv >/dev/null 2>&1 \
		&& uv venv .venv && uv pip install -r requirements.txt --python .venv/bin/python \
		|| (python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt)
	npm install --no-fund --no-audit
	@echo "\nsetup complete. Next: make doctor BRAND=$(BRAND)"

doctor:
	@$(RUN) scripts/doctor.py --brand $(BRAND)

brand:
	@$(RUN) scripts/new_brand.py $(BRAND)

fonts:
	@$(RUN) scripts/fetch_fonts.py $(BRAND)

lockup:
	@$(RUN) scripts/make_lockup.py $(BRAND)

images:
	@$(RUN) scripts/gen_images.py $(SLUG) --brand $(BRAND) $(if $(PROVIDER),--provider $(PROVIDER),)

build:
	@$(RUN) scripts/build_page.py $(SLUG) --brand $(BRAND)

pdf:
	@node scripts/render_pdf.mjs campaigns/$(SLUG)/$(SLUG)-onepager.html campaigns/$(SLUG)/$(SLUG)-brochure.html

social:
	@$(RUN) scripts/social_card.py $(SLUG) --brand $(BRAND)

proof:
	@node scripts/proof.mjs campaigns/$(SLUG)/$(SLUG)-onepager.html campaigns/$(SLUG)/$(SLUG)-brochure.html --scale 1

verify:
	@$(RUN) scripts/verify.py $(SLUG) --brand $(BRAND)

index:
	@$(RUN) scripts/build_index.py --brand $(BRAND)

# The whole pipeline. `verify` is last and non-fatal here so you still get the
# proofs to look at; run `make verify` on its own for the exit code.
campaign: images build pdf social proof index
	@$(RUN) scripts/verify.py $(SLUG) --brand $(BRAND) || true
	@echo "\nOpen the board: file://$(PWD)/campaigns/_index/review-board.html"

# Fonts are fetched, never committed — a licensed face is not ours to
# redistribute. The demo pulls them first so a fresh clone works in one step.
demo: fonts
	@$(MAKE) campaign SLUG=example-retainer BRAND=_example PROVIDER=placeholder

clean:
	@rm -rf campaigns/*/proof campaigns/_index
	@find campaigns -name '*.html' -o -name '*.pdf' | xargs rm -f 2>/dev/null || true
	@echo "cleaned build output (assets and campaign.yaml kept)"
