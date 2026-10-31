# Captura REAL del asistente de instalación y de la primera ejecución (sólo en el servidor de compilación con escritorio Windows)
param([string]$Setup, [string]$Out)
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
New-Item -ItemType Directory -Force -Path $Out | Out-Null
function Shot($n) {
  $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
  $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
  $bmp.Save("$Out\$n.png", [System.Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $bmp.Dispose()
}
$sh = New-Object -ComObject WScript.Shell
function Key($k) { [void]$sh.AppActivate("SIIM"); Start-Sleep -Milliseconds 600; $sh.SendKeys($k) }
$p = Start-Process -FilePath $Setup -PassThru
Start-Sleep 8;  [void]$sh.AppActivate("SIIM"); Start-Sleep 1; Shot "win_inst_1_instalar"
Key "{ENTER}"
Start-Sleep 25; Shot "win_inst_2_finalizar"
Key "{ENTER}"
Start-Sleep 15; Shot "win_app_1_primer_uso"
Get-Process SIIM2026 -ErrorAction SilentlyContinue | Stop-Process -Force
