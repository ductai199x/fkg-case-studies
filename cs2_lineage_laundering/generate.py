# CS2: lineage of a viral image across platforms; where did the AI edit enter, who laundered it.
# Synthetic world. Each instance is a separately transcoded file with its own FKG; ground truth = true spread tree.
import json, random, sys
from datetime import datetime, timedelta
sys.path.insert(0, "../_shared")
from fkgbuild import *
from rdflib.namespace import RDF

import os
rng = random.Random(int(os.environ.get("FKG_SEED", 7)))
# nuisance attributes use their own stream so the world structure (spread trees, claims, counts) matches the earlier version
rng_look = random.Random(int(os.environ.get("FKG_SEED", 7)) + 1000003)
DATA = os.environ.get("FKG_DATA", "data"); os.makedirs(DATA, exist_ok=True)
ds, EX = new_dataset("https://example.org/fkg/cs2#")
det = add_detector(ds, EX, "1.0", "2026-06-22")
PLAT = {"newswire": ("NewsWire", 0.92, False, 4096), "picshare": ("PicShare", 0.85, False, 2048), "chirp": ("Chirp", 0.82, False, 1600),
        "fringe": ("FringeBoard", 0.92, True, 4096), "msg": ("MsgApp", 0.70, False, 1280)}
P = {k: add_platform(ds, EX, k, *v) for k, v in PLAT.items()}
CAMS = ["Canon EOS R6", "Nikon Z6", "Sony A7 IV", "Canon EOS R5"]; GENS = ["FLUX.1", "SDXL", "Midjourney v7", "GPT-Image-1"]
AI_DESC = ["fire", "armed man", "crowd", "flag", "sky", "smoke"]   # shared by true edits and detector false positives
FP_KEEP_P = 0.5   # a content-driven false positive recurs on each child copy with this probability
outlets = [add_account(ds, EX, f"outlet{i}", P["newswire"], CTX.NewsOutlet) for i in range(4)]
users = {pk: [add_account(ds, EX, f"{pk}_user{i}", P[pk], CTX.PersonalAccount) for i in range(25)] for pk in ["picshare", "chirp", "fringe", "msg"]}
editors = [add_account(ds, EX, f"fringe_editor{i}", P["fringe"], CTX.PersonalAccount) for i in range(5)]
gt = {"cluster_of": {}, "patient_zero": [], "parent": {}, "variant": {}, "laundering_posts": [], "hop_source_platform": {}}
n_img = [0]
def iso(d): return d.strftime("%Y-%m-%dT%H:%M:%S")

def emit(cl, node):
    n_img[0] += 1; iid = f"img{n_img[0]:04d}"
    regions = [dict(kind="camera", model=node["cam"], conf=rng.uniform(0.8, 0.97), desc="street scene", objectness=False,
                    comp=dict(q=node["q_cam"] + rng.uniform(-0.008, 0.008), re=node["re_cam"]),
                    post=[("Resampling", {"scaleFactor": round(node["scale"], 3)})] if node["scale"] < 0.999 else None)]
    for gen, st in node["ai"].items():
        conf = st["conf"] - (0.2 if node["plat"] == "msg" else 0.0)          # heavy compression weakens attribution
        regions.append(dict(kind="ai", model=gen, conf=conf, desc=st["desc"], objectness=st["objectness"],
                            comp=dict(q=st["q"] + rng.uniform(-0.008, 0.008), re=st["re"]),
                            post=[("Resampling", {"scaleFactor": round(node["scale"], 3)})] if node["scale"] < 0.999 else None))
    if node.get("spurious"):
        sp = node["spurious"]
        regions.append(dict(kind="ai", model=sp["model"], conf=sp["conf"] - (0.2 if node["plat"] == "msg" else 0.0) + rng_look.uniform(-0.02, 0.02), desc=sp["desc"], objectness=sp["objectness"],
                            comp=dict(q=node["q_cam"] + rng_look.uniform(-0.008, 0.008), re=node["re_cam"]),
                            post=[("Resampling", {"scaleFactor": round(node["scale"], 3)})] if node["scale"] < 0.999 else None))
    img = add_image(ds, EX, iid, regions, det, iso(node["t"] + timedelta(days=20)), node["edge"], rng)
    add_cluster_member(ds, EX, cl, img)
    post = add_post(ds, EX, iid.replace("img", "p"), node["acct"], P[node["plat"]], iso(node["t"]), img,
                    shares=rng.randint(10, 3000), credits=node.get("credits"))
    node["img"], node["post"] = str(img), str(post)

def child(parent, plat, acct, t, edit=None, credits=None):
    q, pt, _, mx = PLAT[plat][1], PLAT[plat][2], None, PLAT[plat][3]
    n = dict(parent); n.update(plat=plat, acct=acct, t=t, credits=credits, parent=parent,
                               spurious=parent.get("spurious") if parent.get("spurious") and rng_look.random() < FP_KEEP_P else None)
    n.pop("is_edit", None)
    n["ai"] = {g: dict(s) for g, s in parent["ai"].items()}
    if edit:                                     # editor re-exports the whole file at ~0.95 after inserting a region
        n["re_cam"] = True; n["q_cam"] = 0.95
        for s in n["ai"].values(): s.update(q=0.95, re=True)
        n["ai"][edit[0]] = dict(conf=rng.uniform(0.78, 0.95), q=0.95, re=False, **ai_region_look(rng_look, AI_DESC))
        n["scale"], n["edge"] = 1.0, parent["edge"]
    elif not pt:
        n["re_cam"], n["q_cam"] = True, q
        for s in n["ai"].values(): s.update(q=q, re=True)
        new_edge = min(parent["edge"], mx); n["scale"] = new_edge / parent["edge"]; n["edge"] = new_edge
    else:
        n["scale"] = 1.0                         # passthrough keeps bytes: same q, same size
    return n

t_base = datetime(2026, 9, 1, 8)
for c in range(8):
    outlet = outlets[c % 4]; cam = rng.choice(CAMS)
    root = dict(plat="newswire", acct=outlet, t=t_base + timedelta(days=4 * c), cam=cam, q_cam=0.92, re_cam=False, ai={}, edge=4000, scale=1.0, parent=None)
    spur = dict(model=rng.choice(GENS), conf=rng_look.uniform(0.70, 0.85), **ai_region_look(rng_look, AI_DESC)) if c in (1, 5) else None
    fp_at = rng_look.randint(0, 10)              # detector false positive first fires on a random early instance (not always the root), then may recur on copies
    root["spurious"] = spur if fp_at == 0 else None
    nodes = [root]
    def add(n):
        if spur and len(nodes) == fp_at and not n["ai"]: n["spurious"] = spur
        nodes.append(n)
    n_edits = 0 if c in (2, 6) else (2 if c == 4 else 1)
    edit_times = sorted(rng.uniform(6, 60) for _ in range(n_edits))
    used_gens = rng.sample(GENS, n_edits)
    for step in range(rng.randint(26, 34)):
        t = nodes[-1]["t"] + timedelta(hours=rng.uniform(0.5, 4))
        hours = (t - root["t"]).total_seconds() / 3600
        if edit_times and hours >= edit_times[0]:
            edit_times.pop(0); gen = used_gens.pop(0)
            par = rng.choice([x for x in nodes if not x["ai"]])
            n = child(par, "fringe", rng.choice(editors), t, edit=(gen, rng.choice(["fire", "armed man", "crowd", "flag"])))   # desc draw kept for alignment; ai_region_look sets the stored one
            n["is_edit"] = gen; add(n); continue
        par = rng.choice(nodes[-8:] + [root])
        plat = rng.choice(["picshare", "chirp", "fringe", "msg", "chirp"])
        cred = outlet if (rng.random() < (0.5 if par["ai"] else 0.3)) else None
        add(child(par, plat, rng.choice(users[plat]), t, credits=cred))
    for n in nodes:
        emit(c, n)
    for n in nodes:
        if n.get("is_edit"): gt["patient_zero"].append(dict(cluster=c, generator=n["is_edit"], post=n["post"], account=str(n["acct"])))
        if n["parent"] is not None: gt["parent"][n["img"]] = n["parent"]["img"]
        gt["variant"][n["img"]] = sorted(n["ai"]); gt["cluster_of"][n["img"]] = c
        if n.get("credits") is not None and n["ai"]: gt["laundering_posts"].append(n["post"])
        if n["plat"] == "fringe" and not n.get("is_edit") and n["parent"] is not None:
            a = n["parent"]
            while a["plat"] == "fringe" and not a.get("is_edit") and a["parent"] is not None: a = a["parent"]
            gt["hop_source_platform"][n["post"]] = "editor_export" if a.get("is_edit") else a["plat"]
write(ds, f"{DATA}/world.trig")
json.dump(gt, open(f"{DATA}/ground_truth.json", "w"), indent=1)
print(len(ds), "quads;", n_img[0], "instances;", len(gt["patient_zero"]), "edits;", len(gt["laundering_posts"]), "laundering;", len(gt["hop_source_platform"]), "passthrough reposts")
