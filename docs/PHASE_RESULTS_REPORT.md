# QRFL Detailed Results Report

**Project:** Threat-Timeline-Driven Quantum-Resistant Federated Learning for Blockchain-Enabled Healthcare Systems  
**Corpus date:** 2026-09-03 (full-scale FL completed)  
**Artifacts root:** `qrfl-artifacts/`  
**Manuscript:** `../main.tex`

---

## 1. Executive summary

All Phases **0–7** are implemented for the measured corpus. Federated learning completed at the full configured scale (**10 seeds × 50 rounds × 270 configs**, ~18.3 hours CPU).

| Finding | Result |
|---------|--------|
| Predictive utility across security modes | **Identical** (Classical = Hybrid = Native PQ); TOST **equivalent** |
| FL round-latency PQ overhead | **Not significant** after Holm correction; native overhead typically **&lt; 1%** |
| HLF simulation (native PQ vs classical) | **80.8 → 84.2 ms** (~4%) |
| Quantum-risk planning trigger | Bootstrap 95% lower bound **~2042.1** (baseline η) |

---

## 2. Phase implementation status

| Phase | Status | Deliverable |
|-------|--------|-------------|
| 0 Infra | Done | venv, `run_all.ps1`/`.sh`, Docker CPU image, GitHub `abhishekeb211/qrfl-artifacts` |
| 1 PQC | Done | `results/pqc/crypto_benchmarks.tex`, `parameter_ablation.tex` (~241k trials) |
| 2 FL | Done | `results/fl/all_results.csv` — **270 rows, 10 seeds, 50 rounds** |
| 3 Stats | Done | `results/statistics/statistical_tests.tex` (9 IID rows) |
| 4 Forecast validation | Done | `results/forecasting/validation/forecast_validation.tex` |
| 5 Resource (Exp F) | Done | `results/resource/resource_profiling.tex` (energy N/A on Windows) |
| 6 Figures | Done | `figures/output/*.pdf` (+ PNG) |
| 7 Fabric verify | Done | orderer + 3 peers + CouchDB **Up**; chaincode deploy optional |

**Macros:** `\FLNumSeeds{10}`, `\FLNumRounds{50}`, `\FLIIDAccuracyClassical{65.3}`, `\FLDeterminismCheck{passed}`.

---

## 3. Experiment A — PQC micro-benchmarks

**Method:** PQClean CFFI via `quantcrypt-cffi`; 10,000 trials after 1,000 warm-up.

| Scheme | Operation | Mean (ms) | SD (ms) |
|--------|-----------|-----------|---------|
| ECDSA-P256 | sign | 0.035 | 0.002 |
| ECDSA-P256 | verify | 0.085 | 0.003 |
| ML-KEM-768 | encapsulate | 0.128 | 0.004 |
| ML-KEM-768 | decapsulate | 0.091 | 0.013 |
| ML-DSA-65 | sign | 0.850 | 0.502 |
| ML-DSA-65 | verify | 0.245 | 0.019 |
| SLH-DSA-SHAKE-256s | sign | 536.8 | 5.84 |

Default healthcare FL profile: **ML-KEM-768 / ML-DSA-65** (NIST Level 3).

---

## 4. Experiment B / B-2 / D — Federated learning

**Dataset:** PneumoniaMNIST · **Aggregator:** FedAvg (plus Median/Krum for Exp D) · **Modes:** classical, hybrid_pq, native_pq.

### 4.1 IID client scaling (α = 1.0, attack = none)

| Clients | Accuracy (mean) | Classical latency (s) | Hybrid (s) | Native (s) | Native overhead |
|---------|-----------------|----------------------|------------|------------|-----------------|
| 5 | 76.7% | 16.70 ± 0.18 | 16.73 ± 0.18 | 16.73 ± 0.18 | +0.17% |
| 10 | 77.8% | 17.09 ± 0.17 | 17.07 ± 0.20 | 17.06 ± 0.15 | −0.15% |
| 25 | 65.3% | 19.06 ± 0.28 | 19.01 ± 0.29 | 18.62 ± 0.32 | −2.30% |
| 50 | 45.4% | 24.70 ± 0.37 | 24.82 ± 0.24 | 24.78 ± 0.37 | +0.34% |

**IID-25 (default):** accuracy **65.34% ± 0.15** and AUROC **0.566** for all three modes (determinism check passed).

### 4.2 Non-IID Dirichlet (25 clients, FedAvg)

| α | Accuracy | F1 | Mean latency (s) |
|---|----------|-----|------------------|
| 0.1 | 65.30% | 0.767 | 19.18 |
| 0.5 | 65.42% | 0.768 | 19.12 |
| 1.0 (IID) | 65.34% | 0.767 | 19.01 |

### 4.3 Byzantine robustness (native PQ, 25 clients)

| Attack | Malicious % | Aggregator | Accuracy | Latency (s) |
|--------|-------------|------------|----------|-------------|
| None | 0% | FedAvg | 65.98% | 19.31 |
| None | 0% | Median | 37.50% | 18.39 |
| None | 0% | Krum | 37.50% | 18.52 |
| Label flip | 10% | FedAvg | 37.45% | 19.01 |
| Label flip | 20% | FedAvg | 41.15% | 19.01 |
| Sign flip | 20% | Krum | 37.50% | 18.52 |

---

## 5. Statistical significance (Phase 3)

**Setting:** IID α=1.0, 25 clients, FedAvg, attack=none · Holm-corrected α=0.05.

| Metric | Mode pairs | Test | Result |
|--------|------------|------|--------|
| accuracy | all three pairs | TOST | **equivalent** |
| f1 | all three pairs | TOST | **equivalent** |
| mean_round_latency_s | classical↔hybrid | paired *t* | not significant |
| mean_round_latency_s | classical↔native | paired *t* | not significant |
| mean_round_latency_s | hybrid↔native | Wilcoxon | not significant |

---

## 6. Experiment C — Blockchain

### 6.1 Calibrated HLF v2.5 lifecycle simulation

| Phase | Classical (ms) | Hybrid (ms) | Native PQ (ms) |
|-------|----------------|-------------|----------------|
| Endorsement | 25.4 | 28.4 | 28.3 |
| Ordering | 40.2 | 40.2 | 40.2 |
| Validation / commit | 15.3 | 16.0 | 15.7 |
| **Total** | **80.8** | **84.6** | **84.2** |

### 6.2 Live testbed

| Container | Status |
|-----------|--------|
| orderer.example.com | Up |
| peer0.hospitala.example.com | Up |
| peer0.hospitalb.example.com | Up |
| peer0.research.example.com | Up |
| couchdb-hospitala | Up |

MSP identity remains ECDSA; ML-DSA payload verification is application-layer (chaincode deploy deferred — Go not installed).

---

## 7. Experiment E — Parameter ablation

Emitted from PQC sweep: Lightweight / Balanced / High-Assurance / Long-term profiles in `results/pqc/parameter_ablation.tex`. System default remains **ML-KEM-768 / ML-DSA-65**.

---

## 8. Experiment F — Resource profiling

**API:** quantcrypt high-level (includes Python wrapper overhead). Distinct from CFFI micro-benchmarks in Exp A.

| Scheme | Operation | Latency (ms) | Peak RSS (MB) | Energy |
|--------|-----------|--------------|---------------|--------|
| ML-KEM-768 | Encaps | 3.69 ± 0.66 | 73.4 | — (no RAPL) |
| ML-KEM-768 | Decaps | 2.70 ± 0.46 | 74.1 | — |
| ML-DSA-65 | Sign | 5.19 ± 1.26 | 76.2 | — |
| ML-DSA-65 | Verify | 2.34 ± 0.47 | 76.3 | — |

---

## 9. Forecast validation (Phase 4)

Exponential growth model on *n*=20 frontier processors.

| Strategy | MAE | RMSE | MAPE (%) |
|----------|-----|------|----------|
| Hold-out (2024–2026) | 563.39 | 602.62 | 424.63 |
| Rolling-origin | 600.51 | 768.92 | 311.40 |
| Leave-one-out | 316.24 | 544.69 | 151.37 |

**Residuals (log-scale):** mean ≈ 0 · Shapiro–Wilk *p*=0.395 · Durbin–Watson=1.80 · Ljung–Box *p*=0.838.  
**Planning trigger:** `\ForecastBootstrapCILower` ≈ **2042.10**.

---

## 10. Manuscript wiring

All of the following resolve via `\IfFileExists` / `\input` in `main.tex`:

- `results/results_macros.tex`
- `results/pqc/crypto_benchmarks.tex`, `parameter_ablation.tex`
- `results/fl/fl_metrics.tex`, `fl_latency.tex`, `non_iid_fl.tex`, `byzantine_robustness.tex`
- `results/statistics/statistical_tests.tex`
- `results/forecasting/validation/forecast_validation.tex`
- `results/resource/resource_profiling.tex`
- `results/blockchain/ledger_latency.tex`
- `figures/output/{pqc,fl,hlf,forecasting,threshold,sensitivity}_*.pdf`

---

## 11. Deferred / out of scope

1. Live Fabric chaincode package/install/approve/commit (requires Go)
2. Intel RAPL energy and ARM Pi/Jetson profiling
3. Zenodo DOI archival
4. Host `pdflatex` compile of `main.tex` (not installed on this Windows server)

---

## 12. Reproduce / regenerate

```powershell
cd qrfl-artifacts
.\.venv\Scripts\python.exe scripts\finalize_fl_results.py
.\.venv\Scripts\python.exe -m statistical_tests.run_all
.\.venv\Scripts\python.exe -m figures.generate_all
```

Full pipeline: `.\run_all.ps1` (FL alone is multi-hour on CPU).

---

*Report generated from measured CSVs/LaTeX under `qrfl-artifacts/results/` and `figures/output/`.*
