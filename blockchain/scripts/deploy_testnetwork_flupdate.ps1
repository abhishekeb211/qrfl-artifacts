# Package/install/approve/commit flupdate on running Fabric test-network (etcdraft).
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
if (-not (Test-Path $FlupdateCopy)) {
  Copy-Item -Recurse $CCSrc $FlupdateCopy
}

# Ensure vendor
if (-not (Test-Path (Join-Path $FlupdateCopy "vendor"))) {
  docker run --rm -e GOTOOLCHAIN=local -v C:/flupdate-cc:/src -w /src golang:1.25 go mod vendor
}

Set-Location (Join-Path $FabricSamples "test-network")
peer lifecycle chaincode package flupdate.tar.gz --path $FlupdateCopy --lang golang --label flupdate_1.0

$script = "C:\fabric-dl\commit4.sh"
if (-not (Test-Path $script)) {
  throw "Missing $script — run from prior deploy or recreate commit helper"
}
bash $script

$marker = Join-Path $Root "network\.chaincode_deployed"
@"
status=deployed
network=fabric-samples-test-network-etcdraft
channel=$Channel
cc=flupdate
"@ | Set-Content $marker -Encoding utf8
Write-Host "Wrote $marker"
