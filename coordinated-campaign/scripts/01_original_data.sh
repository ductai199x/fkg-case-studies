#!/usr/bin/env bash
# Section 7.3 worlds: 8 noise levels x 5 seeds, naive and evasive operators, then SHACL checks (positive and negative).
source "$(dirname "$0")/_common.sh"
$PY queries/build_queries.py
$PY sim/generate.py --etas 0,0.1,0.2,0.3,0.4,0.5,0.7,1.0 --seeds 5 --out "$OUT_ROOT/data" --truth "$OUT_ROOT/truth"
$PY sim/generate.py --behavior evasive --etas 0,0.1,0.2,0.3,0.4,0.5,0.7,1.0 --seeds 5 --out "$OUT_ROOT/data_evasive" --truth "$OUT_ROOT/truth_evasive"
for e in 0.0 0.5; do $PY sim/validate.py "$OUT_ROOT/data/eta_$e/seed_0/dataset.trig"; done
$PY sim/shacl_negative_test.py
