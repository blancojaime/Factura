# ComexBol Pro

Asistente de escritorio (Windows) para **decidir, acompañar y documentar** importaciones en Bolivia.

| Proyecto | Qué hace | Estado |
|---|---|---|
| `ComexBol.Core` | Liquidación tributaria, Incoterms, ruta crítica (CPM), escenarios, catálogo (parser CSV) | Probado |
| `ComexBol.Data` | EF Core + SQLite, operaciones, bitácora, expediente, catálogo NANDINA | Probado |
| `ComexBol.Documentos` | OCR (Tesseract + Poppler), extracción de campos, clasificación, exportación a Excel, **importador del Arancel en PDF** (lectura por coordenadas) | Probado con páginas reales y con el arancel completo |
| `ComexBol.Presentation` | ViewModels MVVM de la ventana principal | Probado |
| `ComexBol.App` | Ventana WPF (XAML) | Compila y se ejecuta (probada con capturas reales); instalador de un clic en `installer/` |

## Instalar (usuario final)
Ejecute `ComexBolPro-Setup-1.0.0.exe` (sin administrador; incluye .NET, OCR con español y lector de PDF). Manuales con capturas reales:
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
3. **Importar catálogo…** con los 3 **PDF** oficiales del Arancel 2026 (≈10 s; 8.132 partidas). También acepta los `.md` convertidos o un CSV (`data/nandina-plantilla.csv`, filas de EJEMPLO).

Manual completo de implementación y pruebas: [`docs/04-Manual-de-Implementacion-y-Pruebas.md`](docs/04-Manual-de-Implementacion-y-Pruebas.md).

## Pendiente
- Probar en un Windows real (hasta ahora se ejecutó bajo Wine); firma digital del instalador.
- Validar parámetros normativos con un despachante (prueba P-09 del manual).
- Pantallas para almacenaje y exportación (DEX/CEDEIM); guardar escenarios.
- Mapeo de casillas SUMA (requiere el instructivo vigente de la ANB); exportación a PDF; compresión de imágenes.
- Mapeo de casillas SUMA, migraciones EF Core, compresión de imágenes, exportación PDF/XLSX.
