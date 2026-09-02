"""Run FL experiments: three security modes, non-IID, Byzantine."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from federated_learning.aggregation import coordinate_median, fedavg, krum
from federated_learning.attacks import apply_attack, select_malicious_clients
from federated_learning.data import dirichlet_partition, load_pneumoniamnist, make_client_loaders
from federated_learning.emit_tables import emit_all_tables
from federated_learning.model import PneumoniaCNN, get_parameters, set_parameters
from federated_learning.security import DEFAULT_MODES, apply_mask, crypto_round_overhead
from federated_learning.train_eval import evaluate, train_local
from qrfl_common.results import ResultsEmitter, load_config


def run_single(
    seed: int,
    num_clients: int,
    alpha: float,
    security_mode: str,
    aggregator: str,
    attack: str,
    malicious_fraction: float,
    cfg: dict,
    device: torch.device,
) -> dict:
    torch.manual_seed(seed)
    np.random.seed(seed)
    train_ds, val_ds, test_ds = load_pneumoniamnist(cfg["batch_size"])
    partitions = dirichlet_partition(train_ds, num_clients, alpha, seed)
    client_loaders = make_client_loaders(train_ds, partitions, cfg["batch_size"], seed=seed)
    test_loader = make_client_loaders(test_ds, [list(range(len(test_ds)))], cfg["batch_size"])[0]
    val_loader = make_client_loaders(val_ds, [list(range(len(val_ds)))], cfg["batch_size"])[0]

    global_model = PneumoniaCNN().to(device)
    mode_cfg = DEFAULT_MODES[security_mode]
    malicious = select_malicious_clients(num_clients, malicious_fraction, seed + 999)

    round_latencies = []
    rounds_to_convergence = cfg["num_rounds"]
    threshold = cfg.get("convergence_val_threshold", 0.85)

    for round_id in range(cfg["num_rounds"]):
        start = time.perf_counter()
        local_updates = []
        for client_id, loader in enumerate(client_loaders):
            local_model = PneumoniaCNN().to(device)
            set_parameters(local_model, get_parameters(global_model))
            params = train_local(local_model, loader, cfg["local_epochs"], cfg["learning_rate"], device)
            flat_update = [p.clone() for p in params]
            if client_id in malicious:
                flat_update = apply_attack(flat_update, attack)
            masked = apply_mask(flat_update, client_id, num_clients, round_id, cfg["mask_modulus"])
            local_updates.append(masked)

        if aggregator == "fedavg":
            aggregated = fedavg(local_updates)
        elif aggregator == "median":
            aggregated = coordinate_median(local_updates)
        elif aggregator == "krum":
            aggregated = krum(local_updates, num_byzantine=int(num_clients * malicious_fraction))
        else:
            raise ValueError(aggregator)

        set_parameters(global_model, aggregated)
        crypto_s = crypto_round_overhead(mode_cfg, num_clients)
        round_latencies.append(time.perf_counter() - start + crypto_s)

        val_metrics = evaluate(global_model, val_loader, device)
        if val_metrics["accuracy"] >= threshold and rounds_to_convergence == cfg["num_rounds"]:
            rounds_to_convergence = round_id + 1

    metrics = evaluate(global_model, test_loader, device)
    val_metrics = evaluate(global_model, val_loader, device)
    return {
        "seed": seed,
        "num_clients": num_clients,
        "alpha": alpha,
        "security_mode": security_mode,
        "aggregator": aggregator,
        "attack": attack,
        "malicious_fraction": malicious_fraction,
        **metrics,
        "val_accuracy": val_metrics["accuracy"],
        "mean_round_latency_s": float(np.mean(round_latencies)),
        "std_round_latency_s": float(np.std(round_latencies, ddof=1)) if len(round_latencies) > 1 else 0.0,
        "rounds_to_convergence": int(rounds_to_convergence),
        "round_latencies": round_latencies,
    }


def assert_predictive_determinism(results_df: pd.DataFrame, tol: float = 1e-6) -> None:
    """Predictive metrics must be identical across security modes (mask cancellation)."""
    for (_seed, _alpha, _agg, attack, mf, nc), group in results_df.groupby(
        ["seed", "alpha", "aggregator", "attack", "malicious_fraction", "num_clients"]
    ):
        if attack != "none" or mf > 0:
            continue
        accs = group["accuracy"].values
        f1s = group["f1"].values
        if len(accs) > 1 and (np.max(accs) - np.min(accs) > tol or np.max(f1s) - np.min(f1s) > tol):
            raise AssertionError(
                f"Predictive metrics differ across security modes: accuracies={accs}, f1s={f1s}"
            )


def _append_result(rows: list, result: dict, out_dir: Path) -> None:
    """Persist one row immediately so long runs survive interruption."""
    row = {k: v for k, v in result.items() if k != "round_latencies"}
    rows.append(row)
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "all_results.csv", index=False)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = load_config("federated_learning.yaml")
    seeds_cfg = load_config("experiment_seeds.yaml")
    seeds = seeds_cfg["federated_learning"]["seeds"][: cfg["num_seeds"]]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"FL device: {device}; seeds={len(seeds)}; rounds={cfg['num_rounds']}")

    rows = []
    out = root / "results" / "fl"
    out.mkdir(parents=True, exist_ok=True)
    num_clients_list = seeds_cfg["federated_learning"]["num_clients"]
    default_nc = cfg["num_clients_default"]

    total = len(seeds) * (
        len(cfg["dirichlet_alphas"]) * len(cfg["security_modes"])
        + len(num_clients_list) * len(cfg["security_modes"])
        + (len(cfg["aggregators"]) - 1)
        + 6  # label_flip grid
        + 1  # sign_flip krum
    )
    print(f"Running {total} FL configurations...")
    done = 0

    for seed in seeds:
        # Experiment B-2: Dirichlet alpha sweep at default client count
        for alpha in cfg["dirichlet_alphas"]:
            for mode in cfg["security_modes"]:
                result = run_single(
                    seed=seed,
                    num_clients=default_nc,
                    alpha=alpha,
                    security_mode=mode,
                    aggregator="fedavg",
                    attack="none",
                    malicious_fraction=0.0,
                    cfg=cfg,
                    device=device,
                )
                _append_result(rows, result, out)
                done += 1
                print(f"  [{done}/{total}] seed={seed} alpha={alpha} mode={mode}")

        # Experiment B: client-count sweep at IID
        for num_clients in num_clients_list:
            for mode in cfg["security_modes"]:
                result = run_single(
                    seed=seed,
                    num_clients=num_clients,
                    alpha=1.0,
                    security_mode=mode,
                    aggregator="fedavg",
                    attack="none",
                    malicious_fraction=0.0,
                    cfg=cfg,
                    device=device,
                )
                _append_result(rows, result, out)
                done += 1
                print(f"  [{done}/{total}] seed={seed} clients={num_clients} mode={mode}")

        # Experiment D: aggregator baseline (no attack)
        for agg in cfg["aggregators"]:
            if agg == "fedavg":
                continue
            result = run_single(
                seed=seed,
                num_clients=default_nc,
                alpha=1.0,
                security_mode="native_pq",
                aggregator=agg,
                attack="none",
                malicious_fraction=0.0,
                cfg=cfg,
                device=device,
            )
            _append_result(rows, result, out)
            done += 1
            print(f"  [{done}/{total}] seed={seed} aggregator={agg}")

        # Experiment D: Byzantine attacks
        for attack in ["label_flip", "sign_flip"]:
            mfractions = [0.1, 0.2] if attack == "label_flip" else [0.2]
            for mf in mfractions:
                aggs = cfg["aggregators"] if attack == "label_flip" else ["krum"]
                for agg in aggs:
                    result = run_single(
                        seed=seed,
                        num_clients=default_nc,
                        alpha=1.0,
                        security_mode="native_pq",
                        aggregator=agg,
                        attack=attack,
                        malicious_fraction=mf,
                        cfg=cfg,
                        device=device,
                    )
                    _append_result(rows, result, out)
                    done += 1
                    print(f"  [{done}/{total}] seed={seed} attack={attack} agg={agg} mf={mf}")

    df = pd.DataFrame(rows)
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "all_results.csv", index=False)

    assert_predictive_determinism(df)

    summary = (
        df.groupby(["security_mode", "alpha", "num_clients"])
        .agg(
            accuracy_mean=("accuracy", "mean"),
            accuracy_std=("accuracy", "std"),
            f1_mean=("f1", "mean"),
            f1_std=("f1", "std"),
            latency_mean=("mean_round_latency_s", "mean"),
            latency_std=("mean_round_latency_s", "std"),
        )
        .reset_index()
    )
    summary.to_csv(out / "summary.csv", index=False)

    emit_all_tables(df, out, default_clients=default_nc)

    emitter = ResultsEmitter(root / "results")
    emitter.set_macro("FLDeterminismCheck", "passed")
    emitter.set_macro("FLNumSeeds", len(seeds))
    emitter.set_macro("FLNumRounds", cfg["num_rounds"])
    emitter.write_macros()
    print("FL experiments complete:", out)


if __name__ == "__main__":
    main()
