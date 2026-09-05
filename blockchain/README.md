# Hyperledger Fabric Testbed (QRFL)

## Recommended live path (etcdraft)

Custom Solo compose on Docker Desktop failed to cut `_lifecycle` blocks. Use **Fabric samples test-network**:

```powershell
# Requires C:\fabric-samples (Fabric 2.5 binaries + test-network) and Docker Desktop
powershell -ExecutionPolicy Bypass -File scripts/up_testnetwork.ps1
powershell -ExecutionPolicy Bypass -File scripts/deploy_testnetwork_flupdate.ps1
```

See `FABRIC_CHAINCODE_BLOCKER.md` for Solo failure history and etcdraft resolution.

## Architecture (application PQC)

| Component | Role |
|-----------|------|
| Fabric MSP | ECDSA P-256 (unchanged) |
| Chaincode `flupdate` | ML-DSA-65 verify of FL update payloads (`cloudflare/circl`) |

This is an honest hybrid deployment model.

## Calibrated simulation

```bash
python client/submit_transactions.py
python client/collect_metrics.py
```

Results: `results/blockchain/` (`ledger_latency.tex`, `live_testbed.tex`).
