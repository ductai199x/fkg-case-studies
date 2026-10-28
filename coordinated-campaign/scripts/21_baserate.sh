#!/usr/bin/env bash
# Base-rate study (doc section 7.8): benign look-alike coordination (fan groups, brand cause-marketing, news syndication)
# added on top of the long-horizon base world, a noise-only control, then the style-tenure filter and a persona warm-up
# counterattack in worlds with four months of platform history. w_base itself comes from 20_waves.sh.
source "$(dirname "$0")/_common.sh"
$PY eval/run_waves.py --exps w_look1 w_look3 w_look10 w_look30 w_base_noise --etas 0,0.3 --seeds 1,2,3 --workers "$WORKERS" --fresh --out "$OUT_ROOT/waves_baserate"
$PY eval/run_waves.py --exps w_br0 w_br10 w_br30 w_br30_warm --etas 0,0.3 --seeds 1,2,3 --workers "$WORKERS" --fresh --out "$OUT_ROOT/waves_baserate_t"
B="$OUT_ROOT/waves_baserate"; T="$OUT_ROOT/waves_baserate_t"
$PY eval/summarize_baserate.py --json "$B/curve.json" --points w_base="$OUT_ROOT/waves/w_base.jsonl" w_base_noise="$B/w_base_noise.jsonl" \
  w_look1="$B/w_look1.jsonl" w_look3="$B/w_look3.jsonl" w_look10="$B/w_look10.jsonl" w_look30="$B/w_look30.jsonl" > "$B/summary.md"
$PY eval/summarize_baserate.py --json "$T/curve.json" --points w_br0="$T/w_br0.jsonl" w_br10="$T/w_br10.jsonl" w_br30="$T/w_br30.jsonl" w_br30_warm="$T/w_br30_warm.jsonl" > "$T/summary.md"
