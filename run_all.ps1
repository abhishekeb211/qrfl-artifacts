# Full QRFL reproducibility pipeline (Windows PowerShell)
# Publication-scale FL: 10 seeds x 50 rounds x 270 configs (~hours on CPU; uses parallel workers).
# Delete results/fl/all_results.csv before a clean re-run.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "=== QRFL Reproducibility Pipeline ==="

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

$env:PYTHONPATH = "$Root;$env:PYTHONPATH"

Write-Host "[1/7] Forecasting..."
& $venvPython -m forecasting.run_all

Write-Host "[2/7] PQC benchmarks..."
& $venvPython -m pqc_benchmarks.run_benchmarks

Write-Host "[3/7] Federated learning..."
& $venvPython -m federated_learning.run_experiment

Write-Host "[4/7] Resource profiling..."
try {
    & $venvPython -m resource_profiling.run_profile
} catch {
    Write-Warning "Resource profiling skipped (RAPL unavailable on this host)."
}

Write-Host "[5/7] Statistical tests..."
& $venvPython -m statistical_tests.run_all

Write-Host "[6/7] Figures..."
& $venvPython -m figures.generate_all

Write-Host "[7/7] Hardware capture..."
try {
    & $venvPython scripts/capture_hardware.py | Out-File -FilePath results/hardware_specs.json -Encoding utf8
} catch {
    Write-Warning "Hardware capture skipped."
}

Write-Host ""
Write-Host "Done. Results in: $Root\results\"
Write-Host "Include in manuscript: \input{qrfl-artifacts/results/results_macros.tex}"
Write-Host ""
Write-Host "Blockchain testbed (optional, requires Docker/WSL):"
Write-Host "  cd blockchain; docker compose up -d; python client/submit_transactions.py; docker compose down"
