"""Figure 2: log-linear OLS physical-qubit forecast with 95% prediction intervals.

Uses only the 20 Table 3 observations and the published Model C coefficients:
    ln(Q_t) = 2.3451 + 0.3721 t,   t = years since 2016.
The mean curve is not refit. The 95% prediction interval is the classical OLS
interval on the log scale, mapped back by exponentiation.

Usage
-----
    python plot_figure2_ols_forecast.py
    python -m figures.plot_figure2_ols_forecast
"""

from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import LogFormatterMathtext, LogLocator, MultipleLocator
from scipy import stats

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_ARTIFACTS = _THIS_DIR.parent
_MANUSCRIPT_ROOT = _ARTIFACTS.parent
_DEFAULT_OUT = _THIS_DIR / "output"
_MANUSCRIPT_FIGS = _MANUSCRIPT_ROOT / "figs"
STEM = "forecasting_model_comparison"

# ---------------------------------------------------------------------------
# Published Model C parameters (do not refit)
# ---------------------------------------------------------------------------
BASE_YEAR = 2016
ALPHA = 2.3451  # ln(a)
BETA = 0.3721
A = 10.4339
R_SQUARED = 0.5309
DOUBLING_YEARS = 1.86

LOGICAL_THRESHOLD = 2330
ETA_BASELINE = 1500
Q_STAR = 3_495_000  # 2330 * 1500
OLS_CROSSING_YEAR = 2050.19

YEAR_HIST_END = 2026.0
YEAR_FORECAST_END = 2070.0

# Okabe–Ito (colorblind-safe; distinct linestyles for grayscale)
COLOR_OBS = "#000000"
COLOR_OLS = "#0072B2"
COLOR_PI = "#56B4E9"
COLOR_THRESH = "#D55E00"
COLOR_GUIDE = "#6E6E6E"

# Table 3 / Table~\ref{tab:frontier_dataset}: announcement month, qubit count.
# t = (year - 2016) + (month - 1)/12, matching the paper's year-since-2016 clock.
OBSERVATIONS: tuple[tuple[int, int, int, str], ...] = (
    (2016, 5, 5, "IBM QX2"),
    (2016, 8, 8, "Rigetti 8-Qubit"),
    (2017, 5, 16, "IBM QX4"),
    (2017, 11, 50, "IBM 50-Qubit"),
    (2018, 3, 72, "Google Bristlecone"),
    (2019, 10, 53, "Google Sycamore"),
    (2020, 9, 27, "IBM Falcon"),
    (2020, 11, 65, "IBM Hummingbird"),
    (2021, 11, 127, "IBM Eagle"),
    (2022, 11, 433, "IBM Osprey"),
    (2023, 3, 20, "Quantinuum H1-1"),
    (2023, 10, 1200, "Atom Computing AC1000"),
    (2023, 12, 1121, "IBM Condor"),
    (2024, 4, 56, "Quantinuum H2-1"),
    (2024, 12, 156, "IBM Heron r2/r3"),
    (2024, 12, 105, "Google Willow"),
    (2024, 12, 84, "Rigetti Ankaa-3"),
    (2025, 9, 120, "IBM Nighthawk"),
    (2025, 10, 1200, "Quantinuum H5-Series"),
    (2026, 2, 2048, "Atom Computing 2048-Atom"),
)


def apply_publication_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "mathtext.fontset": "dejavusans",
            "axes.labelsize": 9.5,
            "axes.titlesize": 10,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "axes.linewidth": 0.8,
            "lines.linewidth": 1.4,
            "xtick.major.width": 0.7,
            "ytick.major.width": 0.7,
            "xtick.major.size": 3.2,
            "ytick.major.size": 3.2,
            "xtick.minor.size": 1.8,
            "ytick.minor.size": 1.8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "path",
            "savefig.dpi": 600,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.05,
            "axes.unicode_minus": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "black",
            "text.color": "black",
            "axes.labelcolor": "black",
            "xtick.color": "black",
            "ytick.color": "black",
        }
    )


def observation_arrays() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Decimal years, t since 2016, and physical-qubit counts from Table 3."""
    years = np.array([y + (m - 1) / 12.0 for y, m, _q, _n in OBSERVATIONS], dtype=float)
    t = years - BASE_YEAR
    qubits = np.array([q for _y, _m, q, _n in OBSERVATIONS], dtype=float)
    return years, t, qubits


def ols_mean(t: np.ndarray) -> np.ndarray:
    """Published exponential mean: Q(t) = a * exp(b t)."""
    return np.exp(ALPHA + BETA * np.asarray(t, dtype=float))


def prediction_interval(t_new: np.ndarray, t_obs: np.ndarray, q_obs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """95% OLS prediction interval for a new observation on the Q scale.

    Log-scale interval:
        ŷ(t0) ± t_{0.975, n-2} * s * sqrt(1 + 1/n + (t0 − t̄)^2 / Sxx)
    then exponentiated. Coefficients (α, β) are the published values.
    """
    t_new = np.asarray(t_new, dtype=float)
    n = t_obs.size
    df = n - 2
    y_ln = np.log(q_obs)
    resid = y_ln - (ALPHA + BETA * t_obs)
    s = float(np.sqrt(np.sum(resid**2) / df))
    t_bar = float(np.mean(t_obs))
    sxx = float(np.sum((t_obs - t_bar) ** 2))
    t_crit = float(stats.t.ppf(0.975, df))
    yhat = ALPHA + BETA * t_new
    se = s * np.sqrt(1.0 + 1.0 / n + (t_new - t_bar) ** 2 / sxx)
    lower = np.exp(yhat - t_crit * se)
    upper = np.exp(yhat + t_crit * se)
    return lower, upper


def apply_axes_style(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out", which="both")
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, which="major", linestyle=":", alpha=0.28, color="#7A7A7A")
    ax.xaxis.grid(False)


def plot_ols_forecast(out_dir: Path | None = None, stem: str = STEM) -> tuple[plt.Figure, plt.Axes]:
    apply_publication_style()
    years_obs, t_obs, q_obs = observation_arrays()
    if years_obs.size != 20:
        raise RuntimeError(f"Expected 20 Table 3 observations, got {years_obs.size}.")

    years = np.linspace(float(BASE_YEAR), YEAR_FORECAST_END, 1400)
    t_grid = years - BASE_YEAR
    q_mean = ols_mean(t_grid)
    q_lo, q_hi = prediction_interval(t_grid, t_obs, q_obs)

    hist = years <= YEAR_HIST_END
    fore = years >= YEAR_HIST_END

    t_star = (np.log(Q_STAR) - ALPHA) / BETA
    crossing_exact = BASE_YEAR + t_star

    fig, ax = plt.subplots(figsize=(7.16, 3.85), layout="constrained")

    # Prediction interval first so lines and points sit above it.
    ax.fill_between(
        years,
        q_lo,
        q_hi,
        color=COLOR_PI,
        alpha=0.33,
        linewidth=0,
        zorder=1,
        label="95% prediction interval",
    )
    ax.plot(years, q_lo, color=COLOR_PI, lw=0.7, alpha=0.85, zorder=2)
    ax.plot(years, q_hi, color=COLOR_PI, lw=0.7, alpha=0.85, zorder=2)

    ax.axvline(YEAR_HIST_END, color=COLOR_GUIDE, lw=0.8, ls=(0, (3.5, 2.8)), alpha=0.75, zorder=3)
    ax.axhline(Q_STAR, color=COLOR_THRESH, lw=1.2, ls="--", zorder=4)
    ax.plot(
        [OLS_CROSSING_YEAR, OLS_CROSSING_YEAR],
        [0.45, Q_STAR],
        color=COLOR_GUIDE,
        lw=0.9,
        ls=":",
        zorder=4,
        solid_capstyle="butt",
        clip_on=True,
    )

    ax.plot(years[hist], q_mean[hist], color=COLOR_OLS, lw=1.85, ls="-", zorder=5, solid_capstyle="round")
    ax.plot(years[fore], q_mean[fore], color=COLOR_OLS, lw=1.85, ls=(0, (5.5, 2.4)), zorder=5, solid_capstyle="round")

    ax.scatter(
        years_obs,
        q_obs,
        s=32,
        c=COLOR_OBS,
        marker="o",
        edgecolors="white",
        linewidths=0.45,
        zorder=6,
        label="Observed",
    )
    ax.plot(
        crossing_exact,
        Q_STAR,
        marker="D",
        ms=5.5,
        color=COLOR_THRESH,
        markeredgecolor="white",
        markeredgewidth=0.5,
        zorder=7,
        linestyle="None",
    )

    ax.set_yscale("log")
    ax.set_xlim(2015.2, 2071.5)
    ax.set_ylim(0.7, 2.0e10)
    ax.set_xlabel("Year")
    ax.set_ylabel("Physical qubits")
    ax.xaxis.set_major_locator(MultipleLocator(10))
    ax.xaxis.set_minor_locator(MultipleLocator(5))
    ax.yaxis.set_major_locator(LogLocator(base=10.0, numticks=12))
    ax.yaxis.set_minor_locator(LogLocator(base=10.0, subs=np.arange(2, 10), numticks=100))
    ax.yaxis.set_major_formatter(LogFormatterMathtext())
    apply_axes_style(ax)

    trans = mpl.transforms.blended_transform_factory(ax.transData, ax.transAxes)
    ax.text(
        2020.6,
        0.035,
        "Observed data",
        transform=trans,
        ha="center",
        va="bottom",
        fontsize=7.5,
        color="#555555",
        fontstyle="italic",
        zorder=8,
        clip_on=False,
    )
    ax.text(
        2046.5,
        0.035,
        "OLS forecast",
        transform=trans,
        ha="center",
        va="bottom",
        fontsize=7.5,
        color="#555555",
        fontstyle="italic",
        zorder=8,
        clip_on=False,
    )

    ax.text(
        2069.6,
        Q_STAR * 1.85,
        "Baseline ECDSA-256 physical threshold\n"
        r"($\eta = 1500$)",
        ha="right",
        va="bottom",
        fontsize=7.5,
        color=COLOR_THRESH,
        linespacing=1.15,
        zorder=8,
    )
    ax.annotate(
        r"OLS crossing $\approx$ 2050.19",
        xy=(crossing_exact, Q_STAR),
        xytext=(2037.8, 2.2e7),
        fontsize=8,
        color="#222222",
        ha="center",
        va="bottom",
        arrowprops={
            "arrowstyle": "-",
            "lw": 0.7,
            "color": COLOR_GUIDE,
            "shrinkA": 0,
            "shrinkB": 3,
        },
        zorder=8,
    )

    ax.text(
        0.015,
        0.975,
        "Log-linear OLS:\n"
        r"$\ln(Q)=2.3451+0.3721\,t$"
        "\n"
        r"$R^{2}=0.5309$"
        "\n"
        "Doubling time = 1.86 years",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8,
        linespacing=1.35,
        zorder=9,
        bbox={
            "boxstyle": "round,pad=0.35",
            "facecolor": "white",
            "edgecolor": "#C8C8C8",
            "linewidth": 0.6,
            "alpha": 0.96,
        },
    )

    handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=COLOR_OBS,
            markeredgecolor="white",
            markeredgewidth=0.4,
            markersize=6.5,
            label="Observed",
        ),
        Line2D([0], [0], color=COLOR_OLS, lw=1.85, label="OLS fit / forecast"),
        Patch(facecolor=COLOR_PI, edgecolor="none", alpha=0.45, label="95% prediction interval"),
        Line2D([0], [0], color=COLOR_THRESH, lw=1.2, ls="--", label="Baseline ECDSA-256 threshold"),
    ]
    ax.legend(
        handles=handles,
        loc="upper left",
        bbox_to_anchor=(0.015, 0.58),
        frameon=True,
        fancybox=False,
        edgecolor="#C8C8C8",
        framealpha=0.96,
        borderpad=0.45,
        handlelength=1.85,
        labelspacing=0.35,
    )

    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_dir / f"{stem}.pdf")
        fig.savefig(out_dir / f"{stem}.svg")
        fig.savefig(out_dir / f"{stem}.png", dpi=600)

    _print_qc(years_obs, q_obs, t_obs, q_lo, q_hi, years, q_mean, crossing_exact)
    return fig, ax


def _print_qc(
    years_obs: np.ndarray,
    q_obs: np.ndarray,
    t_obs: np.ndarray,
    q_lo: np.ndarray,
    q_hi: np.ndarray,
    years: np.ndarray,
    q_mean: np.ndarray,
    crossing_exact: float,
) -> None:
    lo_obs, hi_obs = prediction_interval(t_obs, t_obs, q_obs)
    inside = int(np.sum((q_obs >= lo_obs) & (q_obs <= hi_obs)))
    print(f"observations plotted: {years_obs.size}")
    print(f"y-scale: log   x-range: {years.min():.1f}–{years.max():.1f}")
    print(f"OLS mean at 2050.19: {float(np.exp(ALPHA + BETA * (OLS_CROSSING_YEAR - BASE_YEAR))):.0f}")
    print(f"exact crossing of Q*={Q_STAR:,}: {crossing_exact:.4f}")
    print(f"forecast extends to {years.max():.0f}; Q_mean(2070)={q_mean[-1]:.3e}")
    print(f"PI at 2050.19 visible: [{q_lo[np.argmin(np.abs(years - OLS_CROSSING_YEAR))]:.3e}, "
          f"{q_hi[np.argmin(np.abs(years - OLS_CROSSING_YEAR))]:.3e}]")
    print(f"historical points inside 95% PI: {inside}/{years_obs.size}")


def copy_to_manuscript_figs(src_dir: Path, stem: str = STEM) -> None:
    if not _MANUSCRIPT_FIGS.exists():
        _MANUSCRIPT_FIGS.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png", "svg"):
        src = src_dir / f"{stem}.{ext}"
        if src.exists():
            shutil.copy2(src, _MANUSCRIPT_FIGS / f"{stem}.{ext}")


def main() -> None:
    fig, _ = plot_ols_forecast(_DEFAULT_OUT)
    copy_to_manuscript_figs(_DEFAULT_OUT)
    plt.close(fig)
    print("Wrote:")
    for ext in ("pdf", "png", "svg"):
        print(f"  {_DEFAULT_OUT / f'{STEM}.{ext}'}")
        print(f"  {_MANUSCRIPT_FIGS / f'{STEM}.{ext}'}")


if __name__ == "__main__":
    main()
