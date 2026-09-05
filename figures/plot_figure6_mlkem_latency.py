"""Figure 6: ML-KEM latency grouped bar chart (Table 15 / tab:crypto_benchmarks).

Encapsulation and decapsulation means ± SD are the published Table 15 values.
Key generation is included from the same 10,000-trial PQClean campaign
(omitted from the manuscript table) and rounded to the same 3-decimal style.

Usage
-----
    python plot_figure6_mlkem_latency.py
    python -m figures.plot_figure6_mlkem_latency
"""

from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FormatStrFormatter

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_ARTIFACTS = _THIS_DIR.parent
_MANUSCRIPT_ROOT = _ARTIFACTS.parent
_DEFAULT_OUT = _THIS_DIR / "output"
_MANUSCRIPT_FIGS = _MANUSCRIPT_ROOT / "figs"
STEM = "pqc_overhead_results"

# ---------------------------------------------------------------------------
# Table 15 encapsulate / decapsulate (verbatim). Keygen: same experiment,
# rounded to 3 decimals (summary.csv: 0.0944±0.0031, 0.1234±0.0034, 0.1607±0.0151).
# ---------------------------------------------------------------------------
OPERATIONS = ("Key generation", "Encapsulation", "Decapsulation")

SCHEMES = (
    {
        "legend": "ML-KEM-512 (NIST Level 1)",
        "color": "#aec7e8",
        "edge": "#7ea0c4",
        "mean": (0.094, 0.098, 0.056),
        "sd": (0.003, 0.003, 0.002),
        "baseline": False,
    },
    {
        "legend": "ML-KEM-768 (Proposed QRFL Baseline)",
        "color": "#1f77b4",
        "edge": "#155a8a",
        "mean": (0.123, 0.128, 0.091),
        "sd": (0.003, 0.004, 0.013),
        "baseline": True,
    },
    {
        "legend": "ML-KEM-1024 (NIST Level 5)",
        "color": "#43708a",
        "edge": "#2c4d60",
        "mean": (0.161, 0.175, 0.135),
        "sd": (0.015, 0.015, 0.008),
        "baseline": False,
    },
)

BAR_WIDTH = 0.24


def apply_publication_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "STIX Two Text", "DejaVu Serif"],
            "mathtext.fontset": "stix",
            "axes.labelsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "axes.linewidth": 0.8,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "xtick.major.size": 3.2,
            "ytick.major.size": 3.2,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.04,
            "axes.unicode_minus": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def plot_mlkem_latency(out_dir: Path | None = None, stem: str = STEM) -> tuple[plt.Figure, plt.Axes]:
    apply_publication_style()
    n_ops = len(OPERATIONS)
    n_sch = len(SCHEMES)
    x = np.arange(n_ops, dtype=float)
    offsets = (np.arange(n_sch) - (n_sch - 1) / 2.0) * (BAR_WIDTH + 0.02)

    fig, ax = plt.subplots(figsize=(6.5, 4.2), layout="constrained")

    ax.yaxis.grid(True, linestyle=":", color="#7a7a7a", alpha=0.25)
    ax.set_axisbelow(True)

    for i, spec in enumerate(SCHEMES):
        pos = x + offsets[i]
        means = np.asarray(spec["mean"], dtype=float)
        sds = np.asarray(spec["sd"], dtype=float)
        ax.bar(
            pos,
            means,
            width=BAR_WIDTH,
            color=spec["color"],
            edgecolor=spec["edge"],
            linewidth=0.7 if spec["baseline"] else 0.45,
            zorder=3,
            label=spec["legend"],
        )
        ax.errorbar(
            pos,
            means,
            yerr=sds,
            fmt="none",
            ecolor="#333333",
            elinewidth=1.2,
            capsize=4,
            capthick=1.2,
            zorder=4,
        )
        for px, mu, sd in zip(pos, means, sds):
            ax.text(
                px,
                mu + sd + 0.006,
                f"{mu:.3f}",
                ha="center",
                va="bottom",
                fontsize=8,
                color="#222222",
                zorder=5,
                clip_on=False,
            )

    ax.set_xticks(x)
    ax.set_xticklabels(OPERATIONS, rotation=0, ha="center")
    ax.set_xlim(x[0] - 0.55, x[-1] + 0.55)
    ax.set_ylabel("Execution Latency (ms)")
    ax.set_ylim(0.00, 0.22)
    ax.set_yticks(np.arange(0.00, 0.221, 0.04))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))
    ax.xaxis.grid(False)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    legend = ax.legend(
        loc="upper left",
        frameon=True,
        fancybox=False,
        framealpha=0.0,
        edgecolor="none",
        handlelength=1.35,
        borderpad=0.35,
        labelspacing=0.35,
    )
    for text, spec in zip(legend.get_texts(), SCHEMES):
        if spec["baseline"]:
            text.set_fontweight("bold")

    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_dir / f"{stem}.pdf")
        fig.savefig(out_dir / f"{stem}.png", dpi=300)

    print("schemes=3  operations=", OPERATIONS)
    return fig, ax


def copy_to_manuscript_figs(src_dir: Path, stem: str = STEM) -> None:
    if not _MANUSCRIPT_FIGS.exists():
        _MANUSCRIPT_FIGS.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        src = src_dir / f"{stem}.{ext}"
        if src.exists():
            shutil.copy2(src, _MANUSCRIPT_FIGS / f"{stem}.{ext}")


def main() -> None:
    fig, _ = plot_mlkem_latency(_DEFAULT_OUT)
    copy_to_manuscript_figs(_DEFAULT_OUT)
    plt.close(fig)
    print("Wrote:")
    for ext in ("pdf", "png"):
        print(f"  {_DEFAULT_OUT / f'{STEM}.{ext}'}")
        print(f"  {_MANUSCRIPT_FIGS / f'{STEM}.{ext}'}")


if __name__ == "__main__":
    main()
