"""Emit LaTeX tables for forecast validation results."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from forecasting.backtest import backtest_holdout, rolling_origin_backtest
from forecasting.loocv import loocv
from forecasting.residuals import residual_analysis


def _fmt(value: float, digits: int = 2) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "---"
    return f"{value:.{digits}f}"


def build_validation_summary(df: pd.DataFrame, train_end_year: int, holdout_start_year: int) -> dict:
    holdout = backtest_holdout(df, train_end_year, holdout_start_year)
    rolling = rolling_origin_backtest(df)
    loo = loocv(df)
    res = residual_analysis(df)

    return {
        "holdout_mae": holdout["mae"],
        "holdout_rmse": holdout["rmse"],
        "holdout_mape": holdout["mape"],
        "rolling_mae": float(rolling["abs_error"].mean()),
        "rolling_rmse": float(np.sqrt((rolling["abs_error"] ** 2).mean())),
        "rolling_mape": float(rolling["pct_error"].mean()),
        "loocv_mae": float(loo["abs_error"].mean()),
        "loocv_rmse": float(np.sqrt((loo["abs_error"] ** 2).mean())),
        "loocv_mape": float(loo["pct_error"].mean()),
        "residual_mean": res["residual_mean"],
        "residual_std": res["residual_std"],
        "shapiro_p": res["shapiro_p"],
        "durbin_watson": res["durbin_watson"],
        "ljung_box_p": res["ljung_box_p"],
    }


def emit_forecast_validation_table(summary: dict, out_path: Path) -> None:
    lines = [
        "% Auto-generated forecast validation table",
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Forecast validation metrics for exponential growth model (measured)}",
        "\\label{tab:forecast_validation}",
        "\\small",
        "\\begin{tabular}{lrrr}",
        "\\toprule",
        "Validation strategy & MAE & RMSE & MAPE (\\%) \\\\",
        "\\midrule",
        f"Hold-out (2024--2026) & {_fmt(summary['holdout_mae'])} & {_fmt(summary['holdout_rmse'])} & {_fmt(summary['holdout_mape'])} \\\\",
        f"Rolling-origin & {_fmt(summary['rolling_mae'])} & {_fmt(summary['rolling_rmse'])} & {_fmt(summary['rolling_mape'])} \\\\",
        f"Leave-one-out ($n=20$) & {_fmt(summary['loocv_mae'])} & {_fmt(summary['loocv_rmse'])} & {_fmt(summary['loocv_mape'])} \\\\",
        "\\midrule",
        "\\multicolumn{4}{l}{\\textit{Residual diagnostics (log-scale)}} \\\\",
        f"Residual mean & \\multicolumn{{3}}{{r}}{{{_fmt(summary['residual_mean'], 4)}}} \\\\",
        f"Shapiro--Wilk $p$ & \\multicolumn{{3}}{{r}}{{{_fmt(summary['shapiro_p'], 4)}}} \\\\",
        f"Durbin--Watson & \\multicolumn{{3}}{{r}}{{{_fmt(summary['durbin_watson'], 4)}}} \\\\",
        f"Ljung--Box $p$ (lag 1) & \\multicolumn{{3}}{{r}}{{{_fmt(summary['ljung_box_p'], 4)}}} \\\\",
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")
