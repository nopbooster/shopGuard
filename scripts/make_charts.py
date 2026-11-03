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
# Chart 3: defence effect by framing (gpt-5.4-mini, 33 runs per framing and condition, 32-33 with defences)
frames = ["Spoofed tool result", "Legal urgency", "XML system tag", "Verified owner"]
none = [11, 8, 2, 1]; delim = [0, 1, 0, 0]; inst = [0, 0, 0, 0]
import numpy as np
fig, ax = plt.subplots(figsize=(9, 3.8), dpi=200)
x = np.arange(len(frames)); w = 0.26
for off, vals, col, lab in ((-w, none, RED, "No defence"), (0, delim, GREEN, "Delimited tool output"), (w, inst, "#1b5e3f", "System-prompt rule")):
    ax.bar(x + off, vals, w, color=col, label=lab)
    for xi, v in zip(x + off, vals): ax.text(xi, v + 0.2, str(v), ha="center", fontsize=10, color=MUTED)
ax.set_xticks(x); ax.set_xticklabels(frames); ax.set_ylabel("Hijacked runs (of about 33 per framing)")
ax.set_ylim(0, 13); ax.legend(frameon=False, loc="upper right")
ax.set_title("gpt-5.4-mini: hijacks by framing, with and without a defence", loc="left", fontsize=13, fontweight="bold", pad=12)
for s in ("top", "right"): ax.spines[s].set_visible(False)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
fig.tight_layout(); fig.savefig(OUT / "defences.png", facecolor="white"); plt.close(fig)

# Chart 4: reply length when the assistant meets an injection
fig, ax = plt.subplots(figsize=(9, 3.2), dpi=200)
labels = ["Claude Sonnet 5.5", "Claude Haiku 5.5"]; base = [28.1, 24.1]; atk = [52.6, 32.6]
x = np.arange(2); w = 0.32
ax.bar(x - w / 2, base, w, color=BLUE, label="No attack")
ax.bar(x + w / 2, atk, w, color=RED, label="Attack read by the model")
for xi, v in list(zip(x - w / 2, base)) + list(zip(x + w / 2, atk)): ax.text(xi, v + 1.2, f"{v:.0f}", ha="center", fontsize=10, color=INK, bbox=dict(fc="white", ec="none", pad=1))
ax.axhline(30, color=MUTED, ls="--", lw=1); ax.set_xlim(-0.6, 2.25); ax.text(2.22, 31.5, "shop's 30-word rule", ha="right", fontsize=9, color=MUTED)
ax.set_xticks(x); ax.set_xticklabels(labels); ax.set_ylabel("Mean reply length (words)"); ax.set_ylim(0, 62)
ax.legend(frameon=False, loc="upper center")
ax.set_title("Failed attacks still change the reply: Sonnet explains the hidden text", loc="left", fontsize=13, fontweight="bold", pad=12)
for s in ("top", "right"): ax.spines[s].set_visible(False)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
fig.tight_layout(); fig.savefig(OUT / "reply_length.png", facecolor="white"); plt.close(fig)
print("ok")
