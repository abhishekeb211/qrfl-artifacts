"""Historical backtesting for quantum hardware forecasting."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from forecasting.fit_models import fit_exponential_ols


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true != 0
    return float(100 * np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])))


def backtest_holdout(
    df: pd.DataFrame,
    train_end_year: int = 2023,
    holdout_start_year: int = 2024,
) -> dict:
    train = df[df["year"] <= train_end_year].copy()
    test = df[df["year"] >= holdout_start_year].copy()
    fit = fit_exponential_ols(train)
    y_true = test["qubits"].values.astype(float)
    y_pred = fit.intercept_a * np.exp(fit.growth_rate * test["t_years"].values.astype(float))
    return {
        "train_n": len(train),
        "test_n": len(test),
        "mae": mae(y_true, y_pred),
        "rmse": rmse(y_true, y_pred),
        "mape": mape(y_true, y_pred),
        "predictions": pd.DataFrame(
            {
                "processor": test["processor_name"].values,
                "year": test["year"].values,
                "observed": y_true,
                "predicted": y_pred,
            }
        ),
    }


def rolling_origin_backtest(df: pd.DataFrame, min_train: int = 10) -> pd.DataFrame:
    rows = []
    sorted_df = df.sort_values("year").reset_index(drop=True)
    for i in range(min_train, len(sorted_df)):
        train = sorted_df.iloc[:i]
        test_row = sorted_df.iloc[i : i + 1]
        fit = fit_exponential_ols(train)
        y_true = test_row["qubits"].values[0]
        t = test_row["t_years"].values[0]
        y_pred = fit.intercept_a * np.exp(fit.growth_rate * t)
        rows.append(
            {
                "cutoff_year": train["year"].max(),
                "processor": test_row["processor_name"].values[0],
                "observed": y_true,
                "predicted": y_pred,
                "abs_error": abs(y_true - y_pred),
                "pct_error": 100 * abs(y_true - y_pred) / y_true,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    df = pd.read_csv(root / "datasets" / "quantum_hardware_clean.csv")
    holdout = backtest_holdout(df)
    rolling = rolling_origin_backtest(df)
    out = root / "results" / "forecasting" / "validation"
    out.mkdir(parents=True, exist_ok=True)
    holdout["predictions"].to_csv(out / "holdout_predictions.csv", index=False)
    rolling.to_csv(out / "rolling_origin.csv", index=False)
    summary = {
        "holdout_mae": holdout["mae"],
        "holdout_rmse": holdout["rmse"],
        "holdout_mape": holdout["mape"],
        "rolling_mae": float(rolling["abs_error"].mean()),
        "rolling_rmse": float(np.sqrt((rolling["abs_error"] ** 2).mean())),
        "rolling_mape": float(rolling["pct_error"].mean()),
    }
    pd.Series(summary).to_csv(out / "backtest_summary.csv")
    print(summary)


if __name__ == "__main__":
    main()
