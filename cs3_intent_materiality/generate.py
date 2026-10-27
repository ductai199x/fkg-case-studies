# CS3: how is altered media being presented? Materiality, disclosure, genre, content credentials, and
# accountability (anachronistic attributions, retraction propagation). Synthetic world; generator names fictional.
import json, random, sys
from datetime import datetime, timedelta
sys.path.insert(0, "../_shared")
from fkgbuild import *
from rdflib import Literal, BNode
from rdflib.namespace import RDF, RDFS, XSD

import os
rng = random.Random(int(os.environ.get("FKG_SEED", 31)))
# nuisance attributes use their own stream so the world structure (spread trees, claims, counts) matches the earlier version
rng_look = random.Random(int(os.environ.get("FKG_SEED", 31)) + 1000003)
DATA = os.environ.get("FKG_DATA", "data"); os.makedirs(DATA, exist_ok=True)
ETA = float(os.environ["FKG_ETA"]) if os.environ.get("FKG_ETA") else None   # noise rate; None = fixed planted counts
ds, EX = new_dataset("https://example.org/fkg/cs3#")
ref, ctx = ds.graph(G_REF), ds.graph(G_CTX)
v10 = add_detector(ds, EX, "1.0", "2026-06-22"); v11 = add_detector(ds, EX, "1.1", "2026-08-15")
issue = EX["issue_v1_1_generatorID"]
ref.add((issue, RDF.type, CTX.KnownIssue)); ref.add((issue, CTX.affectsVersion, v11))
ref.add((issue, CTX.affectsProperty, Literal("https://example.org/fkg#hasGeneratorModel", datatype=XSD.anyURI)))
ref.add((issue, RDFS.comment, Literal("Generator-identification head of v1.1 mislabels some attributions; attribution of AI-generated vs camera is unaffected.")))
ref.add((issue, SCHEMA.datePublished, Literal("2026-10-15", datatype=XSD.date)))
GEN = {}
for name, rel in [("Lumen-2", "2025-11-03"), ("Pixa-XL", "2025-02-17"), ("Dreamforge-7", "2026-04-28"), ("Nova-3", "2026-10-10")]:
    g = EX["gen_" + name.replace("-", "_")]; GEN[name] = g
    ref.add((g, RDF.type, CTX.GeneratorModel)); ref.add((g, SCHEMA.name, Literal(name))); ref.add((g, SCHEMA.datePublished, Literal(rel, datatype=XSD.date)))
ENT = {}
for k, lbl in [("MayorLee", "Mayor Lee"), ("SenatorOkafor", "Senator Okafor"), ("CityHall", "City Hall"), ("RiverBridge", "River Bridge"), ("Stadium", "Stadium")]:
    e = EX["ent_" + k]; ENT[k] = (e, lbl); ref.add((e, RDF.type, SCHEMA.Thing)); ref.add((e, RDFS.label, Literal(lbl)))
PERIPH = ["sky", "background crowd", "street sign", "foliage"]
P = {k: add_platform(ds, EX, k, *v) for k, v in {"picshare": ("PicShare", 0.85, False, 2048), "chirp": ("Chirp", 0.82, False, 1600)}.items()}
genres = [CTX.PersonalAccount] * 50 + [CTX.NewsOutlet] * 6 + [CTX.SatireAccount] * 6 + [CTX.ArtAccount] * 6
accts = [(add_account(ds, EX, f"acct{i}", P[["picshare", "chirp"][i % 2]], g), g) for i, g in enumerate(genres)]
by_genre = lambda G: [a for a, g in accts if g in G]
CAMS = ["Canon EOS R5", "iPhone 15 Pro", "Pixel 8", "Sony A7 IV"]
IPTC_CAPTURE, IPTC_AI, IPTC_COMPOSITE = IPTC.digitalCapture, IPTC.trainedAlgorithmicMedia, IPTC.compositeWithTrainedAlgorithmicMedia
gt = {"intent": {}, "credential_contradiction": [], "anachronism": [], "affected_reviews": []}
n = [0]
T0 = datetime(2026, 9, 1)

def make(cat, *, ai=None, ai_desc=None, ai_entity=None, synthetic=False, conf=None, claim_ent=None, genre=None, disclosure=None,
         c2pa=None, post_proc=None, spurious=False, version=v10, when=None, review=False):
    n[0] += 1; iid = f"img{n[0]:04d}"; cam = rng.choice(CAMS)
    when = when or T0 + timedelta(hours=rng.uniform(0, 24 * 50))
    regs = []
    if not synthetic:
        cam_ent = claim_ent if (claim_ent and ai_entity != claim_ent) else None
        regs.append(dict(kind="camera", model=cam, conf=rng.uniform(0.8, 0.97), desc=ENT[cam_ent][1] if cam_ent else "street scene",
                         entity=ENT[cam_ent][0] if cam_ent else None, objectness=bool(cam_ent), comp=dict(q=0.85, re=True),
                         post=post_proc))
    if ai:
        regs.append(dict(kind="ai", model=ai, gen_entity=GEN[ai], conf=conf or rng.uniform(0.75, 0.97),
                         desc=ENT[ai_entity][1] if ai_entity else ai_desc, entity=ENT[ai_entity][0] if ai_entity else None,
                         objectness=True if ai_entity else rng_look.random() < AI_OBJECTNESS_P, comp=dict(q=0.85, re=not synthetic)))
    if spurious:
        g = rng.choice(list(GEN)[:3]); regs.append(dict(kind="ai", model=g, gen_entity=GEN[g], conf=rng_look.uniform(0.70, 0.85), comp=dict(q=0.85, re=True), **ai_region_look(rng_look, PERIPH)))
    img = add_image(ds, EX, iid, regs, version, (when + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S"), 1600, rng)
    pool = by_genre(genre or [CTX.PersonalAccount, CTX.NewsOutlet])
    post = add_post(ds, EX, f"p{n[0]:04d}", rng.choice(pool), P[rng.choice(list(P))], when.strftime("%Y-%m-%dT%H:%M:%S"), img,
                    shares=int(rng.lognormvariate(5, 1.4)), disclosure=disclosure)
    if claim_ent:
        cl = EX[f"claim{n[0]:04d}"]; ctx.add((cl, RDF.type, SCHEMA.Claim)); ctx.add((cl, SCHEMA.appearance, post)); ctx.add((cl, SCHEMA.about, ENT[claim_ent][0]))
        if review:
            rv = EX[f"review{n[0]:04d}"]; rr = EX[f"rating{n[0]:04d}"]
            ctx.add((rv, RDF.type, SCHEMA.ClaimReview)); ctx.add((rv, SCHEMA.itemReviewed, cl)); ctx.add((rv, SCHEMA.isBasedOn, EX[f"{iid}_record"]))
            ctx.add((rv, SCHEMA.reviewRating, rr)); ctx.add((rr, RDF.type, SCHEMA.Rating)); ctx.add((rr, SCHEMA.alternateName, Literal("False")))
            if version == v11: gt["affected_reviews"].append(str(rv))
    if c2pa:
        cr = EX[f"cred{n[0]:04d}"]; ctx.add((cr, RDF.type, CTX.ContentCredential)); ctx.add((cr, CTX.credentialFor, img))
        ctx.add((cr, CTX.digitalSourceType, c2pa[0])); ctx.add((cr, CTX.signatureValid, Literal(True)))
        ctx.add((cr, CTX.claimedCaptureDevice, Literal(c2pa[1] or cam))); ctx.add((cr, FKG.evidenceStatus, FKG.SourceReported))
    gt["intent"][str(post)] = cat
    return post, cam

ents = list(ENT); gens3 = ["Lumen-2", "Pixa-XL", "Dreamforge-7"]
for i in range(60): make("NoAlteration", claim_ent=rng.choice(ents) if i % 2 else None, review=(i % 10 == 1), spurious=ETA is not None and rng.random() < ETA)
for i in range(20): make("NoAlteration", post_proc=[("Sharpening", {"percent": 40}), ("Resampling", {"scaleFactor": 0.5})])
for i in range(3 if ETA is None else 0): make("NoAlteration", spurious=True, claim_ent=rng.choice(ents))   # detector false positives (fixed set)
for i in range(25):
    e = rng.choice(ents); synth = i < 8
    p, _ = make("UndisclosedMaterialAlteration", ai=rng.choice(gens3), ai_entity=e, synthetic=synth, claim_ent=e,
                conf=rng.uniform(0.6, 0.68) if ((i in (10, 11, 12)) if ETA is None else rng.random() < ETA) else None, review=(i % 4 == 0), version=v11 if i % 4 == 0 and i < 16 else v10)
for i in range(20):
    e = rng.choice(ents); make("UndisclosedPeripheralAlteration", ai=rng.choice(gens3), ai_desc=rng.choice(PERIPH), claim_ent=e if i < 14 else None)
for i in range(30):
    e = rng.choice(ents) if i % 3 == 0 else None
    kind = i % 3
    make("DisclosedSynthetic", ai=rng.choice(gens3), ai_entity=e, ai_desc=None if e else rng.choice(PERIPH), synthetic=(i % 2 == 0), claim_ent=e,
         disclosure=CTX.PlatformAILabel if kind == 0 else CTX.CaptionAIDisclosure if kind == 1 else None,
         c2pa=(IPTC_AI if i % 2 == 0 else IPTC_COMPOSITE, None) if kind == 2 else None)
for i in range(25):
    e = rng.choice(ents); make("SatireOrArt", ai=rng.choice(gens3), ai_entity=e, synthetic=(i % 2 == 0),
                             genre=[CTX.SatireAccount] if i % 2 else [CTX.ArtAccount], claim_ent=e if i % 3 == 0 else None)
# content credentials: contradictory (claims a capture, forensics find AI / another camera) and consistent ones
for i in range(6):
    e = rng.choice(ents); p, _ = make("UndisclosedMaterialAlteration", ai=rng.choice(gens3), ai_entity=e, claim_ent=e, c2pa=(IPTC_CAPTURE, None))
    gt["credential_contradiction"].append(str(p))
for i in range(2):
    n_before = n[0]; p, cam = make("NoAlteration", c2pa=(IPTC_CAPTURE, "Nikon Z9"))
    gt["credential_contradiction"].append(str(p))
for i in range(4): make("NoAlteration", c2pa=(IPTC_CAPTURE, None))
# anachronism: v1.1 attributes regions to Nova-3 in posts published before Nova-3's release
for i in range(3):
    e = rng.choice(ents)
    p, _ = make("UndisclosedMaterialAlteration", ai="Nova-3", ai_entity=e, claim_ent=e, version=v11, review=(i == 0),
                when=datetime(2026, 9, 20) + timedelta(days=i * 3))
    gt["anachronism"].append(str(p))
for i in range(6): make("NoAlteration", version=v11)                               # v1.1 records not cited by any review
write(ds, f"{DATA}/world.trig")
json.dump(gt, open(f"{DATA}/ground_truth.json", "w"), indent=1)
from collections import Counter
print(len(ds), "quads;", Counter(gt["intent"].values()), {k: len(v) for k, v in gt.items() if k != "intent"})
