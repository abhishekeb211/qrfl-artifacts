"""Federated aggregation: FedAvg, coordinate-wise Median, Krum."""

from __future__ import annotations

import torch


def fedavg(updates: list[list[torch.Tensor]]) -> list[torch.Tensor]:
    n = len(updates)
    averaged = []
    for layer_idx in range(len(updates[0])):
        stacked = torch.stack([u[layer_idx] for u in updates], dim=0)
        averaged.append(stacked.mean(dim=0))
    return averaged


def coordinate_median(updates: list[list[torch.Tensor]]) -> list[torch.Tensor]:
    out = []
    for layer_idx in range(len(updates[0])):
        stacked = torch.stack([u[layer_idx] for u in updates], dim=0)
        out.append(stacked.median(dim=0).values)
    return out


def _flatten_updates(updates: list[list[torch.Tensor]]) -> torch.Tensor:
    flats = [torch.cat([u.reshape(-1) for u in upd]) for upd in updates]
    return torch.stack(flats, dim=0)


def krum(updates: list[list[torch.Tensor]], num_byzantine: int = 0) -> list[torch.Tensor]:
    flat = _flatten_updates(updates)
    n = flat.size(0)
    f = num_byzantine
    scores = []
    for i in range(n):
        distances = []
        for j in range(n):
            if i == j:
                continue
            distances.append(torch.norm(flat[i] - flat[j]).item())
        distances.sort()
        k = n - f - 2
        scores.append(sum(distances[: max(k, 1)]))
    chosen = int(torch.tensor(scores).argmin().item())
    return updates[chosen]
