# Named stress-test experiments: name -> make_cfg keyword arguments.
EXPS = {
    # iteration 0: sanity, the v2 world rebuilt by the stress generator
    "base": {},
    # iteration 1: adaptive attacker that varies editing parameters per image
    "jitter_10": {"campaign": {"param_mode": "jitter", "jitter": 0.10}},
    "jitter_20": {"campaign": {"param_mode": "jitter", "jitter": 0.20}},
    "jitter_40": {"campaign": {"param_mode": "jitter", "jitter": 0.40}},
    "uniform_params": {"campaign": {"param_mode": "uniform"}},
    "op_pool": {"campaign": {"param_mode": "pool"}},
    "per_account": {"campaign": {"param_mode": "per_account"}},
    "op_shuffle": {"campaign": {"op_shuffle": True}},
    "gen_mix3": {"campaign": {"gens": ["FLUX.1 [dev]", "Midjourney v7", "SDXL"]}},
    "pool_genmix": {"campaign": {"param_mode": "pool", "gens": ["FLUX.1 [dev]", "Midjourney v7", "SDXL"]}},
}

# iteration 2: scale (organic population and brand campaigns x k; campaign stays 12 accounts) and concurrent campaigns
CAMP_B = {"gens": ["Midjourney v7"], "chain": [("GaussianBlur", 1.40), ("Sharpening", 0.60)], "claims": ["C4", "C5"], "start": (2026, 10, 4, 12)}
CAMP_C = {"gens": ["SDXL"], "chain": [("Resampling", 1.25), ("GaussianNoise", 2.10), ("Sharpening", 1.10)], "claims": ["C6"], "start": (2026, 10, 2, 0)}
CAMP_D = {"gens": ["Seedream 4"], "chain": [("GaussianNoise", 0.90), ("Resampling", 0.60)], "claims": ["C7"], "start": (2026, 10, 5, 0)}
CAMP_E = {"gens": ["GPT-Image 1"], "chain": [("Sharpening", 0.45), ("GaussianBlur", 0.90)], "claims": ["C8"], "start": (2026, 10, 1, 6)}
for k in (3, 10, 30, 100):
    EXPS[f"scale_{k}"] = {"scale": k}
EXPS["camps_3_scale3"] = {"scale": 3, "campaigns": [{}, CAMP_B, CAMP_C]}
EXPS["camps_5_scale10"] = {"scale": 10, "campaigns": [{}, CAMP_B, CAMP_C, CAMP_D, CAMP_E]}
EXPS["big_campaign_scale10"] = {"scale": 10, "campaign": {"n_core": 100, "n_amp": 20}}

# iteration 1b: parameter-randomizing attacker that also blends in behaviorally (aged accounts, organic reposts)
EV = {"aged": True, "organic_reposts": True}
EXPS["evasive"] = {"campaign": dict(EV)}
EXPS["per_account_evasive"] = {"campaign": {"param_mode": "per_account", **EV}}
EXPS["op_pool_evasive"] = {"campaign": {"param_mode": "pool", **EV}}
EXPS["pool_genmix_evasive"] = {"campaign": {"param_mode": "pool", "gens": ["FLUX.1 [dev]", "Midjourney v7", "SDXL"], **EV}}

# iteration 3: realism, one block at a time and then all together (scale 3, i.e. 450 organic accounts)
R_PLATFORM = {"platform": "calibrated", "timing": "loguniform", "activity": "heavy"}
R_DETECTOR = {"detector": "calibrated", "rho": 1.0, "bias_sd": 0.05}
R_CLAIMS = {"text_mode": "paraphrase", "claim_match": "calibrated"}
R_RECORDS = {"coverage": 0.8, "fc_coverage": 0.6, "prov_recall": 0.7}
R_HABITS = {"p_habit": 0.5, "p_preset": 0.3}
R_ALL = {**R_PLATFORM, **R_DETECTOR, **R_CLAIMS, **R_RECORDS, **R_HABITS}
SPAMOUFLAGE_SHIFTS = ([(9.5, 12.0), (13.5, 17.5), (19.0, 22.0)], 8)  # Beijing-time shift pattern reported for Spamouflage (Meta, Aug 2023)
EXPS["r_base_scale3"] = {"scale": 3}
EXPS["r_platform"] = {"scale": 3, **R_PLATFORM}
EXPS["r_detector"] = {"scale": 3, **R_DETECTOR}
EXPS["r_claims"] = {"scale": 3, **R_CLAIMS}
EXPS["r_records"] = {"scale": 3, **R_RECORDS}
EXPS["r_habits"] = {"scale": 3, **R_HABITS}
EXPS["r_all"] = {"scale": 3, **R_ALL}
EXPS["r_all_spamouflage"] = {"scale": 3, **R_ALL, "campaign": {"n_core": 30, "n_amp": 10, "hours": SPAMOUFLAGE_SHIFTS}}
EXPS["r_all_evasive_per_account"] = {"scale": 3, **R_ALL, "campaign": {"param_mode": "per_account", "aged": True, "organic_reposts": True}}

# iteration 4: new noise sources and adversary strategies on the realistic world
EXPS["n_mimic_preset"] = {"scale": 3, **R_ALL, "campaign": {"mimic": True}}
EXPS["n_debunkers"] = {"scale": 3, **R_ALL, "debunkers": 15}
EXPS["n_name_drift"] = {"scale": 3, **R_ALL, "name_drift": 0.3}
EXPS["n_name_drift_vocab"] = {"scale": 3, **R_ALL, "name_drift": 0.3, "entity_vocab": True}
EXPS["n_sleeper"] = {"scale": 3, **R_ALL, "campaign": {"window_h": 24 * 12, "start": (2026, 9, 24, 0)}}
EXPS["n_low_volume"] = {"scale": 3, **R_ALL, "campaign": {"posts": (1, 2)}}

# time to detect: the realistic world queried as it stood h hours after the campaign's first post (fact-checks arrive with latency)
from datetime import datetime, timedelta, timezone
for h in (6, 12, 24, 48, 96, 168):
    EXPS[f"ttd_{h}h"] = {"scale": 3, **R_ALL, "as_of": datetime(2026, 10, 3, 6, tzinfo=timezone.utc) + timedelta(hours=h)}
EXPS["r_all_fc_full"] = {"scale": 3, **R_ALL, "fc_coverage": 1.0}

# iteration 5: leak-fixed generator (eval/leak_audit.py), new defender variants, and renewed attacks on the worst failures
R5 = {"scale": 3, **R_ALL, "leakfix": True, "stance": True}
EXPS["i5_base"] = dict(R5)
EXPS["i5_debunkers"] = {**R5, "debunkers": 15}
EXPS["i5_debunkers_weak_stance"] = {**R5, "debunkers": 15, "stance_recall": 0.6, "stance_fpr": 0.10}
EXPS["i5_low_volume"] = {**R5, "campaign": {"posts": (1, 2)}}
EXPS["i5_per_persona_aged"] = {**R5, "campaign": {"param_mode": "per_account", "aged": True, "organic_reposts": True}}
EXPS["i5_spamouflage"] = {**R5, "campaign": {"n_core": 30, "n_amp": 10, "hours": SPAMOUFLAGE_SHIFTS}}
for h in (12, 18, 24, 36, 48):
    EXPS[f"i5_ttd_{h}h"] = {**R5, "as_of": datetime(2026, 10, 3, 6, tzinfo=timezone.utc) + timedelta(hours=h)}

# iteration 5b: same worlds with the per-claim fact-check draw (coverage no longer shifts with unrelated world changes)
for _k in [k for k in list(EXPS) if k.startswith("i5_")]:
    EXPS["i5f_" + _k[3:]] = {**EXPS[_k], "fc_stream": True}

# iteration 6: repost-tie evidence; the operator's next move is to drop in-network reposts among core personas
EXPS["i6_pp_aged_noties"] = {**EXPS["i5f_per_persona_aged"], "campaign": {**EXPS["i5f_per_persona_aged"]["campaign"], "core_reposts": False}}
for _h in (12, 18, 24, 36):
    EXPS[f"i6_pp_aged_ttd_{_h}h"] = {**EXPS["i5f_per_persona_aged"], "as_of": EXPS[f"i5f_ttd_{_h}h"]["as_of"]}
