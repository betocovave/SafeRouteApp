param([string]$ApiUrl = '')
$ErrorActionPreference = 'Stop'
$appRoot = Split-Path $PSScriptRoot -Parent
$container = $null
$previousApi = $env:EXPO_PUBLIC_API_URL

function Test-Backend([string]$Address) {
    $result = Invoke-RestMethod -Uri "$Address/ready" -TimeoutSec 10
    if ($result.database -ne 'ready') { throw 'La base de datos no esta lista.' }
}

Push-Location (Join-Path $appRoot 'frontend')
try {
    if ($ApiUrl) {
        $uri = [uri]$ApiUrl
        if ($uri.Scheme -ne 'https' -or $uri.AbsolutePath -ne '/' -or $uri.Query -or $uri.Fragment -or $uri.UserInfo) {
            throw 'ApiUrl debe ser una URL base HTTPS, sin /api/v1 ni credenciales.'
        }
        $ApiUrl = $ApiUrl.TrimEnd('/')
        Test-Backend $ApiUrl
    } else {
        try { Test-Backend 'http://127.0.0.1:8000' }
        catch { throw 'Inicia Docker Desktop y ejecuta infrastructure/start-backend.ps1 en otra terminal. Espera a Uvicorn running y vuelve a intentar.' }
        $docker = (Get-Command docker -ErrorAction Stop).Source
        & $docker info --format '{{.ServerVersion}}'
        if ($LASTEXITCODE -ne 0) { throw 'Abre Docker Desktop.' }
        $container = 'saferoute-mobile-' + [guid]::NewGuid().ToString('N').Substring(0,8)
        Write-Host 'Preparando tunel HTTPS temporal para la API. La primera vez descarga cloudflared.'
        & $docker run --detach --rm --name $container cloudflare/cloudflared:latest tunnel --no-autoupdate --protocol http2 --url http://host.docker.internal:8000
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo iniciar el tunel de la API.' }
        $deadline = (Get-Date).AddSeconds(90)
        do {
            Start-Sleep -Seconds 2
            # Windows PowerShell 5 treats native stderr as ErrorRecord; cloudflared logs there.
            $ErrorActionPreference = 'Continue'
            try { $logs = (& $docker logs $container 2>&1 | Out-String) }
            finally { $ErrorActionPreference = 'Stop' }
            if ($logs -match 'https://[a-z0-9-]+\.trycloudflare\.com') { $ApiUrl = $Matches[0]; break }
        } while ((Get-Date) -lt $deadline)
        if (-not $ApiUrl) { throw 'Cloudflare no pudo crear el tunel. Revisa la conexion a internet de la computadora.' }
        $reachable = $false
        for ($attempt=0; $attempt -lt 8; $attempt++) {
            try { Test-Backend $ApiUrl; $reachable = $true; break }
            catch { Start-Sleep -Seconds 2 }
        }
        if (-not $reachable) { throw 'El tunel existe pero la API no responde. Confirma que el backend escucha en 0.0.0.0:8000.' }
    }
    $env:EXPO_PUBLIC_API_URL = $ApiUrl
    Write-Host "Backend verificado: $ApiUrl"
    Write-Host 'Iniciando Expo Go por internet. Escanea el nuevo QR; puedes usar datos moviles.'
    Write-Host 'Deja abiertas esta terminal y la del backend. Ctrl+C cierra Expo y este tunel.'
    & npm.cmd run start:internet -- --clear
    if ($LASTEXITCODE -ne 0) { throw 'Expo no pudo iniciar. Ejecuta npm.cmd install en app/frontend y revisa el mensaje anterior.' }
} finally {
    $env:EXPO_PUBLIC_API_URL = $previousApi
    if ($container) { & $docker stop $container | Out-Null }
    Pop-Location
}
