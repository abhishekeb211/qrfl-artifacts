"""Capture hardware specifications for reproducibility documentation."""

from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path

import psutil


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root / "results" / "hardware_specs.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    info = {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "ram_gb": round(psutil.virtual_memory().total / (1024**3), 2),
    }

    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("model name"):
                    info["cpu_model"] = line.split(":", 1)[1].strip()
                    break
    except OSError:
        pass

    try:
        rapl = list(Path("/sys/class/powercap/intel-rapl").glob("intel-rapl:*"))
        info["rapl_available"] = len(rapl) > 0
    except OSError:
        info["rapl_available"] = False

    try:
        docker_version = subprocess.check_output(["docker", "--version"], text=True).strip()
        info["docker"] = docker_version
    except (OSError, subprocess.CalledProcessError):
        info["docker"] = None

    with out.open("w", encoding="utf-8") as handle:
        json.dump(info, handle, indent=2)

    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
