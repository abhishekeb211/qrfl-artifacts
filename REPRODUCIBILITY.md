# QRFL Reproducibility Guide

Companion guide for **Threat-Timeline-Driven Quantum-Resistant Federated Learning for Blockchain-Enabled Healthcare Systems**.

**Public repository:** https://github.com/abhishekeb211/qrfl-artifacts

## Quick reproduce

```bash
cd qrfl-artifacts
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
./run_all.sh          # or run_all.ps1 on Windows
```

Generated LaTeX fragments under `results/` are `\input` by the parent manuscript `../main.tex`.

## RAPL energy profiling

Dedicated slim image **`abhi211b/qrfl-rapl`** (not the full `abhi211b/qrfl` pipeline) runs Exp F + RAPL probes with hardware constraints baked in.

`resource_profiling/run_profile.py` reads `/sys/class/powercap/intel-rapl/*/energy_uj`.

| Host | Expected energy cells |
|------|------------------------|
| Bare-metal Linux Intel with RAPL + privileged container | Filled (mJ/op) |
| Docker Desktop on Windows / WSL2 (this submission host) | `---` — empty powercap; see `results/resource/rapl_probe.json` (`NO_RAPL`) |
| ARM Raspberry Pi / Jetson | Out of scope; deferred |

**Hardware required for numeric mJ:** Intel RAPL exposed as `/sys/class/powercap/intel-rapl/*/energy_uj` (typically bare-metal Linux; Docker Desktop does not expose this). Do **not** invent joules when RAPL is unavailable.

```bash
# Build / tag locally
docker build -f docker/Dockerfile.rapl -t abhi211b/qrfl-rapl:latest .

# Privileged probe (soft-fail NO_RAPL on constrained hosts)
powershell -ExecutionPolicy Bypass -File docker/run_rapl_probe.ps1   # Windows
# ./docker/run_rapl_probe.sh                                      # Linux

# Profile (latency + RSS always; energy --- without RAPL)
powershell -ExecutionPolicy Bypass -File docker/run_resource_profile.ps1
# or: docker compose -f docker/docker-compose.yaml run --rm rapl-profile

# Host-native (no container)
python -m resource_profiling.rapl_probe
python -m resource_profiling.run_profile
```

## Blockchain: simulation vs live

```bash
cd blockchain
docker compose up -d

# Channel + chaincode lifecycle (Windows PowerShell)
powershell -ExecutionPolicy Bypass -File scripts/create_channel.ps1
# Or manually: configtxgen + peer channel create/join (see scripts/)
powershell -ExecutionPolicy Bypass -File scripts/deploy_chaincode.ps1

cd ..
python -m blockchain.client.submit_transactions --mode both   # sim + live probe
# Fail loud if chaincode commit marker is missing:
# python -m blockchain.client.submit_transactions --mode live --require-chaincode
python -m blockchain.client.collect_metrics
```

| Mode | Flag | Outputs |
|------|------|---------|
| Calibrated simulation | `--mode sim` (default) | `results/blockchain/transactions.csv`, `ledger_latency.tex` |
| Live testbed probe | `--mode live` | `live_transactions.csv`, `live_summary.csv`, `live_testbed.tex` |
| Both | `--mode both` | All of the above |
| Require chaincode | `--require-chaincode` | Raises if `.chaincode_deployed` does not record a successful commit |

Live probe measures published peer/orderer TCP RTTs plus real ECDSA/ML-DSA sign–verify. **Confirmed chaincode path (this submission):** Hyperledger `fabric-samples` test-network with etcdraft ordering — `flupdate` approve/commit + `SubmitUpdate` invoke (`live_chaincode`; see `results/blockchain/live_testbed.tex`). An earlier Solo custom compose failed `_lifecycle` block-cut; that history is in [`blockchain/FABRIC_CHAINCODE_BLOCKER.md`](blockchain/FABRIC_CHAINCODE_BLOCKER.md). Chaincode uses Dilithium mode3 (ML-DSA-65) via circl and is vendored for peer builds.

## Statistical tests

```bash
python -m statistical_tests.run_all
```

Emits pairwise TOST / paired-t / Wilcoxon (Holm-corrected), Friedman across three modes, and:

- `results/statistics/statistical_tests.tex`
- `results/statistics/statistical_tests_non_iid.tex`
- `results/statistics/fl_friedman_tests.csv`

## Figures

```bash
python -m figures.generate_all
```

Vector PDF + PNG with Okabe–Ito colorblind-safe palette; copy into `../figs/` for manuscript fallbacks.

## Zenodo archival (optional; not an open gap)

Zenodo DOI deposition is **discarded** for this submission. Cite the GitHub repository below. If you later want a DOI:

1. `python scripts/prepare_zenodo_archive.py`
2. Upload at https://zenodo.org/
3. Paste the DOI into `main.tex` only after deposition completes (never invent a DOI).
