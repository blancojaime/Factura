# Pruebas automáticas (CI) de un SICOM-MUNI instalado en Windows: servicios, firewall, respaldo, punta a punta y reinicio.
param(
    [string]$Instalacion = "$env:ProgramFiles\SICOM-MUNI",
    [int]$Puerto = 8090,
    [string]$Admin = 'admin',
    [Parameter(Mandatory = $true)][string]$Clave,
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Continue'
$fallos = 0
function Comprobar([bool]$ok, [string]$msg) {
    if ($ok) { Write-Host "  OK     $msg" } else { Write-Host "  FALLO  $msg" -ForegroundColor Red; $script:fallos++ }
}
$datos = Join-Path $env:ProgramData 'SICOM-MUNI'
$url = "http://127.0.0.1:$Puerto"

Write-Host "`n== Servicios, red y tareas =="
Comprobar ((Get-Service SICOM-MUNI-BD).Status -eq 'Running') 'Servicio de base de datos SICOM-MUNI-BD en ejecución'
Comprobar ((Get-Service SICOM-MUNI).Status -eq 'Running') 'Servicio SICOM-MUNI en ejecución'
Comprobar ((Get-Service SICOM-MUNI-BD).StartType -eq 'Automatic' -and (Get-Service SICOM-MUNI).StartType -eq 'Automatic') 'Ambos servicios arrancan automáticamente con Windows'
Comprobar ($null -ne (Get-NetFirewallRule -DisplayName 'SICOM-MUNI*' -ErrorAction SilentlyContinue)) 'Regla de firewall creada'
Comprobar ($null -ne (Get-ScheduledTask -TaskName 'SICOM-MUNI Respaldo diario' -ErrorAction SilentlyContinue)) 'Tarea de respaldo diario programada'
$escucha = Get-NetTCPConnection -LocalPort $Puerto -State Listen -ErrorAction SilentlyContinue
Comprobar ($null -ne $escucha) "El sistema escucha en el puerto $Puerto"
Comprobar (-not (Get-NetTCPConnection -LocalPort 54329 -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalAddress -ne '127.0.0.1' })) 'PostgreSQL solo escucha en 127.0.0.1 (no expuesto a la red)'
Comprobar ((Get-Content -Raw (Join-Path $datos 'config\resultado.txt')) -match 'http://') 'Se generó el resumen de direcciones'
Comprobar (-not (Test-Path (Join-Path $Instalacion 'INSTALACION-INCOMPLETA.txt'))) 'La instalación no dejó marca de error'

Write-Host "`n== Prueba de punta a punta (API, PDF con QR, verificación, auditoría) =="
& $Python (Join-Path $PSScriptRoot 'prueba_e2e.py') $url $Admin $Clave
Comprobar ($LASTEXITCODE -eq 0) 'Prueba de punta a punta superada'

Write-Host "`n== Respaldo =="
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Instalacion 'herramientas\respaldar.ps1') -Silencioso
Comprobar ($LASTEXITCODE -eq 0) 'respaldar.ps1 terminó sin errores'
$dump = Get-ChildItem (Join-Path $datos 'respaldos') -Filter 'sicom_*.dump' -ErrorAction SilentlyContinue | Select-Object -First 1
Comprobar ($null -ne $dump -and $dump.Length -gt 10000) 'Se creó el archivo de respaldo de la base de datos'
if ($dump) {
    $lista = & (Join-Path $Instalacion 'pgsql\bin\pg_restore.exe') -l $dump.FullName 2>&1
    Comprobar ($LASTEXITCODE -eq 0 -and ($lista | Out-String) -match 'contrataciones_menores') 'El respaldo es legible y contiene las tablas del sistema'
}

Write-Host "`n== Reinicio de servicios =="
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Instalacion 'herramientas\servicios.ps1') -Accion detener -Silencioso
Comprobar ((Get-Service SICOM-MUNI).Status -eq 'Stopped') 'Los servicios se detienen'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Instalacion 'herramientas\servicios.ps1') -Accion iniciar -Silencioso
$ok = $false
for ($i = 0; $i -lt 40 -and -not $ok; $i++) { try { $ok = (Invoke-WebRequest -UseBasicParsing -Uri "$url/api/v1/salud" -TimeoutSec 5).StatusCode -eq 200 } catch { Start-Sleep -Seconds 2 } }
Comprobar $ok 'El sistema vuelve a responder tras reiniciar los servicios'
$persistencia = @'
import json, sys, urllib.request
url, usuario, clave = sys.argv[1:4]
def llamar(ruta, datos=None, token=None):
    req = urllib.request.Request(url + ruta, data=json.dumps(datos).encode() if datos else None, method='POST' if datos else 'GET')
    req.add_header('Content-Type', 'application/json')
    if token: req.add_header('Authorization', 'Bearer ' + token)
    return json.loads(urllib.request.urlopen(req, timeout=30).read())
t = llamar('/api/v1/auth/login', {'username': usuario, 'password': clave})['access_token']
filas = llamar('/api/v1/contrataciones', token=t)
sys.exit(0 if len(filas) >= 1 else 1)
'@
$archivoPersistencia = Join-Path $env:TEMP 'sicom_persistencia.py'
Set-Content -Path $archivoPersistencia -Value $persistencia -Encoding UTF8
& $Python $archivoPersistencia $url $Admin $Clave
Comprobar ($LASTEXITCODE -eq 0) 'Los datos creados antes del reinicio siguen en la base de datos'


Write-Host ("`nResultado: " + $(if ($fallos -eq 0) { 'TODO CORRECTO' } else { "$fallos comprobaciones fallaron" }))
exit $(if ($fallos -eq 0) { 0 } else { 1 })
