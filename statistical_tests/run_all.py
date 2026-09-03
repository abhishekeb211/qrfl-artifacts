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
    max_abs = float(np.max(np.abs(diff)))
    if max_abs < margin or np.allclose(diff, 0.0):
        return {
            "test": "tost_equivalence",
            "margin": margin,
            "mean_diff": mean_diff,
            "statistic": 0.0,
            "p_equivalence": 0.0,
            "equivalent": True,
            "max_abs_diff": max_abs,
        }
    se = stats.sem(diff)
    df = len(diff) - 1
    if se == 0 or df < 1:
        return {
            "test": "tost_equivalence",
            "margin": margin,
            "mean_diff": mean_diff,
            "statistic": 0.0,
            "p_equivalence": 0.0,
            "equivalent": max_abs < margin,
            "max_abs_diff": max_abs,
        }
    t_lower = (mean_diff + margin) / se
    t_upper = (mean_diff - margin) / se
    p_lower = float(stats.t.cdf(t_lower, df))
    p_upper = float(1 - stats.t.cdf(t_upper, df))
    p_equiv = max(p_lower, p_upper)
    return {
        "test": "tost_equivalence",
        "margin": margin,
        "mean_diff": mean_diff,
        "statistic": mean_diff,
        "p_equivalence": p_equiv,
        "equivalent": p_equiv < alpha,
        "max_abs_diff": max_abs,
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


def _baseline_fl_subset(df: pd.DataFrame, default_nc: int, alpha_val: float) -> pd.DataFrame:
    sub = df[
        (df["num_clients"] == default_nc)
        & (df["alpha"] == alpha_val)
        & (df["aggregator"] == "fedavg")
        & (df["attack"] == "none")
        & (df["malicious_fraction"] == 0.0)
    ]
    return sub


def _compare_modes(
    sub: pd.DataFrame,
    metric: str,
    pairs: list[tuple[str, str]],
    alpha: float,
    eq_margin_acc: float,
    eq_margin_f1: float,
    section: str,
    alpha_val: float,
) -> list[dict]:
    rows = []
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
                "section": section,
                "alpha": alpha_val,
                "metric": metric,
                "mode_a": mode_a,
                "mode_b": mode_b,
                **res,
            }
        )
    return rows


def analyze_fl_results(
    fl_path: Path,
    alpha: float,
    eq_margin_acc: float,
    eq_margin_f1: float,
    default_nc: int = 25,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(fl_path)
    pairs = [
        ("classical", "hybrid_pq"),
        ("classical", "native_pq"),
        ("hybrid_pq", "native_pq"),
    ]
    primary_rows: list[dict] = []
    non_iid_rows: list[dict] = []

    iid_sub = _baseline_fl_subset(df, default_nc, 1.0)
    for metric in ["accuracy", "f1", "mean_round_latency_s"]:
        primary_rows.extend(
            _compare_modes(iid_sub, metric, pairs, alpha, eq_margin_acc, eq_margin_f1, "iid", 1.0)
        )

    for alpha_val in sorted(a for a in df["alpha"].unique() if a != 1.0):
        sub = _baseline_fl_subset(df, default_nc, alpha_val)
        for metric in ["accuracy", "f1", "mean_round_latency_s"]:
            non_iid_rows.extend(
                _compare_modes(sub, metric, pairs, alpha, eq_margin_acc, eq_margin_f1, "non_iid", alpha_val)
            )

    return pd.DataFrame(primary_rows), pd.DataFrame(non_iid_rows)


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


def _row_interp(row: pd.Series) -> str:
    if row.get("test") == "tost_equivalence":
        holm_p = row.get("p_value_holm", row.get("p_equivalence"))
        if pd.notna(holm_p) and float(holm_p) < 0.05:
            return "equivalent"
        if row.get("equivalent"):
            return "equivalent"
        return "not_equivalent"
    return "significant" if row.get("significant_holm") else "not_significant"


def emit_latex_table(primary: pd.DataFrame, out_path: Path, non_iid: pd.DataFrame | None = None) -> None:
    if primary.empty:
        out_path.write_text("% No statistical results yet\n", encoding="utf-8")
        return
    lines = [
        "% Auto-generated statistical test table",
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Statistical comparison of security configurations at IID baseline ($\\alpha=1.0$, 25 clients; Holm-corrected)}",
        "\\label{tab:statistical_tests}",
        "\\small",
        "\\begin{tabular}{llllrrrr}",
        "\\toprule",
        "Metric & Mode A & Mode B & Test & Statistic & $p$ (Holm) & Effect & Interpretation \\\\",
        "\\midrule",
    ]
    for _, row in primary.iterrows():
        pcol = row.get("p_value_holm", row.get("p_value", row.get("p_equivalence", float("nan"))))
        stat = row.get("statistic", row.get("mean_diff", float("nan")))
        effect = row.get("effect_size", row.get("max_abs_diff", float("nan")))
        if pd.isna(effect) and row.get("test") == "tost_equivalence":
            effect = row.get("max_abs_diff", float("nan"))
        interp = _row_interp(row)
        lines.append(
            f"{row.get('metric','')} & {row.get('mode_a','')} & {row.get('mode_b','')} & "
            f"{row.get('test','')} & {stat:.4f} & {pcol:.4f} & {effect:.4f} & {interp} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}"])
    if non_iid is not None and not non_iid.empty:
        lines.extend(
            [
                "",
                "% Non-IID supplementary comparisons (CSV only; not duplicated in main table)",
                f"% {len(non_iid)} non-IID pairwise rows in fl_statistical_tests_non_iid.csv",
            ]
        )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = load_config("experiment_seeds.yaml")["statistical_tests"]
    alpha = cfg["alpha"]

    fl_path = root / "results" / "fl" / "all_results.csv"
    fl_cfg = load_config("federated_learning.yaml")
    default_nc = fl_cfg.get("num_clients_default", 25)
    if not fl_path.exists():
        print("WARN: FL results not found; run federated_learning first")
        fl_primary = pd.DataFrame()
        fl_non_iid = pd.DataFrame()
    else:
        fl_primary, fl_non_iid = analyze_fl_results(
            fl_path, alpha, cfg["equivalence_margin_accuracy"], cfg["equivalence_margin_f1"], default_nc
        )
        fl_primary = apply_holm_correction(fl_primary)
        if not fl_non_iid.empty:
            fl_non_iid = apply_holm_correction(fl_non_iid)

    pqc_stats = analyze_pqc_results(root / "results" / "pqc" / "trials.csv", alpha)

    out = root / "results" / "statistics"
    out.mkdir(parents=True, exist_ok=True)
    fl_primary.to_csv(out / "fl_statistical_tests.csv", index=False)
    fl_non_iid.to_csv(out / "fl_statistical_tests_non_iid.csv", index=False)
    pqc_stats.to_csv(out / "pqc_summary_stats.csv", index=False)
    emit_latex_table(fl_primary, out / "statistical_tests.tex", fl_non_iid)

    emitter = ResultsEmitter(root / "results")
    if not fl_primary.empty:
        lat = fl_primary[
            (fl_primary["metric"] == "mean_round_latency_s")
            & (fl_primary["mode_a"] == "classical")
            & (fl_primary["mode_b"] == "native_pq")
        ]
        if not lat.empty:
            pcol = lat.iloc[0].get("p_value_holm", lat.iloc[0].get("p_value"))
            emitter.set_macro("StatLatencyClassicalVsNativeP", pcol, ".4f")
    emitter.write_macros()
    print("Statistical tests complete:", out)


if __name__ == "__main__":
    main()
