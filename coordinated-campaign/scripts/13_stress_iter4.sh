#!/usr/bin/env bash
# Iteration 4: adversarial and organic-noise attacks on the realistic world, and time-to-detect cuts.
source "$(dirname "$0")/_common.sh"
O="$OUT_ROOT/stress"; $PY queries/build_stress_queries.py
stress --exps r_all_fc_full n_mimic_preset n_debunkers n_name_drift n_name_drift_vocab n_sleeper n_low_volume ttd_6h ttd_12h ttd_24h ttd_48h ttd_96h ttd_168h --etas 0,0.3 --seeds 1,2,3 --timeout 900 --out "$O" \
  --queries context_only forensic_only full full_no_provenance full_self_consistent full_unreviewed_ok full_entity agent_eta0.2 agent_eta0.4 corepost
summ --dir "$O" --exps r_all_fc_full n_mimic_preset n_debunkers n_name_drift n_name_drift_vocab n_sleeper n_low_volume ttd_6h ttd_12h ttd_24h ttd_48h ttd_96h ttd_168h \
  --queries full full+amplifiers full_unreviewed_ok full_self_consistent full_entity context_only agent_eta0.2 agent_eta0.4 corepost > "$O/iter4_summary.md"
