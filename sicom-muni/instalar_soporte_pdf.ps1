# OPCIONAL: instala las librerias graficas (Pango via MSYS2) para que WeasyPrint genere PDF reales en Windows.
$ErrorActionPreference = 'Stop'
try {
    if (-not (Test-Path 'C:\msys64\usr\bin\bash.exe')) {
        if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw "Su Windows no tiene 'winget'. Instale MSYS2 desde https://www.msys2.org y repita." }
        Write-Host 'Instalando MSYS2 (acepte el permiso de administrador si lo pide)...'
        winget install -e --id MSYS2.MSYS2 --silent --accept-package-agreements --accept-source-agreements
    }
    Write-Host 'Instalando Pango (puede tardar varios minutos)...'
    & 'C:\msys64\usr\bin\bash.exe' -lc 'pacman -S --noconfirm mingw-w64-x86_64-pango'
    if ($LASTEXITCODE -ne 0) { throw 'Fallo la instalacion de Pango.' }
    [Environment]::SetEnvironmentVariable('WEASYPRINT_DLL_DIRECTORIES', 'C:\msys64\mingw64\bin', 'User')
    Write-Host 'Listo. Cierre SICOM-MUNI (DETENER-SIN-DOCKER.bat) y vuelva a encenderlo (INICIAR-SIN-DOCKER.bat).' -ForegroundColor Green
}
catch { Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red }
Read-Host 'Presione Enter para cerrar'
