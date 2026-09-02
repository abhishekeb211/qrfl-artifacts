"""Local training and evaluation utilities."""

from __future__ import annotations

import copy

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

from federated_learning.model import get_parameters, set_parameters


def train_local(
    model: nn.Module,
    loader,
    epochs: int,
    lr: float,
    device: torch.device,
) -> list[torch.Tensor]:
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()
    for _ in range(epochs):
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            y = y.view(-1).long()
            optimizer.zero_grad()
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()
    return get_parameters(model)


def evaluate(model: nn.Module, loader, device: torch.device) -> dict:
    model.eval()
    ys, preds, probs = [], [], []
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            y = y.view(-1).long()
            logits = model(x)
            prob = torch.softmax(logits, dim=1)[:, 1].cpu().numpy()
            pred = logits.argmax(dim=1).cpu().numpy()
            ys.extend(y.numpy().tolist())
            preds.extend(pred.tolist())
            probs.extend(prob.tolist())
    ys_arr = np.array(ys)
    probs_arr = np.array(probs)
    valid = np.isfinite(probs_arr)
    auroc = float("nan")
    if len(set(ys_arr.tolist())) > 1 and valid.any():
        try:
            auroc = roc_auc_score(ys_arr[valid], probs_arr[valid])
        except ValueError:
            auroc = float("nan")
    specificity = float("nan")
    if 0 in ys_arr:
        try:
            specificity = recall_score(ys_arr, preds, pos_label=0, zero_division=0)
        except ValueError:
            specificity = float("nan")
    return {
        "accuracy": accuracy_score(ys, preds),
        "auroc": auroc,
        "precision": precision_score(ys, preds, zero_division=0),
        "recall": recall_score(ys, preds, zero_division=0),
        "f1": f1_score(ys, preds, zero_division=0),
        "sensitivity": recall_score(ys, preds, zero_division=0),
        "specificity": specificity,
    }
