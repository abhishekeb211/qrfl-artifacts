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
    if value_col_prefix:
        cols = [c for c in wide_df.columns if c.startswith(value_col_prefix)]
    else:
        cols = list(wide_df.columns)
    # Identical values across modes (e.g., mask-cancelled accuracy) make Friedman undefined.
    stacked = wide_df[cols].to_numpy()
    if stacked.size == 0 or np.allclose(stacked, stacked[:, :1]):
        return {
            "test": "friedman",
            "statistic": 0.0,
            "p_value": 1.0,
            "columns": cols,
            "note": "constant_across_modes",
        }
    arrays = [wide_df[c].values for c in cols]
    stat, p = stats.friedmanchisquare(*arrays)
    if np.isnan(stat) or np.isnan(p):
        return {
            "test": "friedman",
            "statistic": 0.0,
            "p_value": 1.0,
            "columns": cols,
            "note": "undefined_ties",
        }
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


def _friedman_three_mode(sub: pd.DataFrame, metric: str, section: str, alpha_val: float) -> dict | None:
    """Friedman test across classical / hybrid_pq / native_pq for one metric."""
    modes = ["classical", "hybrid_pq", "native_pq"]
    series = []
    for mode in modes:
        s = sub[sub["security_mode"] == mode].groupby("seed")[metric].mean()
        series.append(s.rename(mode))
    wide = pd.concat(series, axis=1, join="inner").dropna()
    if wide.shape[0] < 3 or wide.shape[1] < 3:
        return None
    res = repeated_measures_anova(wide)
    return {
        "section": section,
        "alpha": alpha_val,
        "metric": metric,
        "mode_a": "classical",
        "mode_b": "hybrid_pq+native_pq",
        "test": "friedman",
        "statistic": res["statistic"],
        "p_value": res["p_value"],
        "effect_size": float("nan"),
        "significant": res["p_value"] < 0.05,
        "interpretation": "significant" if res["p_value"] < 0.05 else "not_significant",
        "n_seeds": int(wide.shape[0]),
    }


def analyze_fl_results(
    fl_path: Path,
    alpha: float,
    eq_margin_acc: float,
    eq_margin_f1: float,
    default_nc: int = 25,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(fl_path)
    pairs = [
        ("classical", "hybrid_pq"),
        ("classical", "native_pq"),
        ("hybrid_pq", "native_pq"),
    ]
    primary_rows: list[dict] = []
    non_iid_rows: list[dict] = []
    friedman_rows: list[dict] = []

    iid_sub = _baseline_fl_subset(df, default_nc, 1.0)
    for metric in ["accuracy", "f1", "mean_round_latency_s"]:
        primary_rows.extend(
            _compare_modes(iid_sub, metric, pairs, alpha, eq_margin_acc, eq_margin_f1, "iid", 1.0)
        )
        fr = _friedman_three_mode(iid_sub, metric, "iid", 1.0)
        if fr:
            friedman_rows.append(fr)

    for alpha_val in sorted(a for a in df["alpha"].unique() if a != 1.0):
        sub = _baseline_fl_subset(df, default_nc, alpha_val)
        for metric in ["accuracy", "f1", "mean_round_latency_s"]:
            non_iid_rows.extend(
                _compare_modes(sub, metric, pairs, alpha, eq_margin_acc, eq_margin_f1, "non_iid", alpha_val)
            )
            fr = _friedman_three_mode(sub, metric, "non_iid", float(alpha_val))
            if fr:
                friedman_rows.append(fr)

    return pd.DataFrame(primary_rows), pd.DataFrame(non_iid_rows), pd.DataFrame(friedman_rows)


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


def _fmt_num(val, default: str = "---") -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    try:
        return f"{float(val):.4f}"
    except (TypeError, ValueError):
        return default


def _tex_ident(val, default: str = "---") -> str:
    """Escape underscores so auto-generated identifiers are valid LaTeX text."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    return str(val).replace("_", r"\_")


def emit_latex_table(
    primary: pd.DataFrame,
    out_path: Path,
    non_iid: pd.DataFrame | None = None,
    friedman: pd.DataFrame | None = None,
) -> None:
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
            f"{_tex_ident(row.get('metric',''))} & {_tex_ident(row.get('mode_a',''))} & "
            f"{_tex_ident(row.get('mode_b',''))} & {_tex_ident(row.get('test',''))} & "
            f"{_fmt_num(stat)} & {_fmt_num(pcol)} & {_fmt_num(effect)} & {_tex_ident(interp)} \\\\"
        )
    if friedman is not None and not friedman.empty:
        iid_fr = friedman[friedman["section"] == "iid"] if "section" in friedman.columns else friedman
        for _, row in iid_fr.iterrows():
            lines.append(
                f"{_tex_ident(row.get('metric',''))} & all three & --- & friedman & "
                f"{_fmt_num(row.get('statistic'))} & {_fmt_num(row.get('p_value'))} & --- & "
                f"{_tex_ident(row.get('interpretation',''))} \\\\"
            )
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}"])
    if non_iid is not None and not non_iid.empty:
        lines.extend(
            [
                "",
                "% Non-IID pairwise comparisons also emitted as statistical_tests_non_iid.tex",
                f"% {len(non_iid)} non-IID pairwise rows in fl_statistical_tests_non_iid.csv",
            ]
        )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def emit_non_iid_latex(non_iid: pd.DataFrame, friedman: pd.DataFrame, out_path: Path) -> None:
    """Compact non-IID statistical table for manuscript inclusion."""
    if non_iid.empty:
        out_path.write_text("% No non-IID statistical results yet\n", encoding="utf-8")
        return
    lines = [
        "% Auto-generated non-IID statistical test table",
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Non-IID statistical comparisons (Dirichlet $\\alpha\\in\\{0.1,0.5\\}$, 25 clients; Holm-corrected)}",
        "\\label{tab:statistical_tests_non_iid}",
        "\\small",
        "\\resizebox{\\textwidth}{!}{%",
        "\\begin{tabular}{cllllrrr}",
        "\\toprule",
        "$\\alpha$ & Metric & Mode A & Mode B & Test & $p$ (Holm) & Effect & Interpretation \\\\",
        "\\midrule",
    ]
    # Prefer latency + one utility metric to keep table compact
    prefer = non_iid[
        non_iid["metric"].isin(["mean_round_latency_s", "accuracy"])
        & (non_iid["mode_a"] == "classical")
        & (non_iid["mode_b"].isin(["hybrid_pq", "native_pq"]))
    ]
    if prefer.empty:
        prefer = non_iid
    for _, row in prefer.iterrows():
        pcol = row.get("p_value_holm", row.get("p_value", row.get("p_equivalence", float("nan"))))
        effect = row.get("effect_size", row.get("max_abs_diff", float("nan")))
        if pd.isna(effect) and row.get("test") == "tost_equivalence":
            effect = row.get("max_abs_diff", float("nan"))
        lines.append(
            f"{row.get('alpha','')} & {_tex_ident(row.get('metric',''))} & "
            f"{_tex_ident(row.get('mode_a',''))} & {_tex_ident(row.get('mode_b',''))} & "
            f"{_tex_ident(row.get('test',''))} & {_fmt_num(pcol)} & {_fmt_num(effect)} & "
            f"{_tex_ident(_row_interp(row))} \\\\"
        )
    if friedman is not None and not friedman.empty:
        non_fr = friedman[friedman["section"] == "non_iid"] if "section" in friedman.columns else pd.DataFrame()
        lat_fr = non_fr[non_fr["metric"] == "mean_round_latency_s"] if not non_fr.empty else non_fr
        for _, row in lat_fr.iterrows():
            lines.append(
                f"{row.get('alpha','')} & {_tex_ident(row.get('metric',''))} & all three & --- & friedman & "
                f"{_fmt_num(row.get('p_value'))} & --- & {_tex_ident(row.get('interpretation',''))} \\\\"
            )
    lines.extend(["\\bottomrule", "\\end{tabular}%", "}", "\\end{table}"])
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = load_config("experiment_seeds.yaml")["statistical_tests"]
    alpha = cfg["alpha"]

    fl_path = root / "results" / "fl" / "all_results.csv"
    fl_cfg = load_config("federated_learning.yaml")
    default_nc = fl_cfg.get("num_clients_default", 25)
    fl_friedman = pd.DataFrame()
    if not fl_path.exists():
        print("WARN: FL results not found; run federated_learning first")
        fl_primary = pd.DataFrame()
        fl_non_iid = pd.DataFrame()
    else:
        fl_primary, fl_non_iid, fl_friedman = analyze_fl_results(
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
    fl_friedman.to_csv(out / "fl_friedman_tests.csv", index=False)
    pqc_stats.to_csv(out / "pqc_summary_stats.csv", index=False)
    emit_latex_table(fl_primary, out / "statistical_tests.tex", fl_non_iid, fl_friedman)
    emit_non_iid_latex(fl_non_iid, fl_friedman, out / "statistical_tests_non_iid.tex")

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
    if not fl_friedman.empty:
        lat_fr = fl_friedman[
            (fl_friedman["section"] == "iid") & (fl_friedman["metric"] == "mean_round_latency_s")
        ]
        if not lat_fr.empty:
            emitter.set_macro("StatFriedmanLatencyP", lat_fr.iloc[0]["p_value"], ".4f")
    emitter.write_macros()
    print("Statistical tests complete:", out)


if __name__ == "__main__":
    main()
