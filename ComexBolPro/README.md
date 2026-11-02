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
Ejecute `ComexJB-Setup-1.1.1.exe` (sin administrador; incluye .NET, OCR con español y lector de PDF). Manuales con capturas reales:
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

## Novedades de la versión 1.1.1
Nombre y logo COMEX JB · inicio de sesión con roles · rediseño con colores · selector de partida con descripción automática · editar/eliminar ítems y operaciones ·
tabla de mantenimiento del arancel · menú Configuración (tipos de cambio, UFV, parámetros tributarios, perfil del importador, usuarios, respaldo) · hoja de costos reales · exportación JSON para la DMI.
Datos en `%LocalAppData%\ComexJB` (se migran desde `ComexBolPro` al primer inicio).

## Pendiente
- Probar en un Windows real (hasta ahora se ejecutó bajo Wine); firma digital del instalador.
- Validar parámetros normativos con un despachante (prueba P-09 del manual).
- Pantallas para almacenaje y exportación (DEX/CEDEIM); guardar escenarios.
- Mapeo de casillas SUMA (requiere el instructivo vigente de la ANB); exportación a PDF; compresión de imágenes.
- Migraciones EF Core formales (hoy solo se agregan columnas), cifrado de la base, borradores de solicitudes de AP, actualización remota del arancel.
