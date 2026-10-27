#!/usr/bin/env bash
# Iteration 3: realism blocks (platform, detector, claims, records, habits), alone and together.
source "$(dirname "$0")/_common.sh"
O="$OUT_ROOT/stress"; $PY queries/build_stress_queries.py
stress --exps r_base_scale3 r_platform r_detector r_claims r_records r_habits r_all r_all_spamouflage r_all_evasive_per_account --etas 0,0.3 --seeds 1,2,3 --timeout 900 --out "$O" \
  --queries context_only forensic_only full full_no_provenance full_heavy_processing full_self_consistent full_unreviewed_ok agent_eta0.2 agent_eta0.4 corepost
summ --dir "$O" --exps r_base_scale3 r_platform r_detector r_claims r_records r_habits r_all r_all_spamouflage r_all_evasive_per_account \
  --queries full full+amplifiers full_unreviewed_ok full_self_consistent forensic_only context_only agent_eta0.2 agent_eta0.4 corepost > "$O/iter3_summary.md"
