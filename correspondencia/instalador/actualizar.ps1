# Actualiza el sistema con los archivos de una versión nueva, conservando datos, claves y archivos adjuntos.
. "$PSScriptRoot\comun.ps1"
try {
    Clear-Host
    Titulo 'ACTUALIZAR el sistema a una versión nueva'
    Escribir 'Antes de empezar: descargue la versión nueva (ZIP) y EXTRÁIGALA en cualquier carpeta (por ejemplo en el Escritorio).'
    Escribir 'Se conservarán: usuarios, documentos, archivos adjuntos, configuración y respaldos.' 'Green'
    Escribir ''
    if (-not (Test-Path $Puertos)) { throw 'Este sistema no se instaló con INSTALAR.bat. Si usa XAMPP o un hosting, copie las carpetas app, public, database y bin de la versión nueva (ver el manual, capítulo 10).' }
    $origen = (Read-Host 'Escriba o ARRASTRE aquí la carpeta "correspondencia" de la versión nueva y pulse Enter').Trim('"', ' ')
    if (-not $origen -or -not (Test-Path (Join-Path $origen 'app\bootstrap.php'))) { throw 'Esa carpeta no parece ser la versión nueva (no se encontró app\bootstrap.php). Verifique que eligió la carpeta "correspondencia" ya extraída.' }
    if ((Resolve-Path $origen).Path -eq (Resolve-Path $Raiz).Path) { throw 'Eligió la misma carpeta que ya está instalada. Indique la carpeta de la versión NUEVA.' }

    Titulo 'Paso 1 de 4: copia de seguridad'
    & "$PSScriptRoot\respaldar.ps1"
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo hacer la copia de seguridad; no se actualizó nada.' }

    Titulo 'Paso 2 de 4: deteniendo el sistema'
    Detener-Todo; Ok 'Sistema detenido'

    Titulo 'Paso 3 de 4: copiando archivos nuevos'
    foreach ($d in 'app', 'public', 'database', 'bin', 'docs') {
        $o = Join-Path $origen $d
        if (Test-Path $o) { robocopy $o (Join-Path $Raiz $d) /E /NFL /NDL /NJH /NJS /NP | Out-Null; if ($LASTEXITCODE -ge 8) { throw "Falló la copia de la carpeta $d." } }
    }
    robocopy (Join-Path $origen 'instalador') (Join-Path $Raiz 'instalador') /E /XF actualizar.ps1 *.log /XD descargas /NFL /NDL /NJH /NJS /NP | Out-Null
    foreach ($f in 'INICIAR.bat', 'INICIAR-RED.bat', 'DETENER.bat', 'RESPALDAR.bat', 'DESINSTALAR.bat', 'INSTALAR.bat', 'LEEME-PRIMERO.txt', 'README.md') {
        $o = Join-Path $origen $f; if (Test-Path $o) { Copy-Item $o (Join-Path $Raiz $f) -Force }
    }
    Ok 'Archivos actualizados (config, runtime, storage y respaldos NO se tocaron)'

    Titulo 'Paso 4 de 4: iniciando y actualizando la base de datos'
    & "$PSScriptRoot\iniciar.ps1"
    Escribir ''
    Escribir 'ACTUALIZACIÓN TERMINADA. Si algo no se ve igual, presione Ctrl + F5 en el navegador.' 'Green'
    exit 0
} catch { Fallo $_.Exception.Message; exit 1 }
