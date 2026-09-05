#!/usr/bin/env bash
# Entrypoint for abhi211b/qrfl-rapl — probe or profile with hardware constraints.
set -euo pipefail

MODE="${1:-probe}"
shift || true

export PYTHONPATH="${PYTHONPATH:-/app}"
export QRFL_RAPL_IMAGE="${QRFL_RAPL_IMAGE:-abhi211b/qrfl-rapl:latest}"

case "$MODE" in
  probe)
    exec python3 -m resource_profiling.rapl_probe --image "$QRFL_RAPL_IMAGE" "$@"
    ;;
  profile)
    # Soft-fail: still run latency/RSS; energy stays --- without RAPL.
    python3 -m resource_profiling.rapl_probe --image "$QRFL_RAPL_IMAGE" || true
    exec python3 -m resource_profiling.run_profile "$@"
    ;;
  bash|sh)
    exec "$MODE" "$@"
    ;;
  *)
    echo "Usage: docker run ... abhi211b/qrfl-rapl:latest {probe|profile} [args...]" >&2
    echo "Unknown mode: $MODE" >&2
    exit 1
    ;;
esac
