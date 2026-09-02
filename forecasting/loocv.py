"""Leave-one-out cross-validation for small quantum hardware dataset."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from forecasting.fit_models import fit_exponential_ols


def loocv(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for idx in range(len(df)):
        train = df.drop(index=idx)
        test = df.iloc[idx]
        fit = fit_exponential_ols(train)
        y_pred = fit.intercept_a * np.exp(fit.growth_rate * test["t_years"])
        rows.append(
            {
                "left_out": test["processor_name"],
                "year": test["year"],
                "observed_qubits": test["qubits"],
                "predicted_qubits": y_pred,
                "abs_error": abs(test["qubits"] - y_pred),
                "pct_error": 100 * abs(test["qubits"] - y_pred) / test["qubits"],
                "growth_rate_b": fit.growth_rate,
                "intercept_a": fit.intercept_a,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    df = pd.read_csv(root / "datasets" / "quantum_hardware_clean.csv")
    results = loocv(df)
    out = root / "results" / "forecasting" / "validation"
    out.mkdir(parents=True, exist_ok=True)
    results.to_csv(out / "loocv.csv", index=False)
    print(
        {
            "loocv_mae": float(results["abs_error"].mean()),
            "loocv_rmse": float(np.sqrt((results["abs_error"] ** 2).mean())),
            "loocv_mape": float(results["pct_error"].mean()),
        }
    )


if __name__ == "__main__":
    main()
