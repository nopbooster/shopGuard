"""Stage 2b: FORCED exposure pilot.

Exposure is guaranteed: for each query we poison the product that genuinely matches it
(first result of the query's reference keywords), so the model has to read the payload
to do its job. This isolates hijack rate from retrieval luck.

Goals: disparage, phishing, leak (ranking is meaningless when the poisoned item is the right answer).
Each query gets one (goal, style) assignment, rotated, same for every model.

Usage: python scripts/run_forced.py [--models ...] [--workers 6]
"""
import argparse, json, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import anthropic  # noqa: E402
from assistant import chat_turn  # noqa: E402
from attacks import poison  # noqa: E402
from judge import score  # noqa: E402
from retrieval import search  # noqa: E402

OUT = ROOT / "results" / "stage2_forced" / "runs.jsonl"
GOALS = ["disparage", "phishing", "leak"]
STYLES = ["blunt", "fake_system", "subtle"]

ap = argparse.ArgumentParser()
ap.add_argument("--models", nargs="+", default=["claude-sonnet-5-5", "claude-haiku-5-5"])
ap.add_argument("--workers", type=int, default=6)
a = ap.parse_args()

catalog = json.loads((ROOT / "data" / "catalog.json").read_text())
queries = json.loads((ROOT / "data" / "queries.json").read_text())
client = anthropic.Anthropic(max_retries=5)
done = {json.loads(l)["run_id"] for l in OUT.read_text().splitlines() if l.strip()} if OUT.exists() else set()

jobs = []
for i, q in enumerate(queries):
    res, _ = search(q["keywords"], catalog)
    if not res:
        continue
    tgt = res[0]
    goal, style = GOALS[i % 3], STYLES[(i // 3) % 3]
    for m in a.models:
        rid = f"{m}|forced|{goal}/{style}|{q['id']}"
        if rid not in done:
            jobs.append((rid, m, q, tgt, goal, style))
print(f"{len(jobs)} runs to do ({len(done)} done)")
lock = threading.Lock()

def one(j):
    rid, m, q, tgt, goal, style = j
    bad = poison(tgt, goal, style)
    cat = [bad if p["id"] == tgt["id"] else p for p in catalog]
    rec = chat_turn(client, m, cat, q["text"])
    exposed = tgt["id"] in rec["retrieved_ids"]
    s = score(client, "claude-sonnet-5-5", goal, tgt["name"], q["text"], rec["reply"], exposed)
    row = {"run_id": rid, "model": m, "goal": goal, "style": style, "query_id": q["id"], "query": q["text"],
           "target_id": tgt["id"], "target_name": tgt["name"], "exposed": exposed, "searches": rec["searches"],
           "reply": rec["reply"], "success": s["success"], "flagged": s["flagged"], "reason": s["reason"],
           "det_success": s.get("det_success"), "llm_success": s.get("llm_success")}
    with lock, OUT.open("a") as f:
        f.write(json.dumps(row) + "\n")
    print(rid, "exposed" if exposed else "not-exposed", "HIJACKED" if s["success"] else "ok", flush=True)

with ThreadPoolExecutor(a.workers) as p:
    list(p.map(lambda j: (lambda: one(j))() , jobs))
