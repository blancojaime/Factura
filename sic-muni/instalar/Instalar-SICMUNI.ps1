<#
.SYNOPSIS
  Instalador automatico de SIC-MUNI en Excel (Windows).
.DESCRIPTION
  Crea C:\SIC-MUNI\SIC-MUNI.xlsm, importa los modulos VBA, instala tablas/plantillas/formularios,
  ejecuta la bateria de pruebas automaticas y deja la base limpia si todo pasa.
  Se ejecuta desde la carpeta descomprimida del repositorio (sic-muni\instalar).
.PARAMETER Destino        Carpeta de instalacion (por defecto C:\SIC-MUNI).
.PARAMETER AdminUsuario   Usuario del administrador inicial (por defecto admin).
.PARAMETER Reemplazar     Permite reinstalar sobre un SIC-MUNI.xlsm existente (se guarda copia .bak).
#>
param(
    [string]$Destino = "C:\SIC-MUNI",
    [string]$AdminUsuario = "admin",
    [switch]$Reemplazar
)
$ErrorActionPreference = "Stop"

function Titulo($t) { Write-Host ""; Write-Host "== $t" -ForegroundColor Cyan }
function Ok($t)     { Write-Host "   [OK] $t" -ForegroundColor Green }

function Pedir-Clave($mensaje) {
    $s = Read-Host $mensaje -AsSecureString
    $b = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b) }
}

$xl = $null; $wb = $null; $regKey = $null; $regOld = $null; $regTocado = $false
try {
    Titulo "1. Verificando el entorno"
    $origen = Split-Path -Parent $PSScriptRoot
    $vbaOrigen = Join-Path $origen "vba"
    if (-not (Test-Path (Join-Path $vbaOrigen "modCore.bas"))) { throw "No se encuentra la carpeta vba junto a este instalador ($vbaOrigen)." }
    Ok "Archivos del sistema encontrados en $origen"

    $n35 = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v3.5" -ErrorAction SilentlyContinue
    if (-not $n35 -or $n35.Install -ne 1) {
        Write-Warning ".NET Framework 3.5 NO esta habilitado. Sin el, el login (SHA-256) no funciona."
        Write-Warning "Habilitelo: Panel de control > Programas > Activar o desactivar caracteristicas de Windows > .NET Framework 3.5."
        $r = Read-Host "Continuar de todos modos? (s/N)"
        if ($r -notmatch '^[sS]') { throw "Instalacion cancelada: habilite .NET 3.5 y reintente." }
    } else { Ok ".NET Framework 3.5 habilitado" }

    try { $probe = New-Object -ComObject Excel.Application } catch { throw "No se pudo iniciar Excel de escritorio. Se requiere Microsoft Excel 2010 o superior instalado." }
    $ver = $probe.Version
    $probe.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($probe)
    Ok "Excel version $ver"

    Titulo "2. Datos del administrador"
    Write-Host "   Usuario administrador: $AdminUsuario"
    do {
        $claveAdmin = Pedir-Clave "   Contrasena del administrador (min. 10 car., mayusculas, minusculas y numeros)"
        $okPol = ($claveAdmin.Length -ge 10) -and ($claveAdmin -cmatch '[A-Z]') -and ($claveAdmin -cmatch '[a-z]') -and ($claveAdmin -match '\d') -and ($claveAdmin -notmatch '["]')
        if (-not $okPol) { Write-Warning "No cumple la politica (sin comillas dobles)." ; continue }
        $conf = Pedir-Clave "   Repita la contrasena"
        if ($conf -ne $claveAdmin) { Write-Warning "No coinciden."; $okPol = $false }
    } while (-not $okPol)

    Titulo "3. Preparando $Destino"
    $ruta = Join-Path $Destino "SIC-MUNI.xlsm"
    New-Item -ItemType Directory -Path $Destino -Force | Out-Null
    if (Test-Path $ruta) {
        if (-not $Reemplazar) {
            Write-Warning "Ya existe $ruta (instalacion anterior)."
            $r = Read-Host "   Reinstalar? Se guarda una copia .bak y se reemplaza el libro (s/N)"
            if ($r -notmatch '^[sS]') { throw "Instalacion cancelada por el usuario." }
        }
        Copy-Item $ruta ($ruta + "." + (Get-Date -Format "yyyyMMdd_HHmmss") + ".bak")
        Remove-Item $ruta -Force
    }
    $vbaDest = Join-Path $Destino "vba"
    New-Item -ItemType Directory -Path $vbaDest -Force | Out-Null
    Copy-Item (Join-Path $vbaOrigen "*") $vbaDest -Recurse -Force

    # Clave de proteccion de hojas aleatoria, solo para esta instalacion
    $chars = ((48..57) + (65..90) + (97..122)) | ForEach-Object { [char]$_ }
    $bytes = New-Object byte[] 24
    (New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($bytes)
    $claveProt = -join ($bytes | ForEach-Object { $chars[$_ % $chars.Count] })
    $core = Join-Path $vbaDest "modCore.bas"
    $txt = [IO.File]::ReadAllText($core)
    $txt = [regex]::Replace($txt, 'Public Const PROT_PWD As String = "[^"]*"', [Text.RegularExpressions.MatchEvaluator]{ param($m) 'Public Const PROT_PWD As String = "' + $claveProt + '"' })
    [IO.File]::WriteAllText($core, $txt, [Text.Encoding]::ASCII)
    $archClave = Join-Path $Destino "CLAVE_PROTECCION.txt"
    Set-Content -Path $archClave -Value ("Clave de proteccion de hojas SIC-MUNI (PROT_PWD): " + $claveProt + "`r`nGuardela en un lugar seguro y BORRE este archivo.") -Encoding ASCII
    Ok "Archivos copiados; clave de proteccion generada en $archClave"

    Titulo "4. Habilitando temporalmente el acceso al modelo de objetos VBA"
    $regKey = "HKCU:\Software\Microsoft\Office\$ver\Excel\Security"
    if (-not (Test-Path $regKey)) { New-Item $regKey -Force | Out-Null }
    $regOld = (Get-ItemProperty $regKey -Name AccessVBOM -ErrorAction SilentlyContinue).AccessVBOM
    Set-ItemProperty $regKey -Name AccessVBOM -Value 1 -Type DWord
    $regTocado = $true
    Ok "AccessVBOM = 1 (se restaura al terminar)"

    Titulo "5. Creando el libro e importando los modulos"
    Write-Host "   Excel se abrira visible: NO lo cierre ni lo use mientras dure la instalacion." -ForegroundColor Yellow
    $xl = New-Object -ComObject Excel.Application
    $xl.Visible = $true; $xl.DisplayAlerts = $false
    $wb = $xl.Workbooks.Add()
    $wb.SaveAs($ruta, 52)      # 52 = xlOpenXMLWorkbookMacroEnabled
    $modulos = "modCore","modSecurity","modValidationCHB","modProcurement","modBudgetEngine","modPostAward",
               "modDocumentAutomation","modSetupTemplates","modSetup","modImport","modUIBuilder","modSelfTest"
    foreach ($m in $modulos) { [void]$wb.VBProject.VBComponents.Import((Join-Path $vbaDest "$m.bas")) }
    Ok "$($modulos.Count) modulos importados"

    function Run-Macro([string]$Nombre, [object[]]$Parametros = @()) {
        $full = "'" + $wb.Name + "'!" + $Nombre
        $a = @($full) + $Parametros
        return [System.__ComObject].InvokeMember("Run", [Reflection.BindingFlags]::InvokeMethod, $null, $xl, $a)
    }

    Titulo "6. Verificando el hash SHA-256 (.NET)"
    $h = Run-Macro "modSecurity.SHA256Hex" @("a")
    if ($h -ne "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb") { throw "El hash SHA-256 no funciona (resultado: $h). Revise .NET Framework 3.5." }
    Ok "SHA-256 correcto"

    Titulo "7. Instalando tablas, configuracion, plantillas y datos demo"
    [void](Run-Macro "modCore.SetSilent" @($true))
    [void](Run-Macro "modSetup.InstalarSistemaAuto" @($AdminUsuario, $claveAdmin))
    Ok "Tablas, CONFIG, administrador y 6 plantillas creados"
    [void](Run-Macro "modSetup.CargarDatosDemo")
    Ok "Datos demo cargados (se eliminan al final si las pruebas pasan)"

    Titulo "8. Construyendo formularios y conectando el libro"
    [void](Run-Macro "modUIBuilder.ConstruirFormularios")
    [void]$wb.VBProject.VBComponents.Import((Join-Path $vbaDest "modMain.bas"))
    $cm = $wb.VBProject.VBComponents.Item($wb.CodeName).CodeModule
    $cm.AddFromString([IO.File]::ReadAllText((Join-Path $vbaDest "ThisWorkbook.code.txt")))
    Ok "frmLogin, frmContratacionesConsolidado, modMain y eventos de ThisWorkbook instalados"

    Titulo "9. Ejecutando la bateria de pruebas automaticas"
    $fallos = [int](Run-Macro "modSelfTest.EjecutarPruebas")
    $resultado = Join-Path $Destino "resultado_pruebas.txt"
    if (Test-Path $resultado) { Get-Content $resultado | ForEach-Object { if ($_ -like "FAIL*") { Write-Host $_ -ForegroundColor Red } elseif ($_ -like "PASS*") { Write-Host $_ -ForegroundColor DarkGreen } else { Write-Host $_ } } }

    if ($fallos -eq 0) {
        [void](Run-Macro "modSelfTest.LimpiarDatosPrueba")
        Ok "Todas las pruebas pasaron. Datos de prueba eliminados."
    } else {
        Write-Warning "$fallos prueba(s) fallaron. Los datos de prueba se conservaron para diagnostico."
        Write-Warning "Envie el archivo $resultado para corregir."
    }
    [void](Run-Macro "modCore.SetSilent" @($false))
    [void](Run-Macro "modCore.ProtectDB")
    $wb.Save()
    $wb.Close($false); $wb = $null
    $xl.Quit(); $xl = $null

    Titulo "LISTO"
    Write-Host "Libro: $ruta"
    Write-Host "Administrador: $AdminUsuario"
    Write-Host "PDF se guardaran en: $(Join-Path $Destino 'PDF')"
    Write-Host "Siguiente paso: abra el libro, 'Habilitar contenido', ingrese como $AdminUsuario y cree los usuarios (Alt+F8 > AdminCrearUsuario)."
    Write-Host "Mueva CLAVE_PROTECCION.txt a un lugar seguro y borrelo de $Destino."
    if ($fallos -ne 0) { exit 2 }
}
catch {
    Write-Host ""
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Si Excel muestra un cuadro de error de VBA, anote el mensaje y la linea resaltada." -ForegroundColor Yellow
    exit 1
}
finally {
    try { if ($wb) { $wb.Close($false) } } catch {}
    try { if ($xl) { $xl.Quit() } } catch {}
    if ($regTocado) {
        if ($null -eq $regOld) { Remove-ItemProperty $regKey -Name AccessVBOM -ErrorAction SilentlyContinue }
        else { Set-ItemProperty $regKey -Name AccessVBOM -Value $regOld -Type DWord }
    }
    [GC]::Collect()
}
