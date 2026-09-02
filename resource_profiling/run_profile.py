"""x86 resource profiling: RAPL energy, memory, CPU."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd
import psutil

from qrfl_common.results import ResultsEmitter, load_config

try:
    import oqs
except ImportError:
    oqs = None


def read_rapl_energy_uj() -> int | None:
    base = Path("/sys/class/powercap/intel-rapl")
    if not base.exists():
        return None
    for domain in base.glob("intel-rapl:*"):
        energy = domain / "energy_uj"
        if energy.exists():
            try:
                return int(energy.read_text().strip())
            except OSError:
                continue
    return None


def profile_operation(name: str, func, warmup: int, trials: int) -> pd.DataFrame:
    process = psutil.Process(os.getpid())
    for _ in range(warmup):
        func()

    rows = []
    for trial in range(trials):
        mem_before = process.memory_info().rss
        cpu_before = process.cpu_times()
        e_before = read_rapl_energy_uj()

        start = time.perf_counter()
        func()
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        mem_after = process.memory_info().rss
        cpu_after = process.cpu_times()
        e_after = read_rapl_energy_uj()

        energy_j = None
        if e_before is not None and e_after is not None:
            energy_j = (e_after - e_before) / 1e6

        cpu_delta = (cpu_after.user + cpu_after.system) - (cpu_before.user + cpu_before.system)
        rows.append(
            {
                "operation": name,
                "trial": trial,
                "latency_ms": elapsed_ms,
                "peak_rss_bytes": max(mem_before, mem_after),
                "cpu_time_s": cpu_delta,
                "energy_j": energy_j,
                "platform": "x86_server",
            }
        )
    return pd.DataFrame(rows)


def _build_pqc_operations() -> list[tuple[str, callable]]:
    """Return (name, fn) pairs for PQC resource profiling."""
    kem_ct: list[bytes | None] = [None]
    sig_val: list[bytes | None] = [None]
    msg = b"qrfl-resource-profile"

    if oqs is not None:
        kem = oqs.KeyEncapsulation("ML-KEM-768")
        pub = kem.generate_keypair()
        sec = kem.export_secret_key()

        def encaps() -> None:
            kem.encap_secret(pub)

        def decaps() -> None:
            if kem_ct[0] is None:
                kem_ct[0] = kem.encap_secret(pub)[0]
            kem.decap_secret(kem_ct[0], sec)

        sig = oqs.Signature("ML-DSA-65")
        spub = sig.generate_keypair()
        ssec = sig.export_secret_key()

        def sign() -> None:
            sig.sign(msg)

        def verify() -> None:
            if sig_val[0] is None:
                sig_val[0] = sig.sign(msg)
            sig.verify(msg, sig_val[0], spub)

        return [
            ("ML-KEM-768_encaps", encaps),
            ("ML-KEM-768_decaps", decaps),
            ("ML-DSA-65_sign", sign),
            ("ML-DSA-65_verify", verify),
        ]

    try:
        from quantcrypt import dss as qc_dss
        from quantcrypt import kem as qc_kem
    except ImportError:
        return []

    kem = getattr(qc_kem, "MLKEM_768")()
    pub, sec = kem.keygen()
    sig = getattr(qc_dss, "MLDSA_65")()
    spub, ssec = sig.keygen()

    def encaps() -> None:
        kem.encaps(pub)

    def decaps() -> None:
        if kem_ct[0] is None:
            kem_ct[0] = kem.encaps(pub)[0]
        kem.decaps(sec, kem_ct[0])

    def sign() -> None:
        sig.sign(ssec, msg)

    def verify() -> None:
        if sig_val[0] is None:
            sig_val[0] = sig.sign(ssec, msg)
        sig.verify(spub, msg, sig_val[0])

    return [
        ("ML-KEM-768_encaps", encaps),
        ("ML-KEM-768_decaps", decaps),
        ("ML-DSA-65_sign", sign),
        ("ML-DSA-65_verify", verify),
    ]


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = load_config("experiment_seeds.yaml")["resource_profiling"]
    warmup = cfg["warmup"]
    trials = cfg["trials"]

    frames = []
    for op_name, fn in _build_pqc_operations():
        frames.append(profile_operation(op_name, fn, warmup, trials))
    if not frames:
        print("WARN: no PQC backend available; skipping PQC resource profiling")

    out = root / "results" / "resource"
    out.mkdir(parents=True, exist_ok=True)
    if frames:
        all_df = pd.concat(frames, ignore_index=True)
        all_df.to_csv(out / "trials.csv", index=False)
        summary = (
            all_df.groupby("operation")
            .agg(
                mean_latency_ms=("latency_ms", "mean"),
                sd_latency_ms=("latency_ms", "std"),
                mean_energy_j=("energy_j", "mean"),
                peak_rss_mb=("peak_rss_bytes", lambda x: x.max() / (1024**2)),
            )
            .reset_index()
        )
        summary.to_csv(out / "summary.csv", index=False)
    else:
        pd.DataFrame(columns=["operation", "trial", "latency_ms"]).to_csv(out / "trials.csv", index=False)

    emitter = ResultsEmitter(root / "results")
    emitter.set_macro("ResourcePlatform", "x86\\_server")
    emitter.write_macros()
    print("Resource profiling complete:", out)


if __name__ == "__main__":
    main()
