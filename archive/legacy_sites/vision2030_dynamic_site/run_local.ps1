$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$venvPython = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (Test-Path $venvPython) { & $venvPython ".\run_vision2030.py" } else { & python ".\run_vision2030.py" }
