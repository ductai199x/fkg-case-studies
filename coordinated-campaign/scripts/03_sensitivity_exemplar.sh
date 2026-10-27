#!/usr/bin/env bash
# Threshold sensitivity of the joined query (27 settings x 3 noise levels) and the exemplar FKG record listing.
source "$(dirname "$0")/_common.sh"
if [ -d "$OUT_ROOT/data" ]; then export FKG_DATA="$OUT_ROOT/data" FKG_TRUTH="$OUT_ROOT/truth"; fi
mkdir -p "$OUT_ROOT/original"
$PY eval/sensitivity.py "$OUT_ROOT/original/sensitivity.json"
$PY eval/exemplar.py "$OUT_ROOT/original/exemplar_record.trig" > /dev/null
