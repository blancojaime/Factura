# ComexBol Pro

Asistente de escritorio (Windows) para **decidir, acompañar y documentar** importaciones en Bolivia.

| Proyecto | Qué hace | Estado |
|---|---|---|
| `ComexBol.Core` | Liquidación tributaria, Incoterms, ruta crítica (CPM), escenarios, catálogo (parser CSV) | Probado |
| `ComexBol.Data` | EF Core + SQLite, operaciones, bitácora, expediente, catálogo NANDINA | Probado |
| `ComexBol.Documentos` | OCR (Tesseract CLI), extracción de campos, clasificación del legajo | Probado (incl. Tesseract real) |
| `ComexBol.Presentation` | ViewModels MVVM de la ventana principal | Probado |
| `ComexBol.App` | Ventana WPF (XAML) | **Sin compilar**: requiere Windows (`dotnet build`) |

## Ejecutar pruebas (Linux/Windows)
```bash
for t in tests/*/; do (cd $t && dotnet test); done
```
## Puesta en marcha en Windows
1. Instalar .NET 8 SDK y [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) con el idioma *Spanish*.
2. `dotnet run --project src/ComexBol.App`
3. Menú **Importar catálogo…** con el arancel oficial en CSV (`data/nandina-plantilla.csv` muestra el formato; sus filas son EJEMPLO, no oficiales).

## Pendiente
- Compilar y probar la ventana WPF en Windows; visor de PDF (WebView2) y rasterizado de PDF para OCR.
- Cargar el arancel oficial NANDINA y validar parámetros normativos con un despachante.
- Mapeo de casillas SUMA, migraciones EF Core, compresión de imágenes, exportación PDF/XLSX.
