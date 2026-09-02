#!/usr/bin/env bash
# Full QRFL reproducibility pipeline
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "=== QRFL Reproducibility Pipeline ==="

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

export PYTHONPATH="$ROOT:${PYTHONPATH:-}"

echo "[1/7] Forecasting..."
python -m forecasting.run_all

echo "[2/7] PQC benchmarks..."
python -m pqc_benchmarks.run_benchmarks

echo "[3/7] Federated learning..."
python -m federated_learning.run_experiment

echo "[4/7] Resource profiling..."
python -m resource_profiling.run_profile || echo "WARN: resource profiling skipped (RAPL unavailable)"

echo "[5/7] Statistical tests..."
python -m statistical_tests.run_all

echo "[6/7] Figures..."
python -m figures.generate_all

echo "[7/7] Hardware capture..."
python scripts/capture_hardware.py || true

echo ""
echo "Done. Results in: $ROOT/results/"
echo "Include in manuscript: \\input{qrfl-artifacts/results/results_macros.tex}"
echo ""
echo "Blockchain testbed (optional, requires Docker):"
echo "  cd blockchain && docker compose up -d && python client/submit_transactions.py && docker compose down"
