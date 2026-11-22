$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Push-Location $root

try {
    $venvPython = Join-Path $root ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $venvPython)) {
        if (Get-Command py -ErrorAction SilentlyContinue) {
            & py -3.12 -m venv .venv
        } else {
            & python -m venv .venv
        }
        if ($LASTEXITCODE -ne 0) { throw "Could not create the Python virtual environment." }
    }

    if (-not (Test-Path -LiteralPath (Join-Path $root ".env"))) {
        $secret = & $venvPython -c "import secrets; print(secrets.token_urlsafe(48))"
        if ($LASTEXITCODE -ne 0) { throw "Could not generate the application secret." }
        $envContent = @"
APP_ENV=development
SECRET_KEY=$($secret.Trim())
DATABASE_URL=sqlite:///./data/autotestreport.db
ACCESS_TOKEN_EXPIRE_MINUTES=30
"@
        [System.IO.File]::WriteAllText(
            (Join-Path $root ".env"),
            $envContent,
            [System.Text.UTF8Encoding]::new($false)
        )
    }

    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "Dependency installer update failed." }

    & $venvPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Project dependency installation failed." }

    New-Item -ItemType Directory -Path (Join-Path $root "data") -Force | Out-Null
    & $venvPython -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }

    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw "Node.js and npm are required for the React interface. Install the current Node.js LTS release and rerun setup."
    }

    Push-Location (Join-Path $root "frontend")
    try {
        & npm ci
        if ($LASTEXITCODE -ne 0) { throw "Frontend dependency installation failed." }

        & npm run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend production build failed." }
    } finally {
        Pop-Location
    }

    Write-Host "Setup complete. Start the application with .\run.ps1"
} finally {
    Pop-Location
}
