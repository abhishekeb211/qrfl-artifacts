"""Residual analysis for exponential growth model."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

try:
    from statsmodels.stats.stattools import durbin_watson
    from statsmodels.stats.diagnostic import acorr_ljungbox

    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

    def durbin_watson(residuals: np.ndarray) -> float:
        diff = np.diff(residuals)
        return float(np.sum(diff**2) / np.sum(residuals**2)) if np.sum(residuals**2) > 0 else float("nan")

from forecasting.fit_models import cooks_distance, fit_exponential_ols


def residual_analysis(df: pd.DataFrame) -> dict:
    fit = fit_exponential_ols(df)
    t = df["t_years"].values.astype(float)
    y = np.log(df["qubits"].values.astype(float))
    y_hat = fit.intercept_ln + fit.growth_rate * t
    residuals = y - y_hat

    shapiro_stat, shapiro_p = stats.shapiro(residuals)
    dw = durbin_watson(residuals)

    # Ljung-Box at lag 1
    if HAS_STATSMODELS:
        try:
            lb = acorr_ljungbox(residuals, lags=[1], return_df=True)
            lb_stat = float(lb["lb_stat"].iloc[0])
            lb_p = float(lb["lb_pvalue"].iloc[0])
        except Exception:
            lb_stat, lb_p = float("nan"), float("nan")
    else:
        lb_stat, lb_p = float("nan"), float("nan")

    cook_df = cooks_distance(df, fit)
    return {
        "residual_mean": float(np.mean(residuals)),
        "residual_std": float(np.std(residuals, ddof=1)),
        "shapiro_stat": float(shapiro_stat),
        "shapiro_p": float(shapiro_p),
        "durbin_watson": float(dw),
        "ljung_box_stat": lb_stat,
        "ljung_box_p": lb_p,
        "cooks_distance": cook_df,
        "residuals": pd.DataFrame({"t": t, "residual": residuals, "fitted_ln": y_hat}),
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    df = pd.read_csv(root / "datasets" / "quantum_hardware_clean.csv")
    result = residual_analysis(df)
    out = root / "results" / "forecasting" / "validation"
    out.mkdir(parents=True, exist_ok=True)
    result["cooks_distance"].to_csv(out / "cooks_distance.csv", index=False)
    result["residuals"].to_csv(out / "residuals.csv", index=False)
    summary = {k: v for k, v in result.items() if k not in ("cooks_distance", "residuals")}
    pd.Series(summary).to_csv(out / "residual_summary.csv")
    print(summary)


if __name__ == "__main__":
    main()
