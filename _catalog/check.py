# Parses and runs every catalog sketch on the synthetic world named in catalog.json; records row counts and a sample.
import json, sys, os, time
sys.path.insert(0, "../_shared"); from sparql_runner import load, run, add_triples
cat = json.load(open("catalog.json")); worlds = {}; out = {}
for uc in cat:
    q, w = uc.get("sketch"), uc.get("world")
    if not q or not w: continue
    path = q if q.startswith("..") else q
    ds = load(f"../{w}/data/world.trig") if uc.get("pre") else worlds.setdefault(w, load(f"../{w}/data/world.trig"))
    for pq in uc.get("pre", []): add_triples(ds, run(ds, open(pq).read()))
    t0 = time.time(); rows = run(ds, open(path).read())
    out[uc["id"]] = dict(query=path, world=w, rows=len(rows), seconds=round(time.time() - t0, 2), sample=rows[:3])
    print(uc["id"], w, len(rows), "rows", out[uc["id"]]["seconds"], "s")
json.dump(out, open("check_results.json", "w"), indent=1, default=str)
