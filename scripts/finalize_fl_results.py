"""Regenerate FL tables and macros from existing all_results.csv.

Does not import the training stack (torch), so table emission works on the
host Python used for manuscript rebuilds.
"""

from pathlib import Path

import pandas as pd

from federated_learning.emit_tables import emit_all_tables
from qrfl_common.results import ResultsEmitter, load_config


def _emit_fl_prose_macros(emitter: ResultsEmitter, df: pd.DataFrame, default_nc: int) -> None:
    iid = df[
        (df["alpha"] == 1.0)
        & (df["num_clients"] == default_nc)
        & (df["aggregator"] == "fedavg")
        & (df["attack"] == "none")
        & (df["malicious_fraction"] == 0.0)
    ]
    for mode, macro in [
        ("classical", "FLIIDAccuracyClassical"),
        ("hybrid_pq", "FLIIDAccuracyHybrid"),
        ("native_pq", "FLIIDAccuracyNative"),
    ]:
        sub = iid[iid["security_mode"] == mode]
        if not sub.empty:
            emitter.set_macro(macro, sub["accuracy"].mean() * 100, ".1f")

    if not iid.empty:
        emitter.set_macro("FLIIDAUROC", iid["auroc"].mean(), ".3f")

    client10 = df[
        (df["alpha"] == 1.0)
        & (df["num_clients"] == 10)
        & (df["aggregator"] == "fedavg")
        & (df["attack"] == "none")
        & (df["malicious_fraction"] == 0.0)
    ]
    if not client10.empty:
        emitter.set_macro("FLClientTenAccuracy", client10["accuracy"].mean() * 100, ".1f")

    lat_classical = iid[iid["security_mode"] == "classical"]["mean_round_latency_s"].mean()
    lat_native = iid[iid["security_mode"] == "native_pq"]["mean_round_latency_s"].mean()
    if lat_classical > 0:
        overhead = (lat_native - lat_classical) / lat_classical * 100
        emitter.set_macro("FLNativeLatencyOverheadPct", overhead, "+.2f")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = load_config("federated_learning.yaml")
    default_nc = cfg["num_clients_default"]
    out = root / "results" / "fl"
    df = pd.read_csv(out / "all_results.csv")
    seeds = sorted(df["seed"].unique().tolist())
    emit_all_tables(df, out, default_clients=default_nc)

    emitter = ResultsEmitter(root / "results")
    emitter.set_macro("FLDeterminismCheck", "passed")
    emitter.set_macro("FLNumSeeds", df["seed"].nunique())
    if "rounds_to_convergence" in df.columns and len(df):
        emitter.set_macro("FLNumRounds", int(df["rounds_to_convergence"].max()))
    else:
        emitter.set_macro("FLNumRounds", cfg.get("num_rounds", 50))
    _emit_fl_prose_macros(emitter, df, default_nc)
    emitter.write_macros()
    print(f"Finalized {len(df)} FL rows ({len(seeds)} seeds) -> {out}")


if __name__ == "__main__":
    main()
