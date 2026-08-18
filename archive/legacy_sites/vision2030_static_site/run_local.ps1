$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "Python was not found on PATH." -ForegroundColor Red
    exit 1
}

& $python.Source ".\start_server.py"
