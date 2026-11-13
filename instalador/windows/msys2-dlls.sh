#!/usr/bin/env bash
# Copia las DLL de Pango/HarfBuzz/Fontconfig (y sus dependencias) y las fuentes DejaVu desde MSYS2.
# Uso (dentro de un shell MSYS2 MINGW64):  bash msys2-dlls.sh DESTINO
set -euo pipefail
DEST="$1"
mkdir -p "$DEST/bin" "$DEST/fonts"
cd /mingw64/bin
cola=(libgobject-2.0-0.dll libpango-1.0-0.dll libpangoft2-1.0-0.dll libharfbuzz-0.dll libharfbuzz-subset-0.dll libfontconfig-1.dll libglib-2.0-0.dll)
declare -A vistos=()
while ((${#cola[@]})); do
  dll="${cola[0]}"; cola=("${cola[@]:1}")
  [[ -n "${vistos[$dll]:-}" ]] && continue
  [[ -f "$dll" ]] || { echo "AVISO: no existe $dll"; continue; }
  vistos[$dll]=1
  cp -f "$dll" "$DEST/bin/"
  while read -r dep; do [[ -n "$dep" ]] && cola+=("$dep"); done < <(ldd "$dll" | awk '/\/mingw64\/bin\//{n=split($3,a,"/"); print a[n]}')
done
cp -f /mingw64/share/fonts/TTF/DejaVu*.ttf "$DEST/fonts/"
echo "DLL copiadas: ${#vistos[@]}"
ls "$DEST/bin" | head -80
