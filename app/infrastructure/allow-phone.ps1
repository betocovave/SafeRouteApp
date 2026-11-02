param(
    [Parameter(Mandatory = $true)][System.Net.IPAddress]$PhoneAddress,
    [Parameter(Mandatory = $true)][System.Net.IPAddress]$ComputerAddress,
    [string]$InterfaceAlias = 'Wi-Fi'
)
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Abre PowerShell con Ejecutar como administrador para ajustar el firewall.'
}
$listener = Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $listener) {
    throw 'La API de Python no esta encendida en el puerto 8000. Abre Docker Desktop, ejecuta infrastructure/start-backend.ps1 desde app y espera a ver Uvicorn running. Deja esa terminal abierta y vuelve a ejecutar este comando.'
}
$apiProcess = Get-Process -Id $listener.OwningProcess
if ($apiProcess.ProcessName -notlike 'python*') { throw 'El puerto 8000 no pertenece a Python.' }
$pythonPath = $apiProcess.Path
$ruleName = 'SafeRouteAI-Phone-8000'
$existing = Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue
if ($existing) {
    Set-NetFirewallRule -Name $ruleName -Enabled True -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 -LocalAddress $ComputerAddress.IPAddressToString -RemoteAddress $PhoneAddress.IPAddressToString -Program $pythonPath -InterfaceAlias $InterfaceAlias -Profile Public,Private
} else {
    New-NetFirewallRule -Name $ruleName -DisplayName 'SafeRouteAI API desde telefono Expo' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 -LocalAddress $ComputerAddress.IPAddressToString -RemoteAddress $PhoneAddress.IPAddressToString -Program $pythonPath -InterfaceAlias $InterfaceAlias -Profile Public,Private | Out-Null
}
# Windows-generated deny rules override allows. Keep the deny on every other
# TCP port; the scoped allow above opens 8000 only for the specified phone.
Get-NetFirewallRule -Enabled True -Direction Inbound -Action Block | ForEach-Object {
    $rule = $_
    $application = $rule | Get-NetFirewallApplicationFilter
    $ports = $rule | Get-NetFirewallPortFilter
    if ($application.Program -eq $pythonPath -and $ports.Protocol -eq 'TCP' -and $ports.LocalPort -eq 'Any') {
        Set-NetFirewallRule -Name $rule.Name -LocalPort '1-7999','8001-65535'
    }
}
Write-Host 'Listo. Vuelve a Expo Go e intenta crear tu cuenta. No necesitas reiniciar Docker.'
