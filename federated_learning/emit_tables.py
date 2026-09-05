"""Emit LaTeX tables for FL experiment results."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


MODE_LABELS = {
    "classical": "Classical TLS/ECDSA",
    "hybrid_pq": "Hybrid PQ",
    "native_pq": "Native PQ",
}


def _pct(mean: float, std: float) -> str:
    return f"{mean * 100:.2f}\\% $\\pm$ {std * 100:.2f}\\%"


def _float(mean: float, std: float, digits: int = 4) -> str:
    return f"{mean:.{digits}f} $\\pm$ {std:.{digits}f}"


def _mode_stats(df: pd.DataFrame, mode: str, filters: dict) -> dict:
    sub = df[
        (df["security_mode"] == mode)
        & (df["attack"] == "none")
        & (df["malicious_fraction"] == 0.0)
        & (df["aggregator"] == "fedavg")
    ]
    for key, val in filters.items():
        sub = sub[sub[key] == val]
    if sub.empty:
        return {}
    return {
        "accuracy_mean": sub["accuracy"].mean(),
        "accuracy_std": sub["accuracy"].std(ddof=1) if len(sub) > 1 else 0.0,
        "auroc_mean": sub["auroc"].mean(),
        "auroc_std": sub["auroc"].std(ddof=1) if len(sub) > 1 else 0.0,
        "sensitivity_mean": sub["sensitivity"].mean(),
        "sensitivity_std": sub["sensitivity"].std(ddof=1) if len(sub) > 1 else 0.0,
        "specificity_mean": sub["specificity"].mean(),
        "specificity_std": sub["specificity"].std(ddof=1) if len(sub) > 1 else 0.0,
        "precision_mean": sub["precision"].mean(),
        "precision_std": sub["precision"].std(ddof=1) if len(sub) > 1 else 0.0,
        "recall_mean": sub["recall"].mean(),
        "recall_std": sub["recall"].std(ddof=1) if len(sub) > 1 else 0.0,
        "f1_mean": sub["f1"].mean(),
        "f1_std": sub["f1"].std(ddof=1) if len(sub) > 1 else 0.0,
        "latency_mean": sub["mean_round_latency_s"].mean(),
        "latency_std": sub["mean_round_latency_s"].std(ddof=1) if len(sub) > 1 else 0.0,
        "convergence_mean": sub["rounds_to_convergence"].mean() if "rounds_to_convergence" in sub else np.nan,
        "convergence_std": sub["rounds_to_convergence"].std(ddof=1) if len(sub) > 1 else 0.0,
    }


def emit_fl_metrics(df: pd.DataFrame, out_path: Path, num_clients: int, alpha: float = 1.0) -> None:
    lines = [
        "% Auto-generated FL utility metrics (Experiment B)",
        "\\begin{table*}[htbp]",
        "\\centering",
        "\\caption{Federated Learning Utility and Medical Metrics (measured)}",
        "\\label{tab:fl_metrics}",
        "\\small",
        "\\resizebox{\\textwidth}{!}{",
        "\\begin{tabular}{lccccccc}",
        "\\toprule",
        "Mode & Accuracy & AUROC & Sensitivity & Specificity & Precision & Recall & F1-score \\\\",
        "\\midrule",
    ]
    filters = {"num_clients": num_clients, "alpha": alpha}
    for mode in ["classical", "hybrid_pq", "native_pq"]:
        s = _mode_stats(df, mode, filters)
        if not s:
            continue
        lines.append(
            f"{MODE_LABELS[mode]} & {_pct(s['accuracy_mean'], s['accuracy_std'])} & "
            f"{_float(s['auroc_mean'], s['auroc_std'])} & "
            f"{_pct(s['sensitivity_mean'], s['sensitivity_std'])} & "
            f"{_pct(s['specificity_mean'], s['specificity_std'])} & "
            f"{_pct(s['precision_mean'], s['precision_std'])} & "
            f"{_pct(s['recall_mean'], s['recall_std'])} & "
            f"{_float(s['f1_mean'], s['f1_std'])} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}}", "\\end{table*}"])
    out_path.write_text("\n".join(lines), encoding="utf-8")


def emit_fl_latency(df: pd.DataFrame, out_path: Path) -> None:
    lines = [
        "% Auto-generated FL round latency table (Experiment B)",
        "\\begin{table*}[htbp]",
        "\\centering",
        "\\caption{End-to-End FL Round Latency (measured)}",
        "\\label{tab:fl_latency}",
        "\\small",
        "\\begin{tabular}{lcccc}",
        "\\toprule",
        "Clients & Classical Mode (s) & Hybrid PQ Mode (s) & Native PQ Mode (s) & Native Overhead \\\\",
        "\\midrule",
    ]
    for nc in sorted(df[df["attack"] == "none"]["num_clients"].unique()):
        row = {"num_clients": nc}
        for mode in ["classical", "hybrid_pq", "native_pq"]:
            s = _mode_stats(df, mode, {"num_clients": nc, "alpha": 1.0})
            row[mode] = s
        if not row.get("classical") or not row.get("hybrid_pq") or not row.get("native_pq"):
            continue
        c = row["classical"]["latency_mean"]
        n = row["native_pq"]["latency_mean"]
        overhead = ((n - c) / c * 100.0) if c > 0 else 0.0
        lines.append(
            f"{int(nc)} & {_float(row['classical']['latency_mean'], row['classical']['latency_std'], 2)} & "
            f"{_float(row['hybrid_pq']['latency_mean'], row['hybrid_pq']['latency_std'], 2)} & "
            f"{_float(row['native_pq']['latency_mean'], row['native_pq']['latency_std'], 2)} & "
            f"{overhead:+.2f}\\% \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table*}"])
    out_path.write_text("\n".join(lines), encoding="utf-8")


def emit_non_iid(df: pd.DataFrame, out_path: Path, num_clients: int) -> None:
    lines = [
        "% Auto-generated non-IID FL table (Experiment B-2)",
        "\\begin{table*}[htbp]",
        "\\centering",
        "\\caption{Non-IID Federated Learning Performance under Dirichlet Parameterization (measured)}",
        "\\label{tab:non_iid_fl}",
        "\\small",
        "\\resizebox{\\textwidth}{!}{",
        "\\begin{tabular}{clccccc}",
        "\\toprule",
        "Dirichlet $\\alpha$ & Security Mode & Accuracy & AUROC & F1-score & Rounds to Convergence & Mean Round Latency (s) \\\\",
        "\\midrule",
    ]
    for alpha in sorted(df["alpha"].unique()):
        label = f"{alpha:.1f}" if alpha != 1.0 else "1.0 (IID)"
        if alpha == 1.0:
            label = "1.0 (IID)"
        else:
            label = str(alpha)
        for mode in ["classical", "hybrid_pq", "native_pq"]:
            s = _mode_stats(df, mode, {"num_clients": num_clients, "alpha": alpha})
            if not s:
                continue
            conv = int(round(s["convergence_mean"])) if not np.isnan(s["convergence_mean"]) else "---"
            conv_std = s["convergence_std"]
            conv_str = f"{conv}" if conv_std == 0 or np.isnan(conv_std) else f"{conv} $\\pm$ {conv_std:.1f}"
            lines.append(
                f"{label} & {MODE_LABELS[mode]} & {_pct(s['accuracy_mean'], s['accuracy_std'])} & "
                f"{_float(s['auroc_mean'], s['auroc_std'])} & {_float(s['f1_mean'], s['f1_std'])} & "
                f"{conv_str} & {_float(s['latency_mean'], s['latency_std'], 2)} \\\\"
            )
    lines.extend(["\\bottomrule", "\\end{tabular}}", "\\end{table*}"])
    out_path.write_text("\n".join(lines), encoding="utf-8")


def emit_byzantine(df: pd.DataFrame, out_path: Path, num_clients: int = 25) -> None:
    lines = [
        "% Auto-generated Byzantine robustness table (Experiment D)",
        "\\begin{table*}[htbp]",
        "\\centering",
        "\\caption{Experiment D: Byzantine Robustness and Aggregator Latency Under PQC Signatures (measured)}",
        "\\label{tab:byzantine_robustness}",
        "\\small",
        "\\resizebox{\\textwidth}{!}{",
        "\\begin{tabular}{lclcccccl}",
        "\\toprule",
        "Attack Profile & Malicious \\% & Aggregator & Accuracy & AUROC & F1-score & Round Latency (s) & PQC Overhead Impact \\\\",
        "\\midrule",
    ]

    baseline = df[
        (df["attack"] == "none")
        & (df["malicious_fraction"] == 0.0)
        & (df["security_mode"] == "native_pq")
        & (df["alpha"] == 1.0)
        & (df["num_clients"] == num_clients)
    ]
    fedavg_base = baseline[baseline["aggregator"] == "fedavg"]
    base_acc = fedavg_base["accuracy"].mean() if not fedavg_base.empty else np.nan

    def attack_label(attack: str) -> str:
        return {"none": "None", "label_flip": "Label Flip", "sign_flip": "Sign Flip"}.get(attack, attack)

    def agg_label(agg: str) -> str:
        return {"fedavg": "FedAvg", "median": "Median", "krum": "Krum"}.get(agg, agg)

    attack_rows = [
        ("none", 0.0, ["fedavg", "median", "krum"]),
        ("label_flip", 0.1, ["fedavg", "median", "krum"]),
        ("label_flip", 0.2, ["fedavg", "median", "krum"]),
        ("sign_flip", 0.2, ["krum"]),
    ]
    for attack, mf, aggs in attack_rows:
        for agg in aggs:
            sub = df[
                (df["attack"] == attack)
                & (df["malicious_fraction"] == mf)
                & (df["aggregator"] == agg)
                & (df["security_mode"] == "native_pq")
                & (df["num_clients"] == num_clients)
                & (df["alpha"] == 1.0)
            ]
            if sub.empty:
                continue
            acc = sub["accuracy"].mean()
            if attack == "none" and agg == "fedavg":
                impact = "Baseline PQ Overhead"
            elif attack == "none":
                base_lat = fedavg_base["mean_round_latency_s"].mean() if not fedavg_base.empty else 0
                lat = sub["mean_round_latency_s"].mean()
                pct = ((lat - base_lat) / base_lat * 100) if base_lat > 0 else 0
                impact = f"{pct:+.1f}\\% vs FedAvg latency"
            else:
                change = ((acc - base_acc) / base_acc * 100) if base_acc > 0 else 0
                if change >= 0:
                    impact = f"Accuracy change: ${change:+.1f}\\%$"
                else:
                    impact = f"Accuracy drop: ${change:.1f}\\%$"
            lines.append(
                f"{attack_label(attack)} & {int(mf * 100)}\\% & {agg_label(agg)} & "
                f"{acc * 100:.2f}\\% & {sub['auroc'].mean():.4f} & {sub['f1'].mean():.4f} & "
                f"{sub['mean_round_latency_s'].mean():.2f} & {impact} \\\\"
            )

    lines.extend(["\\bottomrule", "\\end{tabular}}", "\\end{table*}"])
    out_path.write_text("\n".join(lines), encoding="utf-8")


def emit_all_tables(df: pd.DataFrame, out_dir: Path, default_clients: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    emit_fl_metrics(df, out_dir / "fl_metrics.tex", num_clients=default_clients, alpha=1.0)
    emit_fl_latency(df, out_dir / "fl_latency.tex")
    emit_non_iid(df, out_dir / "non_iid_fl.tex", num_clients=default_clients)
    emit_byzantine(df, out_dir / "byzantine_robustness.tex", num_clients=default_clients)
