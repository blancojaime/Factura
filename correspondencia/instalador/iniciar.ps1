param([switch]$Red)
. "$PSScriptRoot\comun.ps1"
try {
    if (-not (Test-Path $Puertos)) { Fallo 'El sistema no está instalado. Ejecute INSTALAR.bat primero.'; exit 1 }
    Escribir 'Iniciando el sistema de correspondencia...' 'Cyan'
    Db-Iniciar
    Push-Location $Raiz
    & (Php-Exe) -c (Join-Path $PhpDir 'php.ini') 'bin\migrar.php'
    Pop-Location
    if ($Red) { Web-Iniciar -Red } else { Web-Iniciar }
    $cfg = Leer-Json $Puertos
    Ok "Listo: http://localhost:$($cfg.web)/"
    if ($Red) {
        $ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.*' } | Select-Object -ExpandProperty IPAddress
        Escribir 'Otras computadoras de la misma red pueden entrar con:' 'Yellow'
        foreach ($ip in $ips) { Escribir "    http://${ip}:$($cfg.web)/" 'Yellow' }
        Aviso 'Si Windows pregunta por el Firewall, elija "Permitir acceso" (solo en red privada).'
    }
    Start-Process "http://localhost:$($cfg.web)/"
    exit 0
} catch { Fallo $_.Exception.Message; exit 1 }
