# QRFL Process Architecture and Step-by-Step Analysis

**Project:** Threat-Timeline-Driven Quantum-Resistant Federated Learning (QRFL)  
**Code root:** `qrfl-artifacts/` · **Manuscript:** `../main.tex`  
**Corpus:** Phases 0–7 complete (FL: 10 seeds × 50 rounds × 270 configs, 2026-09-03)

---

## 1. System purpose and design thesis

QRFL couples three decisions that are usually studied separately:

1. **When** to migrate (quantum-threat timeline forecasting + Mosca inequality).  
2. **What** to migrate to (NIST PQC: ML-KEM, ML-DSA, SLH-DSA; hybrid then native).  
3. **Whether** migration is affordable in a healthcare FL + Fabric stack (measured latency, utility, stats).

The scientific claim is the **integration**, not any single component in isolation.

---

## 2. Five-layer process architecture

```
┌─────────────────────────────────────────────────────────────┐
│ L5  Migration Decision Support (Mosca + MOSCoW roadmap)     │
├─────────────────────────────────────────────────────────────┤
│ L4  Blockchain Validation (HLF 2.5 + PQC payload verify)    │
├─────────────────────────────────────────────────────────────┤
│ L3  Healthcare Federated Learning (FedAvg, masks, Byzantine)│
├─────────────────────────────────────────────────────────────┤
│ L2  PQC / Crypto-Agility (ML-KEM, ML-DSA, SLH-DSA, hybrid)  │
├─────────────────────────────────────────────────────────────┤
│ L1  Quantum-Threat Forecasting (frontier qubits → years)    │
└─────────────────────────────────────────────────────────────┘
         ▲ measured latencies / crossing years feed upward
```

| Layer | Process role | Primary code | Primary outputs |
|-------|--------------|--------------|-----------------|
| **L1 Forecasting** | Estimate ECDSA-256 physical-qubit threshold crossing under η scenarios | `forecasting/run_all.py` | `fit_summary.csv`, `scenarios.csv`, `forecast_validation.tex` |
| **L2 Crypto** | Benchmark classical vs PQ primitives; select Level-3 defaults | `pqc_benchmarks/run_benchmarks.py` | `crypto_benchmarks.tex`, `parameter_ablation.tex` |
| **L3 FL** | Train under Classical / Hybrid / Native PQ security modes | `federated_learning/run_experiment.py` | `fl_*.tex`, `all_results.csv` |
| **L4 Blockchain** | Calibrated HLF lifecycle + live 3-peer testbed | `blockchain/client/submit_transactions.py`, `docker-compose.yaml` | `ledger_latency.tex`, `docker_stats.json` |
| **L5 Migration** | Translate L1–L4 into Mosca timing + MOSCoW roadmap | Manuscript §Discussion | Roadmap table (static prose + macros) |

**Dependency rule:** L2 latencies parameterize L3 crypto overhead and L4 simulation; L1 bootstrap lower bound justifies L2 Level-3 defaults and L5 urgency.

---

## 3. End-to-end reproducibility pipeline (step-by-step)

Orchestrator: `run_all.ps1` / `run_all.sh`.

```
[1/7] forecasting.run_all
        ↓ macros + CSVs + forecast_validation.tex
[2/7] pqc_benchmarks.run_benchmarks
        ↓ trials/summary + crypto_benchmarks.tex + ablation.tex
[3/7] federated_learning.run_experiment
        ↓ all_results.csv + fl_*.tex  (hours on CPU)
[4/7] resource_profiling.run_profile
        ↓ resource_profiling.tex  (energy optional)
[5/7] statistical_tests.run_all
        ↓ statistical_tests.tex (needs FL CSV)
[6/7] figures.generate_all
        ↓ figures/output/*.pdf|png + layer_*.tex
[7/7] scripts/capture_hardware.py
        ↓ hardware_specs.json

Optional (not in 1–7):
  blockchain: generate_crypto → docker compose up → submit_transactions → collect_metrics
```

**Shared bookkeeping:** every stage merges into `results/macros.json` via `qrfl_common.results.ResultsEmitter`, then writes `results/results_macros.tex` so stages can run independently without wiping each other’s macros.

**Manuscript bind:** `main.tex` uses `\IfFileExists{...}\input{...}` for every measured table/figure.

---

## 4. Layer 1 — Forecasting process (detailed)

### 4.1 Steps

| Step | Action | Module |
|------|--------|--------|
| 1 | Build clean *n*=20 frontier processor dataset from raw CSV | `datasets/build_clean.py` |
| 2 | Fit inclusion models A/B/C by hardware status filter | `fit_models.filter_by_status`, `fit_exponential_ols` |
| 3 | Fit Model C exponential OLS + logistic saturation | `fit_exponential_ols`, `fit_logistic` |
| 4 | Bootstrap crossing years (5,000 replicates) for η scenarios | `bootstrap_crossing_years` |
| 5 | Scenario projections (optimistic / baseline / conservative η) | `scenarios.scenario_projections` |
| 6 | Hold-out backtest (train ≤2023, test ≥2024) | `backtest.backtest_holdout` |
| 7 | Rolling-origin + LOOCV | `rolling_origin_backtest`, `loocv` |
| 8 | Residual diagnostics (Shapiro, DW, Ljung–Box, Cook’s D) | `residuals.residual_analysis` |
| 9 | Emit MAE/RMSE/MAPE table + macros | `emit_tables.emit_forecast_validation_table` |

### 4.2 Analysis

| Metric | Hold-out | Rolling | LOOCV |
|--------|----------|---------|-------|
| MAE | 563.39 | 600.51 | 316.24 |
| RMSE | 602.62 | 768.92 | 544.69 |
| MAPE (%) | 424.63 | 311.40 | 151.37 |

- Residuals on log-scale are consistent with normality (Shapiro *p*=0.395) and little autocorrelation (DW≈1.80, LB *p*=0.838).  
- High MAPE reflects sparse, discontinuous hardware jumps — treated as **planning heuristics**, not probabilistic forecasts.  
- **Risk trigger used in architecture:** bootstrap 95% lower bound ≈ **2042.1** (baseline η) → drives Level-3 PQC default.

---

## 5. Layer 2 — PQC / crypto-agility process

### 5.1 Benchmark steps

```
load pqc_benchmarks.yaml + experiment_seeds.yaml
 → choose backend: quantcrypt-cffi (default) | liboqs
 → warm-up 1,000 → trials 10,000 per (scheme, operation)
 → KEM: keygen / encaps / decaps  (ML-KEM-512/768/1024)
 → SIG: keygen / sign / verify    (ML-DSA-44/65/87, SLH-DSA, ECDSA, RSA)
 → summarize → emit Exp A table + Exp E ablation profiles
```

### 5.2 Protocol flows (runtime architecture)

| Flow | Process | Analysis |
|------|---------|----------|
| **F1 Hybrid certs** | Classical ECDSA + ML-DSA identities in X.509 | Cert ≈1 KB → ≈6.3 KB (~6.2×); IoMT needs MTU fragmentation / caching |
| **F2 Hybrid KEM** | ML-KEM-768 ∥ ECDHE → HKDF session key | HNDL-safe if ML-KEM holds; security = stronger component |
| **F3 Masking setup** | Pairwise seeds → modular masks sum to 0 | Lattice-compatible \(\mathbb{Z}_p\) arithmetic; masks cancel at aggregator |
| **F4 Sign + endorse** | ML-DSA-65 on FL update + Fabric endorsements | 3 endorsements ≈9.9 KB sig payload; sim +4% total latency |
| **F5 Revocation / agility** | DCRL on ledger + policy-driven algo swap | Architectural; not timed in current corpus |

### 5.3 Measured primitive cost (CFFI)

| Primitive | Op | Mean ms |
|-----------|-----|---------|
| ECDSA-P256 | sign / verify | 0.035 / 0.085 |
| ML-KEM-768 | encaps / decaps | 0.128 / 0.091 |
| ML-DSA-65 | sign / verify | 0.850 / 0.245 |
| SLH-DSA-256s | sign | 536.8 (long-term only) |

**Design choice:** Balanced profile ML-KEM-768 / ML-DSA-65 — Level 1 too thin vs 2042 trigger; Level 5 adds bytes/latency with diminishing return for clinical FL sessions.

### 5.4 Resource profiling (Exp F) vs micro-benchmarks

Exp F uses the **quantcrypt high-level API** (wrapper overhead): encaps ~3.7 ms, sign ~5.2 ms, peak RSS ~73–76 MB. Energy marked `---` without RAPL. Exp A remains the manuscript’s micro-benchmark truth.

---

## 6. Layer 3 — Federated learning process (step-by-step)

### 6.1 Experiment grid construction

`build_config_queue()` (deduplicated):

1. **B-2:** seeds × `{0.1,0.5,1.0}` × `{classical,hybrid_pq,native_pq}` @ 25 clients, FedAvg  
2. **B:** seeds × `{5,10,50}` clients × modes @ α=1.0 (skip 25 — already in B-2)  
3. **D baseline:** seeds × `{median,krum}` @ native PQ, no attack  
4. **D attacks:** label-flip {10%,20%} × aggregators; sign-flip 20% × Krum  

→ **270 configs** × 50 rounds × up to 50 clients (full scale).

### 6.2 Single-config round loop (`run_single`)

```
for round r = 1..50:
  for each client u:
    clone global CNN → train_local (5 epochs, Adam lr=0.001)
    optional: apply_attack (label_flip / sign_flip)
    apply_mask(params, u, N, r, modulus)     # pairwise SHA-256 seeds
  aggregate: fedavg | coordinate_median | krum
  set_parameters(global)
  wall_time += crypto_round_overhead(mode, N)  # modeled KEM+sig × N
  evaluate(val); record convergence if acc ≥ threshold
evaluate(test) → metrics row → checkpoint all_results.csv
```

### 6.3 Masking mathematics (security analysis)

\[
M_u = \sum_{v>u} S_{u,v} - \sum_{v<u} S_{v,u} \pmod p,\quad
\sum_u M_u = 0
\]

Coordinator sees \(\sum (W_u + M_u) = \sum W_u\). Predictive metrics must match across security modes (`assert_predictive_determinism`) because crypto is overhead-only in this prototype (masks cancel; no differential privacy noise).

### 6.4 Crypto overhead model (`security.crypto_round_overhead`)

Per client per round (seconds):

\[
T_{\mathrm{crypto}} = N \cdot \frac{t_{\mathrm{encaps}}+t_{\mathrm{decaps}}+t_{\mathrm{sign}}+t_{\mathrm{verify}}}{1000}
\]

| Mode | Payload model (B) | Primitive latencies |
|------|-------------------|---------------------|
| classical | 512 | ECDSA sign/verify |
| hybrid_pq / native_pq | 5581 | ML-KEM-768 + ML-DSA-65 (from Exp A means) |

### 6.5 Measured FL analysis (full corpus)

**IID-25 accuracy:** 65.34% ± 0.15 — identical for all modes.  
**AUROC:** 0.566.  
**Latency:** classical 19.06 s vs native 18.62 s (−2.3% at 25 clients; noise-dominated; **not significant** after Holm).  
**Client scaling:** accuracy peaks at 10 clients (77.8%), drops at 50 (45.4%) — data fragmentation / non-stationarity of partitions, not PQC.  
**Non-IID α∈{0.1,0.5,1.0}:** accuracy stable ~65.3–65.4% under 50 rounds — longer training mitigates earlier short-run skew effects seen at 20 rounds.  
**Byzantine:** FedAvg collapses under 10–20% label-flip (~37–41% acc); Median/Krum stay ~37.5% (often degenerate predictions) — robust aggregators need tuning; PQ overhead remains secondary.

---

## 7. Layer 4 — Blockchain process

### 7.1 Live Fabric topology

```
                 orderer.example.com:7050
                    │
     ┌──────────────┼──────────────┐
     ▼              ▼              ▼
 hospitalA:7051  hospitalB:9051  research:10051
     │
 couchdb-hospitala:5984
```

Crypto material: `cryptogen` + `configtxgen` (`OrdererGenesis` system channel) via `blockchain/scripts/generate_crypto.*`.

**Constraint analysis:** Fabric MSP remains ECDSA P-256; post-quantum authenticity for FL payloads is **application-layer** (chaincode ML-DSA-65 verify). This is an honest hybrid deployment boundary, not full native-PQ Fabric.

### 7.2 Calibrated transaction lifecycle (simulation)

```
load_pqc_latencies(results/pqc/summary.csv)
lifecycle_latency_ms(config):
  endorsement = 25 + crypto_verify×endorsers (+ hybrid extras)
  ordering    = 40   (network/consensus dominated)
  validation  = 15 + crypto_verify×endorsers
simulate_submission(N=100, jitter) → ledger_latency.tex
```

| Phase | Classical | Hybrid | Native PQ | Analysis |
|-------|-----------|--------|-----------|----------|
| Endorsement | 25.4 | 28.4 | 28.3 | Verify CPU + payload TX |
| Ordering | 40.2 | 40.2 | 40.2 | Unchanged (ordering not PQ-signed in model) |
| Validation | 15.3 | 16.0 | 15.7 | Small verify add-on |
| **Total** | **80.8** | **84.6** | **84.2** | **~4%** native overhead |

Dominant cost is **network/ordering**, not PQ crypto — supports deployability claim for permissioned clinical LAN.

### 7.3 Live metrics

`collect_metrics.py` → `docker_stats.json` (container CPU/RSS). Complements simulation; does not replace Table `tab:ledger_latency`.

---

## 8. Layer 5 — Migration decision process

```
L1: T* ≈ bootstrap lower bound (~2042)
L2: choose Level-3 PQC now
Mosca: migrate if X + Y ≥ Z
  X = migration time, Y = data secrecy lifetime, Z = years until break
MOSCoW roadmap: Must (hybrid TLS+ML-KEM), Should (ML-DSA identity),
  Could (SLH-DSA archive), Won't (full native Fabric MSP until ecosystem ready)
```

Analysis: with long-retention EHR (Y large) and T*≈2042, **hybrid start immediately** is the rational Must-have; native Fabric MSP waits on vendor support (Won't / later Could).

---

## 9. Statistical analysis process

```
all_results.csv
 → filter IID baseline (α=1.0, 25 clients, fedavg, attack=none)
 → pairwise modes for accuracy, f1, mean_round_latency_s
 → accuracy/f1: TOST with margins 0.01
 → latency: Shapiro on paired diffs → t-test or Wilcoxon
 → Holm–Bonferroni across tests
 → emit statistical_tests.tex (9 primary rows)
 → non-IID pairs → fl_statistical_tests_non_iid.csv (appendix)
```

**Result:** accuracy/f1 **equivalent**; latency **not significant**. Supports claim that PQ mode is utility-neutral and practically latency-neutral under this masking design.

---

## 10. Data/product flow into the manuscript

```
results_macros.tex ──► prose macros (\FLNumSeeds, \ForecastHoldoutMAE, …)
results/*/*.tex    ──► tables (Exp A–F, stats, forecast validation)
figures/output/*   ──► figures (PQC, FL, HLF, forecast, sensitivity)
figs/*             ──► static architecture / modality fallbacks
```

Emitter discipline: **never hand-type measured numbers** into `main.tex`; regenerate via pipeline.

---

## 11. Threat-to-process mapping (analysis)

| Threat | Layer / flow | Empirical validation |
|--------|--------------|----------------------|
| HNDL | L2 F2 ML-KEM hybrid | Exp A latencies; hybrid key schedule analysis in manuscript |
| Gradient leakage | L3 F3 masking | Determinism check across modes |
| Model poisoning | L3 Median/Krum | Exp D table (utility still fragile) |
| Auth / Sybil | L2 ML-DSA certs | Modeled in FL overhead + Fabric endorsements |
| Ledger integrity | L4 endorsements | Simulation + live peers Up |
| Migration timing | L1+L5 | Forecast validation + Mosca |

---

## 12. Limitations (architectural honesty)

1. FL crypto is **overhead-modeled** from Exp A means, not a live TLS/PQ stack per round.  
2. Fabric MSP is still ECDSA; PQ is payload-level.  
3. Resource energy requires Linux RAPL.  
4. Forecast MAPE is high — use lower-bound planning, not point year.  
5. Byzantine Median/Krum need further tuning for PneumoniaMNIST imbalance.  
6. Chaincode deploy deferred (Go toolchain).

---

## 13. Operator runbook (copy-paste)

```powershell
cd qrfl-artifacts
.\.venv\Scripts\Activate.ps1
.\run_all.ps1
# Optional Fabric:
cd blockchain; .\scripts\generate_crypto.ps1; docker compose up -d
..\ .venv\Scripts\python.exe -m blockchain.client.submit_transactions
..\ .venv\Scripts\python.exe blockchain\client\collect_metrics.py
```

After FL-only refresh:

```powershell
python scripts/finalize_fl_results.py
python -m statistical_tests.run_all
python -m figures.generate_all
```

---

*Companion documents:* `PHASE_RESULTS_REPORT.md` (numeric corpus), `README.md` (phase status), interactive canvas `QRFL-Phase-Results-Report.canvas.tsx`.
