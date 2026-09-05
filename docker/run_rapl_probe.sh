#!/usr/bin/env bash
# Privileged RAPL probe via abhi211b/qrfl-rapl (soft-fail NO_RAPL on Docker Desktop).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${QRFL_RAPL_IMAGE:-abhi211b/qrfl-rapl:latest}"
IMAGE_ID="$(docker inspect --format '{{.Id}}' "$IMAGE" 2>/dev/null || true)"

docker run --rm --privileged \
  -e QRFL_RAPL_IMAGE="$IMAGE" \
  -e QRFL_RAPL_IMAGE_ID="$IMAGE_ID" \
  -v "$ROOT/results:/app/results" \
  "$IMAGE" probe "$@"
