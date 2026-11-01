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
3. **Importar catálogo…** con los 3 archivos `.md` del Arancel 2026 (o un CSV; `data/nandina-plantilla.csv` muestra el formato, con filas de EJEMPLO).

Manual completo de implementación y pruebas: [`docs/04-Manual-de-Implementacion-y-Pruebas.md`](docs/04-Manual-de-Implementacion-y-Pruebas.md).

## Pendiente
- Compilar y probar la ventana WPF en Windows; visor de PDF (WebView2) y rasterizado de PDF para OCR.
- Validar parámetros normativos con un despachante (prueba P-09 del manual).
- Pantallas para comparar escenarios, viabilidad y exportación; preferencias por acuerdo.
- Mapeo de casillas SUMA, migraciones EF Core, compresión de imágenes, exportación PDF/XLSX.
