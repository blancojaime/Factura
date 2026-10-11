# Manual de Usuario — SICOM-MUNI

Ingrese a la dirección que le indique su administrador (por ejemplo `http://localhost:3000`) con su usuario y contraseña.
La pantalla **Inicio** muestra contadores por estado y la lista **«Pendientes de mi atención»** con *qué debe hacer* en cada trámite.
Toda acción queda registrada en la auditoría.

## 1. Flujo del trámite
```
BORRADOR → SOLICITADO → CERTIFICADO_PRESUPUESTO → EN_COTIZACION → EVALUADO → ADJUDICADO → FORMALIZADO → RECEPCIONADO → DEVENGADO
                                                                                         (ANULADO / desierto en cualquier etapa permitida)
```
| Rol | Qué hace |
|---|---|
| Solicitante | Crea y envía la solicitud (C-1) con ítems y especificaciones técnicas |
| Presupuesto | Importa el presupuesto y los objetivos del POA, certifica el preventivo (C-31) y el POA, copia el bloque SIGEP, devenga |
| Contrataciones | Importa el catálogo CHB, registra F110, emite fichas, carga cotizaciones, abre ofertas, califica y evalúa |
| RPA | Aprueba el inicio, adjudica, declara desierto, formaliza |
| Recepción | Registra la recepción/conformidad |
| Administrador | Usuarios, parámetros, catálogo CHB, auditoría |

## 2. Solicitante: crear la solicitud
1. **Nueva solicitud** → complete objeto, tipo (Bien / Servicio general / Consultoría), plazo en días, lugar y justificación. La **guía de redacción** le ayuda con las Especificaciones Técnicas.
2. En el **Formulador** agregue ítems: escriba el código UNSPSC o busque en el **Catálogo CHB**; elija partida, unidad, cantidad y precio. Verá en vivo:
   monto total, **modalidad** (Compra directa ≤ 20.000; Consulta de Precios SICOES hasta 50.000; sobre 50.000 se bloquea y se indica derivar a ANPE),
   **método de formalización** (Orden hasta 15 días; Contrato desde 16) y el estado CHB de cada ítem.
3. Si un bien existe en el catálogo CHB, es **compra obligatoria** y no podrá enviar. Para exceptuarlo marque el ítem «fuera de catálogo», escriba la justificación (mín. 80 caracteres) y el código de autorización; el sistema generará el **Informe de Excepción**.
4. Complete **«¿Cómo apoya la compra al logro del objetivo del POA?»** (se imprime en la Certificación del POA) y, si el monto supera Bs 20.000, el **mes estimado de publicación (PAC)**.
5. **Enviar solicitud**: se genera el PDF **C-1** y, si el monto supera Bs 20.000, la **Nota de solicitud de registro al PAC** dirigida a la Máxima Autoridad Ejecutiva (no requiere aprobación). Presupuesto puede devolverla con observaciones (vuelve a BORRADOR).

## 3. Presupuesto
1. Abra el trámite → pestaña **Presupuesto**: vea saldo por partida y el **bloque SIGEP** previsto.
2. Revise la tarjeta **Certificación del POA — programa y objetivo** (programa de cada partida, su objetivo del POA y la justificación; puede corregirla). Si un programa no tiene objetivo, regístrelo en **Objetivos POA**.
3. **Copiar Bloque SIGEP** y péguelo en el SIGEP; registre el N.° de preventivo C-31 y pulse **Certificar** (descuenta el saldo de todas las partidas o ninguna). Se generan la **Certificación presupuestaria C-31** y la **Certificación del POA**.
4. Al final, **Devengar**: libera la diferencia entre lo reservado y lo adjudicado.
5. Menú **Presupuesto**: aperturas programáticas y partidas con presupuesto, ejecutado, preventivo activo y saldo; **Importar desde Excel** y **Registrar partida**.

### 3.1 Importar desde Excel (Presupuesto y Objetivos POA)
Botón **Importar desde Excel** en *Presupuesto* y en *Objetivos POA*. Descargue la **plantilla**, complete sus datos (.xlsx), pulse **Validar archivo** (no guarda nada, muestra errores por fila y vista previa) y luego **Confirmar importación** (solo si no hay errores).
- **Presupuesto:** columnas *Código (apertura programática)* como Programa-Proyecto-Actividad (ej. `002-0000-001`), *Descripción apertura*, *Partida*, *Fuente*, *Organismo*, *Presupuesto*, *Ejecutado*, *Saldo*. Reimportar actualiza las filas existentes.
- **Objetivos POA:** columnas *PROG*, *DENOMINACIÓN DEL PROGRAMA*, *COD OBJ*, *DESCRIPCIÓN OBJETIVO* (un objetivo por programa; «2» y «002» son el mismo programa). También puede registrar o editar uno por uno.

## 4. RPA: aprobar el inicio
En el trámite certificado, la tarjeta **Aprobar inicio** pasa el trámite a cotización.

## 5. Contrataciones: cotizar y evaluar
0. **Catálogo CHB:** menú *Catálogo CHB* → **Importar desde Excel** (columnas *Código UNSPSC*, *Descripción código*, *Precio*): cada importación **reemplaza** los códigos repetidos y registra la fecha de importación.
1. **Compra directa (≤ 20.000)**: cargue la(s) cotización(es). **Consulta de precios (> 20.000)**: primero registre el **N.° de Formulario 110** y la **fecha límite de ofertas**.
2. **Fichas de cotización**: genere la ficha PDF y envíela por **Impreso, WhatsApp (enlace) o Correo** (si SMTP está configurado).
3. **Cargar cotización**: NIT/CI, razón social, monto, plazo. Los montos quedan **sellados** y no se ven hasta abrirlos; un NIT no puede repetirse.
4. **Abrir ofertas** (solo después de vencido el plazo). **Calificar** cada oferta (cumple / no cumple especificaciones, observaciones) y, si corresponde, el **registro de preferencia** (Pro-Bolivia / MyPE) válido con su margen.
5. La **Matriz comparativa** ordena por *precio evaluado* (el margen solo se aplica con registro válido). Una oferta es elegible si cumple, no supera el referencial y su plazo no excede el solicitado. Empate: gana la primera recibida.
6. **Evaluar**: exige el mínimo de cotizaciones (3 en consulta). Genera el **Cuadro comparativo**.

## 6. RPA: adjudicar y formalizar
- **Asistente de adjudicación**: propone la oferta recomendada; adjudicar otra exige un motivo y debe ser elegible. Alternativa: **Declarar desierta** (libera el presupuesto). Se genera la **Nota de adjudicación**.
- **Formalizar**: el método lo determina el plazo (Orden de Compra / de Servicio ≤ 15 días; Contrato Administrativo > 15). En consulta de precios ingrese el **CUCE**.

## 7. Recepción
Registre la fecha, cantidades recibidas por ítem y si es conforme. Con diferencias, marque *no conforme* y anote las observaciones: el trámite sigue FORMALIZADO. Al ser conforme se emite el **Acta de recepción** (NIA para bienes / Informe de conformidad para servicios).

## 8. Documentos y verificación
Pestaña **Documentos**: descargue cada PDF (versión, fecha, hash). Cada PDF lleva **marca de agua** del estado, **código QR** y el **SHA-256 del contenido**.
Cualquier persona puede escanear el QR → página **Verificación de autenticidad**, donde también puede **cargar el PDF** para comprobar que no fue alterado.

## 9. Anular
El botón **Anular** (con motivo) cierra el trámite y libera el presupuesto reservado.

## 10. Administrador
- **Usuarios**: crear, activar/desactivar, restablecer clave (≥ 10 caracteres con mayúscula, minúscula y número).
- **Parámetros del GAM**: nombre, ciudad, DA/UE, logotipo, topes/plazos/mínimos y la **Máxima Autoridad Ejecutiva** (`mae_nombre`, `mae_cargo`) y el prefijo del CITE de la nota PAC (`cite_prefijo_pac`).
- **Catálogo CHB**: buscar y agregar bienes (código UNSPSC de 8 dígitos).
- **Auditoría**: registros inalterables y botón **Verificar integridad de la cadena**.

## 11. Mensajes frecuentes
| Mensaje | Qué hacer |
|---|---|
| «El monto supera el límite de Contratación Menor (Bs 50.000). Derive a la modalidad ANPE» | Cambie ítems/montos o tramite por otra modalidad |
| «Compra obligatoria CHB…» | Use el catálogo o registre excepción justificada |
| «FORMULARIO_110_REQUERIDO» | Registre el N.° F110 en Cotizaciones |
| «PLAZO_VIGENTE» | Espere el vencimiento de la fecha límite para abrir ofertas |
| «COTIZACIONES_INSUFICIENTES» | Cargue más cotizaciones |
| «POA_INCOMPLETO» | Registre el objetivo del programa en *Objetivos POA* y/o escriba la justificación del apoyo al POA (mín. 20 caracteres) |
| «Registre … la Máxima Autoridad Ejecutiva» | El administrador debe completar `mae_nombre` y `mae_cargo` en *Parámetros del GAM* |
| «No se encontró la fila de encabezados» (importación) | Use la plantilla descargable y guarde como .xlsx |
| «FORMALIZACION_CONTRATO_OBLIGATORIO» | Con plazo > 15 días solo corresponde Contrato |
