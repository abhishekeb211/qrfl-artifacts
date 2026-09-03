"""Run all forecasting modules."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from datasets.build_clean import build_clean_dataset
from forecasting.backtest import backtest_holdout, rolling_origin_backtest
from forecasting.fit_models import (
    bootstrap_crossing_years,
    cooks_distance,
    filter_by_status,
    fit_exponential_ols,
    fit_logistic,
)
from forecasting.emit_tables import build_validation_summary, emit_forecast_validation_table
from forecasting.loocv import loocv
from forecasting.residuals import residual_analysis
from forecasting.scenarios import scenario_projections
from qrfl_common.results import ResultsEmitter, load_config


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    raw = root / "datasets" / "quantum_hardware_raw.csv"
    clean = root / "datasets" / "quantum_hardware_clean.csv"
    build_clean_dataset(raw, clean)
    df = pd.read_csv(clean)
    config = load_config("forecasting.yaml")

    out = root / "results" / "forecasting"
    out.mkdir(parents=True, exist_ok=True)

    # Inclusion models
    inclusion = config["inclusion_models"]
    inclusion_rows = []
    for model_name, spec in inclusion.items():
        sub = filter_by_status(df, spec["statuses"])
        fit = fit_exponential_ols(sub)
        inclusion_rows.append(
            {
                "model": model_name,
                "n": fit.n,
                "growth_rate_b": fit.growth_rate,
                "doubling_time": fit.doubling_time,
                "r_squared": fit.r_squared,
            }
        )
    pd.DataFrame(inclusion_rows).to_csv(out / "inclusion_models.csv", index=False)

    fit = fit_exponential_ols(df)
    logistic = fit_logistic(df)
    boot = bootstrap_crossing_years(
        df,
        config["eta_scenarios"]["baseline"],
        config["ecdsa_logical_threshold"],
        config["bootstrap_replicates"],
    )

    fit_summary = {
        "intercept_ln": fit.intercept_ln,
        "intercept_a": fit.intercept_a,
        "growth_rate_b": fit.growth_rate,
        "doubling_time": fit.doubling_time,
        "r_squared": fit.r_squared,
        "adj_r_squared": fit.adj_r_squared,
        "n": fit.n,
        "ci_intercept_ln_lower": fit.ci_intercept[0],
        "ci_intercept_ln_upper": fit.ci_intercept[1],
        "ci_growth_lower": fit.ci_growth[0],
        "ci_growth_upper": fit.ci_growth[1],
        "logistic_L": logistic["L"],
        "logistic_k": logistic["k"],
        "logistic_t0": logistic["t0"],
        "logistic_rmse": logistic["rmse"],
        "logistic_aic": logistic["aic"],
        "bootstrap_median": float(pd.Series(boot).median()),
        "bootstrap_ci_lower": float(pd.Series(boot).quantile(0.025)),
        "bootstrap_ci_upper": float(pd.Series(boot).quantile(0.975)),
    }
    pd.Series(fit_summary).to_csv(out / "fit_summary.csv")

    cooks_distance(df, fit).to_csv(out / "cooks_distance.csv", index=False)
    scenario_projections(df, config).to_csv(out / "scenarios.csv", index=False)

    # Validation
    val_dir = out / "validation"
    val_dir.mkdir(parents=True, exist_ok=True)
    holdout = backtest_holdout(df, config["train_end_year"], config["holdout_start_year"])
    holdout["predictions"].to_csv(val_dir / "holdout_predictions.csv", index=False)
    rolling = rolling_origin_backtest(df)
    rolling.to_csv(val_dir / "rolling_origin.csv", index=False)
    loo_df = loocv(df)
    loo_df.to_csv(val_dir / "loocv.csv", index=False)
    res = residual_analysis(df)
    res["residuals"].to_csv(val_dir / "residuals.csv", index=False)
    res["cooks_distance"].to_csv(val_dir / "cooks_distance.csv", index=False)

    val_summary = build_validation_summary(df, config["train_end_year"], config["holdout_start_year"])
    pd.Series(val_summary).to_csv(val_dir / "backtest_summary.csv")
    residual_summary = {k: v for k, v in res.items() if k not in ("cooks_distance", "residuals")}
    pd.Series(residual_summary).to_csv(val_dir / "residual_summary.csv")
    emit_forecast_validation_table(val_summary, val_dir / "forecast_validation.tex")

    emitter = ResultsEmitter(root / "results")
    emitter.set_macro("ForecastGrowthRate", fit.growth_rate, ".4f")
    emitter.set_macro("ForecastDoublingTime", fit.doubling_time, ".2f")
    emitter.set_macro("ForecastRSquared", fit.r_squared, ".4f")
    emitter.set_macro("ForecastBootstrapCILower", fit_summary["bootstrap_ci_lower"], ".2f")
    emitter.set_macro("ForecastHoldoutMAE", val_summary["holdout_mae"], ".2f")
    emitter.set_macro("ForecastHoldoutRMSE", val_summary["holdout_rmse"], ".2f")
    emitter.set_macro("ForecastHoldoutMAPE", val_summary["holdout_mape"], ".2f")
    emitter.set_macro("ForecastLOOCVMAE", val_summary["loocv_mae"], ".2f")
    emitter.write_macros()
    print("Forecasting complete:", out)


if __name__ == "__main__":
    main()
