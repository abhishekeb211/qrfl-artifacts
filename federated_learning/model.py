"""Simple CNN for PneumoniaMNIST (matches manuscript description)."""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class PneumoniaCNN(nn.Module):
    def __init__(self, num_classes: int = 2) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(1, 16, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.dropout = nn.Dropout(0.25)
        self.fc1 = nn.Linear(32 * 7 * 7, 128)
        self.fc2 = nn.Linear(128, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = self.dropout(x)
        x = x.view(x.size(0), -1)
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        return self.fc2(x)


def get_parameters(model: nn.Module) -> list[torch.Tensor]:
    return [p.detach().cpu().clone() for p in model.parameters()]


def set_parameters(model: nn.Module, params: list[torch.Tensor]) -> None:
    for p, new in zip(model.parameters(), params):
        p.data = new.clone().to(p.device)


def flatten_params(params: list[torch.Tensor]) -> torch.Tensor:
    return torch.cat([p.reshape(-1) for p in params])


def unflatten_params(flat: torch.Tensor, template: list[torch.Tensor]) -> list[torch.Tensor]:
    out = []
    idx = 0
    for p in template:
        n = p.numel()
        out.append(flat[idx : idx + n].reshape(p.shape))
        idx += n
    return out
