$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (Test-Path $py) { & $py ".\run_vision2030.py" } else { & python ".\run_vision2030.py" }
