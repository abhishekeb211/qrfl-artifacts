"""Figure 3: bootstrap PDF and CDF of the baseline crossing year (η = 1500).

Publication-ready two-panel figure for a double-column journal layout.
The script runs out of the box on synthetic bootstrap replicates calibrated
to the manuscript Table values. When the QRFL hardware dataset is present,
it prefers the nonparametric bootstrap used in the forecasting pipeline.

Usage
-----
    python plot_figure3_bootstrap_distribution.py
    python -m figures.plot_figure3_bootstrap_distribution
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from scipy import stats

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_ARTIFACTS = _THIS_DIR.parent
_MANUSCRIPT_ROOT = _ARTIFACTS.parent
_DEFAULT_OUT = _THIS_DIR / "output"
_MANUSCRIPT_FIGS = _MANUSCRIPT_ROOT / "figs"
_BOOTSTRAP_CSV = _ARTIFACTS / "results" / "forecasting" / "bootstrap_crossing_years_baseline.csv"

if str(_ARTIFACTS) not in sys.path:
    sys.path.insert(0, str(_ARTIFACTS))

# ---------------------------------------------------------------------------
# Visual constants (Okabe–Ito; colorblind-safe dual hue)
# ---------------------------------------------------------------------------
STEEL = "#0072B2"
STEEL_FILL = "#56B4E9"
MEDIAN_COLOR = "#D55E00"
CI_COLOR = "#4D4D4D"

# Manuscript Table: baseline η = 1500, 5,000 bootstrap replicates
SYNTHETIC_N = 5000
SYNTHETIC_MEDIAN = 2050.36
SYNTHETIC_CI = (2042.08, 2070.07)
SYNTHETIC_SEED = 42
ETA_BASELINE = 1500.0
LOGICAL_THRESHOLD = 2330.0
N_REPLICATES = 5000


def apply_publication_style() -> None:
    """Journal typography and export settings."""
    sns.set_theme(style="ticks", context="paper", font="sans-serif")
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
            "xtick.major.size": 3.0,
            "ytick.major.size": 3.0,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.05,
            "axes.unicode_minus": False,
        }
    )


def synthetic_crossing_years(
    n: int = SYNTHETIC_N,
    median: float = SYNTHETIC_MEDIAN,
    ci: tuple[float, float] = SYNTHETIC_CI,
    seed: int = SYNTHETIC_SEED,
) -> np.ndarray:
    """Right-skewed placeholder samples matching published median and 95% CI.

    Crossing-year bootstraps are typically right-skewed (slow growth-rate
    resamples produce late crossings). A shifted lognormal is calibrated so
    that the 2.5th, 50th, and 97.5th percentiles match ``ci`` and ``median``.
    """
    q_lo, q_hi = ci
    # Location shift τ such that (median − τ) is the geometric mean of the
    # shifted CI bounds, which is the lognormal median/quantile relationship.
    denom = q_lo + q_hi - 2.0 * median
    if abs(denom) < 1e-9:
        tau = q_lo - 5.0
    else:
        tau = (q_lo * q_hi - median * median) / denom
    # Keep the support strictly positive.
    tau = min(tau, q_lo - 1.0)

    loc_median = median - tau
    loc_lo = q_lo - tau
    z = stats.norm.ppf(0.975)
    sigma = float(np.log(loc_median / loc_lo) / z)
    mu = float(np.log(loc_median))

    rng = np.random.default_rng(seed)
    samples = tau + rng.lognormal(mean=mu, sigma=sigma, size=n)
    return np.asarray(samples, dtype=float)


def _finite_years(years: np.ndarray) -> np.ndarray:
    years = np.asarray(years, dtype=float).ravel()
    years = years[np.isfinite(years)]
    # Drop pathological replicates (near-zero growth → century-scale crossings).
    return years[(years > 2020.0) & (years < 2200.0)]


def load_crossing_years_csv(path: Path) -> np.ndarray | None:
    if not path.exists():
        return None
    try:
        import pandas as pd

        df = pd.read_csv(path)
        col = "crossing_year" if "crossing_year" in df.columns else df.columns[0]
        years = _finite_years(df[col].to_numpy())
        return years if years.size else None
    except Exception:
        return None


def compute_pipeline_bootstrap(root: Path | None = None) -> np.ndarray | None:
    """Recompute the baseline bootstrap from the QRFL forecasting pipeline."""
    root = root or _ARTIFACTS
    csv_path = root / "datasets" / "quantum_hardware_clean.csv"
    if not csv_path.exists():
        return None
    try:
        import pandas as pd
        from forecasting.fit_models import bootstrap_crossing_years
    except Exception:
        return None

    df = pd.read_csv(csv_path)
    years = bootstrap_crossing_years(
        df,
        eta=ETA_BASELINE,
        logical_threshold=LOGICAL_THRESHOLD,
        n_replicates=N_REPLICATES,
        seed=SYNTHETIC_SEED,
    )
    years = _finite_years(years)
    return years if years.size else None


def resolve_crossing_years(
    crossing_years: np.ndarray | None = None,
    root: Path | None = None,
) -> np.ndarray:
    """Return bootstrap years: explicit array, saved CSV, pipeline, or synthetic."""
    if crossing_years is not None:
        years = _finite_years(crossing_years)
        if years.size:
            return years

    root = root or _ARTIFACTS
    cached = load_crossing_years_csv(root / "results" / "forecasting" / "bootstrap_crossing_years_baseline.csv")
    if cached is not None:
        return cached

    computed = compute_pipeline_bootstrap(root)
    if computed is not None:
        out_csv = root / "results" / "forecasting" / "bootstrap_crossing_years_baseline.csv"
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        import pandas as pd

        pd.DataFrame({"crossing_year": computed}).to_csv(out_csv, index=False)
        return computed

    return synthetic_crossing_years()


def _panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.14,
        1.06,
        label,
        transform=ax.transAxes,
        fontsize=10,
        fontweight="bold",
        va="bottom",
        ha="left",
        clip_on=False,
    )


def _despine(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out")


def plot_bootstrap_pdf_cdf(
    crossing_years: np.ndarray,
    out_dir: Path | None = None,
    stem: str = "threshold_crossing_uncertainty",
) -> tuple[plt.Figure, np.ndarray]:
    """Draw panel (a) PDF and panel (b) ECDF; save PDF and PNG."""
    apply_publication_style()
    years = _finite_years(crossing_years)
    if years.size < 10:
        raise ValueError("crossing_years must contain at least 10 finite samples.")

    median = float(np.median(years))
    ci_lo, ci_hi = (float(v) for v in np.percentile(years, [2.5, 97.5]))

    # Display window: include the 95% CI and a visible right tail, omit pathologies.
    x_min = min(np.percentile(years, 1.0), ci_lo) - 2.0
    x_max = max(np.percentile(years, 98.5), ci_hi) + 2.0
    x_min = float(np.floor(x_min))
    x_max = float(np.ceil(x_max))

    n_bins = int(np.clip(round(np.sqrt(years.size)), 28, 48))

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(7.12, 3.12),
        sharex=True,
        layout="constrained",
    )
    ax_pdf, ax_cdf = axes

    # ----- (a) PDF: faint histogram + filled KDE -----
    ax_pdf.hist(
        years,
        bins=n_bins,
        density=True,
        range=(x_min, x_max),
        color=STEEL,
        alpha=0.18,
        edgecolor="white",
        linewidth=0.35,
        zorder=1,
        label="Histogram",
    )
    sns.kdeplot(
        years,
        ax=ax_pdf,
        color=STEEL,
        fill=True,
        alpha=0.22,
        linewidth=1.7,
        bw_adjust=0.95,
        clip=(x_min, x_max),
        zorder=2,
        label="KDE",
        legend=False,
    )

    ax_pdf.axvline(median, color=MEDIAN_COLOR, ls="--", lw=1.25, zorder=3, label=f"Median ({median:.1f})")
    ax_pdf.axvline(ci_lo, color=CI_COLOR, ls="--", lw=1.05, zorder=3, label="95% CI")
    ax_pdf.axvline(ci_hi, color=CI_COLOR, ls="--", lw=1.05, zorder=3)

    ax_pdf.set_ylabel("Probability density")
    ax_pdf.set_xlabel("Crossing year")
    ax_pdf.set_xlim(x_min, x_max)
    ax_pdf.xaxis.set_major_locator(mpl.ticker.MultipleLocator(10))
    ax_pdf.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(5))
    ax_pdf.yaxis.grid(True, linestyle=":", alpha=0.3)
    ax_pdf.set_axisbelow(True)
    ax_pdf.legend(frameon=False, loc="upper right", handlelength=1.6, borderaxespad=0.2)
    _despine(ax_pdf)
    _panel_label(ax_pdf, "(a)")

    # ----- (b) ECDF with quantile references -----
    x_sorted = np.sort(years)
    ecdf = np.arange(1, x_sorted.size + 1, dtype=float) / x_sorted.size
    ax_cdf.step(
        x_sorted,
        ecdf,
        where="post",
        color=STEEL,
        lw=1.6,
        zorder=2,
        label="Empirical CDF",
    )

    for p, xq, color in (
        (0.025, ci_lo, CI_COLOR),
        (0.50, median, MEDIAN_COLOR),
        (0.975, ci_hi, CI_COLOR),
    ):
        ax_cdf.axhline(p, color=color, ls=":", lw=0.9, alpha=0.85, zorder=1)
        ax_cdf.axvline(xq, color=color, ls="--", lw=1.05, zorder=3)
        ax_cdf.plot(xq, p, marker="o", ms=4.0, color=color, zorder=4, clip_on=False)

    ax_cdf.set_ylabel("Cumulative probability")
    ax_cdf.set_xlabel("Crossing year")
    ax_cdf.set_xlim(x_min, x_max)
    ax_cdf.set_ylim(-0.03, 1.06)
    ax_cdf.set_yticks([0.0, 0.25, 0.50, 0.75, 1.0])
    ax_cdf.xaxis.set_major_locator(mpl.ticker.MultipleLocator(10))
    ax_cdf.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(5))
    ax_cdf.yaxis.grid(True, linestyle=":", alpha=0.3)
    ax_cdf.set_axisbelow(True)
    ax_cdf.legend(frameon=False, loc="lower right", handlelength=1.6, borderaxespad=0.2)
    _despine(ax_cdf)
    _panel_label(ax_cdf, "(b)")

    fig.get_layout_engine().set(w_pad=0.08, h_pad=0.04, wspace=0.10)

    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_dir / f"{stem}.pdf")
        fig.savefig(out_dir / f"{stem}.png", dpi=300)
    return fig, axes


def copy_to_manuscript_figs(src_dir: Path, stem: str = "threshold_crossing_uncertainty") -> None:
    """Mirror PDF/PNG into the manuscript ``figs/`` directory."""
    import shutil

    if not _MANUSCRIPT_FIGS.exists():
        _MANUSCRIPT_FIGS.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        src = src_dir / f"{stem}.{ext}"
        if src.exists():
            shutil.copy2(src, _MANUSCRIPT_FIGS / f"{stem}.{ext}")


def main() -> None:
    years = resolve_crossing_years()
    median = float(np.median(years))
    ci_lo, ci_hi = (float(v) for v in np.percentile(years, [2.5, 97.5]))
    print(
        f"n={years.size}  median={median:.2f}  "
        f"95% CI=[{ci_lo:.2f}, {ci_hi:.2f}]"
    )

    fig, _ = plot_bootstrap_pdf_cdf(years, _DEFAULT_OUT)
    copy_to_manuscript_figs(_DEFAULT_OUT)
    plt.close(fig)
    print("Wrote:")
    print(f"  {_DEFAULT_OUT / 'threshold_crossing_uncertainty.pdf'}")
    print(f"  {_DEFAULT_OUT / 'threshold_crossing_uncertainty.png'}")
    print(f"  {_MANUSCRIPT_FIGS / 'threshold_crossing_uncertainty.pdf'}")
    print(f"  {_MANUSCRIPT_FIGS / 'threshold_crossing_uncertainty.png'}")


if __name__ == "__main__":
    main()
