# Privileged RAPL probe via abhi211b/qrfl-rapl (soft-fail NO_RAPL on Docker Desktop).
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsRemain
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Image = if ($env:QRFL_RAPL_IMAGE) { $env:QRFL_RAPL_IMAGE } else { "abhi211b/qrfl-rapl:latest" }
$ImageId = (docker inspect --format "{{.Id}}" $Image 2>$null)
if (-not $ImageId) { $ImageId = "" }

$results = Join-Path $Root "results"
New-Item -ItemType Directory -Force -Path (Join-Path $results "resource") | Out-Null

$dockerArgs = @(
    "run", "--rm", "--privileged",
    "-e", "QRFL_RAPL_IMAGE=$Image",
    "-e", "QRFL_RAPL_IMAGE_ID=$ImageId",
    "-v", "${results}:/app/results",
    $Image, "probe"
) + $ArgsRemain

& docker @dockerArgs
exit $LASTEXITCODE
