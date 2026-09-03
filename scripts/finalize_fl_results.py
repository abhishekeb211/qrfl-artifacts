"""Regenerate FL tables and macros from existing all_results.csv."""

from pathlib import Path

import pandas as pd

from federated_learning.run_experiment import _finalize_results, _merge_cfg_with_seeds
from qrfl_common.results import load_config


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = _merge_cfg_with_seeds(load_config("federated_learning.yaml"), load_config("experiment_seeds.yaml"))
    out = root / "results" / "fl"
    df = pd.read_csv(out / "all_results.csv")
    seeds = sorted(df["seed"].unique().tolist())
    cfg = dict(cfg)
    if "rounds_to_convergence" in df.columns:
        cfg["num_rounds"] = int(df["rounds_to_convergence"].max())
    _finalize_results(df, out, root, cfg, seeds, cfg["num_clients_default"])
    print(f"Finalized {len(df)} FL rows ({len(seeds)} seeds, {cfg['num_rounds']} rounds) -> {out}")


if __name__ == "__main__":
    main()
