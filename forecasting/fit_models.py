"""Quantum hardware forecasting: OLS, logistic, bootstrap."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import curve_fit


@dataclass
class GrowthFit:
    intercept_ln: float
    growth_rate: float
    intercept_a: float
    r_squared: float
    adj_r_squared: float
    doubling_time: float
    n: int
    ci_intercept: tuple[float, float]
    ci_growth: tuple[float, float]


def filter_by_status(df: pd.DataFrame, statuses: list[str]) -> pd.DataFrame:
    return df[df["physical_status"].isin(statuses)].copy()


def fit_exponential_ols(df: pd.DataFrame) -> GrowthFit:
    t = df["t_years"].values.astype(float)
    y = np.log(df["qubits"].values.astype(float))
    n = len(t)
    slope, intercept, r_value, p_value, std_err = stats.linregress(t, y)
    y_hat = intercept + slope * t
    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    adj_r2 = 1 - (1 - r2) * (n - 1) / (n - 2) if n > 2 else r2

    # 95% CI for slope and intercept
    t_crit = stats.t.ppf(0.975, n - 2)
    x_mean = np.mean(t)
    sxx = np.sum((t - x_mean) ** 2)
    se_intercept = std_err * math.sqrt(np.sum(t**2) / (n * sxx)) if sxx > 0 else float("nan")
    ci_intercept = (intercept - t_crit * se_intercept, intercept + t_crit * se_intercept)
    ci_growth = (slope - t_crit * std_err, slope + t_crit * std_err)

    return GrowthFit(
        intercept_ln=intercept,
        growth_rate=slope,
        intercept_a=math.exp(intercept),
        r_squared=r2,
        adj_r_squared=adj_r2,
        doubling_time=math.log(2) / slope if slope > 0 else float("inf"),
        n=n,
        ci_intercept=ci_intercept,
        ci_growth=ci_growth,
    )


def logistic(t: np.ndarray, L: float, k: float, t0: float) -> np.ndarray:
    return L / (1 + np.exp(-k * (t - t0)))


def fit_logistic(df: pd.DataFrame) -> dict:
    t = df["t_years"].values.astype(float)
    q = df["qubits"].values.astype(float)
    p0 = [max(q) * 100, 0.5, float(np.median(t))]
    bounds = ([max(q), 0.01, t.min()], [1e8, 10.0, t.max() + 20])
    popt, pcov = curve_fit(logistic, t, q, p0=p0, bounds=bounds, maxfev=20000)
    L, k, t0 = popt
    pred = logistic(t, *popt)
    rmse = float(np.sqrt(np.mean((q - pred) ** 2)))
    n = len(t)
    k_params = 3
    rss = np.sum((q - pred) ** 2)
    aic = n * np.log(rss / n) + 2 * k_params if rss > 0 else float("inf")
    return {"L": L, "k": k, "t0": t0, "rmse": rmse, "aic": aic, "params": popt}


def crossing_year(fit: GrowthFit, eta: float, logical_threshold: float, base_year: int = 2016) -> float:
    physical_threshold = eta * logical_threshold
    t_star = (math.log(physical_threshold) - fit.intercept_ln) / fit.growth_rate
    return base_year + t_star


def bootstrap_crossing_years(
    df: pd.DataFrame,
    eta: float,
    logical_threshold: float,
    n_replicates: int = 5000,
    seed: int = 42,
    base_year: int = 2016,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    years = []
    n = len(df)
    for _ in range(n_replicates):
        sample = df.sample(n=n, replace=True, random_state=int(rng.integers(0, 2**31 - 1)))
        try:
            fit = fit_exponential_ols(sample)
            if fit.growth_rate <= 0:
                continue
            years.append(crossing_year(fit, eta, logical_threshold, base_year))
        except Exception:
            continue
    return np.array(years)


def cooks_distance(df: pd.DataFrame, fit: GrowthFit) -> pd.DataFrame:
    t = df["t_years"].values.astype(float)
    y = np.log(df["qubits"].values.astype(float))
    n = len(t)
    y_hat = fit.intercept_ln + fit.growth_rate * t
    residuals = y - y_hat
    mse = np.sum(residuals**2) / (n - 2)
    leverage = 1 / n + (t - np.mean(t)) ** 2 / np.sum((t - np.mean(t)) ** 2)
    d = (residuals**2 / (2 * mse)) * (leverage / (1 - leverage) ** 2)
    out = df.copy()
    out["cooks_d"] = d
    return out.sort_values("cooks_d", ascending=False)
