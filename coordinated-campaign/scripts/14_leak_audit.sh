#!/usr/bin/env bash
# Label-leak audit of the simulator: every readable attribute alone vs ground truth, before and after the leak fixes;
# then the key worlds rerun with the fixes on.
source "$(dirname "$0")/_common.sh"
$PY eval/leak_audit.py --exps base r_all --out "$OUT_ROOT/leak_audit_before.json"
$PY eval/leak_audit.py --exps base r_all --set '{"leakfix": true}' --out "$OUT_ROOT/leak_audit_after.json"
O="$OUT_ROOT/stress_leakfix"
stress --exps base r_all r_all_spamouflage n_debunkers r_all_evasive_per_account --etas 0,0.3 --seeds 1,2,3 --timeout 900 --set '{"leakfix": true}' --out "$O" \
  --queries context_only forensic_only full full_self_consistent full_unreviewed_ok agent_eta0.2 agent_eta0.4 corepost
summ --dir "$O" --exps base r_all r_all_spamouflage n_debunkers r_all_evasive_per_account \
  --queries full full+amplifiers full_unreviewed_ok full_self_consistent agent_eta0.2 agent_eta0.4 corepost > "$O/summary.md"
