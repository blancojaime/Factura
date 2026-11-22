# COMEX JB

Asistente de escritorio (Windows; antes «ComexBol Pro») para **decidir, acompañar y documentar** importaciones en Bolivia.

| Proyecto | Qué hace | Estado |
|---|---|---|
| `ComexBol.Core` | Liquidación tributaria, Incoterms, ruta crítica (CPM), escenarios, catálogo (parser CSV) | Probado |
| `ComexBol.Data` | EF Core + SQLite, operaciones, bitácora, expediente, catálogo NANDINA, usuarios (PBKDF2), configuración (tipos de cambio, UFV, parámetros), costos reales | Probado |
| `ComexBol.Documentos` | OCR (Tesseract + Poppler), extracción de campos, clasificación, exportación a Excel, **importador del Arancel en PDF** (lectura por coordenadas) | Probado con páginas reales y con el arancel completo |
| `ComexBol.Presentation` | ViewModels MVVM: inicio de sesión, panel, operaciones, arancel, configuración | Probado |
| `ComexBol.App` | Ventana WPF (XAML) | Compila y se ejecuta (probada con capturas reales); instalador de un clic en `installer/` |

## Instalar (usuario final)
Ejecute `ComexJB-Setup-1.2.0.exe` (sin administrador; incluye .NET, OCR con español y lector de PDF). Manuales con capturas reales:
[Manual de Usuario](docs/manual/Manual-de-Usuario.pdf) · [Manual de Instalación y Pruebas](docs/manual/Manual-de-Instalacion-y-Pruebas.pdf) (también en `.docx`).

## Construir el instalador (equipo técnico)
```bash
installer/construir-instalador.sh        # requiere SDK .NET 8 oficial, nsis, p7zip-full, curl, unzip
python3 docs/manual/generar-manuales.py  # regenera los manuales (python-docx, LibreOffice)
docs/manual/capturas.sh docs/manual/capturas   # regenera las capturas (Wine + Xvfb + xdotool)
```

## Ejecutar pruebas (Linux/Windows)
```bash
for t in tests/*/; do (cd $t && dotnet test); done
```
## Puesta en marcha en Windows
1. Instalar .NET 8 SDK y [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) con el idioma *Spanish*.
2. `dotnet run --project src/ComexBol.App`
3. Cree al administrador en el primer ingreso y, en **Arancel → Importar arancel (PDF)…**, elija los 3 **PDF** oficiales del Arancel 2026 (≈2 min; 8.132 partidas). También acepta los `.md` convertidos o un CSV (`data/nandina-plantilla.csv`, filas de EJEMPLO).

Manual completo de implementación y pruebas: [`docs/04-Manual-de-Implementacion-y-Pruebas.md`](docs/04-Manual-de-Implementacion-y-Pruebas.md).

## Novedades de la versión 1.3.0 (manual de procedimientos de maquinaria)
- **Medidas arancelarias por fecha de la DIM**: D.S. 5646 (−5 puntos y nueva base del GA desde el 06/07/2026) y D.S. 5516 (GA 0 % hasta el 31/12/2026) con avisos de vencimiento e **impacto** frente al régimen anterior.
- **Guía de procedimiento** (11 pasos del manual) y **control del expediente** (12 verificaciones) con avance, notas y sugerencias a partir de los datos.
- **Importador habitual / no habitual**: topes de USD 2.000 por despacho y USD 4.000 por año en la validación de la DIM.
- **Decisión** compara origen (preferencia con Certificado de Origen) y beneficio; **precio de venta sugerido** en el costeo.
- **Hoja SUMA** (Excel con DAV, DIM general y DIM por ítem) para transcribir al SUMA.
- Nuevo documento: **Plan de Complementación** (`docs/manual/Plan-de-Complementacion.pdf`).
- Descarga todo en uno: [Release «COMEX JB - instalador y manuales»](https://github.com/blancojaime/Factura/releases/tag/comexjb-instalador).

## Novedades de la versión 1.2.0 (módulos aduaneros)
- **Valoración (DAV)**: cuestionario de descarte del Primer Método (Decisión 571 CAN), ajustes del Art. 8, validador de precios contra el historial propio.
- **Liquidación detallada**: valor en aduana línea por línea, fórmulas con sus números, liquidación por ítem, gastos de despacho, costo nacionalizado, factor de importación y flujo de caja.
- **Despacho (DIM)**: datos y validación previa de la DIM, canales Verde/Amarillo/Rojo con listas de control, levante y borrador de descargos.
- Pendiente: archivo probatorio inmutable (PDF/A), conciliación bancario-aduanera, gestor de autorizaciones previas, transmisión al SUMA.

## Novedades de la versión 1.1.0
Nombre y logo COMEX JB · inicio de sesión con roles · rediseño con colores · selector de partida con descripción automática · editar/eliminar ítems y operaciones ·
tabla de mantenimiento del arancel · menú Configuración (tipos de cambio, UFV, parámetros tributarios, perfil del importador, usuarios, respaldo) · hoja de costos reales · exportación JSON para la DMI.
Datos en `%LocalAppData%\ComexJB` (se migran desde `ComexBolPro` al primer inicio).

## Pendiente
- Probar en un Windows real (hasta ahora se ejecutó bajo Wine); firma digital del instalador.
- Validar parámetros normativos con un despachante (prueba P-09 del manual).
- Pantallas para almacenaje y exportación (DEX/CEDEIM); guardar escenarios.
- Mapeo de casillas SUMA (requiere el instructivo vigente de la ANB); exportación a PDF; compresión de imágenes.
- Migraciones EF Core formales (hoy solo se agregan columnas), cifrado de la base, borradores de solicitudes de AP, actualización remota del arancel.
