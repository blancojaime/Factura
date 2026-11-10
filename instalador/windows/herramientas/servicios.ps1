# Inicia, detiene o reinicia SICOM-MUNI.   Uso: servicios.ps1 -Accion iniciar|detener|reiniciar
param([ValidateSet('iniciar', 'detener', 'reiniciar')][string]$Accion = 'reiniciar', [switch]$Silencioso)
. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'comun.ps1')
Exigir-Administrador $MyInvocation.MyCommand.Path @('-Accion', $Accion)
try {
    switch ($Accion) {
        'detener'   { Stop-Service $SvcApp -Force -ErrorAction SilentlyContinue; Stop-Service $SvcBd -Force -ErrorAction SilentlyContinue }
        'iniciar'   { Start-Service $SvcBd -ErrorAction SilentlyContinue; Start-Service $SvcApp }
        'reiniciar' { Stop-Service $SvcApp -Force -ErrorAction SilentlyContinue; Restart-Service $SvcBd -Force; Start-Service $SvcApp }
    }
    Write-Host "Listo: $Accion"
    if (-not $Silencioso) { Start-Sleep -Seconds 2 }
}
catch { Write-Host ("ERROR: " + $_.Exception.Message); if (-not $Silencioso) { Read-Host 'Enter para cerrar' }; exit 1 }
