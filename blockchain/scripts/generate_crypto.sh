#!/usr/bin/env bash
# Generate Fabric crypto material and genesis block via fabric-tools container.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

NETWORK_DIR="$ROOT/network"
CONFIG_DIR="$NETWORK_DIR/config"
CRYPTO_DIR="$NETWORK_DIR/crypto-config"

echo "=== QRFL Fabric crypto generation ==="

docker run --rm \
  -v "$NETWORK_DIR:/work" \
  -w /work \
  hyperledger/fabric-tools:2.5 \
  bash -c '
    set -e
    rm -rf crypto-config
    cryptogen generate --config=crypto-config.yaml --output="crypto-config"
    export FABRIC_CFG_PATH=/work
    configtxgen -profile OrdererGenesis -channelID system-channel -outputBlock config/orderer.genesis.block
    configtxgen -profile QRFL -outputCreateChannelTx config/channel.tx -channelID qrflchannel
    configtxgen -profile QRFL -outputAnchorPeersUpdate config/HospitalAMSPanchors.tx -channelID qrflchannel -asOrg HospitalAMSP
    configtxgen -profile QRFL -outputAnchorPeersUpdate config/HospitalBMSPanchors.tx -channelID qrflchannel -asOrg HospitalBMSP
    configtxgen -profile QRFL -outputAnchorPeersUpdate config/ResearchMSPanchors.tx -channelID qrflchannel -asOrg ResearchMSP
  '

echo "Generated:"
echo "  $CRYPTO_DIR/"
echo "  $CONFIG_DIR/orderer.genesis.block"
echo "  $CONFIG_DIR/channel.tx"
