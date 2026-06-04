param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPath = Join-Path $projectRoot ".venv"
$pythonExe = Join-Path $venvPath "Scripts\\python.exe"
$pipExe = Join-Path $venvPath "Scripts\\pip.exe"

Write-Host "Project root: $projectRoot"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python is not available on PATH. Install Python 3.13 or point PATH to a working interpreter first."
}

if (-not (Test-Path $pythonExe)) {
    Write-Host "Creating virtual environment..."
    python -m venv $venvPath
}

if (-not $SkipInstall) {
    Write-Host "Upgrading pip..."
    & $pythonExe -m pip install --upgrade pip

    Write-Host "Installing project dependencies..."
    & $pipExe install -r (Join-Path $projectRoot "requirements.txt")
}

Write-Host "Validating key imports..."
& $pythonExe -c "from airflow.providers.amazon.aws.hooks.s3 import S3Hook; import pyarrow; import pytest; print('Python environment is healthy.')"

Write-Host ""
Write-Host "Next checks:"
Write-Host "1. Start Docker Desktop."
Write-Host "2. Ensure the Docker daemon is running: docker ps"
Write-Host "3. Install the Astro CLI if it is missing."
Write-Host "4. Run: astro dev start"
