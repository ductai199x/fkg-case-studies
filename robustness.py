# Re-generates each synthetic world under fresh seeds (and, for CS1/CS3, a sweep of noise rates eta) and reruns every
# query/baseline; reports mean ± std of the headline metric. eta = per-item probability of each planted failure mode.
import json, os, sys, subprocess, tempfile, importlib.util, statistics as st
ROOT = os.path.dirname(os.path.abspath(__file__)); NSEED = int(sys.argv[1]) if len(sys.argv) > 1 else 5; SEEDS = range(1, NSEED + 1)
ETAS = [0.05, 0.1, 0.2, 0.3, 0.5]
CONFIGS = [("cs1_recycled_media", e) for e in ETAS] + [("cs2_lineage_laundering", None)] + [("cs3_intent_materiality", e) for e in ETAS]
def headline(v):
    if "post" in v: return v["post"]["f1"]
    for k in ("macro_f1", "same_variant_parent", "f1"):
        if k in v: return v[k]
    if "correct" in v: return round(v["correct"] / v["of"], 3)
def extra(v):  # secondary metrics worth tracking
    out = {k: v[k] for k in ("precision", "recall", "accuracy", "exact_parent") if k in v}
    if "post" in v: out.update(precision=v["post"]["precision"], recall=v["post"]["recall"])
    if "edit_steps" in v: out["edit_steps_f1"] = v["edit_steps"]["f1"]
    return out
agg = {}
mods = {}
for case, eta in CONFIGS:
    key = case if eta is None else f"{case} eta={eta}"
    cdir = f"{ROOT}/{case}"; os.chdir(cdir); sys.path.insert(0, cdir)
    if case not in mods:
        spec = importlib.util.spec_from_file_location(f"run_{case}", f"{cdir}/run.py"); mods[case] = importlib.util.module_from_spec(spec); spec.loader.exec_module(mods[case])
    mod = mods[case]
    for seed in (SEEDS if eta is not None else range(1, 2 * NSEED + 1)):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, FKG_SEED=str(seed), FKG_DATA=f"{tmp}/data", FKG_ETA="" if eta is None else str(eta)); os.makedirs(f"{tmp}/res")
            subprocess.run([sys.executable, "generate.py"], cwd=cdir, env=env, check=True, capture_output=True)
            os.environ["FKG_DATA"] = f"{tmp}/data"; R = mod.main("queries", f"{tmp}/res"); del os.environ["FKG_DATA"]
        for name, v in R.items():
            a = agg.setdefault(key, {}).setdefault(name, {"headline": []}); a["headline"].append(headline(v))
            for k, x in extra(v).items(): a.setdefault(k, []).append(x)
        print(key, seed, "done", flush=True)
summ = {c: {n: {k: dict(mean=round(st.mean(xs), 3), std=round(st.pstdev(xs), 3), min=min(xs), max=max(xs)) for k, xs in m.items()} for n, m in d.items()} for c, d in agg.items()}
json.dump(dict(seeds_per_eta=NSEED, seeds_cs2=2 * NSEED, etas=ETAS, summary=summ, raw=agg), open(f"{ROOT}/robustness.json", "w"), indent=1)
with open(f"{ROOT}/robustness.md", "w") as f:
    f.write(f"Headline metric (mean ± std, [min, max]) over {NSEED} seeds per noise rate eta (CS1, CS3) and {2 * NSEED} seeds (CS2). Synthetic worlds; ground truth planted.\n\n")
    for c, d in summ.items():
        f.write(f"\n## {c}\n\n| query | headline | other |\n|---|---|---|\n")
        for n, m in d.items():
            h = m["headline"]; o = ", ".join(f"{k} {x['mean']:.3f}±{x['std']:.3f}" for k, x in m.items() if k != "headline")
            f.write(f"| {n} | {h['mean']:.3f} ± {h['std']:.3f} [{h['min']}, {h['max']}] | {o} |\n")
print(open(f"{ROOT}/robustness.md").read())
