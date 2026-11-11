#!/usr/bin/env bash
# Regenera las capturas REALES del manual ejecutando COMEX JB publicado (Wine + Xvfb + xdotool).
# Requisitos: wine64, xvfb, xdotool, imagemagick; app publicada copiada en $WINEPREFIX/drive_c/cb,
# los 3 PDF del arancel en C:\arancel (a1.pdf a2.pdf a3.pdf) y la factura en C:\cb\ejemplos.
# Uso: capturas.sh <carpeta-salida>
set -u
OUT="${1:-capturas}"; mkdir -p "$OUT"
export WINEPREFIX="${WINEPREFIX:-/tmp/wp5}" DISPLAY=:99 WINEDEBUG=-all
RAW=$(mktemp -d)
shot(){ sleep 0.8; import -window root "$RAW/$1.png" && convert "$RAW/$1.png" -crop 1492x866+104+80 +repage "$OUT/$1.png"; }
click(){ xdotool mousemove "$1" "$2" click 1; sleep 1; }
field(){ click "$1" "$2"; xdotool key ctrl+a; xdotool type --delay 40 -- "$3"; sleep 0.3; }
cell(){ click "$1" "$2"; xdotool type --delay 40 -- "$3"; xdotool key Return; sleep 0.5; }
pgrep Xvfb >/dev/null || { Xvfb :99 -screen 0 1700x1000x24 >/dev/null 2>&1 & sleep 2; }
wineserver -k 2>/dev/null; sleep 1
rm -f "$WINEPREFIX/drive_c/users/root/AppData/Local/ComexJB/comex.db"*     # base vacía
(cd "$WINEPREFIX/drive_c/cb" && WINEDLLOVERRIDES="mshtml=d" nohup wine ComexJB.exe --ventana >/tmp/capturas-app.log 2>&1 &)
for i in $(seq 1 60); do xdotool search --name "COMEX JB" >/dev/null 2>&1 && break; sleep 1; done; sleep 6

# Navegación lateral y pestañas (coordenadas de pantalla)
NAV_PANEL="180 287"; NAV_OPS="180 327"; NAV_ARA="180 367"; NAV_CFG="180 408"; NAV_ACE="180 448"
T_MER="700 212"; T_VAL="806 212"; T_LIQ="913 212"; T_DES="1019 212"; T_DEC="1115 212"; T_CON="1210 212"; T_COS="1300 212"; T_RUT="1373 212"; T_LEG="1445 212"
C_TC="430 167"; C_UFV="533 167"; C_PAR="655 167"; C_PER="831 167"; C_USU="962 167"; C_DAT="1081 167"

# ---- Inicio de sesión (primer uso: crea al administrador) ----
shot 01-primer-uso; convert "$OUT/01-primer-uso.png" -trim +repage "$OUT/01-primer-uso.png"
xdotool type --delay 40 "Jaime Blanco Villegas"; xdotool key Tab; xdotool type --delay 40 "jaime"; xdotool key Tab; xdotool type --delay 40 "comex2026"; xdotool key Tab; xdotool type --delay 40 "comex2026"
shot 02-primer-uso-lleno; convert "$OUT/02-primer-uso-lleno.png" -trim +repage "$OUT/02-primer-uso-lleno.png"
xdotool key Return; sleep 8
shot 03-panel-vacio
# ---- Arancel: sin cargar → importar los 3 PDF → buscar/editar ----
click $NAV_ARA; sleep 2; shot 04-arancel-sin-cargar
click 1316 135; sleep 3; xdotool type --delay 20 '"C:\arancel\a1.pdf" "C:\arancel\a2.pdf" "C:\arancel\a3.pdf"'; xdotool key Return; sleep 4; shot 05-arancel-importando
for i in $(seq 1 60); do sleep 2; done; xdotool key Return; sleep 2   # espera la importación y cierra el aviso
shot 06-arancel-cargado
field 640 239 "8471300010"; sleep 3; click 640 345; sleep 1; shot 07-arancel-buscar-editar
# ---- Operaciones: crear, partida, ítem ----
click $NAV_OPS; sleep 2
field 495 168 "IMP-2026-001"; shot 08-nueva-importacion
click 495 259; sleep 3; click 1330 311; xdotool type --delay 60 "tablet"; sleep 3; shot 09-selector-partida
xdotool key ctrl+a; xdotool type --delay 60 "84713000"; sleep 3; shot 10-selector-por-codigo
click 1300 355; sleep 2
field 1170 475 "40000"; field 1270 475 "200"; field 1390 475 "500"; field 1175 657 "1800"; field 1315 657 "150"; shot 11-formulario-item
click 1162 704; sleep 3; click 740 330; sleep 1; shot 12-item-agregado
click 1385 676; sleep 3; click $T_LIQ; sleep 2; shot 13-liquidacion
click $T_MER; sleep 1; click 740 330; click 700 680; sleep 2; shot 14-editar-item
click 1162 704; sleep 3; shot 15-item-editado
click 740 330; click 840 680; sleep 2; shot 16-confirmar-eliminar-item
xdotool key y; sleep 2; shot 17-item-eliminado
# ---- Decisión, contraste, costos, ruta, legajo ----
click 1330 311; xdotool type --delay 40 "8471300010"; sleep 3; click 1170 475; xdotool key ctrl+a; xdotool type "40000"; click 1270 475; xdotool key ctrl+a; xdotool type "200"; click 1390 475; xdotool key ctrl+a; xdotool type "500"; click 1162 704; sleep 3; click 1385 676; sleep 3
# ---- Valoración aduanera (DAV) ----
click $T_VAL; sleep 1.5; click 668 331; sleep 1; shot 36-valoracion-cuestionario
# operación anterior de la misma partida, para el historial de precios
click $NAV_OPS; sleep 2; field 495 168 "IMP-2025-099"; click 495 259; sleep 3
click $T_MER; sleep 1.5
click 1330 311; xdotool type --delay 40 "8471300010"; sleep 3; click 1170 475; xdotool key ctrl+a; xdotool type "30000"; click 1270 475; xdotool key ctrl+a; xdotool type "200"; click 1390 475; xdotool key ctrl+a; xdotool type "500"; click 1162 704; sleep 3
click 495 439; sleep 3; click $T_VAL; sleep 1.5; click 668 331; click 1566 700; sleep 1
field 877 346 "500"; field 877 398 "1000"; click 1327 418; xdotool type --delay 30 "Royalty por licencia + diseno del fabricante"; click 746 572; sleep 2; shot 37-valoracion-ajustes
click 730 706; sleep 3; click 1566 700; sleep 1; shot 38-valoracion-precios
click 1566 300; sleep 1; shot 39-valoracion-resultado
click $T_MER; sleep 1.5; click 1385 676; sleep 3
click $T_LIQ; sleep 2; shot 40-liquidacion-valor
click 1566 700; sleep 1; shot 41-liquidacion-items-costeo
field 755 604 "3000"; field 1150 604 "2000"; field 1497 604 "5"; click 732 649; sleep 3; shot 42-liquidacion-gastos
# ---- Despacho aduanero (DIM) ----
click $T_DES; sleep 2; click 705 515; sleep 1; click 823 515; sleep 2; shot 43-despacho-validacion-errores
field 730 364 "Tambo Quemado"; field 880 364 "La Paz"; field 1030 364 "ADA-0123"
click 730 416; xdotool type --delay 90 "Carre"; xdotool key Return; sleep 0.5
field 880 416 "CRT-77123"; field 1030 416 "MIC-9981"; field 712 470 "40"; field 825 470 "505"; field 935 470 "DAV-2026-55"
click 823 515; sleep 3; shot 44-despacho-datos-validados
click 1230 347; xdotool type --delay 90 "Roj"; xdotool key Return; sleep 0.5; click 1260 470; sleep 3; shot 45-despacho-canal-rojo
click $T_DEC; sleep 1.5
field 706 311 "200"; field 824 311 "4500"; field 976 311 "2800"
click 743 347; click 743 347; click 743 347; sleep 1; shot 18-decision-escenarios
cell 697 479 "FOB + flete propio"; cell 1089 479 "40000"; cell 1192 479 "1800"; cell 1271 479 "150"
cell 697 520 "CIF del proveedor"; click 1014 520; xdotool type --delay 90 "CIF"; xdotool key Return; sleep 0.5; cell 1089 520 "42000"
cell 697 559 "DAP del proveedor"; click 1014 559; xdotool type --delay 90 "DAP"; xdotool key Return; sleep 0.5; cell 1089 559 "44000"; cell 1350 559 "1200"
click 882 347; sleep 3; shot 19-decision-resultados
click $T_CON; sleep 1.5; field 710 311 "29197,20"; field 840 311 "0"; field 1085 311 "47982,68"; click 716 347; sleep 2; shot 20-contraste
click $T_COS; sleep 1.5; click 800 336; sleep 2; shot 21-costos-reales
click $T_RUT; sleep 2; click 1453 302; sleep 2; shot 22-ruta-critica
click $T_LEG; sleep 2; shot 23-legajo-bitacora
# ---- OCR de factura ----
click $NAV_OPS; sleep 2; click $T_MER; field 495 168 "IMP-2026-002"; click 495 259; sleep 3
click 985 680; sleep 3; xdotool type --delay 30 'C:\cb\ejemplos\factura-ejemplo.png'; xdotool key Return; sleep 15; shot 34-ocr-propuesta
click 1173 502; sleep 3; shot 35-ocr-confirmado
# ---- Configuración ----
click $NAV_CFG; sleep 2
field 1413 372 "6,96"; click 1312 507; sleep 2; shot 24-config-tipo-cambio
click $C_UFV; sleep 1.5; shot 25-config-ufv
click $C_PAR; sleep 1.5; shot 26-config-parametros
click $C_PER; sleep 1.5; shot 27-config-perfil
click $C_USU; sleep 1.5; shot 28-config-usuarios
click $C_DAT; sleep 1.5; shot 29-config-respaldo
click $NAV_PANEL; sleep 2; shot 30-panel
click $NAV_ACE; sleep 2; shot 31-acerca-de
click $NAV_OPS; sleep 2; click 495 440; sleep 1; click 495 896; sleep 2; shot 32-confirmar-eliminar-operacion
xdotool key y; sleep 2; shot 33-operacion-eliminada
wineserver -k 2>/dev/null; echo "Capturas en $OUT"; ls "$OUT" | wc -l
