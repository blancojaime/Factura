# Restablece la contraseña de un usuario del sistema (por ejemplo, si el administrador la olvidó).
. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'comun.ps1')
Exigir-Administrador $MyInvocation.MyCommand.Path
function A-Texto([Security.SecureString]$s) {
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}
try {
    Write-Host "=== Restablecer la contraseña de un usuario de SICOM-MUNI ===`n"
    $usuario = Read-Host 'Nombre de usuario (por ejemplo: admin)'
    $c1 = A-Texto (Read-Host 'Nueva contraseña (mínimo 10 caracteres, con mayúsculas, minúsculas y números)' -AsSecureString)
    $c2 = A-Texto (Read-Host 'Repita la nueva contraseña' -AsSecureString)
    if ($c1 -ne $c2) { throw 'Las contraseñas no coinciden' }
    $env:SICOM_NUEVA_CLAVE = $c1
    $r = Ejecutar-Cli @('restablecer-clave', $usuario)
    Remove-Item Env:\SICOM_NUEVA_CLAVE -ErrorAction SilentlyContinue
    if ($r.Codigo -ne 0) { throw $r.Salida }
    Escribir-Log "Contraseña restablecida para el usuario $usuario" 'herramientas.log'
    Write-Host "`nListo: la contraseña de '$usuario' fue cambiada. Ya puede iniciar sesión con la nueva."
}
catch { Write-Host ("ERROR: " + $_.Exception.Message) -ForegroundColor Red }
Read-Host "`nPresione Enter para cerrar"
