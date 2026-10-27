# CS1: authentic-but-miscaptioned media. Synthetic world; ground truth is planted and saved separately.
import json, random, sys
from datetime import datetime, timedelta
sys.path.insert(0, "../_shared")
from fkgbuild import *
from rdflib import Literal
from rdflib.namespace import RDF, RDFS, XSD

import os
rng = random.Random(int(os.environ.get("FKG_SEED", 20261027)))
# nuisance attributes use their own stream so the world structure (spread trees, claims, counts) matches the earlier version
rng_look = random.Random(int(os.environ.get("FKG_SEED", 20261027)) + 1000003)
DATA = os.environ.get("FKG_DATA", "data"); os.makedirs(DATA, exist_ok=True)
ETA = float(os.environ["FKG_ETA"]) if os.environ.get("FKG_ETA") else None   # noise rate; None = fixed planted counts
ds, EX = new_dataset("https://example.org/fkg/cs1#")
ref, ctx = ds.graph(G_REF), ds.graph(G_CTX)
det = add_detector(ds, EX, "1.0", "2026-06-22")
P = {k: add_platform(ds, EX, k, *v) for k, v in {
    "newswire": ("NewsWire", 0.92, False, 4096), "picshare": ("PicShare", 0.85, False, 2048),
    "chirp": ("Chirp", 0.82, False, 1600), "fringe": ("FringeBoard", 0.75, False, 1280)}.items()}
CAMERAS = ["Canon EOS R6", "Nikon Z6", "Sony A7 IV", "iPhone 15 Pro", "Pixel 8", "Galaxy S24", "Nikon Coolpix S33", "Fujifilm X-T4"]
GENS = ["FLUX.1", "SDXL", "Midjourney v7", "GPT-Image-1"]
AI_DESC = ["floodwater", "burning car", "crowd", "sky", "texture patch"]   # shared by true and spurious AI regions
FP_KEEP_P = 0.7   # a content-driven false positive recurs on each later copy with this probability

def event(key, label, start, place):
    e, pl = EX[f"event_{key}"], EX[f"place_{place.replace(' ', '')}"]
    ref.add((e, RDF.type, SCHEMA.Event)); ref.add((e, RDFS.label, Literal(label)))
    ref.add((e, SCHEMA.startDate, Literal(start, datatype=XSD.dateTime))); ref.add((e, SCHEMA.location, pl))
    ref.add((pl, RDF.type, SCHEMA.Place)); ref.add((pl, RDFS.label, Literal(place)))
    return e, datetime.fromisoformat(start)
CUR = [event("flood2026", "Harbor City flood", "2026-09-14T06:00:00", "Harbor City"),
       event("rally2026", "Riverside rally", "2026-10-03T15:00:00", "Riverside")]
OLD = [event("storm2019", "Harbor City storm", "2019-08-02T09:00:00", "Harbor City"),
       event("rally2021", "Riverside rally", "2021-05-11T14:00:00", "Riverside"),
       event("flood2023", "Coastline flood", "2023-03-20T08:00:00", "Coastline")]
accts = {f"outlet{i}": add_account(ds, EX, f"outlet{i}", P["newswire"], CTX.NewsOutlet) for i in range(3)}
plats = ["picshare", "chirp", "fringe"]
for i in range(60):
    accts[f"user{i}"] = add_account(ds, EX, f"user{i}", P[plats[i % 3]], CTX.PersonalAccount)
users = [k for k in accts if k.startswith("user")]

gt = {"claim_posts": {}, "earliest_appearance": {}}
counter = {"img": 0, "post": 0, "claim": 0}
def nid(k): counter[k] += 1; return f"{k}{counter[k]:04d}"
def iso(dt): return dt.strftime("%Y-%m-%dT%H:%M:%S")

def instance(cluster, regions_fn, plat, when, acct, recompressed, shares=0):
    iid = nid("img"); q = ds.graph(G_REF).value(P[plat], CTX.transcodeQuality).toPython()
    regions = regions_fn(q + rng.uniform(-0.01, 0.01), recompressed)
    img = add_image(ds, EX, iid, regions, det, iso(when + timedelta(days=30)), rng.choice([1280, 1600, 2048]), rng)
    add_cluster_member(ds, EX, cluster, img)
    post = add_post(ds, EX, nid("post"), accts[acct], P[plat], iso(when), img, shares)
    return img, post

def camera_regions(cam, desc, extra=None, spurious=None):
    def f(q, re):
        rs = [dict(kind="camera", model=cam, conf=rng.uniform(0.8, 0.98), desc=desc, objectness=False, comp=dict(q=q, re=re))]
        if extra: rs.append(dict(extra, comp=dict(q=q, re=False)))   # pasted region carries a single-compression trace (physically motivated; audit shows no leak)
        if spurious:
            rng.choice(GENS)   # keeps the main stream aligned with the earlier version
            if rng_look.random() < FP_KEEP_P:
                rs.append(dict(spurious, conf=min(0.99, max(0.5, spurious["conf"] + rng_look.uniform(-0.03, 0.03))), comp=dict(q=q, re=re)))
        return rs
    return f

def claim(post, ev, label):
    c = EX[nid("claim")]
    ctx.add((c, RDF.type, SCHEMA.Claim)); ctx.add((c, SCHEMA.appearance, post)); ctx.add((c, CTX.assertsDepictionOf, ev))
    gt["claim_posts"][str(post)] = label

def history(cluster, regions_fn, start, n_reposts, first_acct=None, first_plat="newswire"):
    """first appearance + reposts; returns list of (img, post, time) in time order"""
    acct = first_acct or rng.choice(list(accts)[:3])
    out = [(*instance(cluster, regions_fn, first_plat, start, acct, False), start)]
    t = start
    for _ in range(n_reposts):
        t = t + timedelta(hours=rng.uniform(2, 24 * 90))
        out.append((*instance(cluster, regions_fn, rng.choice(plats), t, rng.choice(users), True), t))
    return out

cl = 0
# (a) authentic current: captured at a current event, first posted after it starts
for i in range(40):
    cl += 1; (ev, start) = CUR[i % 2]; cam = rng.choice(CAMERAS)
    if ETA is None: spur = rng.uniform(0.55, 0.66) if i < 4 else None            # detector false positives (low confidence)
    else: spur = (rng.uniform(0.55, 0.66) if rng.random() < 0.75 else rng.uniform(0.70, 0.80)) if rng.random() < ETA else None  # a quarter of FPs clear the 0.7 threshold
    if spur: spur = dict(kind="ai", model=rng_look.choice(GENS), conf=spur, post=[("GaussianBlur", {"sigma": round(rng_look.uniform(0.8, 2.5), 2)})] if rng_look.random() < 0.5 else None, **ai_region_look(rng_look, AI_DESC))
    h = history(cl, camera_regions(cam, "street scene", spurious=spur), start + timedelta(hours=rng.uniform(1, 30)), rng.randint(0, 2))
    if (4 <= i < 7) if ETA is None else rng.random() < ETA:        # near-duplicate false merge with an old, different photo
        old_ev, old_start = OLD[i % 3]; other = rng.choice([c for c in CAMERAS if c != cam])
        history(cl, camera_regions(other, "street scene"), old_start + timedelta(days=1), 0)
    tgt = rng.choice(h); claim(tgt[1], ev, "authentic_current")
# (b) recycled out of context: old photo, claim says it shows a current event
for i in range(25):
    cl += 1; (old_ev, old_start) = OLD[i % 3]; (ev, start) = CUR[i % 2]; cam = rng.choice(CAMERAS)
    hidden = i < 3 if ETA is None else rng.random() < ETA          # earliest instance absent from crawl (OWA limit)
    if hidden:
        h = history(cl, camera_regions(cam, "flooded street"), start + timedelta(hours=rng.uniform(5, 48)), 0, first_plat=rng.choice(plats), first_acct=rng.choice(users))
    else:
        h = history(cl, camera_regions(cam, "flooded street"), old_start + timedelta(hours=rng.uniform(2, 48)), rng.randint(0, 2))

    when = start + timedelta(hours=rng.uniform(3, 72))
    img, post = instance(cl, camera_regions(cam, "flooded street"), rng.choice(plats), when, rng.choice(users), True, shares=rng.randint(50, 5000))
    claim(post, ev, "recycled_ooc")
    gt["earliest_appearance"][str(post)] = None if hidden else str(h[0][1])
# (c) archival reuse, correctly captioned as the old event
for i in range(10):
    cl += 1; (old_ev, old_start) = OLD[i % 3]; cam = rng.choice(CAMERAS)
    history(cl, camera_regions(cam, "crowd"), old_start + timedelta(hours=rng.uniform(2, 48)), rng.randint(0, 1))
    img, post = instance(cl, camera_regions(cam, "crowd"), rng.choice(plats), CUR[i % 2][1] + timedelta(days=rng.uniform(1, 10)), rng.choice(users), True)
    claim(post, old_ev, "archival_ok")
# (d) manipulated derivative (AI-inserted region) of an old or current photo, claimed as current
for i in range(15):
    cl += 1; (ev, start) = CUR[i % 2]; cam = rng.choice(CAMERAS); gen = rng.choice(GENS)
    base_t = OLD[i % 3][1] + timedelta(days=2) if i < 8 else start + timedelta(hours=rng.uniform(1, 20))
    history(cl, camera_regions(cam, "street"), base_t, rng.randint(0, 1))
    weak = i in (8, 9) if ETA is None else rng.random() < ETA
    conf = rng.uniform(0.6, 0.68) if weak else rng.uniform(0.75, 0.97)   # weak true positives (below threshold)
    rng.choice(["floodwater", "burning car", "crowd"]); sigma = round(rng.uniform(0.8, 2.5), 2)   # main-stream draws kept for alignment
    extra = dict(kind="ai", model=gen, conf=conf, post=[("GaussianBlur", {"sigma": sigma})] if rng_look.random() < 0.5 else None, **ai_region_look(rng_look, AI_DESC))
    img, post = instance(cl, camera_regions(cam, "street", extra=extra), rng.choice(plats), start + timedelta(hours=rng.uniform(24, 200)), rng.choice(users), True, shares=rng.randint(50, 8000))
    claim(post, ev, "manipulated")
# (e) fully synthetic, claimed as current
for i in range(15):
    cl += 1; (ev, start) = CUR[i % 2]; gen = rng.choice(GENS)
    obj = rng_look.random() < AI_OBJECTNESS_P
    def synth(q, re, gen=gen, obj=obj): return [dict(kind="ai", model=gen, conf=rng.uniform(0.75, 0.99), desc="flooded street", objectness=obj, comp=dict(q=q, re=re))]
    img, post = instance(cl, synth, rng.choice(plats), start + timedelta(hours=rng.uniform(5, 150)), rng.choice(users), False, shares=rng.randint(50, 9000))
    claim(post, ev, "synthetic")

write(ds, f"{DATA}/world.trig")
json.dump(gt, open(f"{DATA}/ground_truth.json", "w"), indent=1)
from collections import Counter
print(len(ds), "quads;", Counter(gt["claim_posts"].values()), "; earliest known:", sum(v is not None for v in gt["earliest_appearance"].values()))
