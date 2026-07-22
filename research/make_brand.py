"""Banner and logo for the challenge Project Page.

Same palette as the console, so the page, the app and the video read as one thing.
The motif is the thing the project is about: a row of registry revisions where one
of them is red because the sponsor filed a date that had already passed.

    python3 research/make_brand.py [banner_w banner_h]

Regenerate at any size if the platform wants different dimensions.
"""
from __future__ import annotations

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_HERE = os.path.dirname(__file__)
OUT = os.path.join(_HERE, "figures")

BG = "#0d1117"
INK = "#c9d1d9"
MUTED = "#8b949e"
GREEN = "#4ade80"
RED = "#f85149"
LINE = "#30363d"


def banner(width_px: int = 1120, height_px: int = 300) -> str:
    dpi = 100
    fig, ax = plt.subplots(figsize=(width_px / dpi, height_px / dpi), facecolor=BG, dpi=dpi)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # The timeline motif: five revisions, the third one carried an expired date.
    xs = [67, 74, 81, 88, 95]
    y = 52
    ax.plot([xs[0], xs[-1]], [y, y], color=LINE, linewidth=1.6, zorder=1)
    for i, x in enumerate(xs):
        if i == 2:
            ax.scatter([x], [y], s=340, color=RED, marker="s", zorder=3)
            ax.annotate("677 days expired", xy=(x, y), xytext=(0, 15),
                        textcoords="offset points", ha="center",
                        color=RED, fontsize=10, fontweight="bold")
        else:
            ax.scatter([x], [y], s=150, color=GREEN, marker="o", zorder=2)

    ax.text(6, 72, "CATALYST INTEGRITY DESK", color=INK, fontsize=25,
            fontweight="bold", family="monospace", va="center")
    ax.text(6, 50, "the dates biotech theses rest on, audited", color=MUTED,
            fontsize=13.5, family="monospace", va="center")
    ax.text(6, 28, "Python computes  ·  Granite judges prose  ·  humans decide",
            color=MUTED, fontsize=10.5, family="monospace", va="center")

    path = os.path.join(OUT, f"banner_{width_px}x{height_px}.png")
    os.makedirs(OUT, exist_ok=True)
    fig.savefig(path, dpi=dpi, facecolor=BG, bbox_inches=None, pad_inches=0)
    plt.close(fig)
    return path


def logo(size_px: int = 512) -> str:
    dpi = 100
    fig, ax = plt.subplots(figsize=(size_px / dpi, size_px / dpi), facecolor=BG, dpi=dpi)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Three revisions stacked, the middle one red. Legible at favicon size.
    ax.plot([14, 86], [58, 58], color=LINE, linewidth=7, zorder=1)
    ax.scatter([14], [58], s=1500, color=GREEN, marker="o", zorder=2)
    ax.scatter([50], [58], s=5200, color=RED, marker="s", zorder=3)
    ax.scatter([86], [58], s=1500, color=GREEN, marker="o", zorder=2)
    ax.text(50, 20, "677d", color=RED, fontsize=44, fontweight="bold",
            family="monospace", ha="center", va="center")

    path = os.path.join(OUT, f"logo_{size_px}.png")
    os.makedirs(OUT, exist_ok=True)
    fig.savefig(path, dpi=dpi, facecolor=BG, bbox_inches=None, pad_inches=0)
    plt.close(fig)
    return path


if __name__ == "__main__":
    w = int(sys.argv[1]) if len(sys.argv) > 1 else 1120
    h = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    print("banner:", banner(w, h))
    print("logo  :", logo())
