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
docker compose up -d

# Generate full crypto material (production):
# cryptogen generate --config=network/crypto-config.yaml
# configtxgen -profile QRFL -outputBlock network/config/orderer.genesis.block

# Build and deploy chaincode
cd chaincode/flupdate && go mod tidy && go build

# Submit transactions
python client/submit_transactions.py --config ../configs/blockchain.yaml
python client/collect_metrics.py
```

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
