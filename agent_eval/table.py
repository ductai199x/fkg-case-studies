# Prints per-question primary scores and means for every scored answer set, default and held-out worlds.
import json, glob, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
for pref, label in [("scores_", "default"), ("heldout_scores_", "heldout")]:
    sets = {}
    for f in sorted(glob.glob(f"{pref}*.json")):
        if pref == "scores_" and f.startswith("scores_") is False: continue
        for k, v in json.load(open(f)).items(): sets[k] = v
    qs = sorted({q for v in sets.values() for q in v if q.startswith("Q")})
    print(f"== {label}"); print("set   " + " ".join(f"{q:>6}" for q in qs) + "   mean  exact_parent")
    for k, v in sets.items():
        prim = [v.get(q, {}).get("primary", 0) or 0 for q in qs]
        print(f"{k:5} " + " ".join(f"{p:6.3f}" for p in prim) + f"  {sum(prim)/len(prim):.3f}  {v.get('Q2.2', {}).get('detail', {}).get('exact_parent')}")
