# Named long-horizon experiments (sim/waves.py): name -> make_wave_cfg keyword arguments. All use the realism blocks
# of the stress tests (R_ALL), the leak fixes, the stance classifier and the per-claim fact-check draw.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from stress_grid import R_ALL
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sim"))
from waves import OPERATOR, OP_B
W = {"scale": 3, **R_ALL}
ops = lambda a={}, b={}: [{**OPERATOR, **a}, {**OP_B, **b}]
WEXPS = {
    # two operators, six events four weeks apart, full persona turnover, 5 % parameter drift and a 15 % chance of a tool change per wave
    "w_base": dict(W),
    # attacks on the cross-wave link, and on the baselines
    "w_shared_narrative": {**W, "operators": ops({"themes": ["sabotage", "elite"]})},          # both push the same narratives
    "w_scheduler": {**W, "operators": ops({"hours": None}, {"hours": None})},                   # scheduling tools: no shift pattern
    "w_drift_high": {**W, "op": {"drift": 0.15, "p_swap": 0.3}},                               # faster preset drift and more tool changes
    "w_gen_switch": {**W, "op": {"p_gen_switch": 0.4}},                                        # a new generator in 40 % of waves
    "w_slow_takedown": {**W, "p_takedown": 0.5, "takedown_lag_d": 70.0},                       # fewer, later takedown reports
    "w_per_persona": {**W, "op": {"param_mode": "per_account"}},                               # a fresh random pipeline per persona and wave
    "w_mimic": {**W, "operators": ops({}, {"mimic": True})},                                   # operator B uses the most popular app preset
    "w_shared_kit": {**W, "operators": ops({}, {"gen": "FLUX.1 [dev]", "kit": OPERATOR["kit"]})},  # both buy the same generator and toolkit
}
# growth: a year of events, and a 10x population, to measure precision and query time as the graph grows
WEXPS["w_long"] = {**W, "n_events": 12, "end": (2027, 4, 1)}
WEXPS["w_long_scale10"] = {**W, "scale": 10, "n_events": 12, "end": (2027, 4, 1)}
# base rate: m extra groups each of fans, brand agencies (with cause marketing at events) and news syndicators on top of w_base
for m in (1, 3, 10, 30): WEXPS[f"w_look{m}"] = {**W, "lookalike": m}
WEXPS["w_base_noise"] = {**W, "obs_salt": 1}  # control: w_base's world with a fresh draw of observation noise
# counter to the style-tenure filter: operators warm personas up by posting the wave's kit style weekly for 60 days first
WEXPS["w_look30_warm"] = {**W, "lookalike": 30, "op": {"warm_d": 60}}
WEXPS["w_warm"] = {**W, "op": {"warm_d": 60}}
# the base-rate sweep with the style-tenure filter: four months of platform history before the first event (start Jan 1)
BR = {**W, "start": (2026, 1, 1)}
for m in (0, 1, 3, 10, 30): WEXPS[f"w_br{m}"] = {**BR, "lookalike": m}
WEXPS["w_br0_warm"] = {**BR, "op": {"warm_d": 60}}
WEXPS["w_br30_warm"] = {**BR, "lookalike": 30, "op": {"warm_d": 60}}
