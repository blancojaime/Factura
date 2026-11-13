# Crea el archivo .env con claves aleatorias (solo si no existe). Lo usa INICIAR-WINDOWS.bat
$ErrorActionPreference = 'Stop'
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$env_file = Join-Path $dir '.env'
if (Test-Path $env_file) { Write-Host 'Ya existe el archivo .env: se conserva.'; exit 0 }
function Nuevo($n) { -join ((48..57 + 65..90 + 97..122) | Get-Random -Count $n | ForEach-Object { [char]$_ }) }
$lineas = @(
  "POSTGRES_PASSWORD=$(Nuevo 24)",
  "SECRET_KEY=$(Nuevo 64)",
  "FERNET_KEY=",
  "MINIO_ROOT_USER=sicomminio",
  "MINIO_ROOT_PASSWORD=$(Nuevo 24)",
  "PUBLIC_BASE_URL=http://localhost:3000",
  "COOKIE_SECURE=false"
)
[System.IO.File]::WriteAllLines($env_file, $lineas, (New-Object System.Text.UTF8Encoding($false)))
Write-Host 'Archivo .env creado con claves aleatorias.'
