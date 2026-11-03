"""Stage 1 of the attack: does the poisoned product even reach the model?

No API calls; this only runs the keyword search. For each poisoned product,
with and without keyword stuffing, count how many of the 40 user queries
retrieve it in the top-k results.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from attacks import poison  # noqa: E402
from retrieval import search  # noqa: E402

catalog = json.loads((ROOT / "data" / "catalog.json").read_text())
queries = json.loads((ROOT / "data" / "queries.json").read_text())

# One poisoned product per category, chosen in advance (the "attacker's listings").
TARGET_IDS = [12, 18, 33, 36, 46]  # speaker, kettle, bottle, wallet, keyboard combo
TOP_K = 5

rows = []
for pid in TARGET_IDS:
    original = next(p for p in catalog if p["id"] == pid)
    for stuffed in (False, True):
        poisoned = poison(original, "ranking", "blunt", stuff_keywords=stuffed)
        cat = [poisoned if p["id"] == pid else p for p in catalog]
        hits = [q["id"] for q in queries if any(p["id"] == pid for p in search(q["text"], cat, TOP_K))]
        rows.append({"product": original["name"], "stuffed": stuffed,
                     "queries_hit": len(hits), "exposure_rate": len(hits) / len(queries)})

print(f"{'Poisoned product':40} {'Stuffed':8} {'Hit':>4} {'Exposure':>9}")
for r in rows:
    print(f"{r['product']:40} {str(r['stuffed']):8} {r['queries_hit']:>4} {r['exposure_rate']:>8.0%}")

for stuffed in (False, True):
    sub = [r["exposure_rate"] for r in rows if r["stuffed"] == stuffed]
    print(f"\nMean exposure, stuffed={stuffed}: {sum(sub)/len(sub):.0%}")

(ROOT / "results").mkdir(exist_ok=True)
(ROOT / "results" / "exposure.json").write_text(json.dumps(rows, indent=2))
