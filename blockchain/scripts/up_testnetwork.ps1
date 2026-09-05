# Bring up Hyperledger Fabric test-network (etcdraft) and deploy flupdate.
# Requires: Docker Desktop, Git Bash, binaries in C:\fabric-samples (or set FABRIC_SAMPLES).
param(
  [string]$FabricSamples = "C:\fabric-samples",
  [string]$Channel = "qrflchannel"
)

$ErrorActionPreference = "Stop"
$env:Path = "$FabricSamples\bin;C:\Program Files\Git\cmd;C:\Program Files\Git\bin;C:\go\bin;" + $env:Path
$env:FABRIC_CFG_PATH = "$FabricSamples\config"
$env:DOCKER_SOCK = "/var/run/docker.sock"

$Root = Split-Path -Parent $PSScriptRoot
$CCSrc = Join-Path $Root "chaincode\flupdate"
$FlupdateCopy = "C:\flupdate-cc"
if (Test-Path $FlupdateCopy) { Remove-Item -Recurse -Force $FlupdateCopy }
Copy-Item -Recurse $CCSrc $FlupdateCopy

$up = @"
#!/usr/bin/env bash
set -eo pipefail
export PATH="$($FabricSamples -replace '\\','/')/bin:`$PATH"
export FABRIC_CFG_PATH="$($FabricSamples -replace '\\','/')/config"
export DOCKER_SOCK=/var/run/docker.sock
cd $($FabricSamples -replace '\\','/')/test-network
./network.sh down || true
./network.sh up createChannel -c $Channel -ca
"@
$upPath = "C:\fabric-dl\qrfl-tn-up.sh"
[IO.File]::WriteAllText($upPath, ($up -replace "`r`n","`n"))
bash $upPath
Write-Host "Network up. Deploy with: .\scripts\deploy_testnetwork_flupdate.ps1"
