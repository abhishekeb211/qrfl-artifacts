# QRFL Reproducibility Artifacts

Reproducibility package for **Threat-Timeline-Driven Quantum-Resistant Federated Learning for Blockchain-Enabled Healthcare Systems**.

This repository generates all experimental numbers, statistical tests, and figure inputs for the manuscript. **Do not hand-type values into `main.tex`**; run the pipeline and include `results/results_macros.tex`.

## Repository Structure

```
qrfl-artifacts/
├── forecasting/          # Quantum hardware forecasting and validation
├── pqc_benchmarks/       # liboqs PQC primitive benchmarks
├── federated_learning/   # Flower + PneumoniaMNIST FL experiments
├── blockchain/           # 3-peer Hyperledger Fabric testbed
├── resource_profiling/   # x86 RAPL energy, memory, CPU profiling
├── statistical_tests/    # Significance tests and LaTeX table emission
├── datasets/             # Raw and cleaned quantum hardware CSV
├── configs/              # YAML experiment configurations
├── docker/               # Dockerfile and Compose
├── figures/              # Figure generation scripts
├── results/              # Generated outputs (CSV, JSON, LaTeX macros)
└── run_all.sh            # Full reproduction workflow
```

## Prerequisites

- Linux server with Docker and Docker Compose
- Python 3.10+
- liboqs built with `-DOQS_DIST_BUILD=ON` (see `docker/Dockerfile`)
- Intel CPU with RAPL support for energy profiling (optional; module degrades gracefully)

## Quick Start

```bash
cd qrfl-artifacts
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run full pipeline (forecasting through statistics)
./run_all.sh              # Linux/macOS
./run_all.ps1             # Windows PowerShell

# Or run modules individually:
python -m forecasting.run_all
python -m pqc_benchmarks.run_benchmarks
python -m federated_learning.run_experiment
python -m resource_profiling.run_profile
python -m statistical_tests.run_all
python -m figures.generate_all
```

**PQC backend:** Defaults to `quantcrypt` with direct PQClean CFFI timing (works on Windows without building liboqs). Set `prefer_liboqs: true` in `configs/pqc_benchmarks.yaml` on hosts with liboqs built.

## Blockchain Testbed (Separate)

The 3-peer Hyperledger Fabric deployment requires Docker and elevated resources:

```bash
cd blockchain
docker compose up -d
python client/submit_transactions.py --config ../configs/blockchain.yaml
python client/collect_metrics.py
docker compose down
```

## Reproducing Manuscript Tables

| Manuscript Table | Source Script | Output |
|------------------|---------------|--------|
| `tab:frontier_dataset` | `datasets/quantum_hardware_raw.csv` | static CSV |
| `tab:regression_results`, bootstrap | `forecasting/fit_models.py` | `results/forecasting/` |
| Forecast validation | `forecasting/backtest.py`, `loocv.py` | `results/forecasting/validation/` |
| `tab:crypto_benchmarks` | `pqc_benchmarks/run_benchmarks.py` | `results/pqc/trials.csv` |
| `tab:fl_metrics`, `tab:fl_latency` | `federated_learning/run_experiment.py` | `results/fl/` |
| `tab:non_iid_fl` | `federated_learning/run_experiment.py` | `results/fl/non_iid/` |
| `tab:byzantine_robustness` | `federated_learning/run_experiment.py` | `results/fl/byzantine/` |
| Statistical tests | `statistical_tests/run_all.py` | `results/statistics/` |
| Resource profiling | `resource_profiling/run_profile.py` | `results/resource/` |
| Fabric testbed | `blockchain/client/` | `results/blockchain/` |

After running, copy or symlink `results/results_macros.tex` into the manuscript build:

```latex
\input{qrfl-artifacts/results/results_macros.tex}
```

## Hardware Specifications

Document your execution environment before publishing results:

```bash
python scripts/capture_hardware.py > results/hardware_specs.json
```

## Seeds and Versions

All random seeds are defined in `configs/experiment_seeds.yaml`. Dependency versions are pinned in `requirements.txt`.

## Citation and Archival

After all artifacts are generated and verified:

1. Push to GitHub
2. Create a Zenodo release and obtain a DOI
3. Update the manuscript Data/Code Availability statements with the DOI

**Do not cite a DOI until the archive exists.**
