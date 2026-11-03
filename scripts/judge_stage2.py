"""Score every Stage 2 run and print the summary tables.

Usage:
  python scripts/judge_stage2.py                 # score new runs, then summarise
  python scripts/judge_stage2.py --summary-only  # just print tables
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from judge import score  # noqa: E402

RUNS = ROOT / "results" / "stage2" / "runs.jsonl"
SCORES = ROOT / "results" / "stage2" / "scores.jsonl"
JUDGE_MODEL = "claude-sonnet-5-5"


def load(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


def score_new():
    import anthropic
    client = anthropic.Anthropic(max_retries=5)
    scored = {s["run_id"] for s in load(SCORES)}
    with SCORES.open("a") as f:
        for r in load(RUNS):
            if r["run_id"] in scored or r["goal"] is None:
                continue
            s = score(client, JUDGE_MODEL, r["goal"], r["target_name"], r["query"], r["reply"], r["exposed"])
            s["run_id"] = r["run_id"]
            f.write(json.dumps(s) + "\n")
            f.flush()
            print(f"  {r['run_id']}: success={s['success']}")


def pct(n, d):
    return f"{n / d:.0%} ({n}/{d})" if d else "n/a"


def summarise():
    runs = {r["run_id"]: r for r in load(RUNS)}
    scores = {s["run_id"]: s for s in load(SCORES)}
    rows = [dict(runs[k], **scores[k]) for k in scores if k in runs]
    if not rows:
        print("No scored runs yet.")
        return

    print("\n== End-to-end attack success, by model and goal ==")
    by = defaultdict(lambda: [0, 0, 0, 0])  # success, total, exposed, success_given_exposed
    for r in rows:
        k = (r["model"], r["goal"])
        by[k][0] += r["success"]
        by[k][1] += 1
        by[k][2] += r["exposed"]
        by[k][3] += r["success"] and r["exposed"]
    print(f"{'model':20} {'goal':10} {'exposure':>14} {'hijack|exposed':>16} {'end-to-end':>14}")
    for (m, g), (s, t, e, se) in sorted(by.items()):
        print(f"{m:20} {g:10} {pct(e, t):>14} {pct(se, e):>16} {pct(s, t):>14}")

    print("\n== Hijack rate when exposed, by phrasing style ==")
    st = defaultdict(lambda: [0, 0])
    for r in rows:
        if r["exposed"]:
            st[(r["model"], r["style"])][0] += r["success"]
            st[(r["model"], r["style"])][1] += 1
    for (m, s), (a, b) in sorted(st.items()):
        print(f"{m:20} {s:12} {pct(a, b):>14}")

    flagged = [r for r in rows if r.get("flagged")]
    print(f"\nReplies that warned the shopper: {len(flagged)}/{len(rows)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary-only", action="store_true")
    a = ap.parse_args()
    if not a.summary_only:
        score_new()
    summarise()
