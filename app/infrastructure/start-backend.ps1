$ErrorActionPreference = 'Stop'
$appRoot = Split-Path $PSScriptRoot -Parent
$python = Join-Path $appRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Falta app/.venv. Sigue la instalacion de Python en app/README.md.'
}
$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$dockerPath = if ($dockerCommand) { $dockerCommand.Source } else { 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' }
if (-not (Test-Path -LiteralPath $dockerPath)) {
    throw 'Instala y abre Docker Desktop (contenedores Linux) para ejecutar PostgreSQL/PostGIS: https://www.docker.com/products/docker-desktop/'
}
& $dockerPath info --format '{{.ServerVersion}}'
if ($LASTEXITCODE -ne 0) { throw 'Abre Docker Desktop y espera a que el motor este listo.' }
Push-Location $appRoot
try {
    & (Join-Path $PSScriptRoot 'setup.ps1')
    & $dockerPath compose -f infrastructure/compose.yaml up -d --wait --wait-timeout 120
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron iniciar PostgreSQL/PostGIS y Azurite.' }
    & $python -m alembic -c backend/alembic.ini upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar la base de datos.' }
    & $python -m backend.cli seed
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron preparar las categorias.' }
    Write-Host 'Backend listo para iniciar. Deja esta terminal abierta y ejecuta npm.cmd start en frontend.'
    & $python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
    if ($LASTEXITCODE -ne 0) { throw 'La API no pudo ejecutarse. Revisa el error anterior.' }
} finally {
    Pop-Location
}
