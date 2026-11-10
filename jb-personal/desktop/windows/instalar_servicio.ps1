<#  Registra JB-Personal como TAREA PROGRAMADA de arranque (SYSTEM): se inicia con el equipo, sin sesion de usuario,
    y se reinicia sola si falla. Parametros: -Dir <carpeta de instalacion>  [-Red]  [-Puerto 8765]
    -Red  : escucha en todas las interfaces y abre el puerto en el Firewall de Windows (acceso desde otras PC).      #>
param([Parameter(Mandatory=$true)][string]$Dir, [switch]$Red, [int]$Puerto = 8765)
$ErrorActionPreference = 'Stop'
$Tarea = 'JB-Personal'
$Datos = Join-Path $env:ProgramData 'JB-Personal'
New-Item -ItemType Directory -Force -Path $Datos, (Join-Path $Datos 'logs'), (Join-Path $Datos 'backups') | Out-Null
$hostIp = if ($Red) { '0.0.0.0' } else { '127.0.0.1' }
Set-Content -Path (Join-Path $Datos 'config.ini') -Encoding ASCII -Value "[servidor]`r`nhost = $hostIp`r`nport = $Puerto`r`n"

if (Get-ScheduledTask -TaskName $Tarea -ErrorAction SilentlyContinue) { Unregister-ScheduledTask -TaskName $Tarea -Confirm:$false }
$accion = New-ScheduledTaskAction -Execute (Join-Path $Dir 'python\pythonw.exe') -Argument '"launcher.py" --servicio' -WorkingDirectory (Join-Path $Dir 'desktop')
$disparador = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$ajustes = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $Tarea -Action $accion -Trigger $disparador -Principal $principal -Settings $ajustes `
    -Description 'JB-Personal: gestion de personal y asistencia municipal (servidor local)' | Out-Null

Get-NetFirewallRule -DisplayName 'JB-Personal' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
if ($Red) { New-NetFirewallRule -DisplayName 'JB-Personal' -Direction Inbound -Protocol TCP -LocalPort $Puerto -Action Allow -Profile Domain,Private | Out-Null }

Start-ScheduledTask -TaskName $Tarea
for ($i = 0; $i -lt 40; $i++) {
    try { $r = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Puerto/api/salud" -TimeoutSec 2; if ($r.StatusCode -eq 200) { Write-Output "OK: JB-Personal responde en http://127.0.0.1:$Puerto/"; exit 0 } } catch { Start-Sleep -Seconds 1 }
}
Write-Output "AVISO: el servicio se registro pero no respondio en 40 s. Revise $Datos\logs\servicio.log"
exit 2
