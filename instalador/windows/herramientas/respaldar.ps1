# Respaldo de SICOM-MUNI: base de datos (pg_dump) + archivos PDF. Conserva los últimos 14 respaldos.
param([switch]$Silencioso)
. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'comun.ps1')
if (-not $Silencioso) { Exigir-Administrador $MyInvocation.MyCommand.Path }
$LogFile = 'respaldo.log'
try {
    $bd = Datos-Bd
    $dest = Join-Path $DataDir 'respaldos'
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    $sello = Get-Date -Format 'yyyyMMdd_HHmm'
    $dump = Join-Path $dest "sicom_$sello.dump"
    $env:PGPASSWORD = $bd.Clave
    $x = Invocar-Nativo (Join-Path $InstallDir 'pgsql\bin\pg_dump.exe') @('-h', $bd.Host, '-p', $bd.Puerto, '-U', $bd.Usuario, '-d', $bd.Base, '-Fc', '-f', $dump)
    if ($x.Codigo -ne 0) { throw "pg_dump falló (código $($x.Codigo)): $($x.Salida)" }
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    $zip = Join-Path $dest "archivos_$sello.zip"
    $origen = Join-Path $DataDir 'archivos'
    if (Get-ChildItem -Path $origen -Recurse -File -ErrorAction SilentlyContinue | Select-Object -First 1) {
        Compress-Archive -Path (Join-Path $origen '*') -DestinationPath $zip -Force
    }
    # copia adicional (USB, disco o carpeta de red) si el administrador la configuró
    $extra = Join-Path $ConfigDir 'respaldo_destino.txt'
    if (Test-Path $extra) {
        $d2 = (Get-Content $extra -Raw).Trim()
        if ($d2 -and (Test-Path $d2)) { Copy-Item $dump, $zip -Destination $d2 -Force -ErrorAction SilentlyContinue }
    }
    Get-ChildItem $dest -Filter 'sicom_*.dump' | Sort-Object LastWriteTime -Descending | Select-Object -Skip 14 | Remove-Item -Force
    Get-ChildItem $dest -Filter 'archivos_*.zip' | Sort-Object LastWriteTime -Descending | Select-Object -Skip 14 | Remove-Item -Force
    Escribir-Log "Respaldo creado: $dump" $LogFile
    if (-not $Silencioso) { Write-Host "`nRespaldo terminado en: $dest"; Read-Host 'Presione Enter para cerrar' }
    exit 0
}
catch {
    Escribir-Log ("ERROR de respaldo: " + $_.Exception.Message) $LogFile
    if (-not $Silencioso) { Read-Host 'Hubo un error. Presione Enter para cerrar' }
    exit 1
}
