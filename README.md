# Factura

Este repositorio contiene una plantilla HTML de remisión (`index.html`, `style.css`, `script.js`) y, en `sigaa/`, el **Sistema Integrado de Gestión de Almacenes, Combustible y Activos Fijos (SIGAA)**.

➡ Ver [`sigaa/README.md`](sigaa/README.md).

## SICOM-MUNI — Instalador para Windows (red local)

Sistema de contratación menor (`sicom-muni/`) con instalador para Windows 10/11 (64 bits): un solo servidor en la red local, los demás equipos solo usan el navegador. Incluye los 6 roles, documentos PDF con código QR y verificación, respaldo diario y licencia por equipo (30 días de prueba).

**Descarga (un solo comprimido por componente):** [Releases](../../releases)
- `SICOM-MUNI-Instalador-Windows-<versión>.zip`: instalador `.exe`, manual de instalación en red local (Word) y `LEEME`.
- `SIC-MUNI-Escritorio-Excel-<versión>.zip`: aplicativo de escritorio (Excel/VBA) con sus manuales.
- `SICOM-MUNI-Manuales-<versión>.zip`: todos los manuales en Word (web y escritorio).
- `SICOM-Emisor-de-Licencias-<versión>.zip`: herramienta del proveedor (no va a los clientes).

- Manual para personas sin conocimientos de informática: `sicom-muni/docs/MANUAL_INSTALACION_RED_LOCAL.docx`
- **Emisor de Licencias** (herramienta externa, solo del proveedor): `SICOM-Emisor-de-Licencias-<versión>.zip` en la misma página, con su manual `sicom-muni/docs/MANUAL_EMISOR_LICENCIAS.docx`.
- Código del instalador: `instalador/windows/`. El flujo `Instalador Windows (SICOM-MUNI)` lo compila, lo instala en un Windows real, ejecuta la prueba de punta a punta, lo desinstala y publica los ZIP.
- La llave privada de licencias **no** está en el repositorio; solo la pública (`sicom-muni/backend/app/licencia_publica.pem`).

Limitaciones: el instalador no está firmado digitalmente (Windows mostrará «Más información → Ejecutar de todas formas»); la red local usa http; el QR solo abre dentro de la misma red y requiere IP fija del servidor.
