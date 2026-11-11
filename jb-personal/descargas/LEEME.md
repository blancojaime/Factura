# Descargas

**`JB-Personal_v1.2.0.zip`** (41 MB) — todo en un solo comprimido:

| Archivo | Contenido |
|---|---|
| `JBPersonal_Setup.exe` | Instalador para Windows 10+ (Siguiente → Instalar → Finalizar). Se instala como servicio: funciona sin sesión de usuario abierta |
| `Manual_JB-Personal.pdf` / `.docx` | Manual de implementación, instalación, activación y pruebas, con capturas de la aplicación (29 páginas) |
| `datos_prueba/` | Dataset ficticio y scripts de carga |
| `SHA256SUMS.txt`, `LEEME.txt` | Sumas de verificación e instrucciones rápidas |

Verifique la descarga: `sha256sum -c JB-Personal_v1.2.0.zip.sha256` (o compare con `Get-FileHash` en PowerShell).
SHA-256 del ZIP: ver `JB-Personal_v1.2.0.zip.sha256`.

El instalador no está firmado digitalmente: si Windows muestra «protegió su PC», pulse *Más información → Ejecutar de todas formas*.
Solo se incluye el instalador de la aplicación; el **JB-Activador** (emisor de licencias, con la clave privada) **no** se publica.
