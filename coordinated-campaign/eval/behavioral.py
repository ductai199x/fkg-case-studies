# Behavioral baseline: co-repost similarity network (accounts that repost the same posts), in the spirit of
# Pacheco et al. (ICWSM 2021). TF-IDF vectors over reposted notes, cosine similarity, threshold, connected components.
import math
from collections import defaultdict

ANNOUNCES = """PREFIX as: <https://www.w3.org/ns/activitystreams#>
SELECT ?account ?note WHERE { GRAPH <https://example.org/cc/graph/platform> { ?a a as:Announce ; as:actor ?account ; as:object ?note } }"""


def corepost(rows, tau=0.3, min_reposts=2, min_component=3):  # defaults: best F1 on two naive base worlds (oracle-tuned)
    items = defaultdict(set)
    for acct, note in rows: items[acct].add(note)
    items = {a: s for a, s in items.items() if len(s) >= min_reposts}
    df = defaultdict(int)
    for s in items.values():
        for n in s: df[n] += 1
    N = len(items) or 1
    vec = {a: {n: math.log(N / df[n]) + 1e-9 for n in s} for a, s in items.items()}
    norm = {a: math.sqrt(sum(v * v for v in x.values())) for a, x in vec.items()}
    by_note = defaultdict(list)
    for a, s in items.items():
        for n in s: by_note[n].append(a)
    dot = defaultdict(float)
    for n, accts in by_note.items():
        if len(accts) > 200: continue  # viral posts carry no coordination signal and dominate cost
        for i in range(len(accts)):
            for j in range(i + 1, len(accts)):
                x, y = sorted((accts[i], accts[j])); dot[(x, y)] += vec[x][n] * vec[y][n]
    adj = defaultdict(set)
    for (x, y), d in dot.items():
        if d / (norm[x] * norm[y]) >= tau: adj[x].add(y); adj[y].add(x)
    seen, flagged = set(), set()
    for a in adj:
        if a in seen: continue
        comp, stack = set(), [a]
        while stack:
            u = stack.pop()
            if u in comp: continue
            comp.add(u); stack.extend(adj[u] - comp)
        seen |= comp
        if len(comp) >= min_component: flagged |= comp
    return flagged
