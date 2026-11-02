#!/usr/bin/env bash
# Regenera las capturas REALES del manual ejecutando la aplicación publicada (Wine + Xvfb + xdotool).
# Requisitos: wine64, xvfb, xdotool, imagemagick; la aplicación publicada copiada en $WINEPREFIX/drive_c/cb y
# una base con el arancel cargado en %LocalAppData%\ComexBolPro\comex.db. Uso: capturas.sh <carpeta-salida>
set -u
OUT="${1:-capturas}"; mkdir -p "$OUT"
export WINEPREFIX="${WINEPREFIX:-/tmp/wp5}" DISPLAY=:99 WINEDEBUG=-all
RAW=$(mktemp -d)
shot(){ import -window root "$RAW/$1.png" && convert "$RAW/$1.png" -crop 1372x806+4+30 +repage "$OUT/$1.png"; }
click(){ xdotool mousemove "$1" "$2" click 1; sleep 0.7; }
field(){ click "$1" "$2"; xdotool key ctrl+a; xdotool type --delay 40 -- "$3"; sleep 0.3; }
cell(){ click "$1" "$2"; xdotool type --delay 40 -- "$3"; xdotool key Return; sleep 0.4; }
pick(){ click "$1" "$2"; xdotool type --delay 90 -- "$3"; xdotool key Return; sleep 0.7; }
pgrep Xvfb >/dev/null || { Xvfb :99 -screen 0 1440x900x24 >/dev/null 2>&1 & sleep 2; }
wineserver -k 2>/dev/null; sleep 1
rm -f "$WINEPREFIX/drive_c/users/root/AppData/Local/ComexBolPro/comex.db"*     # base vacía: se importa el arancel desde pantalla
(cd "$WINEPREFIX/drive_c/cb" && WINEDLLOVERRIDES="mshtml=d" nohup wine ComexBolPro.exe >/tmp/capturas-app.log 2>&1 &)
for i in $(seq 1 60); do xdotool search --name "ComexBol" >/dev/null 2>&1 && break; sleep 1; done; sleep 7

# Coordenadas de pantalla (ventana 1372x806 en 4,30)
TAB_ITEMS=(304 95); TAB_LIQ=(406 95); TAB_DEC=(481 95); TAB_CON=(575 95); TAB_RUTA=(675 95); TAB_LEG=(772 95)

shot 01-ventana-principal
# --- Importar el arancel (3 PDF en C:\arancel) ---
click 420 52; sleep 3; xdotool type --delay 20 '"C:\arancel\a1.pdf" "C:\arancel\a2.pdf" "C:\arancel\a3.pdf"'; xdotool key Return; sleep 4; shot 01b-importando-arancel
sleep 20; shot 01c-arancel-importado; xdotool key Return; sleep 2
# --- Caso 1: tablets FOB ---
field 118 117 "IMP-2026-001"; shot 02-nueva-importacion
click 41 170; sleep 3; shot 03-importacion-creada
field 1136 149 "8471.30.00.10"; field 1136 170 "Tablets con IMEI"; field 1136 191 "40000"; field 1136 212 "800"; field 967 233 "1800"; field 1073 233 "150"
shot 04-formulario-item
click 853 309; sleep 3; shot 05-item-agregado
click 952 309; sleep 3; click ${TAB_LIQ[@]}; sleep 2; shot 06-liquidacion
click ${TAB_RUTA[@]}; sleep 2; shot 07-ruta-critica
click 1297 148; sleep 2; shot 08-etapa-cumplida
click ${TAB_LEG[@]}; sleep 2; shot 09-legajo-bitacora
# --- Caso 2: escenarios ---
click ${TAB_DEC[@]}; sleep 1.5
field 342 128 "200"; field 525 128 "4500"; field 754 128 "2800"
click 315 158; click 315 158; click 315 158; sleep 1
cell 500 212 "FOB + flete propio"; cell 940 212 "40000"; cell 1030 212 "1800"; cell 1110 212 "150"
cell 500 242 "CIF del proveedor"; cell 940 242 "42000"; pick 835 242 "CIF"
cell 500 272 "DAP del proveedor"; cell 940 272 "44000"; cell 1215 272 "1200"; pick 835 272 "DAP"
shot 10-escenarios
click 418 158; sleep 3; shot 11-decision-resultados
# --- Caso 11: contraste con DIM ---
click ${TAB_CON[@]}; sleep 1.5
field 322 152 "29197,20"; field 580 152 "0"; field 705 152 "47982,68"; click 933 152; sleep 2; shot 12-contraste-coincide
field 705 152 "47990"; click 933 152; sleep 2; shot 13-contraste-diferencia
# --- Caso 10: OCR ---
click ${TAB_ITEMS[@]}; sleep 1
field 118 117 "IMP-2026-002"; click 41 170; sleep 3
click 368 136; sleep 3; xdotool type --delay 30 'C:\cb\ejemplos\factura-ejemplo.png'; xdotool key Return; sleep 12; shot 14-ocr-propuesta
field 1106 448 "10500"; shot 15-ocr-corregido
click 861 499; sleep 3; shot 16-ocr-confirmado
click ${TAB_LEG[@]}; sleep 2; shot 17-legajo-con-factura
# --- Caso 4: vehículo con ICE por antigüedad ---
click ${TAB_ITEMS[@]}; sleep 1
field 118 117 "IMP-2026-003"; click 41 170; sleep 3
field 1136 149 "8701.21.00.00"; field 1136 170 "Tractor de carretera usado"; field 1136 191 "20000"; field 1136 212 "4000"; field 967 233 "2500"; field 1073 233 "200"; field 967 254 "3"
shot 18-vehiculo-formulario
click 853 309; sleep 3; click ${TAB_LIQ[@]}; sleep 2; shot 19-vehiculo-avisos-ice
click ${TAB_ITEMS[@]}; sleep 1; click 952 309; sleep 3; click ${TAB_LIQ[@]}; sleep 2; shot 20-vehiculo-liquidacion
# --- Caso 16: preferencia del arancel ---
click ${TAB_ITEMS[@]}; sleep 1
field 118 117 "IMP-2026-004"; click 41 170; sleep 3
field 1136 149 "0101.21.00.00"; field 1136 170 "Caballo reproductor"; field 1136 191 "1000"; field 1136 212 "500"; pick 990 275 "CAN"
shot 21-preferencia-formulario
click 853 309; sleep 3; click ${TAB_LIQ[@]}; sleep 2; shot 22-preferencia-avisos
wineserver -k 2>/dev/null; echo "Capturas en $OUT"; ls "$OUT" | wc -l
