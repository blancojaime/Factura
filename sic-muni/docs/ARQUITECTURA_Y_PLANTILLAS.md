# Arquitectura de datos, flujo y plantillas

Todas las rutinas leen/escriben por **nombre de columna** (fila 1), no por posición. Las hojas de datos y las
plantillas quedan `xlSheetVeryHidden` + protegidas (`ProtectDB`). Las columnas marcadas **+** se agregaron a
las que pide la especificación porque el flujo las necesita.

## 1. Tablas

| Hoja | Columnas |
| :-- | :-- |
| `CONFIG` | Clave, Valor, Descripcion |
| `SECUENCIAS` | Clave, Ultimo |
| `SYS_AUTH` | Usuario, PasswordHash (`sal$hash`), NombreCompleto, Rol, Dependencia_DA, Estado (ACTIVO/BLOQUEADO/INACTIVO), **+**Intentos, **+**UltimoAcceso |
| `CAT_CHB` | CodigoUNSPSC, Descripcion, Unidad, FichaTecnicaCHB (VERDADERO/FALSO), Tipo, Vigencia (fecha), RequiereAutorizacionMDPyEP |
| `PRESUPUESTO` | Gestion, DA, UE, Programa, Proyecto, ActObra, Fuente, Organismo, Partida_ObjetoGasto, DescripcionPartida, PresupuestoAprobado (K), PreventivoComprometido (L), SaldoDisponible (M, fórmula `=IF(K2="","",K2-L2)`) |
| `SOLICITUDES` | ID_Solicitud, Correlativo, Fecha, Cod_DA, Cod_UE, Solicitante, Justificacion, Estado, **+**Modalidad, **+**MontoReferencial |
| `SOLICITUDES_DET` | ID_Solicitud, Item, CodigoUNSPSC, Descripcion, Cantidad, Unidad, PrecioRefUnitario, PrecioRefTotal, CumpleCHB, CodigoExcepcionMDPyEP, **+**JustificacionExcepcion, **+**NroAutorizacionMDPyEP, **+**FechaAutorizacion |
| `COTIZACIONES` | ID_Cotizacion, ID_Solicitud, Proveedor_NIT, RazonSocial, **+**FechaCotizacion, ValidezOferta, MontoTotalCotizado, CumplimientoTecnico, Recomendado, **+**Adjudicada |
| `ORDENES_GASTO` | NroOrden, Tipo, CUCE_SICOES, ID_Solicitud, **+**ID_Cotizacion, Proveedor_Adjudicado, NIT, MontoTotal, NroPreventivo_C31, EstadoC31, FechaEmision, **+**PlazoDias, **+**LugarEntrega, **+**EstadoOrden (EMITIDA/RECIBIDA/ANULADA), **+**MotivoAnulacion, **+**Usuario |
| **+**`C31` | NroInterno, Fecha, ID_Solicitud, DA, UE, MontoTotal, MontoRevertido, Estado, NroC31_SIGEP, Usuario |
| **+**`C31_DET` | NroInterno, Linea, Programa, Proyecto, ActObra, Fuente, Organismo, Partida, Importe, ImporteRevertido |
| **+**`RECEPCIONES` | NroRecepcion, NroOrden, FechaRecepcion, FechaLimite, DiasRetraso, MontoMulta, Resultado (CONFORME/OBSERVADA), Observaciones, Usuario |
| **+**`AUDITORIA` | Fecha, Usuario, Rol, Accion, Detalle |

Las columnas de códigos (DA, UE, programa, partida, NIT, UNSPSC, N° SIGEP) se formatean como **texto** para no perder ceros a la izquierda.

## 2. Estados y reglas de bloqueo

`SOLICITUDES.Estado`: `BORRADOR → EN_COTIZACION → EVALUADA → PRESUPUESTADA → ADJUDICADA → ORDEN_EMITIDA` (la reversión total de C-31 vuelve a `EVALUADA`).
`C31.Estado`: `PREVENTIVO → ASOCIADO → REVERTIDO_PARCIAL | REVERTIDO_TOTAL`.
`SOLICITUDES_DET.CumpleCHB`: `N/A` (fuera de catálogo), `SI` (catálogo + ficha vigente), `EXCEPCION` (excepción completa), `NO` (pendiente → **bloquea**).

| Regla | Dónde |
| :-- | :-- |
| Monto > `TopeContratacionMenor` no pasa a cotización | `EnviarACotizacion` |
| Monto > `TopeSinCuadroComparativo` exige `MinCotizaciones` cotizaciones | `EvaluarCuadro`, `GenerarCuadroComparativo` |
| Empate en precio más bajo no se resuelve solo | `EvaluarCuadro` |
| Reserva C-31 solo con solicitud `EVALUADA`; valida saldo de **todas** las líneas antes de aplicar (todo-o-nada) | `EmitirC31` |
| Adjudicar exige oferta recomendada, CHB habilitado y C-31 vigente que cubra el monto | `Adjudicar` |
| Orden exige además `ADJUDICADA`, CHB habilitado (reconsulta vigencia de ficha) y, si `ExigirC31SIGEPParaOrden=SI`, C-31 asociado a SIGEP | `GenerarOrden` |
| No se revierte totalmente un C-31 con Orden vigente | `RevertirTotal` |

## 3. Matriz RBAC (`PuedeHacer`)

| Permiso | US | RC | PF | ADM |
| :-- | :-: | :-: | :-: | :-: |
| SOLICITUD_EDIT (solo su DA para US) | ✔ | ✔ | | |
| COTIZACION_EDIT, CHB_EVAL, ADJUDICAR, ORDEN_EMIT | | ✔ | | |
| PRESUPUESTO_EDIT, C31_EMIT, C31_REVERT | | | ✔ | |
| DOC_PRINT (US solo el C-1) | ✔ | ✔ | ✔ | ✔ |
| USUARIOS_ADM, CONFIG_ADM, AUDIT_VIEW | | | | ✔ |

Bloqueo tras `MaxIntentosLogin` fallos; cierre de sesión por inactividad `TimeoutSesionMin`.

## 4. Plantillas (creadas por `BuildTemplates`)

Cada plantilla: fila 1 = entidad (`XX_Entidad`), fila 2 = título, fila 3 = gestión (`XX_Gestion`), pie `XX_Pie`.
El detalle tiene capacidad fija; las filas sobrantes se **ocultan** y las columnas calculadas son fórmulas de la plantilla (VBA no las toca).

| Hoja (prefijo) | Orient. | Campos con nombre (celda) | Tabla (encabezado → 1ª fila, capacidad) | Fórmulas |
| :-- | :-- | :-- | :-- | :-- |
| `Doc_Solicitud_C1` (`C1_`) | Vertical | Solicitud C5, Fecha G5, DA C6, UE G6, Solicitante C7, Modalidad G7, Justificacion C8, Literal A27 | Fila 10 → `C1_ItemsIni`=A11, 15 filas, 8 col. | `G11:G25 =IF(E11="","",ROUND(E11*F11,2))`; `G26 =SUM(G11:G25)` |
| `Doc_CuadroComparativo` (`CC_`) | Horizontal | Solicitud C5, Fecha G5, Modalidad C6, Referencial G6, Criterio C7, Recomendacion A22 | Fila 9 → `CC_OfertasIni`=A10, 10 filas, 7 col. | `H10:H19 =IF(E10="","",E10/$G$6-1)`; `F20 =IFERROR(AGGREGATE(15,6,E10:E19/(F10:F19="Cumple"),1),"")` (Excel ≥ 2010) |
| `Doc_JustificacionExcepcionCHB` (`EX_`) | Horizontal | Solicitud C5, Fecha G5, DA C6, Solicitante G6 | Fila 12 → `EX_ItemsIni`=A13, 10 filas, 7 col. | — (autoajuste de alto de fila al volcar) |
| `Doc_Preventivo_C31` (`PV_`) | Horizontal | Nro C5, Sigep H5, Fecha C6, Estado H6, DA C7, UE H7, Solicitud C8, Literal A22 | Fila 10 → `PV_LineasIni`=A11, 10 filas, 9 col. | `J11:J20 =IF(H11="","",H11-I11)`; `H21:J21 =SUM(…)` |
| `Doc_OrdenCompraServicio` (`OC_`) | Vertical | Titulo A2, Nro C4, Fecha F4, CUCE C5, Solicitud F5, Proveedor C6, NIT C7, C31 F7, Plazo C8, Lugar C9, Monto F27, Literal A28, PenPorMil H2, PenMaxPct I2 | Fila 11 → `OC_ItemsIni`=A12, 15 filas, 4 col. | Cláusulas 1, 2, 3 y 5 son fórmulas que concatenan los rangos con nombre (`OC_Plazo`, `OC_PenPorMil`, `TEXT(OC_Monto,"#,##0.00")`, …) |

| `Doc_ActaRecepcion` (`AR_`) | Vertical | Nro C4, Fecha F4, Orden C5, Solicitud F5, Proveedor C6, Limite C7, Dias F7, Monto C8, Multa F8, Conformidad C9, Obs C10 | — | `C11 =IF(AR_Monto="","",AR_Monto-AR_Multa)` |

Nombres duplicados entre hojas no existen: cada uno lleva el prefijo del documento. Si se rediseña una plantilla,
basta mantener los nombres y el ancho de la tabla (`nCols` en la llamada a `FillTable`).

## 5. Lista de pruebas sugerida

1. `InstalarSistema` → `CargarDatosDemo` → `ConstruirFormularios` → cerrar/abrir.
2. Crear usuarios US, RC, PF; verificar bloqueo al 3er intento fallido y que ADM no pueda emitir C-31.
3. Solicitud con ítem `44121600` (ficha vigente) y `56101500` (sin ficha): el segundo debe bloquear la Orden hasta cargar excepción completa.
4. Monto de 25.000 → exige 3 cotizaciones; de 60.000 → no pasa a cotización.
5. C-31 sobre partida demo (saldo 100.000): emitir, intentar exceder saldo, revertir parcial/total y comprobar `PreventivoComprometido`.
6. Generar los 5 PDF y revisar membrete, totales y monto en literal.
