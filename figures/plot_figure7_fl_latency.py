"""Figure 7: two-panel FL scalability and Native-PQ overhead (Table 17 / tab:fl_latency).

Panel (a): end-to-end mean round latency vs client count (mean ± 1 SD).
Panel (b): Native PQ latency delta vs Classical (%).
All numeric values are taken verbatim from the manuscript table.

Usage
-----
    python plot_figure7_fl_latency.py
    python -m figures.plot_figure7_fl_latency
"""

from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FormatStrFormatter, MultipleLocator

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_ARTIFACTS = _THIS_DIR.parent
_MANUSCRIPT_ROOT = _ARTIFACTS.parent
_DEFAULT_OUT = _THIS_DIR / "output"
_MANUSCRIPT_FIGS = _MANUSCRIPT_ROOT / "figs"
STEM = "fl_overhead_results"

# ---------------------------------------------------------------------------
# Table 17 / Table~\ref{tab:fl_latency}
# FedAvg + attack=none + α=1.0 only (same filter as emit_tables._mode_stats).
# Fallback constants match the last regenerated table if the CSV is absent.
# ---------------------------------------------------------------------------
CLIENTS = np.array([5, 10, 25, 50], dtype=float)

CLASSICAL_MEAN = np.array([16.70, 17.09, 19.06, 24.70])
CLASSICAL_SD = np.array([0.18, 0.17, 0.28, 0.37])

HYBRID_MEAN = np.array([16.73, 17.07, 19.01, 24.82])
HYBRID_SD = np.array([0.18, 0.20, 0.29, 0.24])

NATIVE_MEAN = np.array([16.73, 17.06, 18.96, 24.78])
NATIVE_SD = np.array([0.18, 0.15, 0.27, 0.37])

NATIVE_OVERHEAD_PCT = np.array([0.17, -0.15, -0.53, 0.34])


def _load_latency_from_csv() -> None:
    """Overwrite module-level arrays from all_results.csv when available."""
    global CLASSICAL_MEAN, CLASSICAL_SD, HYBRID_MEAN, HYBRID_SD
    global NATIVE_MEAN, NATIVE_SD, NATIVE_OVERHEAD_PCT
    csv_path = _ARTIFACTS / "results" / "fl" / "all_results.csv"
    if not csv_path.exists():
        return
    import pandas as pd

    df = pd.read_csv(csv_path)
    c_m, c_s, h_m, h_s, n_m, n_s, oh = [], [], [], [], [], [], []
    for nc in CLIENTS.astype(int):
        row = {}
        for mode in ("classical", "hybrid_pq", "native_pq"):
            sub = df[
                (df["security_mode"] == mode)
                & (df["attack"] == "none")
                & (df["malicious_fraction"] == 0.0)
                & (df["aggregator"] == "fedavg")
                & (df["num_clients"] == nc)
                & (df["alpha"] == 1.0)
            ]
            if sub.empty:
                return
            row[mode] = (
                float(sub["mean_round_latency_s"].mean()),
                float(sub["mean_round_latency_s"].std(ddof=1)),
            )
        c_m.append(row["classical"][0])
        c_s.append(row["classical"][1])
        h_m.append(row["hybrid_pq"][0])
        h_s.append(row["hybrid_pq"][1])
        n_m.append(row["native_pq"][0])
        n_s.append(row["native_pq"][1])
        base = row["classical"][0]
        oh.append(((row["native_pq"][0] - base) / base * 100.0) if base > 0 else 0.0)
    CLASSICAL_MEAN = np.array(c_m)
    CLASSICAL_SD = np.array(c_s)
    HYBRID_MEAN = np.array(h_m)
    HYBRID_SD = np.array(h_s)
    NATIVE_MEAN = np.array(n_m)
    NATIVE_SD = np.array(n_s)
    NATIVE_OVERHEAD_PCT = np.array(oh)


_load_latency_from_csv()

# Horizontal jitter so overlapping whiskers remain readable (clients are 5–50).
JITTER = (-0.4, 0.0, 0.4)

COLOR_CLASSICAL = "#1f4e79"
COLOR_HYBRID = "#e69f00"
COLOR_NATIVE = "#009e73"
COLOR_POS = "#e89b9b"
COLOR_NEG = "#7ec8bc"
COLOR_ZERO = "#555555"
COLOR_WINDOW = "#c5ddd8"


def apply_publication_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "STIX Two Text", "DejaVu Serif"],
            "mathtext.fontset": "stix",
            "axes.labelsize": 11,
            "xtick.labelsize": 9.5,
            "ytick.labelsize": 9,
            "legend.fontsize": 8.5,
            "axes.linewidth": 0.8,
            "lines.linewidth": 1.6,
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


def _despine(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out")
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, linestyle="--", color="#7a7a7a", alpha=0.25)
    ax.xaxis.grid(False)


def _panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        0.02,
        0.98,
        label,
        transform=ax.transAxes,
        fontsize=12,
        fontweight="bold",
        va="top",
        ha="left",
        zorder=8,
    )


def _plot_mode(
    ax: plt.Axes,
    x: np.ndarray,
    mean: np.ndarray,
    sd: np.ndarray,
    *,
    color: str,
    marker: str,
    linestyle: str,
    label: str,
) -> None:
    ax.fill_between(x, mean - sd, mean + sd, color=color, alpha=0.14, linewidth=0, zorder=1)
    ax.errorbar(
        x,
        mean,
        yerr=sd,
        fmt="none",
        ecolor=color,
        elinewidth=1.15,
        capsize=3.2,
        capthick=1.1,
        zorder=4,
    )
    ax.plot(
        x,
        mean,
        color=color,
        linestyle=linestyle,
        marker=marker,
        markersize=7.2,
        markerfacecolor=color,
        markeredgecolor="white",
        markeredgewidth=0.55,
        lw=1.7,
        label=label,
        zorder=5,
        solid_capstyle="round",
    )


def plot_fl_composite(out_dir: Path | None = None, stem: str = STEM) -> tuple[plt.Figure, np.ndarray]:
    apply_publication_style()
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.5), layout="constrained")
    ax_a, ax_b = axes

    # ----- (a) Absolute scalability -----
    series = (
        (CLASSICAL_MEAN, CLASSICAL_SD, COLOR_CLASSICAL, "o", "-", "Classical TLS/ECDSA"),
        (HYBRID_MEAN, HYBRID_SD, COLOR_HYBRID, "s", "--", "Hybrid PQ (ML-KEM+ECDHE)"),
        (NATIVE_MEAN, NATIVE_SD, COLOR_NATIVE, "D", "-.", "Native PQ (ML-KEM-768)"),
    )
    for (mean, sd, color, marker, ls, label), jit in zip(series, JITTER):
        _plot_mode(ax_a, CLIENTS + jit, mean, sd, color=color, marker=marker, linestyle=ls, label=label)

    ax_a.set_xlabel("Number of Participating Clients ($K$)")
    ax_a.set_ylabel("Mean Round Latency (s)")
    ax_a.set_xticks(CLIENTS)
    ax_a.set_xlim(2.2, 53.5)
    ax_a.set_ylim(14.0, 28.0)
    ax_a.yaxis.set_major_locator(MultipleLocator(2))
    ax_a.yaxis.set_major_formatter(FormatStrFormatter("%.0f"))
    _despine(ax_a)
    ax_a.legend(
        loc="upper left",
        frameon=True,
        fancybox=False,
        framealpha=0.0,
        edgecolor="none",
        handlelength=2.4,
        borderpad=0.3,
        labelspacing=0.32,
    )
    _panel_label(ax_a, "(a)")

    # ----- (b) Native PQ overhead vs Classical -----
    colors = [COLOR_POS if v > 0 else COLOR_NEG for v in NATIVE_OVERHEAD_PCT]
    edges = ["#c07070" if v > 0 else "#4f9a8e" for v in NATIVE_OVERHEAD_PCT]
    ax_b.axhspan(-1.0, 1.0, facecolor=COLOR_WINDOW, alpha=0.45, zorder=0, linewidth=0)
    ax_b.axhline(0.0, color=COLOR_ZERO, ls="--", lw=1.15, zorder=2)
    bar_w = 6.2
    ax_b.bar(
        CLIENTS,
        NATIVE_OVERHEAD_PCT,
        width=bar_w,
        color=colors,
        edgecolor=edges,
        linewidth=0.6,
        zorder=3,
    )
    ax_b.text(
        17.5,
        0.52,
        r"Negligible Impact Window ($<1\%$)",
        fontsize=8,
        color="#3d5f5a",
        ha="center",
        va="center",
        zorder=4,
        fontstyle="italic",
    )
    for x, v in zip(CLIENTS, NATIVE_OVERHEAD_PCT):
        label = f"{v:+.2f}%"
        if v >= 0:
            ax_b.text(x, v + 0.14, label, ha="center", va="bottom", fontsize=8.5, color="#333333", zorder=5)
        else:
            ax_b.text(x, v - 0.14, label, ha="center", va="top", fontsize=8.5, color="#333333", zorder=5)

    ax_b.set_xlabel("Number of Participating Clients ($K$)")
    ax_b.set_ylabel("Latency Delta vs. Classical (%)")
    ax_b.set_xticks(CLIENTS)
    ax_b.set_xlim(2.2, 53.5)
    y_lo = min(-1.5, float(np.min(NATIVE_OVERHEAD_PCT)) - 0.6)
    y_hi = max(1.5, float(np.max(NATIVE_OVERHEAD_PCT)) + 0.6)
    ax_b.set_ylim(y_lo, y_hi)
    ax_b.yaxis.set_major_locator(MultipleLocator(0.5))
    ax_b.yaxis.set_major_formatter(FormatStrFormatter("%+.1f"))
    _despine(ax_b)
    _panel_label(ax_b, "(b)")

    fig.get_layout_engine().set(w_pad=0.10, h_pad=0.04, wspace=0.10)

    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_dir / f"{stem}.pdf")
        fig.savefig(out_dir / f"{stem}.png", dpi=300)

    print(
        f"K={list(CLIENTS.astype(int))}  "
        f"native overhead %={list(NATIVE_OVERHEAD_PCT)}"
    )
    return fig, axes


def copy_to_manuscript_figs(src_dir: Path, stem: str = STEM) -> None:
    if not _MANUSCRIPT_FIGS.exists():
        _MANUSCRIPT_FIGS.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        src = src_dir / f"{stem}.{ext}"
        if src.exists():
            shutil.copy2(src, _MANUSCRIPT_FIGS / f"{stem}.{ext}")


def main() -> None:
    fig, _ = plot_fl_composite(_DEFAULT_OUT)
    copy_to_manuscript_figs(_DEFAULT_OUT)
    plt.close(fig)
    print("Wrote:")
    for ext in ("pdf", "png"):
        print(f"  {_DEFAULT_OUT / f'{STEM}.{ext}'}")
        print(f"  {_MANUSCRIPT_FIGS / f'{STEM}.{ext}'}")


if __name__ == "__main__":
    main()
