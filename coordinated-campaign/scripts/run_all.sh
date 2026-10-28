#!/usr/bin/env bash
# Every result in order. Roughly a day on 4 cores; the stress iterations dominate. Override WORKERS, OUT_ROOT.
set -euo pipefail; D="$(dirname "$0")"
for s in 00_smoke 01_original_data 02_original_eval 03_sensitivity_exemplar 10_stress_iter1 11_stress_iter2 12_stress_iter3 13_stress_iter4 14_leak_audit 15_stress_iter5 16_stress_iter6 20_waves 21_baserate; do
  echo "== $s"; bash "$D/$s.sh"; done
