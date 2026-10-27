import json
from collections import Counter
def set_prf(pred, gold):
    pred, gold = set(pred), set(gold); tp = len(pred & gold)
    p = tp / len(pred) if pred else 0.0; r = tp / len(gold) if gold else 0.0
    return dict(tp=tp, fp=len(pred - gold), fn=len(gold - pred), precision=round(p, 3), recall=round(r, 3), f1=round(2*p*r/(p+r), 3) if p + r else 0.0)
def classify_report(pred, gold, labels):
    """pred/gold: dict item->label. Missing predictions count as wrong."""
    per = {}
    for L in labels:
        per[L] = set_prf([k for k, v in pred.items() if v == L], [k for k, v in gold.items() if v == L])
    acc = sum(pred.get(k) == v for k, v in gold.items()) / len(gold)
    conf = Counter((gold[k], pred.get(k, "missing")) for k in gold)
    return dict(accuracy=round(acc, 3), macro_f1=round(sum(x["f1"] for x in per.values()) / len(labels), 3), per_class=per,
                confusion={f"{g} -> {p}": n for (g, p), n in sorted(conf.items())})
