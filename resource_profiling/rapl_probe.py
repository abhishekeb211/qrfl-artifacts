"""RAPL / powercap hardware probe for honest energy reporting.

Never invent joules. On hosts without intel-rapl (e.g. Docker Desktop WSL2),
emit rapl_available=false / NO_RAPL and leave energy cells as ---.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path


POWERCAP = Path("/sys/class/powercap")
INTEL_RAPL = POWERCAP / "intel-rapl"


def _uname() -> str:
    try:
        return subprocess.check_output(["uname", "-a"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return platform.platform()


def _cpu_model() -> str:
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or "unknown"


def list_powercap() -> list[str]:
    if not POWERCAP.exists():
        return []
    return sorted(p.name for p in POWERCAP.iterdir())


def list_rapl_domains() -> list[dict[str, str | bool]]:
    domains: list[dict[str, str | bool]] = []
    if not INTEL_RAPL.exists():
        return domains
    for domain in sorted(INTEL_RAPL.glob("intel-rapl:*")):
        energy = domain / "energy_uj"
        name = domain / "name"
        domains.append(
            {
                "path": str(domain),
                "name": name.read_text().strip() if name.exists() else domain.name,
                "energy_uj_readable": energy.exists() and os.access(energy, os.R_OK),
            }
        )
    return domains


def probe(*, image_ref: str | None = None) -> dict:
    domains = list_rapl_domains()
    readable = [d for d in domains if d.get("energy_uj_readable")]
    rapl_available = len(readable) > 0
    status = "OK_RAPL" if rapl_available else "NO_RAPL"
    entries = list_powercap()

    result = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "image": image_ref or os.environ.get("QRFL_RAPL_IMAGE", "abhi211b/qrfl-rapl:latest"),
        "image_id": os.environ.get("QRFL_RAPL_IMAGE_ID") or None,
        "host_os": f"{platform.system()} {platform.release()}",
        "kernel": _uname(),
        "cpu": _cpu_model(),
        "rapl_available": rapl_available,
        "status": status,
        "powercap_entries": entries,
        "intel_rapl_domains": domains,
        "hardware_requirements": {
            "numeric_mj": [
                "Bare-metal Linux (or VM with intel-rapl exposed)",
                "Intel CPU with RAPL",
                "/sys/class/powercap/intel-rapl/*/energy_uj readable",
                "Typically docker run --privileged (or bind-mount powercap)",
            ],
            "this_host_policy": (
                "Docker Desktop / WSL2 usually has an empty powercap tree; "
                "energy cells must remain ---; never invent joules"
            ),
        },
        "energy_policy": (
            "Do not invent joules; energy cells remain unavailable (---) "
            "until intel-rapl energy_uj is readable"
        ),
    }
    return result


def write_probe(out_path: Path, data: dict | None = None) -> dict:
    data = data or probe()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe Intel RAPL powercap exposure")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output JSON path (default: results/resource/rapl_probe.json)",
    )
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="Image tag/id recorded in the probe JSON",
    )
    parser.add_argument(
        "--require-rapl",
        action="store_true",
        help="Exit 2 if RAPL is unavailable (default: soft-fail exit 0 with NO_RAPL)",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    out = args.out or (root / "results" / "resource" / "rapl_probe.json")
    data = write_probe(out, probe(image_ref=args.image))

    print(f"RAPL probe: {data['status']} (rapl_available={data['rapl_available']})")
    print(f"Wrote {out}")
    if data["rapl_available"]:
        return 0
    print(
        "WARN: intel-rapl not exposed; energy/op will be --- "
        "(no invented joules). Use bare-metal Linux for numeric mJ."
    )
    return 2 if args.require_rapl else 0


if __name__ == "__main__":
    raise SystemExit(main())
