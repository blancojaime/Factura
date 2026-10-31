# SIIM 2026 – Sistema Integrado de Ingresos Municipales (Windows 10/11)

Reconstrucción del SIIM 98 (Visual FoxPro 2.5) con el mismo esquema funcional —Empadronamiento (PMC), Liquidación, Recaudación, Otros ingresos, Mantenimiento y Utilitarios— sobre **Python + PySide6 + SQLite**, con tablas de IPBI, IPVA, Patentes y Tasas, deuda tributaria (Art. 47 Ley 2492), respaldos verificados y licencias firmadas por equipo.

## Contenido

| Carpeta | Descripción |
|---|---|
| `siim/core` | Base de datos (SQLite WAL), esquema, seguridad y bitácora, licencias (Ed25519), respaldos (SHA‑256 + AES) |
| `siim/calc` | Deuda tributaria, IPBI, IPVA, IMT, Patentes (3 modalidades), plan de pagos |
| `siim/services` | Reglas de negocio: padrón, liquidación, recaudación, otros ingresos, importación |
| `siim/reports` | Motor PDF/Excel, 39 reportes y 14 formularios/documentos |
| `siim/ui` | Interfaz PySide6 |
| `tools/licencias.py` | **Herramienta externa del proveedor** para emitir licencias (no se entrega al cliente) |
| `docs/` | Manuales y folleto (fuentes + `salida/` con PDF/DOCX) |
| `tests/` | 34 pruebas automáticas (cálculos con los ejemplos oficiales, backups, licencias, interfaz sin pantalla) |

## Ejecutar desde el código

```
python -m pip install -r requirements-dev.txt
python run.py                 # abre el sistema
python -m pytest -q tests     # pruebas (QT_QPA_PLATFORM=offscreen en servidores sin pantalla)
python run.py --selftest      # autoprueba rápida
```

## Compilar el instalador para Windows

1. `python tools/licencias.py init` (una sola vez; crea su clave de licencias y copia la clave pública al proyecto).
2. `build_windows.bat` → `dist\SIIM2026_Setup_1.0.0.exe` (PyInstaller + Inno Setup).
3. O use el flujo `.github/workflows/build-windows.yml` (secreto opcional `SIIM_LICENSE_PUBKEY`).

## Emitir una licencia

```
python tools/licencias.py emitir --codigo XXXX-XXXX-XXXX-XXXX --cliente "GAM Ejemplo" --dias 365
```

## Importante

- Las tablas de la gestión 2004 incluidas son **ejemplos de capacitación**; cargue los valores de su ley municipal / resolución vigente.
- SQLite está pensado para **un equipo por base de datos**; no comparta el archivo por red.
- Lea `docs/salida/1_Manual_de_Implementacion_SIIM2026.pdf` antes de poner el sistema en producción.
