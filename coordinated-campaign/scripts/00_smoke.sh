#!/usr/bin/env bash
# Two-minute environment check: one stress world, three detectors, plus SHACL validation of one original dataset.
source "$(dirname "$0")/_common.sh"
$PY -c "import rdflib, pyoxigraph, pyshacl; print('rdflib', rdflib.__version__, 'pyoxigraph', pyoxigraph.__version__, 'pyshacl', pyshacl.__version__)"
$PY sim/generate.py --etas 0.0 --seeds 1 --out "$OUT_ROOT/smoke/data" --truth "$OUT_ROOT/smoke/truth"
$PY sim/validate.py "$OUT_ROOT/smoke/data/eta_0.0/seed_0/dataset.trig"
cmp -s "$OUT_ROOT/smoke/truth/eta_0.0/seed_0.json" truth/eta_0.0/seed_0.json && echo "generator deterministic: truth matches checked-in truth/" || echo "WARNING: regenerated truth differs from truth/"
WORKERS=1 stress --exps base --etas 0 --seeds 1 --queries full open_stance agent_eta0.2 --out "$OUT_ROOT/smoke/stress"
