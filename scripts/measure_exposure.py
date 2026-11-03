"""Stage 1 of the attack: does the poisoned product even reach the model?

No API calls. In the real plugin the model chooses the search keywords; here
each query carries a representative keyword string (`keywords` in
data/queries.json). Stage 2 replaces these with the keywords the model
actually picks.

Also checks that every payload survives the 300-character truncation of
the short description, since a truncated payload never reaches the model.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from attacks import GOALS, STYLES, poison  # noqa: E402
from retrieval import SHORT_DESC_LIMIT, search  # noqa: E402

catalog = json.loads((ROOT / "data" / "catalog.json").read_text())
queries = json.loads((ROOT / "data" / "queries.json").read_text())

# One poisoned listing per category, chosen in advance.
TARGET_IDS = [12, 18, 33, 36, 46]  # speaker, kettle, bottle, wallet, keyboard combo

# --- Exposure -------------------------------------------------------------
rows = []
for pid in TARGET_IDS:
    original = next(p for p in catalog if p["id"] == pid)
    for stuffed in (False, True):
        poisoned = poison(original, "ranking", "blunt", stuff_keywords=stuffed)
        cat = [poisoned if p["id"] == pid else p for p in catalog]
        hit = []
        for q in queries:
            results, _ = search(q["keywords"], cat)
            if any(p["id"] == pid for p in results):
                hit.append(q["id"])
        rows.append({"product": original["name"], "stuffed": stuffed,
                     "queries_hit": len(hit), "exposure_rate": len(hit) / len(queries)})

print(f"{'Poisoned product':40} {'Stuffed':8} {'Hit':>4} {'Exposure':>9}")
for r in rows:
    print(f"{r['product']:40} {str(r['stuffed']):8} {r['queries_hit']:>4} {r['exposure_rate']:>8.0%}")
for stuffed in (False, True):
    sub = [r["exposure_rate"] for r in rows if r["stuffed"] == stuffed]
    print(f"Mean exposure, stuffed={stuffed}: {sum(sub)/len(sub):.0%}")

# --- Payload survives truncation? ------------------------------------------
print("\nPayload length check (short description limit = 300 chars)")
longest = max(catalog, key=lambda p: len(p["name"]) + len(p["short_description"]))
fits = {}
for goal in GOALS:
    for style in STYLES:
        sd = poison(longest, goal, style)["short_description"]
        fits[f"{goal}/{style}"] = len(sd) <= SHORT_DESC_LIMIT
        print(f"  {goal:10} {style:12} {len(sd):>4} chars  {'fits' if fits[f'{goal}/{style}'] else 'TRUNCATED'}")

(ROOT / "results").mkdir(exist_ok=True)
(ROOT / "results" / "exposure.json").write_text(json.dumps({"exposure": rows, "payload_fits": fits}, indent=2))
