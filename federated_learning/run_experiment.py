"""Run FL experiments: three security modes, non-IID, Byzantine."""

from __future__ import annotations

import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from tqdm import tqdm

from federated_learning.aggregation import coordinate_median, fedavg, krum
from federated_learning.attacks import apply_attack, select_malicious_clients
from federated_learning.data import dirichlet_partition, load_pneumoniamnist, make_client_loaders
from federated_learning.emit_tables import emit_all_tables
from federated_learning.model import PneumoniaCNN, get_parameters, set_parameters
from federated_learning.security import DEFAULT_MODES, apply_mask, crypto_round_overhead
from federated_learning.train_eval import evaluate, train_local
from qrfl_common.results import ResultsEmitter, load_config


def _config_key(result: dict) -> tuple:
    return (
        result["seed"],
        result["num_clients"],
        result["alpha"],
        result["security_mode"],
        result["aggregator"],
        result["attack"],
        result["malicious_fraction"],
    )


def _row_key(row: dict | pd.Series) -> tuple:
    return (
        int(row["seed"]),
        int(row["num_clients"]),
        float(row["alpha"]),
        str(row["security_mode"]),
        str(row["aggregator"]),
        str(row["attack"]),
        float(row["malicious_fraction"]),
    )


def build_config_queue(cfg: dict, seeds: list[int], num_clients_list: list[int], default_nc: int) -> list[dict]:
    """Enumerate all FL experiment configurations (deduplicated IID at default_nc)."""
    queue: list[dict] = []
    for seed in seeds:
        for alpha in cfg["dirichlet_alphas"]:
            for mode in cfg["security_modes"]:
                queue.append(
                    {
                        "seed": seed,
                        "num_clients": default_nc,
                        "alpha": alpha,
                        "security_mode": mode,
                        "aggregator": "fedavg",
                        "attack": "none",
                        "malicious_fraction": 0.0,
                        "label": f"seed={seed} alpha={alpha} mode={mode}",
                    }
                )
        for num_clients in num_clients_list:
            if num_clients == default_nc:
                continue
            for mode in cfg["security_modes"]:
                queue.append(
                    {
                        "seed": seed,
                        "num_clients": num_clients,
                        "alpha": 1.0,
                        "security_mode": mode,
                        "aggregator": "fedavg",
                        "attack": "none",
                        "malicious_fraction": 0.0,
                        "label": f"seed={seed} clients={num_clients} mode={mode}",
                    }
                )
        for agg in cfg["aggregators"]:
            if agg == "fedavg":
                continue
            queue.append(
                {
                    "seed": seed,
                    "num_clients": default_nc,
                    "alpha": 1.0,
                    "security_mode": "native_pq",
                    "aggregator": agg,
                    "attack": "none",
                    "malicious_fraction": 0.0,
                    "label": f"seed={seed} aggregator={agg}",
                }
            )
        for attack in ["label_flip", "sign_flip"]:
            mfractions = [0.1, 0.2] if attack == "label_flip" else [0.2]
            for mf in mfractions:
                aggs = cfg["aggregators"] if attack == "label_flip" else ["krum"]
                for agg in aggs:
                    queue.append(
                        {
                            "seed": seed,
                            "num_clients": default_nc,
                            "alpha": 1.0,
                            "security_mode": "native_pq",
                            "aggregator": agg,
                            "attack": attack,
                            "malicious_fraction": mf,
                            "label": f"seed={seed} attack={attack} agg={agg} mf={mf}",
                        }
                    )
    return queue


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
    round_pbar: tqdm | None = None,
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
    num_rounds = cfg["num_rounds"]
    local_epochs = cfg["local_epochs"]

    local_model = PneumoniaCNN().to(device)

    if round_pbar is not None:
        round_pbar.reset(total=num_rounds)

    for round_id in range(num_rounds):
        start = time.perf_counter()
        local_updates = []
        for client_id, loader in enumerate(client_loaders):
            set_parameters(local_model, get_parameters(global_model))
            params = train_local(
                local_model,
                loader,
                local_epochs,
                cfg["learning_rate"],
                device,
            )
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
        if val_metrics["accuracy"] >= threshold and rounds_to_convergence == num_rounds:
            rounds_to_convergence = round_id + 1

        if round_pbar is not None:
            round_pbar.set_postfix(acc=f"{val_metrics['accuracy']:.3f}", refresh=False)
            round_pbar.update(1)

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


def _log_line(log_path: Path, message: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] {message}\n")


def _emit_fl_prose_macros(emitter: ResultsEmitter, df: pd.DataFrame, default_nc: int) -> None:
    """Macros for Experiment B prose in main.tex."""
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


def _finalize_results(df: pd.DataFrame, out: Path, root: Path, cfg: dict, seeds: list[int], default_nc: int) -> None:
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
    emitter.set_macro("FLNumSeeds", df["seed"].nunique())
    if "rounds_to_convergence" in df.columns and len(df):
        emitter.set_macro("FLNumRounds", int(df["rounds_to_convergence"].max()))
    else:
        emitter.set_macro("FLNumRounds", cfg["num_rounds"])
    _emit_fl_prose_macros(emitter, df, default_nc)
    emitter.write_macros()


def _merge_cfg_with_seeds(cfg: dict, seeds_cfg: dict) -> dict:
    fl_seeds = seeds_cfg["federated_learning"]
    merged = dict(cfg)
    merged["num_seeds"] = fl_seeds["num_seeds"]
    merged["num_rounds"] = fl_seeds["num_rounds"]
    merged["local_epochs"] = fl_seeds.get("local_epochs", cfg.get("local_epochs", 5))
    merged["learning_rate"] = fl_seeds.get("learning_rate", cfg.get("learning_rate", 0.001))
    merged["batch_size"] = fl_seeds.get("batch_size", cfg.get("batch_size", 32))
    return merged


def _run_job_worker(job: dict, cfg: dict) -> dict:
    """Run one FL configuration in a worker process."""
    torch.set_num_threads(max(1, int(os.environ.get("FL_TORCH_THREADS", "2"))))
    device = torch.device("cpu")
    return run_single(
        seed=job["seed"],
        num_clients=job["num_clients"],
        alpha=job["alpha"],
        security_mode=job["security_mode"],
        aggregator=job["aggregator"],
        attack=job["attack"],
        malicious_fraction=job["malicious_fraction"],
        cfg=cfg,
        device=device,
        round_pbar=None,
    )


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = _merge_cfg_with_seeds(load_config("federated_learning.yaml"), load_config("experiment_seeds.yaml"))
    seeds_cfg = load_config("experiment_seeds.yaml")
    seeds = seeds_cfg["federated_learning"]["seeds"][: cfg["num_seeds"]]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    out = root / "results" / "fl"
    out.mkdir(parents=True, exist_ok=True)
    log_path = out / "progress.log"
    num_clients_list = seeds_cfg["federated_learning"]["num_clients"]
    default_nc = cfg["num_clients_default"]

    queue = build_config_queue(cfg, seeds, num_clients_list, default_nc)
    total = len(queue)

    rows: list[dict] = []
    completed_keys: set[tuple] = set()
    existing_path = out / "all_results.csv"
    if existing_path.exists():
        existing = pd.read_csv(existing_path)
        rows = existing.to_dict(orient="records")
        completed_keys = {_row_key(r) for r in rows}

    pending = [c for c in queue if _row_key(c) not in completed_keys]
    skipped = total - len(pending)

    header = (
        f"FL device: {device}; seeds={len(seeds)}; rounds={cfg['num_rounds']}; "
        f"configs={total}; resuming {skipped} completed, {len(pending)} pending"
    )
    print(header)
    _log_line(log_path, header)

    max_workers = int(os.environ.get("FL_MAX_WORKERS", "0")) or min(4, max(1, (os.cpu_count() or 4) // 2))
    print(f"Parallel workers: {max_workers}", flush=True)

    config_pbar = tqdm(
        total=total,
        desc="FL configs",
        unit="cfg",
        dynamic_ncols=True,
        initial=skipped,
    )

    t0 = time.perf_counter()
    done_count = skipped

    def _record(job: dict, result: dict) -> None:
        nonlocal done_count
        _append_result(rows, result, out)
        done_count += 1
        config_pbar.update(1)
        config_pbar.set_postfix_str(job["label"], refresh=True)
        elapsed = time.perf_counter() - t0
        eta_s = (elapsed / max(done_count - skipped, 1)) * (total - done_count)
        _log_line(
            log_path,
            f"[{done_count}/{total}] {job['label']} acc={result['accuracy']:.4f} "
            f"latency={result['mean_round_latency_s']:.2f}s ETA={eta_s / 60:.1f}min",
        )
        if done_count % 5 == 0 or done_count == total:
            try:
                _finalize_results(pd.DataFrame(rows), out, root, cfg, seeds, default_nc)
            except Exception as exc:
                _log_line(log_path, f"WARN: partial finalize skipped: {type(exc).__name__}: {exc}")

    if max_workers == 1:
        round_pbar = tqdm(total=cfg["num_rounds"], desc="FL rounds", unit="rnd", leave=False, dynamic_ncols=True)
        for job in pending:
            round_pbar.reset(total=cfg["num_rounds"])
            result = run_single(
                seed=job["seed"],
                num_clients=job["num_clients"],
                alpha=job["alpha"],
                security_mode=job["security_mode"],
                aggregator=job["aggregator"],
                attack=job["attack"],
                malicious_fraction=job["malicious_fraction"],
                cfg=cfg,
                device=device,
                round_pbar=round_pbar,
            )
            _record(job, result)
        round_pbar.close()
    else:
        # Submit in waves so orphaned parents cannot leave unbounded workers.
        batch_size = max_workers
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            for start in range(0, len(pending), batch_size):
                batch = pending[start : start + batch_size]
                futures = {pool.submit(_run_job_worker, job, cfg): job for job in batch}
                for future in as_completed(futures):
                    job = futures[future]
                    result = future.result()
                    _record(job, result)

    config_pbar.close()

    df = pd.DataFrame(rows)
    df.to_csv(out / "all_results.csv", index=False)
    _finalize_results(df, out, root, cfg, seeds, default_nc)

    done_msg = f"FL experiments complete: {out} ({len(df)} configs)"
    print(done_msg, flush=True)
    _log_line(log_path, done_msg)


if __name__ == "__main__":
    import multiprocessing as mp

    mp.freeze_support()
    main()
