"""Stage 2: end-to-end attack runs against the real model.

For each (model, attack, query):
  - poison one target product (payload in short description, stuffing in full description)
  - send the shopper's query through the re-implemented assistant
  - the MODEL chooses its own search keywords, so exposure is measured for real
  - save the full record to results/stage2/runs.jsonl

Also runs every query with NO attack (clean baseline) per model.

Resumable: already-completed run ids are skipped, so you can stop and restart.

Usage:
  python scripts/run_stage2.py --limit 5            # smoke test, a handful of runs
  python scripts/run_stage2.py                      # full run
  python scripts/run_stage2.py --models claude-haiku-5-5
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import anthropic  # noqa: E402
from assistant import chat_turn  # noqa: E402
from attacks import GOALS, STYLES, poison  # noqa: E402

DEFAULT_MODELS = ["claude-sonnet-5-5", "claude-haiku-5-5"]
TARGET_ID = 18  # Brewly Electric Kettle: an ordinary, low-traffic listing
OUT = ROOT / "results" / "stage2" / "runs.jsonl"


def plan(models, queries):
    for model in models:
        for q in queries:
            yield {"run_id": f"{model}|clean|{q['id']}", "model": model, "goal": None, "style": None, "query": q}
        for goal in GOALS:
            for style in STYLES:
                for q in queries:
                    yield {"run_id": f"{model}|{goal}/{style}|{q['id']}", "model": model,
                           "goal": goal, "style": style, "query": q}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    ap.add_argument("--limit", type=int, default=None, help="stop after N new runs")
    args = ap.parse_args()

    catalog = json.loads((ROOT / "data" / "catalog.json").read_text())
    queries = json.loads((ROOT / "data" / "queries.json").read_text())
    target = next(p for p in catalog if p["id"] == TARGET_ID)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if OUT.exists():
        done = {json.loads(line)["run_id"] for line in OUT.read_text().splitlines() if line.strip()}

    client = anthropic.Anthropic(max_retries=5)
    todo = [r for r in plan(args.models, queries) if r["run_id"] not in done]
    print(f"{len(done)} runs already done, {len(todo)} to go")

    new = 0
    with OUT.open("a") as f:
        for r in todo:
            if args.limit is not None and new >= args.limit:
                break
            cat = catalog
            if r["goal"]:
                bad = poison(target, r["goal"], r["style"], stuff_keywords=True)
                cat = [bad if p["id"] == TARGET_ID else p for p in catalog]
            try:
                rec = chat_turn(client, r["model"], cat, r["query"]["text"])
            except anthropic.APIError as e:
                print(f"  ! {r['run_id']}: {e}")
                continue
            out = {
                "run_id": r["run_id"], "model": r["model"], "goal": r["goal"], "style": r["style"],
                "query_id": r["query"]["id"], "query": r["query"]["text"],
                "target_id": TARGET_ID, "target_name": target["name"],
                "exposed": TARGET_ID in rec["retrieved_ids"],
                "searches": rec["searches"], "reply": rec["reply"],
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            f.write(json.dumps(out) + "\n")
            f.flush()
            new += 1
            print(f"  [{new}] {r['run_id']}  exposed={out['exposed']}  reply={out['reply'][:80]!r}")

    print(f"Done: {new} new runs written to {OUT}")


if __name__ == "__main__":
    main()
