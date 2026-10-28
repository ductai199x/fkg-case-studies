#!/usr/bin/env bash
# Long-horizon study (doc section 7.8): months of activity, one campaign wave per event, full persona turnover, preset drift,
# takedown reports with a lag. Attack grid on seeds 1-3, held-out seeds 4-6, then growth runs (a year of events, 10x population).
source "$(dirname "$0")/_common.sh"
W="w_base w_shared_narrative w_scheduler w_drift_high w_gen_switch w_slow_takedown w_per_persona w_mimic w_shared_kit"
$PY eval/run_waves.py --exps $W --etas 0,0.3 --seeds 1,2,3 --workers "$WORKERS" --fresh --out "$OUT_ROOT/waves"
$PY eval/run_waves.py --exps w_base w_gen_switch w_shared_kit --etas 0,0.3 --seeds 4,5,6 --workers "$WORKERS" --fresh --out "$OUT_ROOT/waves_heldout"
$PY eval/run_waves.py --exps w_long --etas 0 --seeds 1 --workers 1 --scaling --timeout 1800 --naive-timeout 1800 --fresh --out "$OUT_ROOT/waves_growth"
$PY eval/run_waves.py --exps w_long_scale10 --etas 0 --seeds 1 --workers 1 --scaling --timeout 1800 --naive-timeout 300 --out "$OUT_ROOT/waves_growth"
$PY eval/summarize_waves.py --dir "$OUT_ROOT/waves_growth" --exps w_long > "$OUT_ROOT/waves_growth/summary.md"
$PY eval/summarize_waves.py --dir "$OUT_ROOT/waves" --exps $W > "$OUT_ROOT/waves/summary.md"
$PY eval/summarize_waves.py --dir "$OUT_ROOT/waves_heldout" --exps w_base w_gen_switch w_shared_kit > "$OUT_ROOT/waves_heldout/summary.md"
