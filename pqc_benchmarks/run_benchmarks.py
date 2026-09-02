"""PQC and classical cryptographic benchmarks (Experiment A).

Timings call PQClean/liboqs C entry points directly with preallocated buffers so
Python wrapper overhead (quantcrypt rebuilds ``FFI()`` on every call) does not
inflate reported latencies.

Primary backend: ``quantcrypt`` (bundled PQClean). Optional: ``liboqs``/``oqs``.
Every latency is measured; parameter sizes come from generated artifacts.
"""

from __future__ import annotations

import platform
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd
from cffi import FFI

from qrfl_common.results import ResultsEmitter, load_config

try:
    import oqs
except ImportError:
    oqs = None

try:
    from quantcrypt import dss as qc_dss
    from quantcrypt import kem as qc_kem
except ImportError:
    qc_kem = None
    qc_dss = None


# Config key -> quantcrypt class name (resolved at runtime).
QUANTCRYPT_KEM = {
    "ML-KEM-512": "MLKEM_512",
    "ML-KEM-768": "MLKEM_768",
    "ML-KEM-1024": "MLKEM_1024",
}

QUANTCRYPT_SIG = {
    "ML-DSA-44": "MLDSA_44",
    "ML-DSA-65": "MLDSA_65",
    "ML-DSA-87": "MLDSA_87",
    "SLH-DSA-SHAKE-128s": "SMALL_SPHINCS",
    "SLH-DSA-SHAKE-128f": "FAST_SPHINCS",
}

# NIST FIPS 203/204 parameter sizes for sanity checks (pk, ct/sig).
NIST_EXPECTED = {
    "ML-KEM-512": {"public_key_bytes": 800, "ciphertext_bytes": 768},
    "ML-KEM-768": {"public_key_bytes": 1184, "ciphertext_bytes": 1088},
    "ML-KEM-1024": {"public_key_bytes": 1568, "ciphertext_bytes": 1568},
    "ML-DSA-44": {"public_key_bytes": 1312, "signature_bytes": 2420},
    "ML-DSA-65": {"public_key_bytes": 1952, "signature_bytes": 3309},
    "ML-DSA-87": {"public_key_bytes": 2592, "signature_bytes": 4627},
}

BENCH_MESSAGE = b"qrfl-benchmark-payload"


@dataclass
class Budget:
    warmup: int
    trials: int
    max_seconds: float

    def run(self, func: Callable[[], None]) -> list[float]:
        for _ in range(self.warmup):
            func()
        timings: list[float] = []
        deadline = time.perf_counter() + self.max_seconds
        for _ in range(self.trials):
            start = time.perf_counter()
            func()
            timings.append((time.perf_counter() - start) * 1000.0)
            if time.perf_counter() > deadline:
                break
        return timings


def _warmup_for(op: str, budget: Budget) -> Budget:
    return Budget(0 if op == "keygen" else budget.warmup, budget.trials, budget.max_seconds)


def _rows(
    scheme: str,
    backend: str,
    impl: str,
    timings_by_op: dict[str, list[float]],
    sizes: dict,
) -> list[dict]:
    rows = []
    for op, timings in timings_by_op.items():
        for i, ms in enumerate(timings):
            rows.append(
                {
                    "scheme": scheme,
                    "operation": op,
                    "backend": backend,
                    "implementation": impl,
                    "trial": i,
                    "latency_ms": ms,
                    **sizes,
                }
            )
    return rows


def _derive_sphincs_label(cdef_name: str, pk_size: int, sig_size: int) -> str:
    """Map compiled PQClean symbol + sizes to a manuscript-safe label."""
    name = cdef_name.upper()
    if "SHAKE256" in name and "SSIMPLE" in name:
        return "SLH-DSA-SHAKE-256s"
    if "SHAKE256" in name and "FSIMPLE" in name:
        return "SLH-DSA-SHAKE-256f"
    if "SHAKE128" in name and "SSIMPLE" in name:
        return "SLH-DSA-SHAKE-128s"
    if "SHAKE128" in name and "FSIMPLE" in name:
        return "SLH-DSA-SHAKE-128f"
    return f"SPHINCS+ (pk={pk_size}B, sig={sig_size}B)"


def _impl_label(cdef_name: str) -> str:
    upper = cdef_name.upper()
    if "AVX2" in upper:
        return "avx2"
    if "AARCH64" in upper:
        return "aarch64"
    if "CLEAN" in upper:
        return "clean"
    return cdef_name


def benchmark_kem_cffi(config_name: str, budget: Budget) -> list[dict]:
    cls = getattr(qc_kem, QUANTCRYPT_KEM[config_name])
    kem = cls()
    lib, cdef = kem._lib, kem._cdef_name
    impl = _impl_label(cdef)
    p = kem.param_sizes

    ffi = FFI()
    pk = ffi.new(f"uint8_t [{p.pk_size}]")
    sk = ffi.new(f"uint8_t [{p.sk_size}]")
    ct = ffi.new(f"uint8_t [{p.ct_size}]")
    ss_enc = ffi.new(f"uint8_t [{p.ss_size}]")
    ss_dec = ffi.new(f"uint8_t [{p.ss_size}]")

    keypair = getattr(lib, f"{cdef}_crypto_kem_keypair")
    encaps = getattr(lib, f"{cdef}_crypto_kem_enc")
    decaps = getattr(lib, f"{cdef}_crypto_kem_dec")

    assert keypair(pk, sk) == 0
    assert encaps(ct, ss_enc, pk) == 0
    assert decaps(ss_dec, ct, sk) == 0
    assert bytes(ffi.buffer(ss_enc, p.ss_size)) == bytes(ffi.buffer(ss_dec, p.ss_size))

    def keygen() -> None:
        keypair(pk, sk)

    def encap() -> None:
        encaps(ct, ss_enc, pk)

    def decap() -> None:
        decaps(ss_dec, ct, sk)

    timings = {
        "keygen": _warmup_for("keygen", budget).run(keygen),
        "encapsulate": _warmup_for("encapsulate", budget).run(encap),
        "decapsulate": _warmup_for("decapsulate", budget).run(decap),
    }
    sizes = {
        "public_key_bytes": p.pk_size,
        "secret_key_bytes": p.sk_size,
        "ciphertext_bytes": p.ct_size,
        "signature_bytes": None,
        "cdef_symbol": cdef,
    }
    expected = NIST_EXPECTED.get(config_name)
    if expected and (
        sizes["public_key_bytes"] != expected["public_key_bytes"]
        or sizes["ciphertext_bytes"] != expected["ciphertext_bytes"]
    ):
        raise ValueError(
            f"{config_name} size mismatch: got pk={sizes['public_key_bytes']} "
            f"ct={sizes['ciphertext_bytes']}, expected {expected}"
        )
    return _rows(config_name, "quantcrypt-cffi", impl, timings, sizes)


def benchmark_sig_cffi(config_name: str, budget: Budget) -> list[dict]:
    cls = getattr(qc_dss, QUANTCRYPT_SIG[config_name])
    sig_obj = cls()
    lib, cdef = sig_obj._lib, sig_obj._cdef_name
    impl = _impl_label(cdef)
    p = sig_obj.param_sizes

    ffi = FFI()
    pk = ffi.new(f"uint8_t [{p.pk_size}]")
    sk = ffi.new(f"uint8_t [{p.sk_size}]")
    sig_buf = ffi.new(f"uint8_t [{p.sig_size}]")
    sig_len = ffi.new("size_t *")

    keypair = getattr(lib, f"{cdef}_crypto_sign_keypair")
    sign = getattr(lib, f"{cdef}_crypto_sign_signature")
    verify = getattr(lib, f"{cdef}_crypto_sign_verify")

    assert keypair(pk, sk) == 0
    sig_len[0] = p.sig_size
    msg_len = len(BENCH_MESSAGE)
    assert sign(sig_buf, sig_len, BENCH_MESSAGE, msg_len, sk) == 0
    actual_sig_len = int(sig_len[0])
    assert verify(sig_buf, actual_sig_len, BENCH_MESSAGE, msg_len, pk) == 0

    def keygen() -> None:
        keypair(pk, sk)

    def do_sign() -> None:
        sig_len[0] = p.sig_size
        sign(sig_buf, sig_len, BENCH_MESSAGE, msg_len, sk)

    def do_verify() -> None:
        verify(sig_buf, actual_sig_len, BENCH_MESSAGE, msg_len, pk)

    timings = {
        "keygen": _warmup_for("keygen", budget).run(keygen),
        "sign": _warmup_for("sign", budget).run(do_sign),
        "verify": _warmup_for("verify", budget).run(do_verify),
    }

    if config_name.startswith("SLH-DSA"):
        scheme = _derive_sphincs_label(cdef, p.pk_size, p.sig_size)
    else:
        scheme = config_name
        expected = NIST_EXPECTED.get(config_name)
        if expected and (
            p.pk_size != expected["public_key_bytes"]
            or p.sig_size != expected["signature_bytes"]
        ):
            raise ValueError(f"{config_name} size mismatch vs NIST constants")

    sizes = {
        "public_key_bytes": p.pk_size,
        "secret_key_bytes": p.sk_size,
        "ciphertext_bytes": None,
        "signature_bytes": p.sig_size,
        "cdef_symbol": cdef,
    }
    return _rows(scheme, "quantcrypt-cffi", impl, timings, sizes)


def benchmark_kem_oqs(name: str, budget: Budget) -> list[dict]:
    state: dict = {}
    kem = oqs.KeyEncapsulation(name)
    state["pk"] = kem.generate_keypair()
    state["sk"] = kem.export_secret_key()
    state["ct"], _ = kem.encap_secret(state["pk"])

    def keygen() -> None:
        state["pk"] = kem.generate_keypair()

    def encaps() -> None:
        state["ct"], _ = kem.encap_secret(state["pk"])

    def decaps() -> None:
        kem.decap_secret(state["ct"])

    timings = {
        op: _warmup_for(op, budget).run(fn)
        for op, fn in [
            ("keygen", keygen),
            ("encapsulate", encaps),
            ("decapsulate", decaps),
        ]
    }
    sizes = {
        "public_key_bytes": len(state["pk"]),
        "secret_key_bytes": len(state["sk"]),
        "ciphertext_bytes": len(state["ct"]),
        "signature_bytes": None,
        "cdef_symbol": name,
    }
    return _rows(name, "liboqs", "liboqs", timings, sizes)


def benchmark_sig_oqs(name: str, budget: Budget) -> list[dict]:
    state: dict = {}
    sig = oqs.Signature(name)
    state["pk"] = sig.generate_keypair()
    state["sk"] = sig.export_secret_key()
    state["sig"] = sig.sign(BENCH_MESSAGE)

    def keygen() -> None:
        state["pk"] = sig.generate_keypair()

    def do_sign() -> None:
        state["sig"] = sig.sign(BENCH_MESSAGE)

    def do_verify() -> None:
        sig.verify(BENCH_MESSAGE, state["sig"], state["pk"])

    timings = {
        op: _warmup_for(op, budget).run(fn)
        for op, fn in [("keygen", keygen), ("sign", do_sign), ("verify", do_verify)]
    }
    sizes = {
        "public_key_bytes": len(state["pk"]),
        "secret_key_bytes": len(state["sk"]),
        "ciphertext_bytes": None,
        "signature_bytes": len(state["sig"]),
        "cdef_symbol": name,
    }
    return _rows(name, "liboqs", "liboqs", timings, sizes)


def benchmark_ecdsa_p256(budget: Budget) -> list[dict]:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    digest = hashes.Hash(hashes.SHA256())
    digest.update(BENCH_MESSAGE)
    msg_hash = digest.finalize()
    algorithm = ec.ECDSA(Prehashed(hashes.SHA256()))

    state: dict = {}
    state["sk"] = ec.generate_private_key(ec.SECP256R1())
    state["pk"] = state["sk"].public_key()
    state["sig"] = state["sk"].sign(msg_hash, algorithm)

    def keygen() -> None:
        state["sk"] = ec.generate_private_key(ec.SECP256R1())
        state["pk"] = state["sk"].public_key()

    def do_sign() -> None:
        state["sig"] = state["sk"].sign(msg_hash, algorithm)

    def do_verify() -> None:
        state["pk"].verify(state["sig"], msg_hash, algorithm)

    timings = {
        op: _warmup_for(op, budget).run(fn)
        for op, fn in [("keygen", keygen), ("sign", do_sign), ("verify", do_verify)]
    }
    raw_point = state["pk"].public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    sizes = {
        "public_key_bytes": len(raw_point) - 1,
        "secret_key_bytes": 32,
        "ciphertext_bytes": None,
        "signature_bytes": len(state["sig"]),
        "cdef_symbol": "ECDSA-P256",
    }
    return _rows("ECDSA-P256", "cryptography", "openssl", timings, sizes)


def benchmark_rsa_2048(budget: Budget, keygen_trials: int) -> list[dict]:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.hazmat.primitives.asymmetric.utils import Prehashed

    digest = hashes.Hash(hashes.SHA256())
    digest.update(BENCH_MESSAGE)
    msg_hash = digest.finalize()
    pad = padding.PKCS1v15()
    prehashed = Prehashed(hashes.SHA256())

    state: dict = {}
    state["sk"] = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    state["pk"] = state["sk"].public_key()
    state["sig"] = state["sk"].sign(msg_hash, pad, prehashed)

    def keygen() -> None:
        state["sk"] = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        state["pk"] = state["sk"].public_key()

    def do_sign() -> None:
        state["sig"] = state["sk"].sign(msg_hash, pad, prehashed)

    def do_verify() -> None:
        state["pk"].verify(state["sig"], msg_hash, pad, prehashed)

    timings = {
        "keygen": Budget(0, keygen_trials, budget.max_seconds).run(keygen),
        "sign": _warmup_for("sign", budget).run(do_sign),
        "verify": _warmup_for("verify", budget).run(do_verify),
    }
    sizes = {
        "public_key_bytes": state["pk"].key_size // 8,
        "secret_key_bytes": None,
        "ciphertext_bytes": None,
        "signature_bytes": len(state["sig"]),
        "cdef_symbol": "RSA-2048",
    }
    return _rows("RSA-2048", "cryptography", "openssl", timings, sizes)


def summarize_trials(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["scheme", "operation"], as_index=False)
        .agg(
            backend=("backend", "first"),
            implementation=("implementation", "first"),
            cdef_symbol=("cdef_symbol", "first"),
            mean_ms=("latency_ms", "mean"),
            sd_ms=("latency_ms", "std"),
            median_ms=("latency_ms", "median"),
            p95_ms=("latency_ms", lambda s: s.quantile(0.95)),
            min_ms=("latency_ms", "min"),
            n=("latency_ms", "count"),
            public_key_bytes=("public_key_bytes", "first"),
            ciphertext_bytes=("ciphertext_bytes", "first"),
            signature_bytes=("signature_bytes", "first"),
        )
    )


def _security_level(scheme: str, operation: str) -> str:
    levels = {
        "ML-KEM-512": "NIST Level 1",
        "ML-KEM-768": "NIST Level 3",
        "ML-KEM-1024": "NIST Level 5",
        "ML-DSA-44": "NIST Level 2",
        "ML-DSA-65": "NIST Level 3",
        "ML-DSA-87": "NIST Level 5",
        "SLH-DSA-SHAKE-256s": "NIST Level 1 (256s)",
        "SLH-DSA-SHAKE-128s": "NIST Level 1",
        "ECDSA-P256": "Classical",
        "RSA-2048": "Classical",
    }
    return levels.get(scheme, "")


def _format_op(op: str) -> str:
    return {
        "encapsulate": "Encapsulate",
        "decapsulate": "Decapsulate",
        "keygen": "Keygen",
        "sign": "Sign",
        "verify": "Verify",
    }.get(op, op.title())


def emit_crypto_table(summary: pd.DataFrame, out_path: Path) -> None:
    """Write Experiment A table for manuscript inclusion."""
    rows_for_table = summary[
        summary["operation"].isin(
            ["encapsulate", "decapsulate", "sign", "verify", "keygen"]
        )
    ].copy()
    # Manuscript table omits keygen; keep it in CSV only.
    rows_for_table = rows_for_table[~rows_for_table["operation"].eq("keygen")]

    op_order = {"encapsulate": 0, "decapsulate": 1, "sign": 2, "verify": 3}
    rows_for_table["sort_op"] = rows_for_table["operation"].map(op_order)
    rows_for_table = rows_for_table.sort_values(["scheme", "sort_op"])

    lines = [
        "% Auto-generated crypto benchmark table (Experiment A)",
        "\\begin{table*}[htbp]",
        "\\centering",
        "\\caption{Cryptographic Primitive Performance Overheads (measured)}",
        "\\label{tab:crypto_benchmarks}",
        "\\resizebox{\\textwidth}{!}{%",
        "\\begin{tabular}{lcccccc}",
        "\\toprule",
        "Scheme & Operation & Mean (ms) & SD (ms) & Public key size (B) & Sig./CT size (B) & Security level \\\\",
        "\\midrule",
    ]
    for _, row in rows_for_table.iterrows():
        pk = int(row["public_key_bytes"]) if pd.notna(row["public_key_bytes"]) else "---"
        payload = row["ciphertext_bytes"] if pd.notna(row["ciphertext_bytes"]) else row["signature_bytes"]
        payload_str = str(int(payload)) if pd.notna(payload) else "---"
        sd = row["sd_ms"] if pd.notna(row["sd_ms"]) else 0.0
        lines.append(
            f"{row['scheme']} & {_format_op(row['operation'])} & "
            f"{row['mean_ms']:.3f} & {sd:.3f} & {pk} & {payload_str} & "
            f"{_security_level(row['scheme'], row['operation'])} \\\\"
        )
    lines.extend(["\\bottomrule", "\\end{tabular}}", "\\end{table*}"])
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = load_config("pqc_benchmarks.yaml")
    seeds = load_config("experiment_seeds.yaml")["pqc_benchmarks"]

    warmup = int(cfg.get("warmup_iterations", seeds["warmup_iterations"]))
    trials = int(cfg.get("trials", seeds["trials"]))
    max_seconds = float(cfg.get("max_seconds_per_operation", 60.0))
    rsa_keygen_trials = int(cfg.get("rsa_keygen_trials", 25))
    budget = Budget(warmup=warmup, trials=trials, max_seconds=max_seconds)

    if qc_kem is None and oqs is None:
        raise SystemExit(
            "No PQC backend available. Install quantcrypt or build liboqs with oqs."
        )

    use_oqs = oqs is not None and bool(cfg.get("prefer_liboqs", False))
    backend_label = "liboqs" if use_oqs else "quantcrypt-cffi"
    print(f"Backend: {backend_label}; trials={trials}, warmup={warmup}, budget={max_seconds}s/op")

    rows: list[dict] = []
    for name in cfg["schemes"]["kem"]:
        try:
            if use_oqs:
                rows += benchmark_kem_oqs(name, budget)
            else:
                rows += benchmark_kem_cffi(name, budget)
            print(f"  KEM  {name}: done")
        except Exception as exc:
            print(f"  WARN: KEM {name} skipped: {exc}")

    for name in cfg["schemes"]["sig"]:
        try:
            if use_oqs:
                rows += benchmark_sig_oqs(name, budget)
            elif name in QUANTCRYPT_SIG:
                batch = benchmark_sig_cffi(name, budget)
                actual = batch[0]["scheme"] if batch else name
                if actual != name:
                    print(f"  NOTE: {name} resolved to compiled scheme {actual}")
                rows += batch
            else:
                print(f"  WARN: SIG {name} has no quantcrypt mapping; skipped")
            print(f"  SIG  {name}: done")
        except Exception as exc:
            print(f"  WARN: SIG {name} skipped: {exc}")

    classical = cfg["schemes"].get("classical", [])
    if "ECDSA-P256" in classical:
        rows += benchmark_ecdsa_p256(budget)
        print("  CLS  ECDSA-P256: done")
    if "RSA-2048" in classical:
        rows += benchmark_rsa_2048(budget, rsa_keygen_trials)
        print("  CLS  RSA-2048: done")

    if not rows:
        raise SystemExit("No benchmarks completed; refusing to write empty results.")

    all_trials = pd.DataFrame(rows)
    summary = summarize_trials(all_trials)

    out = root / "results" / "pqc"
    out.mkdir(parents=True, exist_ok=True)
    all_trials.to_csv(out / "trials.csv", index=False)
    summary.to_csv(out / "summary.csv", index=False)
    emit_crypto_table(summary, out / "crypto_benchmarks.tex")

    impls = summary[["scheme", "implementation", "cdef_symbol"]].drop_duplicates()
    emitter = ResultsEmitter(root / "results")
    emitter.save_json(
        "pqc/environment.json",
        {
            "backend": backend_label,
            "python": sys.version,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "machine": platform.machine(),
            "trials_requested": trials,
            "warmup_iterations": warmup,
            "max_seconds_per_operation": max_seconds,
            "implementations": impls.to_dict(orient="records"),
        },
    )

    for _, row in summary.iterrows():
        stem = f"PQC {row['scheme']} {row['operation']}".title().replace(" ", "")
        emitter.set_macro(f"{stem}Mean", float(row["mean_ms"]), ".3f")
        if pd.notna(row["sd_ms"]):
            emitter.set_macro(f"{stem}SD", float(row["sd_ms"]), ".3f")
        emitter.set_macro(f"{stem}N", int(row["n"]))
    emitter.set_macro("PQCBackend", backend_label)
    emitter.write_macros()

    print(f"\nPQC benchmarks complete: {out}")
    print(summary[["scheme", "operation", "implementation", "mean_ms", "sd_ms", "n"]].to_string(index=False))


if __name__ == "__main__":
    main()
