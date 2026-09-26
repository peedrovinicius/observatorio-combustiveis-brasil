param(
    [switch]$WithPostgres,
    [switch]$Snapshot
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Step "Criando ambiente virtual"
    python -m venv .venv
}

Write-Step "Instalando dependências"
& $python -m pip install -r requirements.txt

Write-Step "Executando testes"
& $python -m pytest

Write-Step "Executando pipeline completo"
& $python -m src.pipeline

if ($WithPostgres) {
    Write-Step "Iniciando PostgreSQL"
    docker compose up -d postgres

    Write-Step "Carregando PostgreSQL"
    & $python -m src.load_postgres
}

if ($Snapshot) {
    Write-Step "Gerando snapshot versionável"
    & $python -m src.snapshot
}

Write-Step "Concluído"
Write-Host "Revise os arquivos gerados antes de qualquer commit."
