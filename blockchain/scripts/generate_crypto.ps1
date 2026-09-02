# Generate Fabric crypto material and genesis block (Windows wrapper)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
$NetworkDir = Join-Path $Root "network"

Write-Host "=== QRFL Fabric crypto generation ==="

docker run --rm `
  -v "${NetworkDir}:/work" `
  -w /work `
  hyperledger/fabric-tools:2.5 `
  bash -c @"
set -e
rm -rf crypto-config
cryptogen generate --config=crypto-config.yaml --output=crypto-config
export FABRIC_CFG_PATH=/work
configtxgen -profile OrdererGenesis -channelID system-channel -outputBlock config/orderer.genesis.block
configtxgen -profile QRFL -outputCreateChannelTx config/channel.tx -channelID qrflchannel
configtxgen -profile QRFL -outputAnchorPeersUpdate config/HospitalAMSPanchors.tx -channelID qrflchannel -asOrg HospitalAMSP
configtxgen -profile QRFL -outputAnchorPeersUpdate config/HospitalBMSPanchors.tx -channelID qrflchannel -asOrg HospitalBMSP
configtxgen -profile QRFL -outputAnchorPeersUpdate config/ResearchMSPanchors.tx -channelID qrflchannel -asOrg ResearchMSP
"@

Write-Host "Done. Crypto: $NetworkDir\crypto-config"
Write-Host "Genesis: $NetworkDir\config\orderer.genesis.block"
