# QRFL Reproducibility Artifacts

Reproducibility package for **Threat-Timeline-Driven Quantum-Resistant Federated Learning for Blockchain-Enabled Healthcare Systems**.

This repository generates all experimental numbers, statistical tests, and figure inputs for the manuscript. **Do not hand-type values into `main.tex`**; run the pipeline and include `results/results_macros.tex`.

The LaTeX manuscript (`main.tex`) is maintained at the parent project path `../main.tex` relative to this repo and is not versioned inside `qrfl-artifacts/`.

**Documentation export:** see [`docs/`](docs/) in this repo and the workspace [`../docs/`](../docs/) (architecture analysis + phase results reports).

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
python -m federated_learning.run_experiment   # 10 seeds x 50 rounds x 270 configs (experiment_seeds.yaml)
python scripts/finalize_fl_results.py         # regenerate fl_*.tex from results/fl/all_results.csv
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
| `tab:regression_results`, bootstrap | `forecasting/run_all.py` | `results/forecasting/` |
| `tab:forecast_validation` | `forecasting/emit_tables.py` | `results/forecasting/validation/forecast_validation.tex` |
| `tab:crypto_benchmarks` | `pqc_benchmarks/run_benchmarks.py` | `results/pqc/crypto_benchmarks.tex` |
| `tab:fl_metrics`, `tab:fl_latency` | `federated_learning/run_experiment.py` | `results/fl/fl_*.tex` |
| `tab:non_iid_fl` | `federated_learning/run_experiment.py` | `results/fl/non_iid_fl.tex` |
| `tab:byzantine_robustness` | `federated_learning/run_experiment.py` | `results/fl/byzantine_robustness.tex` |
| `tab:statistical_tests` | `statistical_tests/run_all.py` | `results/statistics/statistical_tests.tex` |
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

## Phase status (current corpus)

Phases 0–7 pipeline code and manuscript `\input` hooks are in place. **No Cursor plan todos remain pending** (Remaining Tasks + Phases 2–7). Measured outputs used for submission are:

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Infra | Done | venv, `run_all.ps1` / `.sh`, Docker CPU image, GitHub remote |
| 1 PQC | Done | `results/pqc/crypto_benchmarks.tex`, parameter ablation |
| 2 FL | Done | **Current:** 10 seeds × 50 rounds × 270 configs in `results/fl/all_results.csv` (full `experiment_seeds.yaml` target). |
| 3 Stats | Done | `results/statistics/statistical_tests.tex` (IID baseline, Holm-corrected) |
| 4 Forecast validation | Done | `results/forecasting/validation/forecast_validation.tex` |
| 5 Resource (Exp F) | Done | `results/resource/resource_profiling.tex` (energy N/A without RAPL) |
| 6 Figures | Done | `figures/output/*.pdf` (+ PNG) |
| 7 Verify / Fabric | Done | 3-peer + orderer + CouchDB compose; chaincode deploy optional (needs Go) |

**Intentional / deferred (not blocking manuscript with current corpus):**

1. Live Fabric chaincode package/deploy — optional; requires Go
2. Docker RAPL / ARM edge resource profiling — deferred
3. Zenodo DOI archival — post-submission
4. Local `pdflatex` compile of `../main.tex` — not installed on this host

Macros in `results/results_macros.tex` reflect the current FL corpus (`\FLNumSeeds{10}`, `\FLNumRounds{50}`).

To regenerate FL tables after any future re-run:

```bash
python scripts/finalize_fl_results.py
python -m statistical_tests.run_all
python -m figures.generate_all
```

*Companion documents:* `PHASE_RESULTS_REPORT.md` (numeric corpus), `ARCHITECTURE_PROCESS_ANALYSIS.md` (process architecture + step-by-step analysis), `README.md` (phase status), canvases `QRFL-Phase-Results-Report` and `QRFL-Architecture-Process-Analysis`.

## License

This repository is licensed under the [MIT License](LICENSE).

## Citation and Archival

After all artifacts are generated and verified:

1. Push to GitHub
2. Create a Zenodo release and obtain a DOI
3. Update the manuscript Data/Code Availability statements with the DOI

**Do not cite a DOI until the archive exists.**
