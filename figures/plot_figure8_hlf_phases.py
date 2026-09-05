"""Figure 8: stacked HLF v2.5 lifecycle latencies (Table 19 / tab:ledger_latency).

Endorsement, ordering, and validation/commit phases under Classical, Hybrid,
and Native PQ. Values are taken verbatim from the manuscript table.

Usage
-----
    python plot_figure8_hlf_phases.py
    python -m figures.plot_figure8_hlf_phases
"""

from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MultipleLocator

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_ARTIFACTS = _THIS_DIR.parent
_MANUSCRIPT_ROOT = _ARTIFACTS.parent
_DEFAULT_OUT = _THIS_DIR / "output"
_MANUSCRIPT_FIGS = _MANUSCRIPT_ROOT / "figs"
STEM = "hlf_phase_latencies"

# ---------------------------------------------------------------------------
# Table 19 / Table~\ref{tab:ledger_latency} (verbatim)
# ---------------------------------------------------------------------------
CONFIGS = (
    "Classical (ECDSA)",
    "Hybrid (ECDSA + ML-DSA)",
    "Native PQ (ML-DSA-65)",
)
ENDORSEMENT = np.array([25.4, 28.4, 28.3])
ORDERING = np.array([40.2, 40.2, 40.2])
VALIDATION = np.array([15.3, 16.0, 15.7])
TOTALS = np.array([80.8, 84.6, 84.2])
TOP_NOTES = ("80.8 ms\n(Baseline)", "84.6 ms\n(+4.7%)", "84.2 ms\n(+4.2%)")

COLOR_END = "#1f4e79"
COLOR_ORD = "#d99b26"
COLOR_VAL = "#2e7d5a"
EDGE = "white"
BAR_WIDTH = 0.52


def apply_publication_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "STIX Two Text", "DejaVu Serif"],
            "mathtext.fontset": "stix",
            "axes.labelsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 9,
            "legend.fontsize": 10,
            "axes.linewidth": 0.8,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "xtick.major.size": 3.2,
            "ytick.major.size": 3.2,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.05,
            "axes.unicode_minus": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def plot_hlf_stacked(out_dir: Path | None = None, stem: str = STEM) -> tuple[plt.Figure, plt.Axes]:
    apply_publication_style()
    x = np.arange(len(CONFIGS), dtype=float)
    phases = (
        ("Endorsement", ENDORSEMENT, COLOR_END, "white"),
        ("Ordering", ORDERING, COLOR_ORD, "#1a1a1a"),
        ("Validation & Commit", VALIDATION, COLOR_VAL, "white"),
    )

    fig, ax = plt.subplots(figsize=(6.8, 4.8), layout="constrained")
    ax.yaxis.grid(True, linestyle="--", color="#7a7a7a", alpha=0.3, zorder=0)
    ax.set_axisbelow(True)

    bottom = np.zeros(len(CONFIGS))
    for label, heights, color, tcolor in phases:
        ax.bar(
            x,
            heights,
            bottom=bottom,
            width=BAR_WIDTH,
            color=color,
            edgecolor=EDGE,
            linewidth=0.8,
            label=label,
            zorder=3,
        )
        for xi, h, b in zip(x, heights, bottom):
            ax.text(
                xi,
                b + h / 2.0,
                f"{h:.1f}",
                ha="center",
                va="center",
                fontsize=9,
                fontweight="bold",
                color=tcolor,
                zorder=5,
            )
        bottom = bottom + heights

    ax.plot(
        [x[0], x[-1] + 0.62],
        [TOTALS[0], TOTALS[0]],
        color="#6e6e6e",
        linestyle="--",
        linewidth=0.95,
        zorder=4,
        solid_capstyle="butt",
    )

    for xi, total, note in zip(x, TOTALS, TOP_NOTES):
        ax.text(
            xi,
            total + 2.2,
            note,
            ha="center",
            va="bottom",
            fontsize=9,
            color="#222222",
            linespacing=1.25,
            zorder=6,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(CONFIGS, fontsize=10)
    ax.set_xlim(-0.55, 2.65)
    ax.set_ylabel("Transaction Latency (ms)")
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_locator(MultipleLocator(20))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=3,
        frameon=False,
        handlelength=1.25,
        columnspacing=1.4,
        borderaxespad=0.15,
    )

    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_dir / f"{stem}.pdf")
        fig.savefig(out_dir / f"{stem}.png", dpi=300)

    print(f"totals={list(TOTALS)}  phases=endorsement/ordering/validation")
    return fig, ax


def copy_to_manuscript_figs(src_dir: Path, stem: str = STEM) -> None:
    if not _MANUSCRIPT_FIGS.exists():
        _MANUSCRIPT_FIGS.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        src = src_dir / f"{stem}.{ext}"
        if src.exists():
            shutil.copy2(src, _MANUSCRIPT_FIGS / f"{stem}.{ext}")


def main() -> None:
    fig, _ = plot_hlf_stacked(_DEFAULT_OUT)
    copy_to_manuscript_figs(_DEFAULT_OUT)
    plt.close(fig)
    print("Wrote:")
    for ext in ("pdf", "png"):
        print(f"  {_DEFAULT_OUT / f'{STEM}.{ext}'}")
        print(f"  {_MANUSCRIPT_FIGS / f'{STEM}.{ext}'}")


if __name__ == "__main__":
    main()
