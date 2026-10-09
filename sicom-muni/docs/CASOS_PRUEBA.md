# Casos de prueba de validación

Ambos casos están **automatizados** (`backend/tests/test_flujo_bienes.py`, `test_flujo_servicio.py`) y se ejecutan de punta a punta
contra la API real (SQLite y PostgreSQL). Aquí se describen para ejecutarlos también **manualmente desde la interfaz** con los
usuarios demo (clave `Sicom#2026Demo`). Partidas demo: 34200 (Bs 80.000) y 25800 (Bs 45.000).

## Caso 1 — Bienes: material de construcción, Bs 18.500

**Objetivo:** validar compra directa (≤ Bs 20.000, sin F110), Orden de Compra (plazo ≤ 15 días), bloqueo y excepción CHB, sobres sellados y devengado.

| Paso | Usuario | Acción | Resultado esperado |
|---|---|---|---|
| 1 | solicitante | Nueva solicitud: «Adquisición de material de construcción para mantenimiento de la plaza principal», Bien, plazo 10 días | Trámite `CM-AAAA-NNNNNN` en BORRADOR |
| 2 | solicitante | Ítems (partida 34200): cemento 30111505, 120 bolsas × 62,00; ladrillo 30131501, 3.950 × 1,30; arena 11111501, 30 m³ × 85,00; piedra 11111503, 25 m³ × 135,00 | Total **18.500,00**; modalidad **Compra directa**; formalización **Orden de Compra**; cemento y ladrillo marcados **Compra CHB obligatoria**, arena y piedra **Sin coincidencia** |
| 3 | solicitante | Intentar «Enviar solicitud» | **Bloqueado**: debe comprar por el Catálogo «Compro Hecho en Bolivia» o justificar |
| 4 | solicitante | Marcar cemento y ladrillo «fuera de catálogo», justificación ≥ 80 caracteres y código de autorización; enviar | Estado SOLICITADO; se generan **C-1** e **Informe de Excepción CHB** |
| 5 | presupuesto | Ver bloque SIGEP previsto; certificar con preventivo `C31-2026-00123` | CERTIFICADO_PRESUPUESTO; saldo 34200: 80.000 → **61.500**; bloque `01 \| 001 \| 01 \| 0000 \| 001 \| 20 \| 230 \| 34200 \| 18500.00` |
| 6 | rpa | Aprobar inicio | EN_COTIZACION (no exige Formulario 110) |
| 7 | contrataciones | Cargar cotizaciones: FERRETERIA EL CONSTRUCTOR S.R.L. (NIT 1023456028) Bs 18.200, 8 días; MATERIALES BOLIVIA LTDA. (NIT 4012345011) Bs 17.900, 10 días. Probar NIT repetido | Montos **sellados** (no visibles); NIT repetido rechazado |
| 8 | contrataciones | Abrir ofertas; calificar ambas «cumple»; ver matriz | Ranking 1.° MATERIALES BOLIVIA (17.900) |
| 9 | contrataciones | Evaluar | EVALUADO; se genera **Cuadro comparativo** |
| 10 | rpa | Adjudicar (asistente: aceptar recomendada) | ADJUDICADO; **Nota de adjudicación** |
| 11 | rpa | Formalizar (probar «Contrato») | Contrato **rechazado** (plazo 10 días); correcto: **Orden de Compra** |
| 12 | recepcion | Recepción con 100 bolsas de cemento (faltan 20), «conforme» | Rechazada (cantidad ≠ pedida); con «no conforme» + observación → sigue FORMALIZADO |
| 13 | recepcion | Recepción conforme completa | RECEPCIONADO; **Acta/Informe NIA-…** |
| 14 | presupuesto | Devengar | DEVENGADO; saldo 34200 = **62.100** (se libera 18.500 − 17.900 = 600) |
| 15 | admin | Auditoría → «Verificar integridad» | Cadena íntegra |

## Caso 2 — Servicio: mantenimiento eléctrico, Bs 32.000 (Consulta de Precios SICOES)

**Objetivo:** validar F110 obligatorio, mínimo de cotizaciones, margen de preferencia MyPE, apertura de sobres y regla de plazo (Orden vs Contrato).

| Paso | Usuario | Acción | Resultado esperado |
|---|---|---|---|
| 1 | solicitante | Servicio general «Mantenimiento correctivo de las instalaciones eléctricas del edificio municipal», plazo 12 días; ítem partida 25800, Global, 1 × 32.000 | Modalidad **Consulta de Precios SICOES**; ítem CHB «No aplica» |
| 2 | solicitante → presupuesto → rpa | Enviar; certificar (`C31-2026-00456`); aprobar inicio | Saldo 25800: 45.000 → 13.000; EN_COTIZACION |
| 3 | contrataciones | Intentar cargar cotización o emitir fichas **sin** F110 | Error `FORMULARIO_110_REQUERIDO` |
| 4 | contrataciones | Registrar F110 `F110-2026-000457` con plazo de ofertas (+2 h) | Se habilita la captura |
| 5 | contrataciones | Emitir fichas (Impreso, WhatsApp, Correo) para ELECTRO SERVICIOS S.R.L. | PDF de ficha; enlace `wa.me`; correo «NO_CONFIGURADO» si no hay SMTP |
| 6 | contrataciones | Ofertas: ELECTRO SERVICIOS 31.500 (12 d); INSTALACIONES BOLIVIA LTDA. (MyPE) 30.800 (10 d); MANTENIMIENTO INTEGRAL S.A. 29.900 (12 d); OFERTAS BARATAS S.R.L. 28.000 (12 d) | Sobres sellados |
| 7 | contrataciones | «Abrir ofertas» antes del plazo | Rechazado `PLAZO_VIGENTE`. (En pruebas automáticas se vence el plazo en BD; manualmente espere o registre un plazo corto) |
| 8 | contrataciones | Calificar: OFERTAS BARATAS **no cumple**; INSTALACIONES BOLIVIA con registro MyPE válido, margen 5 % | Precio evaluado 30.800 × 0,95 = **29.260** → 1.° lugar (supera a 29.900); OFERTAS BARATAS excluida pese a ser la más barata |
| 9 | contrataciones | Evaluar | EVALUADO (≥ 3 ofertas; con menos: `COTIZACIONES_INSUFICIENTES`) |
| 10 | rpa | Adjudicar otra oferta sin motivo / una no elegible | Rechazado; adjudicar la recomendada: ADJUDICADO |
| 11 | rpa | Formalizar sin CUCE | Rechazado (CUCE obligatorio); con `26-1234-00-1234567-1-1` → **Orden de Servicio** |
| 12 | recepcion | Recepción conforme | RECEPCIONADO; **Informe de conformidad IC-…** |
| 13 | presupuesto | Devengar | Saldo 25800 = 45.000 − 32.000 + **1.200** = 14.200 |

**Variante (plazo 20 días):** metodo de formalización calculado = **Contrato Administrativo**; intentar Orden de Compra/Servicio devuelve `FORMALIZACION_CONTRATO_OBLIGATORIO`; se genera el **Contrato** y no la orden.

## Supuestos del sistema (no verificados con la norma)
Mínimo de 3 cotizaciones en consulta de precios (1 en compra directa); una oferta elegible debe ser ≤ monto referencial y ofrecer plazo ≤ el solicitado; desempate por la primera propuesta recibida. Todos son parámetros ajustables.
