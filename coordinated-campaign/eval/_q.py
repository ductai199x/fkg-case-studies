# Runs one SPARQL query (read from stdin) on an in-memory Oxigraph store loaded from an N-Quads file; prints the
# selected ?account values and the query time (load time excluded).
import json, sys, time
import pyoxigraph as ox
store = ox.Store(); store.bulk_load(path=sys.argv[1], format=ox.RdfFormat.N_QUADS); q = sys.stdin.read(); var = sys.argv[2] if len(sys.argv) > 2 else "account"
t0 = time.time(); res = store.query(q)
if var == "*": rows = [[s[v].value for v in res.variables] for s in res]  # all columns
else: rows = sorted({s[var].value for s in res})
print(json.dumps({"seconds": time.time() - t0, "rows": rows}))
