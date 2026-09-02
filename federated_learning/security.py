"""Secure aggregation masks and crypto overhead modeling."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

import numpy as np
import torch


@dataclass
class SecurityModeConfig:
    name: str
    kem_encaps_ms: float = 0.0
    kem_decaps_ms: float = 0.0
    sig_sign_ms: float = 0.0
    sig_verify_ms: float = 0.0
    payload_overhead_bytes: int = 0


DEFAULT_MODES = {
    "classical": SecurityModeConfig("classical", 0.0, 0.0, 0.035, 0.085, 512),
    "hybrid_pq": SecurityModeConfig("hybrid_pq", 0.128, 0.091, 0.850, 0.245, 5581),
    "native_pq": SecurityModeConfig("native_pq", 0.128, 0.091, 0.850, 0.245, 5581),
}


def pairwise_seed(client_u: int, client_v: int, round_id: int, modulus: int) -> int:
    key = f"{client_u}:{client_v}:{round_id}".encode()
    digest = hashlib.sha256(key).digest()
    return int.from_bytes(digest[:8], "big") % modulus


def compute_mask(flat_params: torch.Tensor, client_id: int, num_clients: int, round_id: int, modulus: int) -> torch.Tensor:
    """Lattice-compatible masking over prime field; masks sum to zero."""
    mask = torch.zeros_like(flat_params)
    n_params = flat_params.numel()
    for other in range(num_clients):
        if other == client_id:
            continue
        seed = pairwise_seed(min(client_id, other), max(client_id, other), round_id, modulus)
        rng = np.random.default_rng(seed)
        values = rng.integers(0, modulus, size=n_params, dtype=np.int64)
        contrib = torch.from_numpy(values).to(flat_params.dtype)
        if client_id < other:
            mask += contrib
        else:
            mask -= contrib
    return mask


def apply_mask(params: list[torch.Tensor], client_id: int, num_clients: int, round_id: int, modulus: int) -> list[torch.Tensor]:
    flat = torch.cat([p.reshape(-1) for p in params])
    masked_flat = flat + compute_mask(flat, client_id, num_clients, round_id, modulus)
    # unflatten
    out = []
    idx = 0
    for p in params:
        n = p.numel()
        out.append(masked_flat[idx : idx + n].reshape(p.shape))
        idx += n
    return out


def crypto_round_overhead(mode: SecurityModeConfig, num_clients: int) -> float:
    """Return simulated crypto overhead in seconds per FL round."""
    per_client = (mode.kem_encaps_ms + mode.kem_decaps_ms + mode.sig_sign_ms + mode.sig_verify_ms) / 1000.0
    return per_client * num_clients
