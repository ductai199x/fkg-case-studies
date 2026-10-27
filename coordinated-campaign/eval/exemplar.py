# Extracts one operation post (an AI-edited image) with its FKG record, post, claim match and fact-check as a TriG listing.
import json, os, sys
from rdflib import Dataset, URIRef, Namespace
from rdflib.namespace import RDF
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
DATA, TRUTH = Path(os.environ.get("FKG_DATA", ROOT / "data")), Path(os.environ.get("FKG_TRUTH", ROOT / "truth"))
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results/exemplar_record.trig"
ds = Dataset(); ds.parse(DATA / "eta_0.0/seed_0/dataset.trig", format="trig")
truth = json.load(open(TRUTH / "eta_0.0/seed_0.json"))
FKG = Namespace("https://example.org/fkg#"); AS = Namespace("https://www.w3.org/ns/activitystreams#"); SDO = Namespace("https://schema.org/")
G = lambda n: ds.graph(URIRef(f"https://example.org/cc/graph/{n}"))
gf, gp, gc = G("forensics"), G("platform"), G("factcheck")
core = set(truth["core"])
for note in gp.subjects(RDF.type, AS.Note):
    acct, img = gp.value(note, AS.attributedTo), gp.value(note, AS.attachment)
    if str(acct) in core and img is not None and len(list(gf.objects(img, FKG.hasRegion))) == 2 and list(gc.subjects(SDO.appearance, note)):
        break
out = Dataset(); [out.bind(p, n) for p, n in ds.namespaces()]
of, op, oc = (out.graph(URIRef(f"https://example.org/cc/graph/{n}")) for n in ("forensics", "platform", "factcheck"))
def closure(src, dst, node, seen):
    if node in seen: return
    seen.add(node)
    for p, o in src.predicate_objects(node):
        dst.add((node, p, o))
        if isinstance(o, URIRef) and not str(o).startswith(("https://example.org/fkg#", "ni:")): closure(src, dst, o, seen)
seen = set(); closure(gf, of, img, seen)
for rec in gf.subjects(FKG.aboutImage, img): closure(gf, of, rec, seen)
for t in gf.triples((img, None, None)): of.add(t)
for p, o in gp.predicate_objects(note): op.add((note, p, o))
for act in gp.subjects(AS.object, note):
    if (act, RDF.type, AS.Create) in gp: [op.add((act, p, o)) for p, o in gp.predicate_objects(act)]
claim = next(gc.subjects(SDO.appearance, note))
oc.add((claim, SDO.appearance, note)); oc.add((claim, RDF.type, SDO.Claim)); oc.add((claim, SDO.text, gc.value(claim, SDO.text)))
rev = next(gc.subjects(SDO.itemReviewed, claim)); closure(gc, oc, rev, {claim})
OUT.parent.mkdir(parents=True, exist_ok=True); out.serialize(OUT, format="trig")
print(OUT.read_text())
