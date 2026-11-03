"""Compute the Stage 2 statistics and write results/summary.json (no API calls).

Reports, per model: exposure, hijack rate when exposed with a 95% Wilson interval,
end-to-end success, how often the assistant warned the shopper, how long replies get
under attack, and what drives exposure (category filters, multi-word searches).
"""
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "results" / "stage2" / "runs.jsonl"
SCORES = ROOT / "results" / "stage2" / "scores.jsonl"


def load(p):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0.0, c - h), min(1.0, c + h)]


def words(t):
    return len(t.split())


def main():
    runs = {r["run_id"]: r for r in load(RUNS)}
    scores = {s["run_id"]: s for s in load(SCORES)}
    models = sorted({r["model"] for r in runs.values()})
    goals = ["ranking", "disparage", "phishing", "leak"]
    styles = ["blunt", "fake_system", "subtle"]
    out = {"models": {}, "n_runs": len(runs), "n_scored": len(scores)}

    for m in models:
        att = [(runs[k], scores[k]) for k in scores if runs[k]["model"] == m]
        clean = [r for r in runs.values() if r["model"] == m and r["goal"] is None]
        exp = [(r, s) for r, s in att if r["exposed"]]
        unexp = [(r, s) for r, s in att if not r["exposed"]]
        d = {
            "attacked_runs": len(att), "clean_runs": len(clean),
            "exposed": len(exp), "exposure_rate": len(exp) / len(att),
            "exposure_ci": wilson(len(exp), len(att)),
            "hijacks": sum(s["success"] for _, s in att),
            "hijack_given_exposed": sum(s["success"] for _, s in exp) / len(exp) if exp else None,
            "hijack_ci": wilson(sum(s["success"] for _, s in exp), len(exp)),
            "flagged_given_exposed": sum(s["flagged"] for _, s in exp) / len(exp) if exp else None,
            "string_only_matches": sum(s.get("det_success", False) and not s["success"] for _, s in att),
            "words_clean": sum(words(r["reply"]) for r in clean) / len(clean),
            "words_attacked_unexposed": sum(words(r["reply"]) for r, _ in unexp) / len(unexp) if unexp else None,
            "words_attacked_exposed": sum(words(r["reply"]) for r, _ in exp) / len(exp) if exp else None,
            "by_goal": {}, "by_style": {},
        }
        for g in goals:
            a = [(r, s) for r, s in att if r["goal"] == g]
            e = [(r, s) for r, s in a if r["exposed"]]
            d["by_goal"][g] = {"n": len(a), "exposed": len(e), "hijacks": sum(s["success"] for _, s in a),
                               "flagged": sum(s["flagged"] for _, s in e)}
        for st in styles:
            a = [(r, s) for r, s in att if r["style"] == st]
            e = [(r, s) for r, s in a if r["exposed"]]
            d["by_style"][st] = {"n": len(a), "exposed": len(e), "hijacks": sum(s["success"] for _, s in a),
                                 "flagged": sum(s["flagged"] for _, s in e)}
        searches = [x["input"] for r in runs.values() if r["model"] == m for x in r["searches"]]
        d["searches"] = len(searches)
        d["search_with_category"] = sum("category" in x for x in searches) / len(searches)
        d["search_multiword"] = sum(len(x.get("keywords", "").split()) > 1 for x in searches) / len(searches)
        d["clean_exposed"] = sum(r["exposed"] for r in clean)
        out["models"][m] = d

    (ROOT / "results" / "summary.json").write_text(json.dumps(out, indent=2))
    for m, d in out["models"].items():
        ci = d["hijack_ci"]
        print(f"\n{m}")
        print(f"  exposure          {d['exposure_rate']:.0%}  ({d['exposed']}/{d['attacked_runs']})")
        print(f"  hijack | exposed  {d['hijacks']}/{d['exposed']}  95% CI {ci[0]:.1%}-{ci[1]:.1%}")
        print(f"  warned shopper    {d['flagged_given_exposed']:.0%} of exposed")
        print(f"  string-only false matches (refusals quoting the offer): {d['string_only_matches']}")
        print(f"  reply words       clean {d['words_clean']:.0f} | attacked, unexposed {d['words_attacked_unexposed']:.0f} | attacked, exposed {d['words_attacked_exposed']:.0f}")
        print(f"  searches          {d['search_with_category']:.0%} use a category filter, {d['search_multiword']:.0%} are multi-word")


if __name__ == "__main__":
    main()
