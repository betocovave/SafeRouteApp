$ErrorActionPreference = 'Stop'
$appRoot = Split-Path $PSScriptRoot -Parent
$envPath = Join-Path $appRoot 'backend/.env'
if (-not (Test-Path -LiteralPath $envPath)) {
    $bytes = New-Object byte[] 32
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $generator.GetBytes($bytes)
    $generator.Dispose()
    $secret = [BitConverter]::ToString($bytes).Replace('-', '')
    $content = Get-Content -LiteralPath (Join-Path $appRoot 'backend/.env.example') -Raw
    $content = $content.Replace('REEMPLAZAR_POR_SECRETO_ALEATORIO_DE_AL_MENOS_32_CARACTERES', $secret)
    # Credencial publica exclusiva del emulador Azurite; nunca usar en Azure real.
    $connection = 'DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;'
    $content = $content.Replace('AZURE_BLOB_CONNECTION_STRING=', 'AZURE_BLOB_CONNECTION_STRING=' + $connection)
    Set-Content -LiteralPath $envPath -Value $content -Encoding utf8
}
Write-Host 'Configuracion lista. Coloca tu Azure Maps API KEY en app/backend/.env.'
Write-Host 'Desde app: docker compose -f infrastructure/compose.yaml up -d'
