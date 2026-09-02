"""Scenario projections with uncertainty intervals."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from forecasting.fit_models import bootstrap_crossing_years, crossing_year, fit_exponential_ols
from qrfl_common.results import ResultsEmitter, load_config


def scenario_projections(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    fit = fit_exponential_ols(df)
    rows = []
    logical = config["ecdsa_logical_threshold"]
    base_year = config["base_year"]
    for name, eta in config["eta_scenarios"].items():
        point = crossing_year(fit, eta, logical, base_year)
        boot = bootstrap_crossing_years(
            df,
            eta,
            logical,
            n_replicates=config.get("bootstrap_replicates", 5000),
            base_year=base_year,
        )
        rows.append(
            {
                "scenario": name,
                "eta": eta,
                "point_estimate_year": point,
                "bootstrap_median": float(np.median(boot)) if len(boot) else float("nan"),
                "ci_lower_95": float(np.percentile(boot, 2.5)) if len(boot) else float("nan"),
                "ci_upper_95": float(np.percentile(boot, 97.5)) if len(boot) else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    config = load_config("forecasting.yaml")
    df = pd.read_csv(root / "datasets" / "quantum_hardware_clean.csv")
    scenarios = scenario_projections(df, config)
    out = root / "results" / "forecasting"
    out.mkdir(parents=True, exist_ok=True)
    scenarios.to_csv(out / "scenarios.csv", index=False)

    emitter = ResultsEmitter(out.parent)
    baseline = scenarios[scenarios["scenario"] == "baseline"].iloc[0]
    emitter.set_macro("ForecastBaselineYear", baseline["point_estimate_year"], ".2f")
    emitter.set_macro("ForecastBaselineCILower", baseline["ci_lower_95"], ".2f")
    emitter.set_macro("ForecastBaselineCIUpper", baseline["ci_upper_95"], ".2f")
    emitter.write_macros()
    print(scenarios)


if __name__ == "__main__":
    main()
