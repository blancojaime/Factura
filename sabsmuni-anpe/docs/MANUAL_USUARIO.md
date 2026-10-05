# Manual de usuario

## 1. Cómo funciona el sistema

Cada contratación es un **proceso** que avanza por una secuencia fija de estados. En cada paso solo actúa el rol responsable y el botón
de avance **se habilita únicamente cuando se cumplen las condiciones** (si está gris, pase el cursor: explica qué falta).
Al avanzar, el sistema emite solo los documentos oficiales de ese paso (PDF con marca de agua, hash SHA-256 y QR de verificación).

```
Borrador → Requerimiento validado → Presupuesto certificado → DBC elaborado → DBC aprobado → Publicado
→ Evaluación → Recomendación emitida → Adjudicado → Contrato formalizado → Recepción → Liquidado
```

| Rol | Qué hace | Pestañas que usa |
|---|---|---|
| **Unidad Solicitante (US)** | Describe lo que necesita, redacta ET/TdR, justifica CHB | 1 |
| **Resp. de Presupuesto (RP)** | Certifica el presupuesto y prepara el C-31 | 2 |
| **Resp. de Contrataciones / Comisión (RC)** | Cronograma, DBC, propuestas, V-1, evaluación, contrato, recepción, expediente | 3, 4, 5, 6 |
| **Autoridad RPA** | Aprueba el DBC, adjudica o declara desierto, firma | 4, 5, 6 |
| **Administrador** | Usuarios, configuración, catálogos, respaldos | Administración |

**Ingreso:** abra la dirección del sistema, escriba su correo y contraseña. La sesión se renueva sola; al salir use el icono de la esquina superior derecha.

---

## 2. Caso práctico: «Adquisición de lote de cemento para pavimento» — Bs 180.000

3.000 bolsas de cemento Portland de 50 kg a Bs 60 cada una. Es una compra de **Bienes** por **Precio Evaluado Más Bajo**.
Como el precio referencial es ≤ Bs 200.000, el plazo mínimo entre publicación y apertura es de **4 días hábiles**.

### Paso 1 · Unidad Solicitante (US)

1. En **Procesos** pulse **Nueva solicitud** y complete: *Objeto* «Adquisición de lote de cemento para pavimento»; *Tipo* Bienes;
   *Método* Precio evaluado más bajo; *Plazo de entrega* 15 → **Crear borrador**.
2. En la pestaña **1 · Requerimiento y CHB**, sección *Ítems requeridos*, agregue el ítem:

   | UNSPSC | Partida | Unidad | Cantidad | P. unitario | Descripción técnica |
   |---|---|---|---|---|---|
   | 30111505 | 34200 | bolsa | 3000 | 60,00 | Cemento Portland tipo IP en bolsa de 50 kg, resistencia ≥ 32,5 MPa |

   El **Precio referencial total** pasa a **Bs 180.000,00**. (El sistema rechaza un total fuera de Bs 50.001 – 1.000.000.)
3. En *Especificaciones Técnicas* complete las 5 secciones (cada una ≥ 20 caracteres). Mientras escribe, el analizador marca en rojo lo
   **bloqueante** (p. ej. «cemento marca Soboce» sin «o equivalente») y en ámbar las advertencias.
   Ejemplo de redacción correcta de «Características técnicas mínimas»: *«Resistencia a la compresión mínima de 32,5 MPa a 28 días y fraguado inicial mayor a 45 minutos.»*
4. Pulse **Validar y cruzar con CHB**. Resultado esperado:
   - «Requerimiento sin hallazgos bloqueantes y completo».
   - Ítem 1: **Cubierto por CHB** → *adjuntar ficha del producto nacional* (hay producción nacional del código; no corresponde excepción).
5. Pulse **→ Requerimiento validado**. Se emite el documento **Solicitud C-1 y ET**.

### Paso 2 · Responsable de Presupuesto (RP)

1. Abra el proceso → pestaña **2 · Captura SIGEP**.
2. Complete la línea: DA `40` · UE `1` · Programa `1` · Proyecto `1` · Act./Obra `1` · Fuente `20` · Organismo `210` · Partida `34200` · Importe `180000`.
   El recuadro verde confirma «Los importes cuadran con los ítems en total y por partida». Si escribe 179.999,99 pasa a ámbar y no podrá avanzar.
3. Escriba el *N° Preventivo C-31* (p. ej. `000321`; puede completarlo tras registrar en SIGEP) y pulse **Guardar certificación**.
4. A la derecha (**interfaz espejo**) copie campo por campo con los iconos, copie la **glosa** o pulse **Copiar bloque para SIGEP**
   y transcriba al comprobante C-31 en el SIGEP.
5. Pulse **→ Presupuesto certificado** (se emite el *Preventivo C-31* en PDF).

### Paso 3 · Responsable de Contrataciones (RC): cronograma y DBC

1. Pestaña **3 · Cronograma y DBC**. Elija la *Fecha de publicación* `09/11/2026` (lunes) → **Simular**:

   | Actividad | Fecha |
   |---|---|
   | Publicación del DBC | 09/11/2026 |
   | Presentación y apertura (4.º día hábil) | 13/11/2026 |
   | Adjudicación o declaratoria desierta | 17/11/2026 |
   | Presentación de documentos para formalizar | 23/11/2026 |
   | Suscripción de contrato u orden | 26/11/2026 |

   Si elige un sábado, domingo o feriado, o una apertura anterior al mínimo legal, el sistema lo rechaza con el motivo.
2. **Guardar cronograma** y luego **→ DBC elaborado**: se genera el *Documento Base de Contratación* (Parte I y II) listo para aprobación.

### Paso 4 · Autoridad RPA

Abra el proceso, revise el DBC en la pestaña **6 · Expediente** (icono de descarga) y pulse **→ DBC aprobado**.

### Paso 5 · RC: publicación y evaluación

1. Publique el DBC en el SICOES y pulse **→ Publicado**, y luego **→ Evaluación** en la fecha de apertura.
2. Pestaña **4 · Evaluación**. Registre las propuestas (NIT, razón social, categoría, monto, plazo):

   | Proponente | Categoría | Oferta | Plazo | Precio de comparación |
   |---|---|---|---|---|
   | Cementos del Valle SRL | Nacional · 10 % | Bs 168.000 | 8 d | 168.000 × 0,90 = **Bs 151.200** |
   | Ferretería Andina (MyPE) | MyPE/APP/OECA · 18 % | Bs 172.000 | 10 d | 172.000 × 0,82 = **Bs 141.040** |

3. Marque en la matriz **V-1** los documentos que cada proponente **presentó**. Un solo «No presentó» descalifica (se ve en rojo).
4. Pulse **Ejecutar evaluación**. La fila con el trofeo es la recomendada: **Ferretería Andina**, que gana pese a ofertar más, por el margen MyPE.
   Cualquier cambio posterior en una propuesta o en el V-1 **anula** la evaluación y obliga a recalcularla.
5. **→ Recomendación emitida**: se generan *Verificación V-1*, *Cuadro comparativo* e *Informe de evaluación y recomendación*.

### Paso 6 · RPA: adjudicación

Pulse **→ Adjudicado**. Se emite la *Resolución de adjudicación*. (Adjudicar a otra propuesta distinta de la recomendada exige fundamentar en el campo de observación;
declarar **Desierto** también.)

### Paso 7 · Contrato u Orden y garantía (RC o RPA)

1. Pestaña **5 · Contrato**. El sistema muestra: Instrumento **Orden de compra** (plazo 10 ≤ 15 días calendario), monto **Bs 172.000**,
   **Garantía 3,5 % = Bs 6.020,00** (proponente MyPE). Para un proponente general sería 7 % = Bs 12.040.
2. Indique *Fecha de firma* `26/11/2026` (día hábil), instrumento de garantía (Boleta de Garantía), N° de boleta, entidad emisora y vigencia → **Generar contrato / orden**.
3. RPA: **→ Contrato formalizado**.

### Paso 8 · Recepción y cierre (RC)

1. En la misma pestaña, *Fecha de recepción* (p. ej. `07/12/2026`) y observaciones → **Registrar recepción y generar acta**.
2. **→ Recepción** y luego **→ Liquidado**. Adjunte en la pestaña 6 el *Devengado C-31* firmado (PDF) con **Adjuntar PDF externo**.

### Paso 9 · Expediente Único de Contratación (RC o RPA)

En la pestaña **6 · Expediente** pulse **Compilar expediente único**. Se genera **un solo PDF** con: índice foliado, C-1, Preventivo C-31, DBC, V-1,
cuadro comparativo, informe, resolución, orden/contrato y acta de recepción; cada página lleva «Fs. n/N», el PDF trae **marcadores** de navegación
y el índice muestra el **SHA-256** de cada documento y el **sello del expediente**. Entregue ese archivo a Auditoría Interna o a la Contraloría General del Estado.

---

## 3. Verificar que un documento es auténtico

Escanee el **QR** del pie de cualquier página (o abra `…/verificar/<hash>`). La página pública indica:
*«Documento auténtico: el archivo coincide con el hash registrado»*, el tipo, versión, proceso y fecha. Si el archivo fue alterado, o el hash no existe,
muestra una alerta. El QR del expediente verifica el **sello del conjunto**.

## 4. Situaciones frecuentes

| Situación | Qué hacer |
|---|---|
| **Bien sin producción nacional** (p. ej. computadoras UNSPSC 43211500) | Al validar, el resultado es *Sin producción nacional* y el sistema **emite automáticamente el Formulario de Justificación de Insuficiencia Técnica**. No requiere acción adicional; el RPA lo ve en el expediente. |
| **Existe producto nacional pero no sirve** | En el ítem, complete *Incompatibilidad técnica con el CHB* explicando el motivo; el resultado pasa a *Incompatible con CHB* y se emite la justificación. |
| **El analizador bloquea mi texto** | Quite marcas, símbolos ® ™, «único proveedor», «patentado». Si necesita referencia, use «… o equivalente». |
| **El botón de avance está gris** | Pase el cursor: se lista lo que falta (p. ej. «La certificación presupuestaria no cuadra aritméticamente con los ítems»). |
| **Se declara desierto** | El RPA fundamenta y pulsa **→ Desierto**. El RC puede volver a **Presupuesto certificado** para reprogramar una nueva convocatoria; propuestas y resolución previas se descartan del proceso pero **quedan en la auditoría y en el expediente**. |
| **Corregí algo y ya se generó el documento** | Los documentos son inmutables: al regenerar se crea una **versión nueva**; el expediente usa siempre la más reciente. |
| **Error «Su rol no está autorizado…»** | Esa operación corresponde a otro rol (ver tabla del §1). |

## 5. Administración (Administrador)

- **Usuarios:** crear, desactivar/activar (al desactivar se cierran sus sesiones). No puede quitarse a sí mismo el rol de administrador.
- **Configuración institucional, catálogos CHB / partidas / feriados / marcas:** por API (ver `docs/openapi.json`) con el rol Administrador.
- **Auditoría:** lista de las últimas acciones (fecha, usuario, IP, acción) y botón **Verificar integridad** que recorre la cadena de hashes. También disponible para el RPA.
- **Respaldos:** ver el *Manual de implementación* §6.
