# Prueba (CI) de permisos de la base de datos y de recuperación tras un corte brusco.
# Reproduce el fallo visto en un equipo real: PANIC "could not open file pg_logical/replorigin_checkpoint.tmp: Permission denied".
param(
    [string]$Instalacion = "$env:ProgramFiles\SICOM-MUNI",
    [int]$Puerto = 8090
)
$ErrorActionPreference = 'Continue'
$fallos = 0
function Comprobar([bool]$ok, [string]$msg) {
    if ($ok) { Write-Host "  OK     $msg" } else { Write-Host "  FALLO  $msg" -ForegroundColor Red; $script:fallos++ }
}
$datos = Join-Path $env:ProgramData 'SICOM-MUNI'
$bin = Join-Path $Instalacion 'pgsql\bin'

function Pg-Listo([int]$intentos = 60) {
    for ($i = 0; $i -lt $intentos; $i++) {
        & (Join-Path $bin 'pg_isready.exe') -h 127.0.0.1 -p 54329 *> $null
        if ($LASTEXITCODE -eq 0) { return $true }
        Start-Sleep -Seconds 2
    }
    return $false
}

Write-Host "`n== Permisos heredables en la base de datos y recuperación tras un corte =="
foreach ($sub in 'pg_logical', 'pg_wal', 'base', 'global') {
    $ruta = Join-Path $datos "pgdata\$sub"
    $ns = (Get-Acl $ruta).Access | Where-Object {
        try { $_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -eq 'S-1-5-20' } catch { $false } }
    $bien = $ns | Where-Object { $_.IsInherited -and ($_.InheritanceFlags -match 'ObjectInherit') -and ($_.FileSystemRights -match 'FullControl') }
    Comprobar ($null -ne $bien) "pgdata\$sub transmite el permiso de NetworkService a los archivos nuevos"
}

# Corte brusco: se mata PostgreSQL sin dejar que cierre limpiamente (obliga a una recuperación al volver a arrancar)
Stop-Service SICOM-MUNI -Force -ErrorAction SilentlyContinue
Get-Process postgres -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 6
for ($i = 0; $i -lt 10; $i++) {
    try { Start-Service SICOM-MUNI-BD -ErrorAction Stop; break } catch { Start-Sleep -Seconds 5 }
}
Comprobar (Pg-Listo 90) 'PostgreSQL arranca y se recupera solo después de un corte brusco'
$panic = Get-ChildItem (Join-Path $datos 'pgdata\log') -Filter *.log -ErrorAction SilentlyContinue | Select-String -Pattern 'PANIC' -SimpleMatch
if ($panic) { $panic | Select-Object -First 5 | ForEach-Object { Write-Host "    $($_.Line)" } }
Comprobar (-not $panic) 'El registro de PostgreSQL no contiene PANIC'
try { Start-Service SICOM-MUNI -ErrorAction Stop } catch { }
$ok = $false
for ($i = 0; $i -lt 60 -and -not $ok; $i++) { try { $ok = (Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Puerto/api/v1/salud" -TimeoutSec 5).StatusCode -eq 200 } catch { Start-Sleep -Seconds 3 } }
Comprobar $ok 'El sistema vuelve a responder tras la recuperación'

Write-Host ("`nResultado: " + $(if ($fallos -eq 0) { 'TODO CORRECTO' } else { "$fallos comprobaciones fallaron" }))
exit $(if ($fallos -eq 0) { 0 } else { 1 })
