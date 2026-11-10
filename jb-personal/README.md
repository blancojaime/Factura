# JB-Personal — Gestión de Personal y Asistencia Municipal (Bolivia)

![JB](frontend/img/logo.jpg)

Sistema para Gobiernos Autónomos Municipales: personal permanente, eventual y consultores en línea; importación de relojes biométricos de **distintas marcas**, motor de asistencia, permisos con boleta PDF, instructivos con cite correlativo, planillas, informe `.docx`, consolidado para la UAI/CGE (`.txt/.csv` y `.xlsx`), respaldos cifrados y **activación por licencia**.

## Novedades de la versión 1.1
1. **Instalador como servicio de Windows**, independiente de la sesión de usuario (`JBPersonal_Setup.exe`).
2. Nueva identidad **JB-Personal** con el logotipo e icono de Jaime Blanco.
3. Consolidado de auditoría también en **Excel plano** (solo títulos y datos).
4. **Marcaciones de cualquier marca de reloj:** autodetección, asistente de mapeo de columnas, perfiles guardados y estructura «ancha».
5. **Diseño cálido** (terracota, ámbar y crema) en la aplicación y los reportes.
6. **Planillas corregidas:** muestran a todos los empleados (los reportes de periodos abiertos se recalculan siempre).
7. **Activador externo** (`activador/`, JB-Activador): emite códigos de activación firmados por equipo; prueba de 30 días y modo solo lectura.
8. Manuales actualizados (Word, PDF y Markdown).

## Inicio rápido
```bash
cd jb-personal/backend
pip install -r requirements.txt
GAM_DATA_DIR=./data uvicorn app.main:app --port 8000      # http://127.0.0.1:8000
```
En Windows use el instalador (`desktop/JBPersonal_Setup.exe`, ver el manual). La primera vez se crea el administrador desde el navegador. Datos de prueba: `python datos_prueba/cargar_dataset.py --clave '<su clave>'`.

## Contenido
| Carpeta | Qué hay |
|---|---|
| `backend/` | API FastAPI, motor de reglas, reportes, licencia, **86 pruebas automáticas** |
| `frontend/` | Interfaz (JS puro, sin Internet) y logotipo |
| `desktop/` | Lanzador/servicio de Windows, scripts PowerShell, instalador NSIS, constructores (`build_installer.py`, `build_activador.py`) |
| `activador/` | **JB-Activador** (herramienta del emisor de licencias) |
| `db/` | DDL SQL de SQLite y PostgreSQL |
| `datos_prueba/` | Dataset de 5 servidores (CSV/DAT/XLSX) y script de carga |
| `docs/` | **`Manual_JB-Personal.docx` / `.pdf`** (manual completo) · `ARQUITECTURA.md` · `MANUAL_IMPLEMENTACION.md` · `GUIA_PRUEBAS.md` |

## Instaladores
```bash
cd desktop
python build_installer.py --manual ../docs/Manual_JB-Personal.pdf ../docs/Manual_JB-Personal.docx   # JBPersonal_Setup.exe
python build_activador.py --clave-privada RUTA/clave_privada.pem                                    # JBActivador_Setup.exe (solo emisor)
```
Requieren Python 3.9+, NSIS (`makensis`) e Internet. **Los `.exe` no se versionan** (ni la clave privada del activador).

## Estado verificado
* 86 pruebas automáticas en verde en **SQLite y PostgreSQL 16**; cifras de liquidación contrastadas con cálculo manual.
* Interfaz recorrida con navegador automatizado (login, asistente de estructura, licencia, reportes) sin errores de JavaScript.
* Reportes `.docx`/`.xlsx` abiertos y renderizados con LibreOffice.
* **No verificado:** ejecución del instalador en Windows (se construyó en Linux) y archivos reales de Anviz/Dahua/Hikvision/Suprema. Ver `docs/ARQUITECTURA.md` §6.

> ⚠️ Los parámetros legales (descuento doble por falta, tolerancia, escalas, tasas AFP, feriados) provienen de los documentos de ejemplo y de la especificación; **deben ser validados por la Unidad Jurídica** (`docs/ARQUITECTURA.md` §5).
