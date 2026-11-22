$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$venvPython = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Virtual environment not found. Run .\setup.ps1 first."
}
if (-not (Test-Path -LiteralPath (Join-Path $root ".env"))) {
    throw ".env not found. Run .\setup.ps1 first."
}
if (-not (Test-Path -LiteralPath (Join-Path $root "frontend\dist\index.html"))) {
    throw "Frontend build not found. Run .\setup.ps1 first."
}

Push-Location $root
try {
    Write-Host "Open the AutoTestReport Hub panel at http://127.0.0.1:8000"
    & $venvPython -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
    if ($LASTEXITCODE -ne 0) { throw "The API server stopped with an error." }
} finally {
    Pop-Location
}
