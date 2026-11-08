# Guía de pruebas con casos de uso reales

Dataset **ficticio** (nombres y C.I. inventados) del mes **octubre 2026** — elegido porque no tiene feriados nacionales y tiene **22 días hábiles** (el 2 de noviembre, mes del archivo de ejemplo, es feriado de Todos Santos). Se regenera de forma determinista con `python datos_prueba/generar_dataset.py`.

| Archivo (`datos_prueba/`) | Uso |
|---|---|
| `personal.csv` | Carga masiva de 5 servidores (2 permanentes, 2 eventuales, 1 consultor en línea) |
| `biometrico_octubre_2026.csv` / `.dat` / `.xlsx` | **Las mismas 408 marcas** en 3 formatos (delimitado, ZKTeco ATTLOG y Excel con el diseño `1_Marcaciones_Crudas`) |
| `permisos_octubre_2026.csv` | 6 permisos a registrar (5 aprobados + 1 pendiente) |
| `cargar_dataset.py` | Carga todo por la API y descarga los 6 reportes (`pip install httpx`) |

## 1. Escenario de cada servidor (jornada 08:00‑12:00 / 14:30‑18:30, tolerancia 10 min, retraso grave > 30 min)

| Código | C.I. | Modalidad | Haber/Honorario | Incidencias sembradas |
|---|---|---|---|---|
| 1001 Mamani Quispe Juan Carlos | 1000001 | Permanente | 6.000 | 06/10 entra 08:12 (12 min) · 20/10 vuelve de almuerzo 14:48 (18 min) · 14/10 **sin marca de salida mañana** (omisión) |
| 1002 Vargas Rojas María Elena | 1000002 | Permanente | 4.500 | 02/10 08:25 (25 min) · 07/10 08:45 (**45 min, grave**) · 15/10 **falta** día completo |
| 2001 Choque Condori Luis Alberto | 1000003 | Eventual | 3.800 | 12‑13/10 licencia médica aprobada · 21/10 permiso 08:00‑10:00 y llega 10:05 (**retraso cubierto**) · 28/10 **sin marcas en la tarde** (media falta) |
| 2002 Flores Apaza Carla Andrea | 1000004 | Eventual (alta 01/10) | 3.500 | 09/10 permiso particular **sin goce** · 14/10 vuelve 14:52 (22 min) · 22/10 sin marca de entrada tarde (omisión) |
| 3001 Salazar Copa Miguel Ángel | 1000005 | Consultor en línea (concluye 30/10) | 7.000 | 08/10 y 19/10 **2 días justificados con fiscal** (1 gratis + 1 de exceso) · 13/10 08:50 (**50 min, grave**) · 27/10 permiso **PENDIENTE** (no justifica → falta) |

## 2. Procedimiento

**Opción A – por la interfaz** (web `http://servidor:8000` o escritorio):
1. *Primer ingreso*: cree el administrador. En **Configuración** complete nombre, sigla, ciudad, SIGEP, MAE, responsable de RR.HH. y quien aprueba (si quedan vacíos, el `.docx` mostrará `[Nombre Completo]`).
2. **Personal** → *Importar* `personal.csv` → debe decir *Creados: 5 · Errores: 0*.
3. **Marcaciones** → importar `biometrico_octubre_2026.dat` (o `.csv`/`.xlsx`) → *leídas 408, nuevas 408, duplicadas 0, rechazadas 0*.
   *Prueba de duplicados:* importe después el `.csv` → *nuevas 0, duplicadas 408* (mismas marcas, otro formato). Reimportar **el mismo archivo** es rechazado ("ya fue importado").
4. **Permisos y boletas** → *Nueva solicitud* y registre las 6 filas de `permisos_octubre_2026.csv` (octubre/2026). Verifique que la boleta PDF se genera con correlativo `GAM-RRHH-BOL-00N/2026`. Pruebe aprobar el permiso de consultor **sin** "Autorizado por": debe rechazarse con el mensaje del fiscal.
5. **Inicio / Planilla** → mes *Octubre 2026* → *Procesar periodo*.
6. **Reportes** → descargue los 6.

**Opción B – por script:** `python datos_prueba/cargar_dataset.py --url http://127.0.0.1:8000 --clave 'SuClave#2026' --salida reportes_prueba`

**Opción C – automática:** `cd backend && python -m pytest tests -q` → **53 pruebas** (26 del motor, 6 del parser, 21 de punta a punta; verde en SQLite y en PostgreSQL 16).

## 3. Resultados esperados (calculados a mano)

### 3.1 Liquidación (base de los reportes 4, 5 y 6)

| Servidor | Días lab. | Asistidos | Faltas | Min. retraso | Justif. | Días de descuento | Total ganado | AFP 12,71 % | Desc. asistencia | **Líquido** |
|---|---|---|---|---|---|---|---|---|---|---|
| 1001 Mamani | 22 | 22 | 0 | 30 | 0 | 0 | 6.000,00 | 762,60 | 0,00 | **5.237,40** |
| 1002 Vargas | 22 | 21 | 1 | 70 | 0 | **2,5** (1×2 falta + 0,5 escala) | 4.500,00 | 571,95 | 375,00 (300+75) | **3.553,05** |
| 2001 Choque | 22 | 19,5 | 0,5 | 0 | 2 | **1** (0,5×2) | 3.800,00 | 482,98 | 126,67 | **3.190,35** |
| 2002 Flores | 22 | 21 | 0 | 22 | 1 | **1** (sin goce) | 3.500,00 | 444,85 | 116,67 | **2.938,48** |
| 3001 Salazar | 22 | 19 | 1 | 50 | 2 | **2** (1 falta ×1 + 1 exceso) | 7.000,00 | 0,00 | 466,66 (233,33+233,33) | **6.533,34** |
| **Totales** | | | | | | | **24.800,00** | **2.262,38** | **1.085,00** | **21.452,62** |

Sanciones por retrasos: 1002 → *Descuento 0,5 día* (70 min en tramo 61‑90) · 3001 → *Amonestación escrita* (50 min) · 1001 (30 min) y 2002 (22 min) → sin sanción. Cálculo del día: `haber ÷ 30` (4.500/30 = 150 → 2,5 días = 375).
Control de cruce: ganado − aportes − descuento = 24.800,00 − 2.262,38 − 1.085,00 = **21.452,62** ✔.

### 3.2 Estados diarios destacados
`02/10` Vargas → Retraso leve (25) · `07/10` Vargas → **Retraso grave** (45) · `15/10` Vargas → **Falta injustificada** (1) · `12/10` Choque → **Falta justificada** · `21/10` Choque → Normal (retraso cubierto por el permiso) · `28/10` Choque → Falta injustificada 0,5 · `14/10` Mamani y `22/10` Flores → **Omisión de marcación** · `27/10` Salazar → Falta injustificada (el permiso pendiente no cuenta; al **aprobarlo** con fiscal el motor se actualiza solo y el descuento sube a 466,67) · `03‑04/10` → No laborable.

### 3.3 Los 6 reportes

1. **Informe de asistencia (.docx)** — membrete del municipio, `CITE: GAM-VE/DAF/URRHH/INF-ASIST/N° S/N (BORRADOR)/2026` (con *Emitir*: `N° 001`), periodo "Del 01 al 31 de octubre de 2026 (22 días hábiles administrativos)".
   *Cuadro de resumen (§3)*: Total controlado **5 / 110 días‑hombre / 100 %** · Asistencia regular puntual **0 servidores / 94 días / 85,45 %** · Con atrasos **4 / 172 minutos** · Vacación **0** · Licencias con goce **2 servidores / 3 días / 2,73 %** · Permisos y comisiones **2 / 2 días (16 h) / 1,82 %** · Faltas injustificadas **3 / 2,5 días / 2,27 %**.
   *§4 Atrasos*: Vargas (2 · 70 min · descuento 0,5 día), Salazar (1 · 50 min · amonestación), Mamani (2 · 30 min · sin sanción), Flores (1 · 22 min · sin sanción).
   *§6*: 5 licencias/permisos. *§7*: faltas de Vargas (15/10, descuento ×2 = 2 días), Choque (28/10, 0,5 día), Salazar (27/10, ×1) y tabla de **omisiones** (Mamani 14/10, Flores 22/10). *§8*: índice 85,45 % y recomendaciones (descuentos por atrasos: 1 servidor; faltas: 3; exceso de ausencias de consultor: Salazar). Sin abandono de funciones.
2. **Planilla de Nuevo Personal (.xlsx)** — 1 fila: **Flores Apaza Carla Andrea**, ingreso 01/10/2026, Eventual, partida 12100, vigencia 31/12/2026, 30 días, ganado 3.500,00, líquido **2.938,48**.
3. **Planilla de Desvinculados (.xlsx)** — 1 fila: **Salazar Copa Miguel Ángel**, baja 30/10/2026, causal *Conclusión de contrato*, honorario 7.000,00, líquido **6.533,34**.
4. **Planilla de Sueldos (.xlsx)** — 3 bloques: Permanentes (2 · ganado 10.500,00 · líquido 8.790,45) · Eventuales (2 · 7.300,00 · 6.128,83) · Consultores (1 · 7.000,00 · 6.533,34) · **Total general 24.800,00 / 21.452,62** (fórmulas `SUM` auditables; hoja *Resumen*).
5. **Reporte detallado (.xlsx)** — *Resumen institucional* (5 filas con los valores de §3.1), *Detalle diario* (154 filas = 4×31 + 30, coloreadas por estado), *Faltas y retrasos* (**16** registros: 4 retrasos leves, 2 graves, 3 faltas injustificadas, 5 justificadas, 2 omisiones), *Leyenda* con las reglas aplicadas.
6. **Consolidado plano (.txt UTF‑8, tabulador, sin BOM)**:
```
PERIODO CI      CODIGO TIPO_CONTRATO   DIAS_LAB ASIST  FALTAS MIN_RET JUSTIF IMPORTE_DESC
2026-10 1000001 1001   PERMANENTE      22       22.00  0.00   30      0.00   0.00
2026-10 1000002 1002   PERMANENTE      22       21.00  1.00   70      0.00   375.00
2026-10 1000003 2001   EVENTUAL        22       19.50  0.50   0       2.00   126.67
2026-10 1000004 2002   EVENTUAL        22       21.00  0.00   22      1.00   116.67
2026-10 1000005 3001   CONSULTOR_LINEA 22       19.00  1.00   50      2.00   466.66
```
(encabezados reales: `PERIODO CI CODIGO_EMPLEADO TIPO_CONTRATO TOTAL_DIAS_LABORABLES DIAS_ASISTIDOS FALTAS MINUTOS_RETRASO DIAS_PERMISO_JUSTIFICADO IMPORTE_DESCUENTOS_APLICADOS`; opciones: coma, punto y coma, BOM).

## 4. Pruebas negativas / de control

| Acción | Resultado esperado |
|---|---|
| Aprobar permiso de consultor sin "Autorizado por" | 422 "… autorizado por el fiscal de servicio…" |
| Reimportar el mismo archivo biométrico | 422 "ya fue importado (lote N)" |
| Importar `.xlsx` sin columnas de ID/Fecha/Hora o dañado | 422 con mensaje claro |
| Fila con fecha/hora inválida | Se rechaza **solo esa fila**, el resto se importa (se informa) |
| Generar reportes de un mes no procesado | 422 "aún no fue procesado" |
| Cerrar periodo → importar/permiso/reprocesar | Bloqueado; reabrir exige ADMIN y motivo ≥ 10 caracteres |
| `UPDATE`/`DELETE` directo sobre `audit_log` o `UPDATE` sobre `marca` | La base lo rechaza (trigger) |
| Alterar un byte de un respaldo / hash incorrecto / contraseña errónea | Verificación y restauración fallan sin tocar los datos |
| Usuario CONSULTA intenta procesar o respaldar | 403 |
| Sin token / token inválido | 401 |
