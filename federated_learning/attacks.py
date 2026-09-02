"""Byzantine attack simulation."""

from __future__ import annotations

import random

import torch


def apply_attack(
    params: list[torch.Tensor],
    attack: str,
    num_classes: int = 2,
) -> list[torch.Tensor]:
    if attack == "none":
        return params
    if attack == "sign_flip":
        return [-p for p in params]
    if attack == "label_flip":
        # Represent label-flip poisoning as destructive weight perturbation
        return [p * -1.0 + torch.randn_like(p) * 0.5 for p in params]
    raise ValueError(f"Unknown attack: {attack}")


def select_malicious_clients(num_clients: int, fraction: float, seed: int) -> set[int]:
    rng = random.Random(seed)
    k = int(round(num_clients * fraction))
    return set(rng.sample(range(num_clients), k)) if k > 0 else set()
