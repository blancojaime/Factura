# Gestión de Personal y Asistencia Municipal (GAM – Bolivia)

Sistema web y de escritorio para Gobiernos Autónomos Municipales: personal permanente, eventual y consultores en línea; importación de relojes biométricos, motor de asistencia, permisos con boleta PDF, instructivos con cite correlativo, planillas, informe `.docx`, consolidado para la UAI/CGE y respaldos cifrados.

## Inicio rápido (5 minutos)
```bash
cd gam-personal/backend
pip install -r requirements.txt
GAM_DATA_DIR=./data uvicorn app.main:app --port 8000      # luego abrir http://127.0.0.1:8000
```
La primera vez crea el administrador desde el navegador. Para ver el sistema funcionando con datos: `python datos_prueba/cargar_dataset.py --clave '<su clave>'` (ver `docs/GUIA_PRUEBAS.md`).

## Instalador para Windows y manual
* `desktop/GAMPersonal_Setup.exe` — instalador sencillo (31 MB, incluye Python y librerías, sin permisos de administrador). Se reconstruye con `python desktop/build_installer.py` (requiere NSIS).
* `docs/Manual_GAM_Personal.docx` / `.pdf` — manual de implementación, instalación y pruebas (se regenera con `python docs/generar_manual.py`).
* ⚠️ El instalador se construyó en Linux y **aún no se ejecutó en Windows**: pruébelo en una PC piloto (manual §7.6).

## Contenido
| Carpeta | Qué hay |
|---|---|
| `backend/` | API FastAPI, motor de reglas, reportes, **53 pruebas automáticas** |
| `frontend/` | Interfaz (JS puro, sin Internet): configuración, personal, marcaciones, asistencia, permisos, instructivos, reportes, respaldos, auditoría, usuarios |
| `desktop/` | Lanzador Windows, PyInstaller, instalador NSIS, respaldo programado |
| `db/` | DDL SQL de SQLite y PostgreSQL |
| `datos_prueba/` | Dataset de 5 servidores (CSV/DAT/XLSX) y script de carga |
| `docs/` | `ARQUITECTURA.md` (reglas y supuestos legales a validar) · `MANUAL_IMPLEMENTACION.md` · `GUIA_PRUEBAS.md` (resultados esperados de los 6 reportes) |

## Estado verificado
* 53 pruebas automáticas en verde en **SQLite y PostgreSQL 16**; cifras de liquidación contrastadas con cálculo manual.
* Interfaz recorrida con navegador automatizado (login, importación, procesamiento, descargas) sin errores de JavaScript.
* Reportes `.docx`/`.xlsx` abiertos y renderizados con LibreOffice; fórmulas `SUM` recalculadas correctamente.
* **No verificado:** compilación del `.exe`/instalador en Windows; archivos reales de Anviz/Dahua. Ver `docs/ARQUITECTURA.md` §6.

> ⚠️ Los parámetros legales (descuento doble por falta, tolerancia, escalas, tasas AFP, feriados) provienen de sus documentos de ejemplo y de la especificación; **deben ser validados por la Unidad Jurídica** antes de usarse en planillas reales (`docs/ARQUITECTURA.md` §5).
