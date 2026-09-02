"""Data loading and Dirichlet non-IID partitioning."""

from __future__ import annotations

from typing import Sequence

import numpy as np
import torch
from medmnist import INFO
from torch.utils.data import DataLoader, Subset
from torchvision import transforms


def _extract_label(y) -> int:
    if hasattr(y, "item"):
        return int(y.item())
    return int(y)


def load_pneumoniamnist(batch_size: int = 32):
    info = INFO["pneumoniamnist"]
    DataClass = getattr(__import__("medmnist", fromlist=[info["python_class"]]), info["python_class"])
    transform = transforms.Compose([transforms.ToTensor(), transforms.Normalize([0.5], [0.5])])
    train = DataClass(split="train", transform=transform, download=True)
    val = DataClass(split="val", transform=transform, download=True)
    test = DataClass(split="test", transform=transform, download=True)
    return train, val, test


def dirichlet_partition(
    dataset,
    num_clients: int,
    alpha: float,
    seed: int,
    num_classes: int = 2,
) -> list[list[int]]:
    rng = np.random.default_rng(seed)
    labels = np.array([_extract_label(dataset[i][1]) for i in range(len(dataset))])
    idx_by_class = [np.where(labels == c)[0] for c in range(num_classes)]
    client_indices: list[list[int]] = [[] for _ in range(num_clients)]
    for c in range(num_classes):
        idx_c = idx_by_class[c]
        if len(idx_c) == 0:
            continue
        rng.shuffle(idx_c)
        proportions = rng.dirichlet(alpha * np.ones(num_clients))
        split_points = (np.cumsum(proportions) * len(idx_c)).astype(int)[:-1]
        splits = np.split(idx_c, split_points)
        for client_id, part in enumerate(splits):
            client_indices[client_id].extend(part.tolist())

    # Dirichlet splits can yield empty clients; rebalance from the largest donor.
    for cid in range(num_clients):
        if client_indices[cid]:
            continue
        donor = max(range(num_clients), key=lambda i: len(client_indices[i]))
        if client_indices[donor]:
            client_indices[cid].append(client_indices[donor].pop())

    return client_indices


def make_client_loaders(
    dataset,
    client_indices: Sequence[list[int]],
    batch_size: int,
    seed: int = 0,
) -> list[DataLoader]:
    loaders = []
    for client_id, indices in enumerate(client_indices):
        if not indices:
            raise ValueError("Client partition is empty after rebalancing; reduce num_clients or alpha.")
        subset = Subset(dataset, indices)
        generator = torch.Generator().manual_seed(seed + client_id)
        loaders.append(
            DataLoader(
                subset,
                batch_size=min(batch_size, len(indices)),
                shuffle=True,
                generator=generator,
            )
        )
    return loaders
