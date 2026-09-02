"""Collect CPU/memory metrics from Docker during blockchain testbed runs."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def collect_docker_stats() -> list[dict]:
    try:
        output = subprocess.check_output(
            ["docker", "stats", "--no-stream", "--format", "{{json .}}"],
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    rows = []
    for line in output.strip().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    stats = collect_docker_stats()
    out = root / "results" / "blockchain"
    out.mkdir(parents=True, exist_ok=True)
    with (out / "docker_stats.json").open("w", encoding="utf-8") as handle:
        json.dump(stats, handle, indent=2)
    print(f"Collected stats for {len(stats)} containers")


if __name__ == "__main__":
    main()
