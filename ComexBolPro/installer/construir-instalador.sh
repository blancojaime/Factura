#!/usr/bin/env bash
# Construye dist/ComexBolPro-Setup-<version>.exe desde Linux o macOS (requiere: dotnet SDK 8 oficial, nsis, p7zip, curl, unzip).
# Uso: installer/construir-instalador.sh [directorio-con-tessdata-spa]
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION=$(sed -n 's:.*<Version>\(.*\)</Version>.*:\1:p' src/ComexBol.App/ComexBol.App.csproj)
TESS_URL="https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-v5.3.0.20221214.exe"
POPPLER_URL="https://github.com/oschwartz10612/poppler-windows/releases/download/v24.08.0-0/Release-24.08.0-0.zip"
SPA_TRAINEDDATA="${1:-/usr/share/tesseract-ocr/5/tessdata/spa.traineddata}"
CACHE=dist/cache; mkdir -p "$CACHE" dist/ocr/tesseract/tessdata dist/ocr/poppler

echo "1/4 Publicando aplicación (win-x64, autocontenida)…"
rm -rf dist/publish
dotnet publish src/ComexBol.App -c Release -r win-x64 --self-contained true -p:EnableWindowsTargeting=true -o dist/publish >/dev/null

echo "2/4 Preparando OCR (Tesseract + Poppler)…"
[ -f "$CACHE/tess.exe" ]   || curl -fsSL -o "$CACHE/tess.exe"   "$TESS_URL"
[ -f "$CACHE/poppler.zip" ] || curl -fsSL -o "$CACHE/poppler.zip" "$POPPLER_URL"
rm -rf "$CACHE/tess" "$CACHE/popp"; 7z x -y -o"$CACHE/tess" "$CACHE/tess.exe" >/dev/null; unzip -q -o "$CACHE/poppler.zip" -d "$CACHE/popp"
cp "$CACHE"/tess/tesseract.exe "$CACHE"/tess/*.dll dist/ocr/tesseract/
cp -r "$CACHE"/tess/tessdata/configs dist/ocr/tesseract/tessdata/ 2>/dev/null || true
cp "$CACHE"/tess/tessdata/eng.traineddata "$CACHE"/tess/tessdata/osd.traineddata dist/ocr/tesseract/tessdata/
cp "$SPA_TRAINEDDATA" dist/ocr/tesseract/tessdata/spa.traineddata
cp "$CACHE"/popp/poppler-*/Library/bin/* dist/ocr/poppler/

echo "3/4 Documentación…"
mkdir -p dist/docs; cp -f docs/manual/*.pdf docs/manual/*.docx dist/docs/ 2>/dev/null || true

echo "4/4 Empaquetando instalador…"
makensis -V1 -DVERSION="$VERSION" installer/ComexBolPro.nsi
ls -lh dist/ComexBolPro-Setup-*.exe
