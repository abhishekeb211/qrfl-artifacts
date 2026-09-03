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
    }
)

PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]


def plot_forecasting(root: Path, out: Path) -> None:
    csv_path = root / "datasets" / "quantum_hardware_clean.csv"
    if not csv_path.exists():
        return
    df = pd.read_csv(csv_path)
    fig, ax = plt.subplots(figsize=(3.5, 2.8))
    ax.scatter(df["year"], df["qubits"], c=PALETTE[0], s=40, label="Observed")
    t = df["t_years"].values
    import numpy as np
    from scipy import stats

    slope, intercept, _, _, _ = stats.linregress(t, np.log(df["qubits"]))
    years = np.linspace(df["year"].min(), df["year"].max() + 15, 100)
    t_proj = years - 2016
    pred = np.exp(intercept + slope * t_proj)
    ax.plot(years, pred, color=PALETTE[1], label="OLS exponential")
    ax.set_xlabel("Year")
    ax.set_ylabel("Physical qubits")
    ax.set_yscale("log")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out / "forecasting_model_comparison.pdf")
    fig.savefig(out / "forecasting_model_comparison.png")
    plt.close(fig)


def plot_threshold_uncertainty(root: Path, out: Path) -> None:
    scenarios = root / "results" / "forecasting" / "scenarios.csv"
    if not scenarios.exists():
        return
    df = pd.read_csv(scenarios)
    fig, ax = plt.subplots(figsize=(3.5, 2.8))
    labels = df["scenario"].str.capitalize()
    medians = df["bootstrap_median"]
    lowers = df["ci_lower_95"]
    uppers = df["ci_upper_95"]
    x = range(len(df))
    ax.errorbar(
        x,
        medians,
        yerr=[medians - lowers, uppers - medians],
        fmt="o",
        color=PALETTE[0],
        capsize=4,
        label="Bootstrap median",
    )
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Threshold crossing year")
    ax.set_xlabel("Scenario")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out / "threshold_crossing_uncertainty.pdf")
    fig.savefig(out / "threshold_crossing_uncertainty.png")
    plt.close(fig)


def plot_sensitivity(root: Path, out: Path) -> None:
    scenarios = root / "results" / "forecasting" / "scenarios.csv"
    if not scenarios.exists():
        return
    df = pd.read_csv(scenarios)
    fig, ax = plt.subplots(figsize=(3.5, 2.8))
    ax.bar(df["scenario"], df["point_estimate_year"], color=PALETTE[1], label="Point estimate")
    ax.set_ylabel("Crossing year")
    ax.set_xlabel("Scenario ($\\eta$)")
    ax.set_title("Timeline sensitivity by $\\eta$ scenario")
    fig.tight_layout()
    fig.savefig(out / "sensitivity_analysis.pdf")
    fig.savefig(out / "sensitivity_analysis.png")
    plt.close(fig)


def plot_pqc_summary(root: Path, out: Path) -> None:
    summary = root / "results" / "pqc" / "summary.csv"
    if not summary.exists():
        return
    df = pd.read_csv(summary)
    kem = df[df["scheme"].str.contains("ML-KEM", na=False)]
    if kem.empty:
        return
    fig, ax = plt.subplots(figsize=(3.5, 2.8))
    ops = kem["operation"].unique()
    x = range(len(ops))
    for i, scheme in enumerate(kem["scheme"].unique()):
        sub = kem[kem["scheme"] == scheme]
        means = [sub[sub["operation"] == op]["mean_ms"].values[0] for op in ops]
        ax.bar([xi + i * 0.25 for xi in x], means, width=0.25, label=scheme, color=PALETTE[i % len(PALETTE)])
    ax.set_xticks([xi + 0.25 for xi in x])
    ax.set_xticklabels(ops, rotation=20, ha="right")
    ax.set_ylabel("Latency (ms)")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "pqc_overhead_results.pdf")
    fig.savefig(out / "pqc_overhead_results.png")
    plt.close(fig)


def plot_fl_latency(root: Path, out: Path) -> None:
    fl = root / "results" / "fl" / "summary.csv"
    if not fl.exists():
        return
    df = pd.read_csv(fl)
    sub = df[df["alpha"] == 1.0] if "alpha" in df.columns else df
    if sub.empty:
        return
    fig, ax = plt.subplots(figsize=(3.5, 2.8))
    for i, mode in enumerate(sub["security_mode"].unique()):
        m = sub[sub["security_mode"] == mode]
        ax.plot(m["num_clients"], m["latency_mean"], marker="o", label=mode, color=PALETTE[i])
    ax.set_xlabel("Number of clients")
    ax.set_ylabel("Mean round latency (s)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out / "fl_overhead_results.pdf")
    fig.savefig(out / "fl_overhead_results.png")
    plt.close(fig)


def plot_hlf_phases(root: Path, out: Path) -> None:
    """Stacked bar chart of HLF lifecycle phases from calibrated simulation."""
    from blockchain.client.submit_transactions import load_pqc_latencies, lifecycle_latency_ms

    lat = load_pqc_latencies(root)
    configs = [
        ("classical", "Classical"),
        ("hybrid", "Hybrid"),
        ("native_pq", "Native PQ"),
    ]
    phases = ["endorsement_ms", "ordering_ms", "validation_ms"]
    phase_labels = ["Endorsement", "Ordering", "Validation"]
    data = {label: [lifecycle_latency_ms(cfg, lat)[p] for p in phases] for cfg, label in configs}

    fig, ax = plt.subplots(figsize=(3.5, 2.8))
    x = range(len(configs))
    bottom = [0.0] * len(configs)
    for i, (phase_key, phase_label) in enumerate(zip(phases, phase_labels)):
        heights = [data[label][i] for _, label in configs]
        ax.bar(x, heights, bottom=bottom, label=phase_label, color=PALETTE[i % len(PALETTE)], width=0.55)
        bottom = [b + h for b, h in zip(bottom, heights)]
    ax.set_xticks(list(x))
    ax.set_xticklabels([label for _, label in configs])
    ax.set_ylabel("Latency (ms)")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "hlf_phase_latencies.pdf")
    fig.savefig(out / "hlf_phase_latencies.png")
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
    plot_pqc_summary(root, out)
    plot_fl_latency(root, out)
    plot_hlf_phases(root, out)
    write_architecture_tikz(out)
    print("Figures generated:", out)


if __name__ == "__main__":
    main()
