# Initialize git repository for qrfl-artifacts (requires Git for Windows or MinGit on PATH)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $Root

$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    Write-Error @"
Git is not installed. Install from https://git-scm.com/download/win
or add MinGit to PATH, then re-run: .\scripts\init_git.ps1
"@
}

if (-not (Test-Path ".git")) {
    git init
    git branch -M main
}

git add .
git status
Write-Host ""
Write-Host "Review staged files, then commit with:"
Write-Host '  git commit -m "Phase 0-1: PQC benchmarks, FL pipeline, manuscript wiring"'
