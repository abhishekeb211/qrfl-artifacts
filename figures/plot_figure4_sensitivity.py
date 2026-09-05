"""Figure 4: multi-parameter timeline sensitivity (Table 10 / tab:sensitivity_matrix).

Crossing years vs physical-to-logical overhead η for three Shor thresholds.
Values are taken verbatim from the manuscript table; they are not refit.

Usage
-----
    python plot_figure4_sensitivity.py
    python -m figures.plot_figure4_sensitivity
"""

from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.ticker import MultipleLocator, NullLocator, ScalarFormatter

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_ARTIFACTS = _THIS_DIR.parent
_MANUSCRIPT_ROOT = _ARTIFACTS.parent
_DEFAULT_OUT = _THIS_DIR / "output"
_MANUSCRIPT_FIGS = _MANUSCRIPT_ROOT / "figs"
STEM = "sensitivity_analysis"

# ---------------------------------------------------------------------------
# Table 10 / Table~\ref{tab:sensitivity_matrix} (verbatim)
# ---------------------------------------------------------------------------
ETA = np.array([500, 1000, 1500, 2000, 3000, 5000], dtype=float)
ECDSA_2330 = np.array([2047.24, 2049.10, 2050.19, 2050.97, 2052.06, 2053.43])
RSA_3072 = np.array([2048.76, 2050.62, 2051.71, 2052.48, 2053.57, 2054.94])
RSA_4096 = np.array([2051.16, 2053.02, 2054.11, 2054.88, 2055.97, 2057.34])

HNDL_YEAR = 2041.0
BASELINE_ETA = 1500.0
BASELINE_YEAR = 2050.19

LABEL_ECDSA = r"Shor ECDSA-256 ($Q^{*}\!=\!2{,}330$)"
LABEL_RSA3072 = r"Shor RSA-3072 ($Q^{*}\!=\!4{,}096$)"
LABEL_RSA4096 = r"Shor RSA-4096 ($Q^{*}\!=\!10{,}000$)"

COLOR_ECDSA = "#1f77b4"
COLOR_RSA3072 = "#2ca02c"
COLOR_RSA4096 = "#ff7f0e"
COLOR_HNDL = "#d62728"


def apply_publication_style() -> None:
    sns.set_theme(style="ticks", context="paper")
    mpl.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "STIX Two Text", "DejaVu Serif"],
            "mathtext.fontset": "stix",
            "axes.labelsize": 11,
            "axes.titlesize": 11,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "axes.linewidth": 0.8,
            "lines.linewidth": 1.7,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "xtick.major.size": 3.4,
            "ytick.major.size": 3.4,
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


def long_form_table() -> pd.DataFrame:
    rows = []
    for eta, y in zip(ETA, ECDSA_2330):
        rows.append({"eta": eta, "crossing_year": y, "curve": LABEL_ECDSA})
    for eta, y in zip(ETA, RSA_3072):
        rows.append({"eta": eta, "crossing_year": y, "curve": LABEL_RSA3072})
    for eta, y in zip(ETA, RSA_4096):
        rows.append({"eta": eta, "crossing_year": y, "curve": LABEL_RSA4096})
    return pd.DataFrame(rows)


def plot_sensitivity_sweep(out_dir: Path | None = None, stem: str = STEM) -> tuple[plt.Figure, plt.Axes]:
    apply_publication_style()
    df = long_form_table()
    palette = {
        LABEL_ECDSA: COLOR_ECDSA,
        LABEL_RSA3072: COLOR_RSA3072,
        LABEL_RSA4096: COLOR_RSA4096,
    }
    markers = {LABEL_ECDSA: "o", LABEL_RSA3072: "s", LABEL_RSA4096: "D"}

    fig, ax = plt.subplots(figsize=(7.5, 4.5), layout="constrained")

    # HNDL risk band and Mosca deadline (drawn first).
    y_bottom = 2040.0
    ax.axhspan(y_bottom, HNDL_YEAR, facecolor=COLOR_HNDL, alpha=0.10, zorder=0, linewidth=0)
    ax.axhline(HNDL_YEAR, color=COLOR_HNDL, ls="--", lw=1.35, zorder=2)

    sns.lineplot(
        data=df,
        x="eta",
        y="crossing_year",
        hue="curve",
        style="curve",
        palette=palette,
        markers=markers,
        dashes=False,
        linewidth=1.85,
        markersize=8.5,
        markeredgecolor="white",
        markeredgewidth=0.45,
        ax=ax,
        zorder=4,
        legend=True,
    )

    # Baseline operating point (η = 1500, ECDSA-256).
    ax.scatter(
        [BASELINE_ETA],
        [BASELINE_YEAR],
        s=160,
        facecolors="none",
        edgecolors=COLOR_ECDSA,
        linewidths=1.7,
        zorder=6,
        clip_on=False,
    )
    ax.annotate(
        r"Baseline: $\eta=1500$, ECDSA-256" "\n" r"crossing $=2050.19$",
        xy=(BASELINE_ETA, BASELINE_YEAR),
        xytext=(2300, 2045.15),
        fontsize=9,
        ha="left",
        va="center",
        color="#1a1a1a",
        arrowprops={
            "arrowstyle": "-|>",
            "color": "#444444",
            "lw": 0.9,
            "shrinkA": 0,
            "shrinkB": 4,
        },
        zorder=7,
        bbox={
            "boxstyle": "round,pad=0.28",
            "facecolor": "white",
            "edgecolor": "#c8c8c8",
            "linewidth": 0.55,
            "alpha": 0.96,
        },
    )

    ax.text(
        520,
        HNDL_YEAR + 0.28,
        r"HNDL Migration Deadline (2041, Mosca $X{+}Y$)",
        ha="left",
        va="bottom",
        fontsize=9,
        color=COLOR_HNDL,
        zorder=5,
    )

    ax.set_xscale("log")
    ax.set_xlim(430, 5800)
    ax.set_xticks(list(ETA))
    ax.xaxis.set_major_formatter(ScalarFormatter())
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xlabel(r"Physical-to-logical overhead $\eta$")

    # Zoomed calendar-year window; 2040 lower bound keeps the 2041 HNDL line visible.
    ax.set_ylim(y_bottom, 2060.35)
    ax.yaxis.set_major_locator(MultipleLocator(2))
    ax.set_ylabel("Crossing year")

    ax.grid(True, which="major", linestyle=":", color="#7a7a7a", alpha=0.3)
    ax.set_axisbelow(True)
    sns.despine(ax=ax, top=True, right=True)

    legend = ax.legend(
        title=None,
        loc="upper left",
        frameon=True,
        fancybox=False,
        edgecolor="#c8c8c8",
        framealpha=0.96,
        handlelength=1.8,
        borderpad=0.45,
        labelspacing=0.35,
    )
    legend.get_frame().set_linewidth(0.55)

    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_dir / f"{stem}.pdf")
        fig.savefig(out_dir / f"{stem}.png", dpi=300)

    print(
        f"points={df.shape[0]}  "
        f"baseline=({BASELINE_ETA:.0f}, {BASELINE_YEAR:.2f})  "
        f"HNDL={HNDL_YEAR:.0f}"
    )
    return fig, ax


def copy_to_manuscript_figs(src_dir: Path, stem: str = STEM) -> None:
    if not _MANUSCRIPT_FIGS.exists():
        _MANUSCRIPT_FIGS.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        src = src_dir / f"{stem}.{ext}"
        if src.exists():
            shutil.copy2(src, _MANUSCRIPT_FIGS / f"{stem}.{ext}")


def main() -> None:
    fig, _ = plot_sensitivity_sweep(_DEFAULT_OUT)
    copy_to_manuscript_figs(_DEFAULT_OUT)
    plt.close(fig)
    print("Wrote:")
    for ext in ("pdf", "png"):
        print(f"  {_DEFAULT_OUT / f'{STEM}.{ext}'}")
        print(f"  {_MANUSCRIPT_FIGS / f'{STEM}.{ext}'}")


if __name__ == "__main__":
    main()
