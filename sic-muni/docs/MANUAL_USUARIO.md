# SIC-MUNI — Manual de Usuario

Sistema Integrado de Contrataciones Municipales — Contratación Menor

Versión 1.0 · Octubre 2026 · Para Unidad Solicitante (US), Responsable de Contrataciones (RC), Presupuesto/Finanzas (PF) y Administrador (ADM)

---

## 1. Para qué sirve el sistema

SIC-MUNI es un libro de Excel con macros que lleva una contratación menor desde que la unidad pide un bien o servicio hasta que se recibe y se emite el acta de conformidad. En una sola pantalla se hace:

- La **solicitud** con sus ítems y especificaciones técnicas (Formulario C-1).
- La **verificación del catálogo "Compro Hecho en Bolivia" (CHB)** y el registro de excepciones.
- Las **cotizaciones**, el cuadro comparativo y la adjudicación.
- La **reserva presupuestaria** (C-31 Preventivo) con control de saldo, su asociación al número de SIGEP y sus reversiones.
- La **Orden de Compra o de Servicio**, la recepción con cálculo de multa por retraso y el acta de recepción.
- Los **documentos en PDF** con el membrete del Gobierno Autónomo Municipal.

> **Importante.** El C-31 que genera este sistema es un registro interno de reserva. El C-31 oficial se registra y aprueba en el SIGEP; aquí solo se anota su número. El sistema no se conecta al SIGEP ni al SICOES.

## 2. Quién hace qué

Cada persona ve y puede ejecutar solo lo que corresponde a su rol. Si intenta algo que no le corresponde, el sistema lo rechaza y lo registra en la auditoría.

| Rol | Quién es | Qué hace en el sistema |
| :-- | :-- | :-- |
| **US** Unidad Solicitante | Servidor público de la unidad que necesita el bien o servicio | Crea solicitudes de **su propia Dirección Administrativa (DA)**, agrega ítems, las envía a cotización e imprime el C-1 |
| **RC** Responsable de Contrataciones | Encargado de compras menores | Evalúa el catálogo CHB, registra excepciones y cotizaciones, evalúa el cuadro comparativo, adjudica, emite la Orden, registra la recepción y puede anular |
| **PF** Presupuesto / Finanzas | Unidad de contabilidad / presupuesto | Consulta saldos, emite el C-31 Preventivo, lo asocia al número de SIGEP y hace reversiones parciales o totales |
| **ADM** Administrador | Máxima autoridad administrativa o su delegado | Crea usuarios, desbloquea cuentas, importa catálogo y presupuesto, configura la entidad y revisa la auditoría. **No registra transacciones** (separación de funciones) |

## 3. El recorrido completo de una contratación

```
US  crea solicitud ─► agrega ítems ─► envía a cotización
                                         │
RC  evalúa CHB ─► registra cotizaciones ─► evalúa cuadro (queda EVALUADA)
                                         │
PF  verifica saldo ─► emite C-31 Preventivo ─► lo registra en SIGEP ─► asocia el N° SIGEP
                                         │
RC  adjudica ─► genera Orden ─► (recepción) ─► acta de recepción
```

Estados por los que pasa una solicitud (se ven en la línea "Estado:" de la pantalla):

| Estado | Significa | Siguiente paso |
| :-- | :-- | :-- |
| BORRADOR | Se está armando; se pueden agregar ítems | US: enviar a cotización |
| EN_COTIZACION | Recibiendo cotizaciones y evaluación CHB | RC: registrar cotizaciones y evaluar el cuadro |
| EVALUADA | Hay una oferta recomendada | PF: reservar presupuesto |
| PRESUPUESTADA | Tiene C-31 Preventivo vigente | RC: adjudicar. PF: asociar el N° de SIGEP (antes de generar la Orden) |
| ADJUDICADA | Oferta adjudicada | RC: generar la Orden (antes PF asocia el N° SIGEP) |
| ORDEN_EMITIDA | Tiene Orden vigente | RC: registrar la recepción |
| ANULADA | Cancelada | — |

## 4. Entrar y salir del sistema

### 4.1 Abrir el sistema

1. Abra el archivo `SIC-MUNI.xlsm` (normalmente en `C:\SIC-MUNI`).
2. Si Excel muestra una barra amarilla **"Habilitar contenido"**, púlsela. Sin eso el sistema no funciona.
3. Aparece la ventana **Inicio de sesión**. Escriba su usuario y contraseña y pulse **Ingresar**.

> Solo **una persona a la vez** puede tener abierto el archivo. Si otro usuario lo está usando, Excel le avisará que está en uso: espere a que lo cierre.

### 4.2 Reglas de acceso

- Tras **3 intentos fallidos** la cuenta se bloquea. Pida al Administrador que la desbloquee.
- Tras **20 minutos sin actividad** la sesión se cierra por seguridad (el tiempo lo define el Administrador). Vuelva a ingresar.
- La contraseña debe tener **al menos 10 caracteres** con mayúsculas, minúsculas y números. No la comparta.
- Para cambiar su contraseña, pida al Administrador (menú opción 3).

### 4.3 Salir

Pulse **Cerrar sesión** (arriba a la derecha de la pantalla principal) y luego cierre el libro de Excel. Responda **Guardar** si Excel pregunta.

## 5. La pantalla principal (US, RC y PF)

Después de iniciar sesión aparece la pantalla **Contrataciones Menores**:

| Zona | Contenido |
| :-- | :-- |
| Arriba | Su nombre, rol y DA; botón **Cerrar sesión** |
| Segunda línea | Casilla **Solicitud N°**, botón **Cargar** y, a la derecha, el estado de la solicitud, el monto referencial y la modalidad |
| Pestañas | **1 Solicitud · 2 Evaluación CHB · 3 Cotizaciones · 4 Presupuesto / C-31 · 5 Orden / Recepción** |
| Cuerpo | Los campos y botones de la pestaña elegida |

Cómo trabajar con una solicitud que ya existe: escriba su número (por ejemplo `SOL-2026-000001`) en **Solicitud N°** y pulse **Cargar**. Se actualizan el estado, la lista de ítems y la lista de cotizaciones.

Los botones que su rol no puede usar aparecen **deshabilitados** (en gris).

Los **PDF** se guardan en la carpeta `PDF` junto al libro (por ejemplo `C:\SIC-MUNI\PDF\`). Al terminar, el sistema muestra la ruta del archivo.

## 6. Guía para la Unidad Solicitante (US)

### 6.1 Crear una solicitud (pestaña 1)

1. Escriba la **DA** y la **UE** (Unidad Ejecutora). La DA ya aparece con la suya y debe ser la suya: el sistema no permite crear solicitudes de otra DA.
2. Escriba la **Justificación** (al menos 20 caracteres): por qué se necesita la compra o el servicio.
3. Pulse **Crear solicitud**. El sistema asigna el número (por ejemplo `SOL-2026-000001`) y lo muestra en **Solicitud N°**. **Anótelo.**

### 6.2 Agregar ítems

Para cada bien o servicio:

1. **Código UNSPSC**: escríbalo y salga del campo. Si el código está en el catálogo CHB, aparece una **alerta en rojo** y se completan solos la descripción y la unidad.
2. **Descripción**: especificaciones técnicas claras. No deben dirigir la compra a un proveedor determinado.
3. **Unidad**, **Cantidad** y **P. ref. unit. (Bs)**: el precio referencial por unidad.
4. Pulse **Agregar item**. El ítem aparece en la lista con su total.

Al agregar un ítem que está en el catálogo CHB el sistema muestra un aviso: la decisión (comprar por catálogo o pedir excepción) la toma el Responsable de Contrataciones en la pestaña 2. No necesita hacer nada más.

La línea de estado muestra el **monto referencial** acumulado y la **modalidad** que corresponde:

| Monto referencial | Modalidad que muestra el sistema |
| :-- | :-- |
| Hasta Bs 20.000 | Contratación menor |
| Más de Bs 20.000 y hasta Bs 50.000 | Contratación menor con invitación y cuadro comparativo (se exigen 3 cotizaciones) |
| Más de Bs 50.000 | Fuera de alcance: debe tramitarse como ANPE/Licitación fuera de este sistema |

> Los topes son los que configuró el Administrador y deben ser validados por la entidad contra la normativa vigente.

### 6.3 Enviar a cotización e imprimir el C-1

1. Revise que el monto y los ítems sean correctos. **Después de enviar ya no se pueden agregar ítems.**
2. Pulse **Enviar a cotización**. Si el monto excede el tope de contratación menor, el sistema lo rechaza.
3. Pulse **Generar C-1 (PDF)** para obtener el Formulario de Requerimiento y Especificaciones Técnicas con la declaración de no impedimento. Imprímalo y fírmelo.

### 6.4 Si se equivoca

- Puede anular la solicitud usted mismo: pestaña 5, escriba el **Motivo de anulación** (mínimo 10 caracteres) y pulse **Anular solicitud**. Luego cree una nueva.
- No se pueden editar ni borrar ítems una vez cargados: anule y cree otra solicitud.

## 7. Guía para el Responsable de Contrataciones (RC)

### 7.1 Evaluación del catálogo CHB (pestaña 2)

Cada ítem cuyo código está en el catálogo "Compro Hecho en Bolivia" debe resolverse antes de poder adjudicar o emitir la Orden. Hay dos caminos:

**A. Comprar por catálogo** (ficha técnica vigente)
1. Escriba el **N de item** (como aparece en la lista de la pestaña 1).
2. **No** marque la casilla "Comprar FUERA del catálogo CHB".
3. Pulse **Registrar evaluación CHB**. El ítem queda en **SI**.

**B. Comprar fuera del catálogo** (por insuficiencia de calidad, cantidad o plazo, o porque no hay ficha técnica vigente)
1. Escriba el **N de item** y marque **Comprar FUERA del catálogo CHB**.
2. Complete los cuatro datos que exige la excepción:
   - **Cod. Excepción**: Código Único de Excepción (solicitud de excepción de ficha técnica).
   - **N Autoriz. MDPyEP**: número de la autorización expresa del Ministerio de Desarrollo Productivo y Economía Plural.
   - **Fecha autoriz.**: fecha de esa autorización (no puede ser futura).
   - **Justificación**: razón técnica y legal detallada (mínimo 80 caracteres).
3. Pulse **Registrar evaluación CHB**. Si falta algo, el sistema dice qué y el ítem queda en **NO** (bloqueado). Si todo está completo queda en **EXCEPCION**.
4. Pulse **Justificación de excepción (PDF)** para obtener el reporte que se archiva en el expediente.

Resultado que verá en la columna **CHB** de la lista de ítems:

| Valor | Significado | ¿Permite la Orden? |
| :-- | :-- | :-- |
| N/A | El código no está en el catálogo CHB | Sí |
| SI | En catálogo, con ficha técnica vigente, compra por catálogo | Sí |
| EXCEPCION | Fuera de catálogo con excepción completa | Sí |
| NO | Pendiente o excepción incompleta | **No: bloquea la adjudicación y la Orden** |

> Si la ficha técnica de un ítem vence después de evaluarlo, el sistema lo vuelve a bloquear al intentar adjudicar o emitir la Orden.

### 7.2 Cotizaciones y cuadro comparativo (pestaña 3)

1. Cargue la solicitud (debe estar **EN_COTIZACION**).
2. Para cada oferta recibida, complete **NIT** (solo números, 6 o más dígitos), **Razón social**, **Validez** (fecha hasta la que vale la oferta), **Monto cotizado** (total de la oferta) y marque **Cumple técnicamente** si corresponde. Pulse **Registrar**.
3. Cuántas cotizaciones se necesitan: **1** hasta Bs 20.000; **3** si el referencial supera Bs 20.000.
4. Cuando tenga todas, pulse **Evaluar cuadro**. El sistema aplica el criterio *Cumple / No cumple* y *Precio evaluado más bajo*, y marca como **recomendada** la oferta vigente, que cumple técnicamente y tiene el menor monto. La solicitud pasa a **EVALUADA**.
   - Si hay **empate** en el precio más bajo, el sistema avisa y **no** elige: usted debe resolverlo con el criterio de desempate de la entidad.
   - Si ninguna oferta cumple, también lo avisa.
5. Pulse **Cuadro comparativo (PDF)** para imprimirlo.

Si una oferta supera el referencial en más del porcentaje de tolerancia, el sistema muestra un aviso (no impide registrarla).

### 7.3 Adjudicar (pestaña 3)

**Antes de adjudicar, Presupuesto debe haber reservado el presupuesto (sección 8).** Con la solicitud en estado PRESUPUESTADA:

1. En la lista de cotizaciones, **seleccione** la oferta recomendada.
2. Pulse **Adjudicar seleccionada**.

Solo se puede adjudicar la oferta recomendada, con CHB habilitado y con un C-31 vigente que cubra el monto cotizado.

### 7.4 Generar la Orden de Compra o de Servicio (pestaña 5)

Requisitos: solicitud **ADJUDICADA**, CHB habilitado y, si la entidad lo exige (opción por defecto), que Presupuesto haya **asociado el número de C-31 de SIGEP**.

1. Elija el **Tipo**: COMPRA o SERVICIO.
2. Escriba el **CUCE (SICOES)**, el **Plazo (días calendario)** y el **Lugar** de entrega o prestación.
3. Pulse **Generar Orden**. El sistema asigna el número (por ejemplo `OC-2026-000001`) y lo muestra.
4. Pulse **Orden (PDF)** para imprimirla. Incluye las cláusulas de objeto, plazo, penalidades, recepción, forma de pago y marco normativo.

### 7.5 Recepción y acta (pestaña 5)

1. Cargue la solicitud: el número de la Orden aparece solo.
2. Escriba la **Fecha recepción** (no puede ser anterior a la Orden ni futura).
3. Marque **Recepción CONFORME** si todo se recibió bien. Si no, déjela sin marcar y detalle las **Observaciones** (mínimo 10 caracteres).
4. Pulse **Registrar recepción**. El sistema calcula los **días de retraso** respecto al plazo de la Orden y la **multa** (por mil por día, con tope), y muestra el número de recepción (por ejemplo `REC-2026-000001`).
5. Pulse **Acta de recepción (PDF)** para imprimir el acta con el monto neto a pagar.

Notas:
- Una recepción **conforme** deja la Orden en RECIBIDA. Una **observada** la deja abierta para registrar otra después de que el proveedor subsane.
- El número de acta se muestra junto al botón después de registrar la recepción. **Anótelo**: si cierra el formulario, el número queda guardado en la hoja de recepciones y el Administrador puede ayudarle a recuperarlo.

### 7.6 Anulaciones (pestaña 5)

- **Anular Orden**: escriba el **Motivo de anulación** (mínimo 10 caracteres) y pulse el botón. La solicitud vuelve a ADJUDICADA y puede emitirse otra Orden. No se anula una Orden con recepción conforme. La reserva del C-31 sigue vigente: si hay que liberarla, la revierte Presupuesto.
- **Anular solicitud**: cancela todo el trámite. Exige que no haya Orden vigente ni C-31 vigente.

## 8. Guía para Presupuesto / Finanzas (PF)

### 8.1 Emitir el C-31 Preventivo (pestaña 4)

Condición: la solicitud debe estar **EVALUADA** (con oferta recomendada).

1. Cargue la solicitud.
2. Para cada línea de imputación escriba: **Programa, Proyecto, Act./Obra, Fuente, Organismo, Partida** (objeto del gasto) e **Importe (Bs)**. Los códigos se escriben tal como están en el presupuesto (por ejemplo `01`, `0000`, `001`).
3. Pulse **Consultar saldo** para ver el saldo disponible de esa estructura.
4. Pulse **Agregar línea**. La línea pasa a la lista. Repita si el gasto se imputa a varias partidas.
5. Pulse **Emitir C-31 Preventivo**.

El sistema valida **todas** las líneas antes de reservar: si una no tiene saldo o la estructura no existe en el presupuesto de la gestión, no reserva nada. Si todo está bien, asigna el número interno (por ejemplo `C31P-2026-000001`) y descuenta el importe del saldo.

El importe reservado debe **cubrir el monto de la oferta** recomendada. Una solicitud solo puede tener un C-31 vigente a la vez.

### 8.2 Asociar el número de C-31 de SIGEP

1. Registre el C-31 en el SIGEP.
2. Vuelva a la pestaña 4 y compruebe que **N C-31 interno** muestra el número del preventivo (si no, escríbalo).
3. Escriba el **N C-31 SIGEP** (solo números, hasta 10 dígitos) y pulse **Asociar C-31**. El estado pasa a ASOCIADO. El mismo número SIGEP no puede asociarse a dos preventivos.
4. Pulse **C-31 (PDF)** para imprimir la boleta con la estructura programática, los importes por partida y el total.

### 8.3 Reversiones

- **Reversión parcial**: escriba el **N C-31 interno**, el número de **Línea a revertir**, el **Monto a revertir** y el **Motivo** (mínimo 10 caracteres) y pulse **Reversión parcial**. El monto vuelve al saldo de esa partida.
- **Reversión total**: con el N° de C-31 interno y el motivo, pulse **Reversión total** y confirme. Todo el saldo vuelve al presupuesto y la solicitud regresa a EVALUADA para poder presupuestarse de nuevo.

No se puede revertir un preventivo que tiene una **Orden vigente**: primero hay que anular la Orden.

## 9. Guía para el Administrador (ADM)

Al iniciar sesión como administrador aparece el **Menú Administrador**. Escriba el número de la opción:

| Opción | Qué hace |
| :-- | :-- |
| 1 | **Crear usuario**: usuario, nombre completo, rol (US, RC, PF o ADM), código de DA y contraseña inicial |
| 2 | **Desbloquear usuario** bloqueado por intentos fallidos |
| 3 | **Cambiar la contraseña** de un usuario |
| 4 | **Importar catálogo CHB** desde un archivo CSV |
| 5 | **Importar presupuesto** desde un archivo CSV |
| 6 | **Mostrar las hojas de datos** para editar la hoja `CONFIG` (entidad, gestión, topes, penalidades) |
| 7 | **Ocultar y proteger** de nuevo las hojas de datos |
| 8 | **Ver la auditoría** (quién hizo qué y cuándo) |
| 0 o vacío | Cerrar sesión |

Para volver a abrir el menú: **Alt+F8**, elija `MenuAdmin` y pulse *Ejecutar*.

### 9.1 Crear los usuarios

Por cada persona use la opción 1. Los usuarios de rol **US** solo verán las solicitudes de su propia **DA**, por eso el código de DA es obligatorio al crearlos. Entregue la contraseña inicial en privado y pida que la cambien.

### 9.2 Cargar el catálogo y el presupuesto (CSV)

Prepare el archivo en Excel y guárdelo como **CSV UTF-8**. La primera fila lleva los nombres de columna **exactamente** así:

Catálogo CHB (opción 4): `CodigoUNSPSC, Descripcion, Unidad, FichaTecnicaCHB, Tipo, Vigencia, RequiereAutorizacionMDPyEP`

```
CodigoUNSPSC;Descripcion;Unidad;FichaTecnicaCHB;Tipo;Vigencia;RequiereAutorizacionMDPyEP
44121600;Papel bond tamaño carta;Paquete;SI;Bien;2026-12-31;NO
```

Presupuesto (opción 5): `Gestion, DA, UE, Programa, Proyecto, ActObra, Fuente, Organismo, Partida_ObjetoGasto, DescripcionPartida, PresupuestoAprobado`

```
Gestion,DA,UE,Programa,Proyecto,ActObra,Fuente,Organismo,Partida_ObjetoGasto,DescripcionPartida,PresupuestoAprobado
2026,01,001,01,0000,001,20,230,31120,Material de oficina,100000.00
```

Reglas: el delimitador puede ser coma o punto y coma; los campos con ese carácter van entre comillas; la fecha de vigencia se escribe `AAAA-MM-DD`; `FichaTecnicaCHB` y `RequiereAutorizacionMDPyEP` aceptan SI/NO. En el catálogo, un código que ya existe se **actualiza**. En el presupuesto, una estructura que ya existe se **rechaza** (para no alterar lo ya comprometido). Al terminar se muestra cuántos registros fueron nuevos, actualizados y rechazados, con el motivo de las líneas con problema.

### 9.3 Configurar la entidad (hoja CONFIG)

Con la opción 6 se muestran las hojas. En `CONFIG` complete como mínimo: **Entidad** (sale en el membrete), **Gestion**, **CodDA** y **CodUE**. Revise los topes y las penalidades con su Asesoría Legal. Al terminar use la opción 7.

## 10. Los documentos que genera el sistema

| Documento | Quién lo genera | Dónde | Contenido principal |
| :-- | :-- | :-- | :-- |
| Formulario C-1: Requerimiento y Especificaciones Técnicas | US, RC | Pestaña 1 | Datos de la solicitud, ítems, total en literal, declaración de no impedimento, firmas |
| Cuadro Comparativo de Cotizaciones | RC | Pestaña 3 | Ofertas, evaluación Cumple/No cumple, menor oferta hábil, recomendación |
| Justificación de Excepción CHB | RC | Pestaña 2 | Ítems fuera de catálogo con código de excepción, autorización MDPyEP y justificación |
| C-31 Preventivo (boleta interna) | PF, RC | Pestaña 4 | Estructura programática, importes por partida, revertido, vigente, total en literal |
| Orden de Compra / de Servicio | RC | Pestaña 5 | Datos del proveedor, ítems, monto, plazo, cláusulas, firmas |
| Acta de Recepción y Conformidad | RC | Pestaña 5 | Fechas, días de retraso, multa, resultado y monto neto a pagar |

Cada PDF se guarda con el número del trámite y la fecha y hora en el nombre. Imprima, firme y archive en el expediente de la contratación.

## 11. Mensajes que puede ver y qué hacer

| Mensaje | Qué significa | Qué hacer |
| :-- | :-- | :-- |
| Sesion no iniciada o expirada | Pasó el tiempo de inactividad | Ingrese nuevamente |
| Su rol (X) no tiene permiso para esta operacion | Esa acción no es de su rol | Pídala a quien corresponda |
| Justificacion insuficiente | Escribió menos de 20 caracteres | Detalle más |
| Solo puede crear solicitudes de su propia Direccion Administrativa | La DA no coincide con la suya | Corrija la DA |
| Solo se editan solicitudes en BORRADOR | Ya se envió a cotización | Anule y cree otra |
| Monto referencial Bs X excede el tope de Contratacion Menor | Supera el límite del sistema | Tramitar como ANPE/Licitación |
| La solicitud no tiene items | Falta agregar ítems | Agregue al menos uno |
| Se requieren N cotizaciones; hay M | Faltan ofertas para el cuadro | Registre las que falten |
| Ninguna oferta cumple tecnicamente / vigente | Todas incumplen o vencieron | Solicite nuevas ofertas |
| EMPATE en precio mas bajo | Dos ofertas con el mismo monto | Resuelva con el criterio de desempate |
| Bloqueado por CHB | Hay ítems sin ficha vigente ni excepción | Complete la pestaña 2 |
| Saldo insuficiente en partida X | La partida no alcanza | Cambie la partida o gestione modificación presupuestaria |
| La estructura programatica no existe en el presupuesto | Algún código no coincide | Revise los códigos con el presupuesto |
| El preventivo no cubre el monto cotizado | La reserva es menor que la oferta | PF revierte y emite otro por el monto correcto |
| Asocie primero el N de C-31 aprobado en SIGEP | Falta asociar el número SIGEP | PF lo asocia (sección 8.2) |
| Existe una Orden emitida con cargo a este preventivo | Intenta revertir con Orden vigente | Anule primero la Orden |
| Solo puede adjudicarse la oferta recomendada | Seleccionó otra oferta | Seleccione la recomendada |
| Usuario bloqueado por intentos fallidos | 3 errores de contraseña | Pida el desbloqueo al ADM |

## 12. Preguntas frecuentes

**¿Puedo trabajar con el archivo desde dos computadoras a la vez?** No. Excel no soporta escritura simultánea; use una persona por vez o una copia por unidad y consolide con el Administrador.

**¿Se pierde lo que hago si se corta la luz?** Se pierde lo que no se guardó. Excel guarda al cerrar y con Ctrl+G. Acostumbre guardar después de cada trámite importante.

**¿Dónde quedan los PDF?** En la carpeta `PDF` junto al libro, por ejemplo `C:\SIC-MUNI\PDF`.

**Me equivoqué en un monto o un ítem.** Antes de enviar a cotización, anule la solicitud y cree otra. Después de adjudicar, anule la Orden y revierta el C-31 con motivo.

**El sistema dice que el ítem está en el catálogo CHB. ¿Qué hago?** Si es US, nada: siga con su solicitud. El RC decidirá si compra por catálogo o pide excepción.

**¿Quién ve mis solicitudes?** Los usuarios US solo ven las de su DA; RC, PF y ADM ven todas.

**¿Qué registra la auditoría?** Ingresos, intentos fallidos, creación y cambio de estado de solicitudes, cotizaciones, C-31, órdenes, recepciones, anulaciones, importaciones y cada documento generado, con usuario, rol, fecha y hora.

## 13. Glosario

| Término | Significado |
| :-- | :-- |
| ANPE | Apoyo Nacional a la Producción y Empleo, modalidad de contratación para montos mayores |
| C-1 | Formulario de requerimiento y especificaciones técnicas |
| C-31 | Comprobante de ejecución presupuestaria; el preventivo reserva el presupuesto antes de contratar |
| CHB | Catálogo electrónico "Compro Hecho en Bolivia" |
| CUCE | Código Único de Contratación Estatal asignado por el SICOES |
| DA / UE | Dirección Administrativa / Unidad Ejecutora |
| MDPyEP | Ministerio de Desarrollo Productivo y Economía Plural |
| NB-SABS | Normas Básicas del Sistema de Administración de Bienes y Servicios |
| Partida | Objeto del gasto del clasificador presupuestario |
| SIGEP | Sistema de Gestión Pública |
| SICOES | Sistema de Contrataciones Estatales |
| UNSPSC | Clasificación estándar de productos y servicios que usa el catálogo |

## 14. Tarjetas de consulta rápida

**US:** Pestaña 1 → Crear solicitud → Agregar ítems → Enviar a cotización → C-1 (PDF).

**RC:** Cargar solicitud → Pestaña 2 evaluar cada ítem → Pestaña 3 registrar cotizaciones → Evaluar cuadro → (espera C-31 de PF) → Adjudicar → Pestaña 5 Generar Orden → Recepción → Acta.

**PF:** Cargar solicitud EVALUADA → Pestaña 4 líneas de imputación → Consultar saldo → Emitir C-31 → Registrar en SIGEP → Asociar N° SIGEP → Reversiones si corresponde.

**ADM:** Menú: 1 usuarios · 2 desbloqueo · 3 contraseña · 4-5 importar · 6-7 configurar y proteger · 8 auditoría.

## 15. Practique con casos de ejemplo

Antes de usar el sistema con trámites reales, practique en una **copia de ensayo** con los cinco ejemplos guiados del **Anexo E del Manual de Implementación** (con usuarios, catálogo y presupuesto de práctica). Cubren: compra simple, contratación con cuadro comparativo, excepciones CHB, orden de servicio con reversiones y anulación, y recepción con multa.
