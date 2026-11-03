"""Draw the README charts from the numbers in the results files (hard-coded counts match docs/EXPERIMENTS.md)."""
import math
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent.parent / "docs" / "img"
INK, MUTED, GRID = "#1f2328", "#59636e", "#d8dee4"
BLUE, RED, GREEN = "#2f6fb3", "#c4432b", "#2b8a5c"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": GRID, "text.color": INK,
                     "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": INK})

def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); a = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return 100 * max(0, (c - a) / d), 100 * min(1, (c + a) / d)

def clean(ax):
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)

# Chart 1: hijack rate given the poisoned listing was read
rows = [("Claude Sonnet 5.5", 0, 561, BLUE), ("Claude Haiku 5.5", 0, 330, BLUE), ("gpt-5.5", 0, 330, BLUE),
        ("gpt-5.4-mini", 22, 330, RED), ("gpt-5.4-mini + system-prompt rule", 0, 326, GREEN),
        ("gpt-5.4-mini + delimited tool output", 1, 326, GREEN)]
fig, ax = plt.subplots(figsize=(9, 4.2), dpi=200)
for i, (name, k, n, col) in enumerate(rows):
    lo, hi = wilson(k, n); y = len(rows) - 1 - i; r = 100 * k / n
    ax.plot([lo, hi], [y, y], color=col, lw=2.5, solid_capstyle="round")
    ax.plot([r], [y], "o", color=col, ms=8, clip_on=False, zorder=3)
    ax.text(hi + 0.25, y, f"{k} of {n}  ({r:.1f}%)", va="center", fontsize=10, color=MUTED)
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows][::-1])
ax.set_xlim(0, 14); ax.set_xlabel("Share of attacks that hijacked the assistant (%), with 95% interval")
ax.set_title("How often an injected instruction was followed", loc="left", fontsize=13, fontweight="bold", pad=12)
clean(ax); fig.tight_layout(); fig.savefig(OUT / "hijack_rate.png", facecolor="white"); plt.close(fig)

# Chart 2: exposure
ex = [("Claude Sonnet 5.5", 192, 480), ("Claude Haiku 5.5", 33, 480), ("gpt-5.5", 37, 330), ("gpt-5.4-mini", 6, 330)]
fig, ax = plt.subplots(figsize=(9, 3.4), dpi=200)
for i, (name, k, n) in enumerate(ex):
    y = len(ex) - 1 - i; r = 100 * k / n
    ax.barh(y, r, color=BLUE, height=0.55)
    ax.text(r + 0.8, y, f"{r:.0f}%  ({k} of {n})", va="center", fontsize=10, color=MUTED)
ax.set_yticks(range(len(ex))); ax.set_yticklabels([e[0] for e in ex][::-1])
ax.set_xlim(0, 55); ax.set_xlabel("Share of conversations where the model's own search returned the poisoned listing (%)")
ax.set_title("Exposure: does the poisoned listing reach the model?", loc="left", fontsize=13, fontweight="bold", pad=12)
clean(ax); fig.tight_layout(); fig.savefig(OUT / "exposure.png", facecolor="white"); plt.close(fig)
print("ok")
