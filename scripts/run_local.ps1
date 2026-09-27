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

function Invoke-NativeChecked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [Parameter(Mandatory = $true)]
        [string]$Description
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw (
            "$Description falhou com código de saída " +
            "$LASTEXITCODE."
        )
    }
}

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Step "Criando ambiente virtual"
    Invoke-NativeChecked -FilePath "python" -Arguments @("-m", "venv", ".venv") -Description "Criação do ambiente virtual"
}

Write-Step "Instalando dependências"
Invoke-NativeChecked -FilePath $python -Arguments @("-m", "pip", "install", "-r", "requirements.txt") -Description "Instalação das dependências"

Write-Step "Executando testes"
Invoke-NativeChecked -FilePath $python -Arguments @("-m", "pytest") -Description "Execução dos testes"

Write-Step "Executando pipeline completo"
Invoke-NativeChecked -FilePath $python -Arguments @("-m", "src.pipeline") -Description "Execução do pipeline"

if ($WithPostgres) {
    Write-Step "Iniciando PostgreSQL"
    Invoke-NativeChecked -FilePath "docker" -Arguments @("compose", "up", "-d", "postgres") -Description "Inicialização do PostgreSQL"

    Write-Step "Carregando PostgreSQL"
    Invoke-NativeChecked -FilePath $python -Arguments @("-m", "src.load_postgres") -Description "Carga do PostgreSQL"
}

if ($Snapshot) {
    Write-Step "Gerando snapshot versionável"
    Invoke-NativeChecked -FilePath $python -Arguments @("-m", "src.snapshot") -Description "Geração do snapshot"
}

Write-Step "Concluído"
Write-Host "Revise os arquivos gerados antes de qualquer commit."
