"""Build cleaned quantum hardware dataset with derived time index."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_YEAR = 2016


def build_clean_dataset(raw_path: Path, out_path: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    df["t_years"] = df["year"] + (df["month"] - 1) / 12.0 - BASE_YEAR
    df["ln_qubits"] = df["qubits"].apply(lambda x: pd.NA if x <= 0 else __import__("math").log(x))
    df = df.dropna(subset=["ln_qubits"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return df


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    build_clean_dataset(
        root / "datasets" / "quantum_hardware_raw.csv",
        root / "datasets" / "quantum_hardware_clean.csv",
    )
