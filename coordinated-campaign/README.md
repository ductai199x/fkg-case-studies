# Coordinated-campaign case study (FKG, IEEE BIG)

A simulated case study showing that knowledge-graph queries, hand-written or written by an investigating agent, find a coordinated
manipulated-media campaign by joining Forensic Knowledge Graph (FKG) processing fingerprints with platform, fact-check and provenance
records, and an iterated failure hunt (attack the detector, fix it, attack again) under increasingly realistic simulated worlds.
**All accounts, posts, claims, images and forensic findings are synthetic.** The flood, the town (Brennerton) and every claim are fictional.

## Layout

| Path | What it holds |
|---|---|
| `ontology/` | FKG core vocabulary (`fkg-core.ttl`) and SHACL shapes (`fkg-shapes.ttl`) |
| `sim/generate.py` | Section 7.3 world: one campaign (naive or evasive operator) in an organic population, written as TriG with 4 named graphs + ground truth |
| `sim/stress.py` | Stress-test world: scale, several campaigns, adaptive operators, realism blocks (`R_PLATFORM`, `R_DETECTOR`, `R_CLAIMS`, `R_RECORDS`, `R_HABITS`), leak fixes, stance classifier; writes N-Quads |
| `sim/validate.py`, `sim/shacl_negative_test.py` | SHACL validation of a dataset, and a test that broken records are rejected |
| `queries/build_queries.py` | Builds the Section 7.3 detectors (`full`, `forensic_only`, `context_only`, ablations) and the amplifier template |
| `queries/build_stress_queries.py` | Builds the stress-test detectors in `queries/stress/` (open-world, stance-aware, one-operation, self-consistent, repost-tie, age-free amplifier hop) |
| `agent/` | Agent-written detectors: schema card the agent was given, each run's investigation log, numbered exploratory queries and final detector (frozen outputs) |
| `eval/run_eval.py` | Scores detectors on `sim/generate.py` worlds (account-level P/R/F1) |
| `eval/run_stress.py`, `eval/stress_grid.py` | Generates and scores named stress experiments; one JSON row per world x detector in `<out>/<exp>.jsonl` |
| `eval/summarize_stress.py`, `eval/union_scores.py`, `eval/ttd_active.py` | Tables: mean metric per experiment x detector; unions of detectors; early detection against accounts already active |
| `sim/waves.py` | Long-horizon world: a news event every 4 weeks, operators that run one wave per event with fresh personas and drifting presets, persistent benign actors (brands, a fan group, debunkers), takedown reports (operator + removed accounts) published with a lag; every record is timestamped so a snapshot as of T is a prefix of one fixed set of observations |
| `eval/run_waves.py`, `eval/waves_grid.py`, `eval/summarize_waves.py` | Per event: windowed detectors, cross-wave TTP edges (`queries/waves/sig_edges.rq.tmpl`), attribution by one hop or chained through earlier waves, baselines (account overlap, co-repost, narrative, posting time), fusion; growth runs with `--scaling` |
| `eval/leak_audit.py` | Scores every readable attribute alone against the labels (balanced accuracy) to find leaks the generator wrote in |
| `eval/sensitivity.py`, `eval/exemplar.py`, `eval/behavioral.py`, `eval/two_stage.py` | Threshold sensitivity; one exemplar FKG record; co-repost baseline (after Pacheco et al.); two-stage evaluation of the joined query |
| `scripts/` | One script per result (below) |
| `data/`, `truth/`, `data_evasive/`, `truth_evasive/` | Section 7.3 worlds (8 noise levels x 5 seeds) and labels; not committed (about 160 MB), regenerate with `scripts/01_original_data.sh` or `make campaign` from the repository root |
| `results/` | Checked-in results the paper quotes |

## Environment

Python 3.13 with `rdflib 7.6.0`, `pyoxigraph 0.5.13`, `pyshacl 0.40.1`, locked in the repository's `uv.lock`: run `uv sync` at
the repository root once, then the scripts here use `uv run python` (override with `PY=...`).
Stress worlds are written to `$STRESS_SCRATCH` (default: the system temp folder) and deleted after scoring. Every generator is seeded,
so a rerun gives the same worlds and scores; `scripts/00_smoke.sh` checks this against the checked-in files.

## Reproducing each result

Scripts write under `$OUT_ROOT` (default `repro/`), so `results/` stays as published and can be diffed against a rerun.
`WORKERS` sets parallel worlds (default 3). The original-study scripts take minutes; each stress iteration takes hours.

| Script | Result (doc section) | Output under `$OUT_ROOT` |
|---|---|---|
| `00_smoke.sh` | Environment and determinism check | `smoke/` |
| `01_original_data.sh` | Section 7.3 worlds + SHACL checks | `data/`, `truth/`, `data_evasive/`, `truth_evasive/` |
| `02_original_eval.sh` | Section 7.3 tables: hand-written and agent-written detectors, naive and evasive operators | `original/*.json`, `*.md` |
| `03_sensitivity_exemplar.sh` | Threshold sensitivity; exemplar record listing | `original/sensitivity.json`, `exemplar_record.trig` |
| `10_stress_iter1.sh` | Iteration 1: parameter jitter, operation order, generator mix, evasive operator | `stress/iter1_summary.md` |
| `11_stress_iter2.sh` | Iteration 2: 3x to 30x population, several campaigns | `stress/iter2_summary.md` |
| `12_stress_iter3.sh` | Iteration 3: realism blocks alone and together | `stress/iter3_summary.md` |
| `13_stress_iter4.sh` | Iteration 4: adversarial and organic-noise attacks; time to detect | `stress/iter4_summary.md` |
| `14_leak_audit.sh` | Leak audit before and after the fixes; key worlds rerun | `leak_audit_*.json`, `stress_leakfix/summary.md` |
| `15_stress_iter5.sh` | Iteration 5 (Table 7.6): stance-aware and one-operation detectors, ensembles, held-out seeds 4 to 6 | `stress/i5f_*.md`, `stress_fresh/*.md` |
| `16_stress_iter6.sh` | Iteration 6: repost ties, age-free amplifier hop, operator without ties, early detection vs active accounts, unions | `stress6/*.md` |
| `20_waves.sh` | Long horizon (7.8): months of events, one wave per event with full persona turnover, preset drift, takedown reports; cross-wave attribution vs baselines; growth runs | `waves/`, `waves_heldout/`, `waves_growth/` |
| `run_all.sh` | All of the above in order | |

Notes. The agent-written detectors are frozen outputs of the agent runs; the scripts score them but do not re-run the agent.
Iteration 5 was first run with fact-check coverage drawn from the shared world stream (`i5_*`, `results/stress/iter5.log`); that
coupling is a bug the doc describes, and every reported number uses the per-claim draw (`i5f_*`). In iteration 6 the repost-tie
detector was designed after looking at seed 1, so `unions.md` also reports seeds 2 to 6.

### Long-horizon study (`20_waves.sh`)

The question is whether FKG queries can tie a new campaign wave to the operator behind earlier waves after every account has been
replaced. Each event is evaluated 96 h after it starts against the KG as it stood then. `sig_edges` pairs window posts that carry a
synthetic image and an unrefuted claim with images of accounts that a takedown report names, or that an earlier evaluation flagged,
when the generator matches (or, in the `any_gen` form, regardless of generator) and at least two operations agree within 15 %.
A direct label takes the takedown operator one hop away; a chained label follows these edges back through earlier flagged accounts.
Query plans matter here: building per-side (image, generator, operation, value) tables in subqueries and joining them took the
windowed TTP join from 234 s to 1.7 s on a 204K-quad snapshot with the same rows.
