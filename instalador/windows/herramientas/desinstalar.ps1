# Quita los servicios, el firewall y la tarea de respaldo (lo ejecuta el desinstalador). Los datos se conservan salvo -EliminarDatos.
param([switch]$EliminarDatos, [string]$InstallDirParam = '')
. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'comun.ps1')
if ($InstallDirParam) { $script:InstallDir = $InstallDirParam.TrimEnd('\') }
$ErrorActionPreference = 'Continue'
$diag = Join-Path $env:SystemRoot 'Temp\sicom-desinstalacion.log'
"$(Get-Date -Format s) EliminarDatos=$EliminarDatos InstallDir=$InstallDir DataDir=$DataDir" | Out-File $diag -Encoding UTF8
Stop-Service $SvcApp -Force -ErrorAction SilentlyContinue
try { (Get-Service $SvcApp -ErrorAction Stop).WaitForStatus('Stopped', '00:00:40') } catch { }
$exe = Join-Path $ConfigDir 'servicio\SICOM-MUNI-Servicio.exe'
if (Test-Path $exe) { & $exe uninstall 2>&1 | Out-Null }
Stop-Service $SvcBd -Force -ErrorAction SilentlyContinue
try { (Get-Service $SvcBd -ErrorAction Stop).WaitForStatus('Stopped', '00:00:60') } catch { }
$pgctl = Join-Path $InstallDir 'pgsql\bin\pg_ctl.exe'
if (Test-Path $pgctl) { & $pgctl unregister -N $SvcBd 2>&1 | Out-Null }
& sc.exe delete $SvcApp 2>&1 | Out-Null
& sc.exe delete $SvcBd 2>&1 | Out-Null
Get-NetFirewallRule -DisplayName 'SICOM-MUNI*' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
Unregister-ScheduledTask -TaskName 'SICOM-MUNI Respaldo diario' -Confirm:$false -ErrorAction SilentlyContinue
if ($EliminarDatos -and (Test-Path $DataDir)) {
    # Cierra procesos que aún tengan archivos abiertos y reintenta (PostgreSQL tarda en soltar la carpeta)
    Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -and ($_.Path -like "$InstallDir\*") } | Stop-Process -Force -ErrorAction SilentlyContinue
    for ($i = 0; $i -lt 15 -and (Test-Path $DataDir); $i++) {
        & icacls.exe $DataDir '/grant' '*S-1-5-32-544:(OI)(CI)F' '/T' '/C' '/Q' 2>&1 | Out-Null
        Remove-Item -Recurse -Force $DataDir -ErrorAction SilentlyContinue
        if (Test-Path $DataDir) { Start-Sleep -Seconds 2 }
    }
    if (Test-Path $DataDir) {
        "Quedan archivos en $DataDir :" | Out-File $diag -Append -Encoding UTF8
        Get-ChildItem $DataDir -Recurse -Force -ErrorAction SilentlyContinue | Select-Object -First 40 -ExpandProperty FullName | Out-File $diag -Append -Encoding UTF8
        try { Remove-Item -Recurse -Force $DataDir -ErrorAction Stop } catch { ("Error: " + $_.Exception.Message) | Out-File $diag -Append -Encoding UTF8 }
    }
}
exit 0
