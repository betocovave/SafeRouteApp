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
    & $dockerPath compose -f infrastructure/compose.yaml up -d --wait --wait-timeout 120 postgres
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo iniciar PostgreSQL/PostGIS.' }
    # Base aparte de la de desarrollo: las pruebas recrean su esquema.
    $exists = & $dockerPath compose -f infrastructure/compose.yaml exec -T postgres psql -U saferoute -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='saferoute_test'"
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo consultar PostgreSQL.' }
    if (-not $exists) {
        & $dockerPath compose -f infrastructure/compose.yaml exec -T postgres psql -U saferoute -d postgres -c 'CREATE DATABASE saferoute_test'
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear la base saferoute_test.' }
    }
    $password = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { 'saferoute' }
    $env:TEST_DATABASE_URL = "postgresql+psycopg://saferoute:$password@127.0.0.1:5432/saferoute_test"
    & $python -m pytest backend/tests/test_postgis_integration.py -q
    if ($LASTEXITCODE -ne 0) { throw 'Fallaron las pruebas de PostGIS.' }
} finally {
    Pop-Location
}
