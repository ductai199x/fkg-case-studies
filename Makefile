# Reproduce every result in the report. Each target regenerates its synthetic world from a fixed seed, then runs and scores the queries.
PY ?= uv run python
.PHONY: all setup check validate cs1 cs2 cs3 catalog sweep audit agents campaign campaign-agents campaign-stress figures docs clean
all: validate cs1 cs2 cs3 catalog campaign figures

setup:            ## create .venv with the locked dependencies (uv.lock)
	uv sync
validate:         ## SHACL-validate the three single-image-centred worlds
	cd _shared && $(PY) validate.py
cs1:              ## recycled out-of-context media
	cd cs1_recycled_media && $(PY) generate.py && $(PY) run.py
cs2:              ## lineage, patient zero, laundering, hidden platform hop
	cd cs2_lineage_laundering && $(PY) generate.py && $(PY) run.py
cs3:              ## materiality, credentials, intent, detector audits
	cd cs3_intent_materiality && $(PY) generate.py && $(PY) run.py
heldout:          ## fresh-seed worlds used to score the agents (seed 101, eta 0.2 for CS1/CS3)
	cd cs1_recycled_media && FKG_SEED=101 FKG_ETA=0.2 FKG_DATA=heldout $(PY) generate.py
	cd cs2_lineage_laundering && FKG_SEED=101 FKG_DATA=heldout $(PY) generate.py
	cd cs3_intent_materiality && FKG_SEED=101 FKG_ETA=0.2 FKG_DATA=heldout $(PY) generate.py
catalog:          ## run the 18-use-case catalog sketches
	cd _catalog && $(PY) check.py
sweep:            ## noise sweep: 5 seeds x 5 noise rates (CS1, CS3) and 10 seeds (CS2); about 10 minutes
	$(PY) robustness.py 5
audit:            ## label-leak audit of the CS1-CS3 generators
	cd _audit && $(PY) leak_audit.py .. after.json
agents:           ## rescore every stored agent answer set on default and held-out worlds (slow: one lineage query takes ~10 min)
	cd agent_eval && for s in hand A1 A2 B1 B2 B1r B2r; do d=$$s; [ $$s != hand ] && d=agents/$$s; \
	  EVAL_DATA=data SCORE_TIMEOUT=900 SCORES_OUT=scores_$$s.json $(PY) score.py $$d; \
	  EVAL_DATA=heldout SCORE_TIMEOUT=900 SCORES_OUT=heldout_scores_$$s.json $(PY) score.py $$d; done; $(PY) table.py
campaign:         ## CS4 coordinated campaign: generate 8 noise levels x 5 seeds (plus evasive variant), score hand-written queries
	cd coordinated-campaign && $(PY) sim/generate.py --etas 0,0.1,0.2,0.3,0.4,0.5,0.7,1.0 --seeds 5 \
	  && $(PY) sim/generate.py --etas 0,0.1,0.2,0.3,0.4,0.5,0.7,1.0 --seeds 5 --behavior evasive --out data_evasive --truth truth_evasive \
	  && $(PY) queries/build_queries.py && $(PY) eval/run_eval.py
campaign-stress:  ## CS4 stress tests (attackers, scale, realism); pass EXPS="base scale_3 ..." (names in eval/stress_grid.py); long
	cd coordinated-campaign && $(PY) eval/run_stress.py --exps $(EXPS)
check:            ## audit every SPARQL query and check the reported numbers (uv run pytest, a few minutes)
	uv run pytest -q
figures:          ## redraw figures/ from the stored results
	$(PY) scripts/make_figures.py
docs:             ## vector figures plus docs/report.pdf and docs/summary.pdf (needs a TeX Live install with latexmk)
	$(PY) scripts/make_paper_figures.py
	cd docs && latexmk -pdf -interaction=nonstopmode report.tex summary.tex && latexmk -c report.tex summary.tex
clean:
	find . -name __pycache__ -prune -exec rm -rf {} +; rm -rf .stress_worlds
help:
	@grep -E '^[a-z-]+:.*##' Makefile | sed 's/:.*##/\t/'
