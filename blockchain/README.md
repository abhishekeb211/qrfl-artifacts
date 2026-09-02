# Hyperledger Fabric 3-Peer Testbed

## Architecture

| Peer | Role |
|------|------|
| `peer0.hospitala.example.com` | Hospital / Healthcare Organization A |
| `peer0.hospitalb.example.com` | Hospital / Healthcare Organization B |
| `peer0.research.example.com` | Research / Aggregation Node |

## PQC Integration Constraint

Hyperledger Fabric MSP identity uses **ECDSA P-256** and cannot be replaced with ML-DSA without forking Fabric. PQC protection is implemented at the **application/chaincode layer**:

- FL update payloads carry **ML-DSA-65** signatures
- Chaincode verifies signatures via `cloudflare/circl` (`blockchain/chaincode/flupdate/`)

This is an honest hybrid deployment model and should be described as such in the manuscript.

## Setup

```bash
cd blockchain

# 1. Generate crypto material and system-channel genesis block
./scripts/generate_crypto.sh          # Windows: .\scripts\generate_crypto.ps1

# 2. Start orderer, peers, and CouchDB
docker compose up -d

# 3. (Optional) Create application channel and join peers
./scripts/create_channel.sh

# 4. Build chaincode (requires Go 1.20+)
cd chaincode/flupdate && go mod tidy && go build

# 5. Submit calibrated simulation transactions + collect live Docker stats
python client/submit_transactions.py
python client/collect_metrics.py
```

The manuscript lives at `../main.tex` (sibling to this repo). Generated LaTeX tables are under `results/` and referenced via `\input{qrfl-artifacts/...}`.

## Measured Metrics

- Transaction latency (ms)
- Throughput (TPS)
- Block confirmation time
- Payload size increase
- CPU and memory (`docker stats`)
- Failure/retry behavior

## Configurations Compared

1. **Classical** — ECDSA-signed payloads, minimal overhead
2. **Hybrid** — ECDSA MSP + ML-DSA-65 application signatures
3. **Native PQ** — ML-DSA-65 application signatures (MSP remains ECDSA)

Results are written to `results/blockchain/`.
