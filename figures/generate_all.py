"""Generate publication-quality figures from results."""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd


# Journal-readable defaults
mpl.rcParams.update(
    {
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "legend.fontsize": 10,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "axes.prop_cycle": mpl.cycler(color=["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"]),
    }
)

# Okabe–Ito colorblind-safe palette
PALETTE = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#000000"]


def plot_forecasting(root: Path, out: Path) -> None:
    """Figure 2: published log-linear OLS forecast with 95% prediction intervals."""
    from figures.plot_figure2_ols_forecast import copy_to_manuscript_figs, plot_ols_forecast

    fig, _ = plot_ols_forecast(out)
    copy_to_manuscript_figs(out)
    plt.close(fig)


def plot_threshold_uncertainty(root: Path, out: Path) -> None:
    """Figure 3: PDF + ECDF of baseline (η = 1500) bootstrap crossing years."""
    from figures.plot_figure3_bootstrap_distribution import (
        copy_to_manuscript_figs,
        plot_bootstrap_pdf_cdf,
        resolve_crossing_years,
    )

    years = resolve_crossing_years(root=root)
    fig, _ = plot_bootstrap_pdf_cdf(years, out)
    copy_to_manuscript_figs(out)
    plt.close(fig)


def plot_sensitivity(root: Path, out: Path) -> None:
    """Figure 4: Table 10 multi-parameter η–Q* crossing-year sweep."""
    from figures.plot_figure4_sensitivity import copy_to_manuscript_figs, plot_sensitivity_sweep

    fig, _ = plot_sensitivity_sweep(out)
    copy_to_manuscript_figs(out)
    plt.close(fig)


def plot_architecture(root: Path, out: Path) -> None:
    """Figure 5: seaborn-themed Plotly QRFL architecture (PNG + PDF)."""
    from figures.plot_figure5_architecture import copy_to_manuscript_figs, plot_architecture as _plot

    _plot(out)
    copy_to_manuscript_figs(out)


def plot_pqc_summary(root: Path, out: Path) -> None:
    """Figure 6: Table 15 ML-KEM grouped latency bars with SD error bars."""
    from figures.plot_figure6_mlkem_latency import copy_to_manuscript_figs, plot_mlkem_latency

    fig, _ = plot_mlkem_latency(out)
    copy_to_manuscript_figs(out)
    plt.close(fig)


def plot_fl_latency(root: Path, out: Path) -> None:
    """Figure 7: Table 17 two-panel FL latency and Native-PQ overhead."""
    from figures.plot_figure7_fl_latency import copy_to_manuscript_figs, plot_fl_composite

    fig, _ = plot_fl_composite(out)
    copy_to_manuscript_figs(out)
    plt.close(fig)


def plot_hlf_phases(root: Path, out: Path) -> None:
    """Figure 8: Table 19 stacked HLF lifecycle latencies."""
    from figures.plot_figure8_hlf_phases import copy_to_manuscript_figs, plot_hlf_stacked

    fig, _ = plot_hlf_stacked(out)
    copy_to_manuscript_figs(out)
    plt.close(fig)


def write_architecture_tikz(out: Path) -> None:
    layers = [
        ("ForecastingLayer", "Quantum-Threat Forecasting", "Hardware dataset, exponential/logistic models, bootstrap UQ"),
        ("CryptoLayer", "PQC / Crypto-Agility", "ML-KEM, ML-DSA, SLH-DSA, hybrid PKI"),
        ("FLLayer", "Healthcare Federated Learning", "FedAvg, secure aggregation, non-IID, Byzantine robustness"),
        ("BlockchainLayer", "Blockchain Validation", "HLF endorsements, chaincode PQC verification"),
        ("MigrationLayer", "Migration Decision Support", "Mosca inequality, MOSCoW roadmap"),
    ]
    for fname, title, desc in layers:
        tex = f"""% Auto-generated architecture layer: {title}
\\begin{{figure}}[htbp]
\\centering
\\begin{{tikzpicture}}[
  layer/.style={{draw, rounded corners, minimum width=7cm, minimum height=1.2cm, align=center, fill=gray!8}}
]
\\node[layer] (box) {{\\textbf{{{title}}}\\\\\\footnotesize {desc}}};
\\end{{tikzpicture}}
\\caption{{{title} layer of the QRFL framework.}}
\\label{{fig:{fname.lower()}}}
\\end{{figure}}
"""
        (out / f"layer_{fname.lower()}.tex").write_text(tex, encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root / "figures" / "output"
    out.mkdir(parents=True, exist_ok=True)
    plot_forecasting(root, out)
    plot_threshold_uncertainty(root, out)
    plot_sensitivity(root, out)
    plot_architecture(root, out)
    plot_pqc_summary(root, out)
    plot_fl_latency(root, out)
    plot_hlf_phases(root, out)
    write_architecture_tikz(out)
    print("Figures generated:", out)


if __name__ == "__main__":
    main()
