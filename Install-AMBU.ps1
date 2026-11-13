$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Get-Command sumo -ErrorAction SilentlyContinue)) {
    Write-Warning 'Install Eclipse SUMO and add its bin directory to PATH, or set SUMO_HOME before starting.'
}
Write-Host 'Ready. Run Start-AMBU.bat, then open http://127.0.0.1:8877.'
