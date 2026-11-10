<# Detiene JB-Personal (tarea y procesos de la carpeta de instalación). Uso: -Dir <carpeta> [-Quitar] (-Quitar elimina la tarea y la regla de firewall) #>
param([Parameter(Mandatory=$true)][string]$Dir, [switch]$Quitar)
$ErrorActionPreference = 'SilentlyContinue'
Stop-ScheduledTask -TaskName 'JB-Personal'
Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($Dir, [StringComparison]::OrdinalIgnoreCase) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Sleep -Seconds 1
if ($Quitar) {
    Unregister-ScheduledTask -TaskName 'JB-Personal' -Confirm:$false
    Get-NetFirewallRule -DisplayName 'JB-Personal' | Remove-NetFirewallRule
}
