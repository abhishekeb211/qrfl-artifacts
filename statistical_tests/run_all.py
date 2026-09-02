"""Statistical significance testing for FL and PQC results."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from scipy import stats

from qrfl_common.results import ResultsEmitter, load_config


def shapiro_ok(values: np.ndarray, alpha: float = 0.05) -> bool:
    if len(values) < 3:
        return False
    _, p = stats.shapiro(values)
    return p > alpha


def paired_test(
    a: np.ndarray,
    b: np.ndarray,
    alpha: float = 0.05,
) -> dict:
    diff = a - b
    normal = shapiro_ok(diff, alpha)
    if normal:
        stat, p = stats.ttest_rel(a, b)
        dz = float(np.mean(diff) / np.std(diff, ddof=1)) if np.std(diff, ddof=1) > 0 else 0.0
        ci = stats.t.interval(0.95, len(diff) - 1, loc=np.mean(diff), scale=stats.sem(diff))
        test_name = "paired_t_test"
    else:
        stat, p = stats.wilcoxon(a, b)
        n = len(diff)
        r = 1 - (2 * stat) / (n * (n + 1) / 2) if n > 0 else 0.0
        dz = float(r)
        ci = (float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5)))
        test_name = "wilcoxon_signed_rank"
    return {
        "test": test_name,
        "statistic": float(stat),
        "p_value": float(p),
        "effect_size": dz,
        "ci_lower": float(ci[0]),
        "ci_upper": float(ci[1]),
        "mean_a": float(np.mean(a)),
        "mean_b": float(np.mean(b)),
        "sd_a": float(np.std(a, ddof=1)),
        "sd_b": float(np.std(b, ddof=1)),
        "significant": float(p) < alpha,
    }


def tost_equivalence(
    a: np.ndarray,
    b: np.ndarray,
    margin: float,
    alpha: float = 0.05,
) -> dict:
    diff = a - b
    mean_diff = float(np.mean(diff))
    se = stats.sem(diff)
    df = len(diff) - 1
    t_lower = (mean_diff + margin) / se if se > 0 else float("inf")
    t_upper = (mean_diff - margin) / se if se > 0 else float("-inf")
    p_lower = float(stats.t.cdf(t_lower, df))
    p_upper = float(1 - stats.t.cdf(t_upper, df))
    p_equiv = max(p_lower, p_upper)
    return {
        "test": "tost_equivalence",
        "margin": margin,
        "mean_diff": mean_diff,
        "p_equivalence": p_equiv,
        "equivalent": p_equiv < alpha,
        "max_abs_diff": float(np.max(np.abs(diff))),
    }


def repeated_measures_anova(wide_df: pd.DataFrame, value_col_prefix: str = "") -> dict:
    """Simple one-way repeated measures via Friedman test (non-parametric fallback)."""
    cols = [c for c in wide_df.columns if c.startswith(value_col_prefix) or value_col_prefix == ""]
    if value_col_prefix:
        cols = [c for c in wide_df.columns if c.startswith(value_col_prefix)]
    else:
        cols = list(wide_df.columns)
    arrays = [wide_df[c].values for c in cols]
    stat, p = stats.friedmanchisquare(*arrays)
    return {"test": "friedman", "statistic": float(stat), "p_value": float(p), "columns": cols}


def holm_correction(p_values: list[float]) -> list[float]:
    """Step-down Holm-Bonferroni adjusted p-values."""
    m = len(p_values)
    order = np.argsort(p_values)
    adjusted = np.ones(m)
    prev = 0.0
    for rank, idx in enumerate(order):
        raw = p_values[idx] * (m - rank)
        adj = min(1.0, max(raw, prev))
        adjusted[idx] = adj
        prev = adj
    return adjusted.tolist()


def _extract_p_value(row: dict) -> float:
    if "p_value" in row and pd.notna(row.get("p_value")):
        return float(row["p_value"])
    if "p_equivalence" in row and pd.notna(row.get("p_equivalence")):
        return float(row["p_equivalence"])
    return float("nan")


def apply_holm_correction(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    pvals = [_extract_p_value(row) for _, row in out.iterrows()]
    out["p_value_raw"] = pvals
    valid_idx = [i for i, p in enumerate(pvals) if not np.isnan(p)]
    adjusted = [float("nan")] * len(pvals)
    if valid_idx:
        subset = [pvals[i] for i in valid_idx]
        holm = holm_correction(subset)
        for j, i in enumerate(valid_idx):
            adjusted[i] = holm[j]
    out["p_value_holm"] = adjusted
    out["significant_holm"] = out["p_value_holm"] < 0.05
    return out


def analyze_fl_results(fl_path: Path, alpha: float, eq_margin_acc: float, eq_margin_f1: float) -> pd.DataFrame:
    df = pd.read_csv(fl_path)
    rows = []
    pairs = [
        ("classical", "hybrid_pq"),
        ("classical", "native_pq"),
        ("hybrid_pq", "native_pq"),
    ]
    for alpha_val in df["alpha"].unique():
        sub = df[(df["num_clients"] == df["num_clients"].mode().iloc[0]) & (df["alpha"] == alpha_val)]
        if "attack" in sub.columns:
            sub = sub[sub["attack"] == "none"]
        elif "malicious_fraction" in sub.columns:
            sub = sub[sub["malicious_fraction"] == 0.0]
        for metric in ["accuracy", "f1", "mean_round_latency_s"]:
            for mode_a, mode_b in pairs:
                a = sub[sub["security_mode"] == mode_a].groupby("seed")[metric].mean()
                b = sub[sub["security_mode"] == mode_b].groupby("seed")[metric].mean()
                aligned = pd.concat([a, b], axis=1, join="inner").dropna()
                if aligned.empty:
                    continue
                if metric in ("accuracy", "f1"):
                    res = tost_equivalence(
                        aligned.iloc[:, 0].values,
                        aligned.iloc[:, 1].values,
                        eq_margin_acc if metric == "accuracy" else eq_margin_f1,
                        alpha,
                    )
                    res["interpretation"] = "equivalent" if res["equivalent"] else "not_equivalent"
                else:
                    res = paired_test(aligned.iloc[:, 0].values, aligned.iloc[:, 1].values, alpha)
                    res["interpretation"] = "significant" if res["significant"] else "not_significant"
                rows.append(
                    {
                        "alpha": alpha_val,
                        "metric": metric,
                        "mode_a": mode_a,
                        "mode_b": mode_b,
                        **res,
                    }
                )
    return pd.DataFrame(rows)


def analyze_pqc_results(pqc_path: Path, alpha: float) -> pd.DataFrame:
    if not pqc_path.exists():
        return pd.DataFrame()
    df = pd.read_csv(pqc_path)
    rows = []
    for (scheme, op), group in df.groupby(["scheme", "operation"]):
        rows.append(
            {
                "scheme": scheme,
                "operation": op,
                "mean_ms": group["latency_ms"].mean(),
                "sd_ms": group["latency_ms"].std(ddof=1),
                "n": len(group),
            }
        )
    return pd.DataFrame(rows)


def emit_latex_table(df: pd.DataFrame, out_path: Path) -> None:
    if df.empty:
        out_path.write_text("% No statistical results yet\n", encoding="utf-8")
        return
    lines = [
        "% Auto-generated statistical test table",
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Statistical comparison of security configurations (Holm-corrected)}",
        "\\label{tab:statistical_tests}",
        "\\small",
        "\\begin{tabular}{llllrrrr}",
        "\\toprule",
        "Metric & Mode A & Mode B & Test & Statistic & $p$ (Holm) & Effect & Interpretation \\\\",
        "\\midrule",
    ]
    for _, row in df.iterrows():
        pcol = row.get("p_value_holm", row.get("p_value", row.get("p_equivalence", float("nan"))))
        stat = row.get("statistic", row.get("mean_diff", float("nan")))
        effect = row.get("effect_size", row.get("max_abs_diff", float("nan")))
        interp = row.get("interpretation", "")
        if "significant_holm" in row and row.get("test") not in ("tost_equivalence",):
            interp = "significant" if row["significant_holm"] else "not_significant"
        lines.append(
            f"{row.get('metric','')} & {row.get('mode_a','')} & {row.get('mode_b','')} & "
            f"{row.get('test','')} & {stat:.4f} & {pcol:.4f} & {effect:.4f} & {interp} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}"])
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = load_config("experiment_seeds.yaml")["statistical_tests"]
    alpha = cfg["alpha"]

    fl_path = root / "results" / "fl" / "all_results.csv"
    if not fl_path.exists():
        print("WARN: FL results not found; run federated_learning first")
        fl_stats = pd.DataFrame()
    else:
        fl_stats = analyze_fl_results(fl_path, alpha, cfg["equivalence_margin_accuracy"], cfg["equivalence_margin_f1"])
        fl_stats = apply_holm_correction(fl_stats)

    pqc_stats = analyze_pqc_results(root / "results" / "pqc" / "trials.csv", alpha)

    out = root / "results" / "statistics"
    out.mkdir(parents=True, exist_ok=True)
    fl_stats.to_csv(out / "fl_statistical_tests.csv", index=False)
    pqc_stats.to_csv(out / "pqc_summary_stats.csv", index=False)
    emit_latex_table(fl_stats, out / "statistical_tests.tex")

    emitter = ResultsEmitter(root / "results")
    if not fl_stats.empty:
        lat = fl_stats[(fl_stats["metric"] == "mean_round_latency_s") & (fl_stats["mode_a"] == "classical") & (fl_stats["mode_b"] == "native_pq")]
        if not lat.empty:
            emitter.set_macro("StatLatencyClassicalVsNativeP", lat.iloc[0]["p_value"], ".4f")
    emitter.write_macros()
    print("Statistical tests complete:", out)


if __name__ == "__main__":
    main()
