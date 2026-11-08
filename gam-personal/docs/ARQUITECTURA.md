# Arquitectura, reglas de negocio y supuestos

## 1. Decisiones técnicas

| Tema | Decisión | Motivo |
|---|---|---|
| Backend | Python 3.11+ · FastAPI · SQLAlchemy 2 | Un solo código para web y escritorio; el motor de reglas son funciones puras (`app/services/motor.py`) fáciles de auditar |
| Base de datos | SQLite (por defecto) **o** PostgreSQL 16 con el mismo ORM | Probado: **las 53 pruebas pasan en ambos motores** |
| Frontend | HTML + JavaScript puro + CSS propio (SPA, sin dependencias) | Debe funcionar **sin Internet** en el escritorio y sin cadena de compilación Node. **Es una desviación consciente de "React o Vue + Tailwind"**: la especificación admite "interfaz moderna y accesible"; si su equipo exige React/Vue, la API REST (`/api/docs`) ya está lista para consumirse |
| Escritorio | Lanzador Python + `pywebview` (WebView2) + PyInstaller + instalador NSIS | Mismo backend local en `127.0.0.1`; datos en `%APPDATA%\GAMPersonal` |
| Reportes | `python-docx` (plantilla), `openpyxl`, `reportlab`, CSV/TXT UTF-8 | Formatos editables y abiertos |
| Seguridad | scrypt para claves, JWT HS256 de 10 h, roles ADMIN/RRHH/CONSULTA, bloqueo tras 5 intentos fallidos, cabeceras CSP/nosniff | Control de acceso mínimo exigible a un sistema de personal |

## 2. Estructura del código

```
backend/app/
  models.py            Modelo relacional (21 tablas)         db.py   Motor, sesión, triggers de inalterabilidad
  audit.py             Bitácora encadenada SHA-256            security.py  Autenticación y roles
  seed.py              Parámetros, horario, escalas, tipos de permiso, feriados nacionales 2026-2030
  services/
    motor.py           Reglas de asistencia y liquidación (PURO)
    biometrico.py      Parser ZKTeco / CSV / Excel
    proceso.py         Importación, procesamiento mensual, cierre/reapertura, correlativos
    personal.py        Carga masiva de personal   consultas.py  Datos de un periodo para reportes
    pdfs.py            Boleta e instructivo (PDF)  backup.py  Respaldo cifrado AES-256-GCM + SHA-256
  reports/             informe_docx.py · planillas_xlsx.py · asistencia_xlsx.py · auditoria_txt.py
  routers/             API REST por módulo (A: catalogos/personal · B: asistencia · C: permisos · D: reportes)
  templates/informe_asistencia.docx   Plantilla institucional (membrete, marco normativo, firmas)
```

## 3. Modelo de datos (resumen)

`entidad` · `unidad_organizacional` · `horario` + `turno` · `escala_sancion` · `feriado` · `empleado` · `contrato` ·
`import_biometrico` + `marca` · `permiso_tipo` + `permiso` · `correlativo` · `instructivo` + `instructivo_destinatario` ·
`periodo` · `asistencia_dia` · `liquidacion` · `usuario` · `audit_log` · `backup_registro`.
DDL completo: `db/schema_sqlite.sql` y `db/schema_postgresql.sql` (generados con `python -m app.cli ddl` desde el mismo modelo).

### Inalterabilidad (Ley 1178 – auditoría posterior)
* `marca`: trigger que **impide UPDATE** (las marcas se guardan tal como las entrega el reloj; se corrigen con justificaciones, nunca editándolas).
* `audit_log`: triggers que impiden UPDATE y DELETE **y** cada fila contiene el SHA-256 de la anterior; `GET /api/auditoria/verificar` recorre la cadena.
* Periodos **CERRADOS**: bloquean importaciones, permisos y reproceso; reabrir exige rol ADMIN y motivo (queda en bitácora).
* Los cites (`GAM-RRHH-INST-001/2026`, boletas, informes) usan un correlativo atómico por tipo y gestión; los anulados **no se reutilizan**.

## 4. Reglas del motor de asistencia (configurables en pantalla)

1. **Asignación de marcas**: no se confía en la etiqueta Entrada/Salida del reloj. Cada turno tiene una región delimitada por los puntos medios entre horas oficiales; ≥2 marcas en la región → primera = entrada, última = salida. Una sola marca: es entrada si cae antes de la mitad del turno **o** si el lapso hasta ella está cubierto por un permiso; si no, es salida (falta la entrada → *omisión*). Marcas a menos de 5 min se consideran doble pulsación. Los segundos se descartan.
2. **Tolerancia** (por horario, defecto 10 min): hasta ese minuto no hay retraso; superada, se cuenta el retraso **completo** desde la hora oficial (opción: contar solo el exceso). **Retraso grave**: > 30 min (configurable).
3. **Estados diarios**: Asistencia normal · Retraso leve · Retraso grave · Falta injustificada · Falta justificada · Omisión de marcación · No laborable · Feriado.
4. **Falta**: turno sin marcas y no cubierto por completo por un permiso aprobado. Fracción = duración del turno / jornada (0,5 con dos turnos iguales). Un permiso parcial no justifica un turno ausente.
5. **Permisos por horas** cubren retrasos/salidas dentro de su intervalo. Un permiso aprobado **no** anula la asistencia real (si la persona marcó, se computa asistencia).
6. **Escala de sanción por retrasos** del mes (editable, 2 modos): *por minutos acumulados* (0‑30 sin sanción · 31‑60 amonestación escrita · 61‑90 → 0,5 día · 91‑120 → 1 día · >120 → 2 días + llamada severa) o *por cantidad de retrasos* (ej. de la especificación: 1‑3 amonestación; 4‑6 → 0,5; 7+ → 1).
7. **Liquidación** (formato de la "Planilla de Remuneración" adjunta): `Total ganado = haber/30 × días trabajados (base comercial 30) + bono`; `Aporte laboral = 12,71 %` del total ganado; aporte patronal 17,21 % **solo informativo**; `RC‑IVA` dato manual por contrato; `Descuento = haber/30 × días de descuento`; `Líquido = ganado − aportes − RC‑IVA − descuento`. Los importes se redondean a 2 decimales por columna (las filas suman exacto). El descuento por asistencia se limita al total ganado.
8. **Días de descuento** = faltas × factor (planta/eventual ×2, consultor ×1) + escala de atrasos + permisos *sin goce* (planta/eventual).
9. **Consultor Individual de Línea**: sin sueldo, honorario pactado; sin aporte laboral por defecto; **máximo 1 día justificado al mes sin descuento**, siempre que el permiso esté autorizado por el fiscal de servicio (el sistema **rechaza (422)** aprobar un permiso de consultor sin ese dato, y en el cálculo ignora los que no lo tengan). Días justificados adicionales → descuento de honorario/30 por día.
10. **Abandono de funciones** (informe tipo): 3 días hábiles continuos o 6 discontinuos de falta en el mes → el informe recomienda remitir a la Autoridad Sumariante.

## 5. Supuestos y puntos que DEBE validar su Unidad Jurídica / RR.HH.

> Estos valores se tomaron de los documentos que usted adjuntó o de la especificación; **no los verifiqué contra la normativa vigente** y los textos legales del informe provienen de su plantilla. Todo es editable en *Configuración*.

| Tema | Valor usado | Origen |
|---|---|---|
| Descuento por falta injustificada = **doble** del haber diario (Art. 22 D.S. 25749) | ×2 | Informe tipo adjunto |
| Tolerancia 10 min; jornada 08:00‑12:00 y 14:30‑18:30 | 10 min | Informe tipo (rango "5 a 10") |
| Tramo 46‑60 min de la escala por minutos | Amonestación escrita | **Supuesto mío**: el informe tipo no define ese tramo (solo 31‑45 y 61‑90) |
| Escala por cantidad de retrasos | 1‑3 / 4‑6 / 7+ | Ejemplo ilustrativo de la especificación; ajuste a su RIP |
| Aporte laboral 12,71 % / patronal 17,21 % | Tasas de su planilla | Planilla adjunta (hay un caso con 1 %/15,5 % → use *tasa por contrato*) |
| Consultor: 1 día justificado/mes | 1 | Especificación |
| Duración de licencias (luto, matrimonio, cumpleaños, lactancia) | **sin tope** (queda a su RIP) | No quise inventar plazos; sí se validan paternidad = 3 días (D.S. 1212) y examen preventivo = 1 día (Ley 252) según su informe tipo |
| Feriados nacionales 2026‑2030 | Calculados (Pascua) | **Verifique cada año** los decretos (p. ej. Carnaval se siembra como asueto) y agregue feriados locales |

## 6. Limitaciones conocidas (honestas)

* **El `.exe`/instalador de Windows no se pudo compilar aquí** (entorno Linux). El lanzador se probó en Linux; `build_windows.bat`, el `.spec` y `installer.nsi` están escritos pero **sin ejecutar en Windows**: haga una primera compilación de prueba (ver manual §4).
* Los formatos de reloj se probaron con archivos sintéticos basados en su Excel y en el estándar ZKTeco ATTLOG; **no con exportaciones reales de Anviz/Dahua** (se cubren por nombres de columna usuales). Si un modelo exporta otra estructura, el parser rechaza las filas y lo informa sin detener la carga.
* Un empleado liquida con **un solo contrato por mes** (el de inicio más reciente); un cambio de haber a mitad de mes no se prorratea entre dos contratos.
* Los **saldos de vacaciones** no se calculan: se registran gestión y saldo como texto informativo en cada permiso.
* Retenciones de consultores (IT/IVA/RC‑IVA por factura) y bono de antigüedad automático **no** se calculan: el bono y el RC‑IVA son datos de entrada.
* La restauración en SQLite/PostgreSQL requiere que no haya otros usuarios operando; se recomienda reiniciar el servicio después.
* La frontera de una sola marca en el turno es heurística (§4.1); un retorno de almuerzo antes de las 13:15 se interpreta como salida de la mañana y se marca como *omisión* para su regularización.
