# Loads an N-Quads file into an in-memory Oxigraph store once, then answers queries read as JSON lines on stdin
# ({"q": ..., "var": "account" | "*"}) with JSON lines {"seconds", "rows"} on stdout. Used by run_waves.py.
import json, sys, time
import pyoxigraph as ox
t0 = time.time(); store = ox.Store(); store.bulk_load(path=sys.argv[1], format=ox.RdfFormat.N_QUADS)
print(json.dumps({"loaded": time.time() - t0, "quads": len(store)}), flush=True)
for line in sys.stdin:
    req = json.loads(line); t0 = time.time(); res = store.query(req["q"]); var = req.get("var", "account")
    if var == "*": rows = [[s[v].value for v in res.variables] for s in res]
    else: rows = sorted({s[var].value for s in res})
    print(json.dumps({"seconds": time.time() - t0, "rows": rows}), flush=True)
