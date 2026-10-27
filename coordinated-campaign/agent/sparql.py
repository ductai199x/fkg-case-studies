# SPARQL runner for the investigating agent: uv run python sparql.py QUERY_FILE_OR_STRING [--limit N]
import sys, pyoxigraph as ox
from pathlib import Path
here = Path(__file__).resolve().parent
args = sys.argv[1:]; limit = 200
if "--limit" in args: i = args.index("--limit"); limit = int(args[i + 1]); del args[i:i + 2]
q = Path(args[0]).read_text() if Path(args[0]).is_file() else args[0]
st = ox.Store(); st.load(path=str(here / "dataset.trig"), format=ox.RdfFormat.TRIG)
res = st.query(q)
if isinstance(res, bool): print(res); sys.exit()
if isinstance(res, ox.QueryTriples): print(res.serialize(format=ox.RdfFormat.TURTLE).decode()[:20000]); sys.exit()
vars_ = [v.value for v in res.variables]; print("\t".join(vars_)); n = 0
for s in res:
    n += 1
    if n <= limit: print("\t".join("" if s[v] is None else str(s[v]) for v in vars_))
print(f"-- {n} rows" + (f" (showing {limit})" if n > limit else ""))
