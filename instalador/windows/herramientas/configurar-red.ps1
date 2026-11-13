# Cambia el puerto o la dirección con la que se publica el sistema en la red local (y en los códigos QR).
param([string]$Direccion = '', [int]$Puerto = 0, [switch]$Silencioso)
. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'comun.ps1')
Exigir-Administrador $MyInvocation.MyCommand.Path ($(if ($Direccion) { @('-Direccion', $Direccion) } else { @() }) + $(if ($Puerto) { @('-Puerto', $Puerto) } else { @() }))
try {
    $e = Leer-Env
    $puertoActual = [int]$e['SERVIDOR_PUERTO']
    $ipActual = Ip-Local
    if (-not $Silencioso) {
        Write-Host "Configuración actual:  $($e['PUBLIC_BASE_URL'])`nIP detectada de este equipo:  $ipActual`n"
        if (-not $Direccion) { $Direccion = Read-Host "Dirección (IP o nombre) para los usuarios [Enter = $ipActual]" }
        if (-not $Puerto) { $p = Read-Host "Puerto [Enter = $puertoActual]"; if ($p) { $Puerto = [int]$p } }
    }
    if (-not $Direccion) { $Direccion = $ipActual }
    if (-not $Puerto) { $Puerto = $puertoActual }
    $url = "http://{0}:{1}" -f $Direccion, $Puerto
    $ruta = Join-Path $ConfigDir '.env'
    $lineas = Get-Content $ruta -Encoding UTF8 | ForEach-Object {
        if ($_ -match '^PUBLIC_BASE_URL=') { "PUBLIC_BASE_URL=$url" } elseif ($_ -match '^SERVIDOR_PUERTO=') { "SERVIDOR_PUERTO=$Puerto" } else { $_ }
    }
    Set-Content -Path $ruta -Value $lineas -Encoding UTF8
    Get-NetFirewallRule -DisplayName 'SICOM-MUNI*' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    New-NetFirewallRule -DisplayName "SICOM-MUNI (puerto $Puerto)" -Direction Inbound -Protocol TCP -LocalPort $Puerto -Action Allow -Profile Any -RemoteAddress LocalSubnet | Out-Null
    Restart-Service -Name $SvcApp -Force
    Set-Content -Path (Join-Path $ConfigDir 'puerto.txt') -Value $Puerto -Encoding ASCII
    Escribir-Log "Red reconfigurada: $url" 'herramientas.log'
    if (-not $Silencioso) { Write-Host "`nListo. Los usuarios deben entrar a:  $url/`nLos códigos QR de los documentos NUEVOS usarán esta dirección."; Read-Host 'Presione Enter para cerrar' }
}
catch { Escribir-Log ("ERROR: " + $_.Exception.Message); if (-not $Silencioso) { Read-Host 'Error. Enter para cerrar' }; exit 1 }
