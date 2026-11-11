#!/usr/bin/env bash
# Crea SIGAA_Descarga_Completa.zip: todo el material (codigo, manuales, capacitacion, base demostrativa) en un solo comprimido.
# Uso (desde la carpeta sigaa):  bash tools/crear-zip-completo.sh
set -euo pipefail
cd "$(dirname "$0")/.."
SALIDA="SIGAA_Descarga_Completa.zip"
rm -f "$SALIDA"
TMP="$(mktemp -d)"
mkdir -p "$TMP/SIGAA/sigaa"
# Solo archivos versionados o nuevos no ignorados (sin node_modules, dist, datos, claves privadas), sin el zip anterior
git ls-files -c -o --exclude-standard . | grep -v "^$SALIDA$" | grep -v "^docs/fuentes/__pycache__/" | while read -r f; do
  [ -f "$f" ] || continue
  mkdir -p "$TMP/SIGAA/sigaa/$(dirname "$f")"; cp -p "$f" "$TMP/SIGAA/sigaa/$f"
done
cp LEEME_DESCARGA.txt "$TMP/SIGAA/LEEME.txt"
( cd "$TMP" && zip -q -r -9 "$OLDPWD/$SALIDA" SIGAA )
rm -rf "$TMP"
echo "Creado $SALIDA ($(du -h "$SALIDA" | cut -f1))"
