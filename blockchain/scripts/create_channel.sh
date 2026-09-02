#!/usr/bin/env bash
# Create qrflchannel and join all peers (run after docker compose up).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NETWORK="$ROOT/network"
CHANNEL=qrflchannel

run_peer() {
  local peer_name=$1
  local msp=$2
  local addr=$3
  shift 3
  docker run --rm --network qrfl-net \
    -v "$NETWORK/crypto-config/peerOrganizations/${peer_name%.*}.$(echo $peer_name | cut -d. -f2-)/users/Admin@${peer_name#peer0.}/msp:/etc/hyperledger/fabric/msp" \
    -v "$NETWORK/core.yaml:/etc/hyperledger/fabric/core.yaml" \
    -e FABRIC_CFG_PATH=/etc/hyperledger/fabric \
    -e CORE_PEER_LOCALMSPID="$msp" \
    -e CORE_PEER_ADDRESS="$addr" \
    -e CORE_PEER_TLS_ENABLED=false \
    hyperledger/fabric-tools:2.5 peer "$@"
}

echo "Creating channel $CHANNEL..."
docker run --rm --network qrfl-net \
  -v "$NETWORK:/work" -w /work \
  -e FABRIC_CFG_PATH=/work \
  hyperledger/fabric-tools:2.5 \
  peer channel create -o orderer.example.com:7050 -c "$CHANNEL" -f config/channel.tx

echo "Joining peers..."
for spec in "hospitala.example.com:HospitalAMSP:peer0.hospitala.example.com:7051" \
            "hospitalb.example.com:HospitalBMSP:peer0.hospitalb.example.com:9051" \
            "research.example.com:ResearchMSP:peer0.research.example.com:10051"; do
  IFS=: read -r domain msp peer port <<< "$spec"
  echo "  $peer"
  docker run --rm --network qrfl-net \
    -v "$NETWORK/crypto-config/peerOrganizations/$domain/peers/$peer:/etc/hyperledger/peer" \
    -v "$NETWORK/core.yaml:/etc/hyperledger/fabric/core.yaml" \
    -e FABRIC_CFG_PATH=/etc/hyperledger/fabric \
    -e CORE_PEER_LOCALMSPID="$msp" \
    -e CORE_PEER_ADDRESS="$peer:$port" \
    -e CORE_PEER_MSPCONFIGPATH=/etc/hyperledger/peer/msp \
    -e CORE_PEER_TLS_ENABLED=false \
    hyperledger/fabric-tools:2.5 \
    peer channel join -b "${CHANNEL}.block" || true
done

echo "Channel setup complete."
