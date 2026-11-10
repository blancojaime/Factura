# Quita los servicios, el firewall y la tarea de respaldo (lo ejecuta el desinstalador). Los datos se conservan salvo -EliminarDatos.
param([switch]$EliminarDatos, [string]$InstallDirParam = '')
. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'comun.ps1')
if ($InstallDirParam) { $script:InstallDir = $InstallDirParam.TrimEnd('\') }
$ErrorActionPreference = 'Continue'
Stop-Service $SvcApp -Force -ErrorAction SilentlyContinue
$exe = Join-Path $ConfigDir 'servicio\SICOM-MUNI-Servicio.exe'
if (Test-Path $exe) { & $exe uninstall 2>&1 | Out-Null }
Stop-Service $SvcBd -Force -ErrorAction SilentlyContinue
$pgctl = Join-Path $InstallDir 'pgsql\bin\pg_ctl.exe'
if (Test-Path $pgctl) { & $pgctl unregister -N $SvcBd 2>&1 | Out-Null }
& sc.exe delete $SvcApp 2>&1 | Out-Null
& sc.exe delete $SvcBd 2>&1 | Out-Null
Get-NetFirewallRule -DisplayName 'SICOM-MUNI*' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
Unregister-ScheduledTask -TaskName 'SICOM-MUNI Respaldo diario' -Confirm:$false -ErrorAction SilentlyContinue
if ($EliminarDatos -and (Test-Path $DataDir)) { Remove-Item -Recurse -Force $DataDir -ErrorAction SilentlyContinue }
exit 0
