---
title: "Guía de uso — Importador Excel → VSIAF 2.0"
subtitle: "Carga masiva de activos fijos, revalúos, transferencias y bajas a la base de datos del VSIAF"
lang: es
---

# 1. Qué es y qué hace

El **Importador Excel → VSIAF** es una aplicación de escritorio para Windows que lee un libro Excel (`.xlsx`) y registra su contenido **directamente en las tablas FoxPro (DBF) del VSIAF 2.0**, reproduciendo lo que hacen las pantallas del sistema:

| Hoja de Excel | Equivale en el VSIAF a… | Tabla(s) DBF que escribe |
|---|---|---|
| `UNIDADES` | Administrar Unidad → Nuevo | `UNIDADADMIN` |
| `OFICINAS` | Oficinas y Responsables → Nuevo (oficina) | `OFICINA` |
| `RESPONSABLES` | Oficinas y Responsables → Nuevo (responsable) | `RESP` |
| `AUXILIARES` | Grupos y Auxiliares → Nuevo | `AUXILIAR` |
| `ACTIVOS` | Activos Fijos → Nuevo | `ACTUAL` (+ memo `ACTUAL.FPT`) |
| `REVALUOS` | Opciones → Revalúo técnico | `REVAL` y actualiza `ACTUAL` |
| `TRANSFERENCIAS` | Activos Fijos → Transferencia | `TRASFE` y actualiza `ACTUAL` |
| `BAJAS` | Opciones → Dar de baja | `BAJAS` y marca como borrado el registro de `ACTUAL` |

Además, **antes de escribir**:

* **valida** cada fila con las mismas reglas del VSIAF (código único, UFV registrada, vida útil del grupo, estados, oficinas/responsables activos, etc.);
* **calcula una vista previa** de actualización por UFV, depreciación y valor neto con el mismo método del VSIAF, para que pueda verificar los totales;
* crea un **respaldo automático** compatible con *Respaldos BD → Restaurar* del VSIAF;
* si algo falla durante la escritura, **deja la base exactamente como estaba**;
* genera un **informe Excel** (errores, avisos, cálculo por activo, totales por grupo contable).

**Qué NO hace (a propósito):** no modifica los índices UFV, no toca las llaves de «Incorporaciones Especiales» de la DGCF, no cierra gestiones, no aprueba activos salvo que usted lo indique, y no reemplaza al VSIAF: después de importar hay que ejecutar **Re-indexar** dentro del VSIAF (ver §7).

> **Regla de oro:** primero practique con una **copia** de su base (o con la base de demostración que se explica en §9), y recién después importe a la base real.

# 2. Cómo trabaja el VSIAF por dentro (lo que se estudió para construir la herramienta)

## 2.1 Tecnología y archivos

* VSIAF 2.0 está hecho en **Visual FoxPro 9** (`vsiaf.exe` + `VFP9R.DLL`). Los datos son tablas `.DBF` con memos `.FPT` e índices compuestos `.CDX` en la carpeta `C:\vsiaf\dbfs`.
* La instalación guarda sus rutas en el registro de Windows: `HKEY_CURRENT_USER\SOFTWARE\MEFP\SIAF` (`APPinstall`, `APPDBFS`, `APPIncEsp`, `Llave`, `Updated`, `version`).
* Las **UFV no están en `dbfs`**: viven dentro de `tipocambio.app` (tabla `TIPCAMB`: `DIA, MES, ANO, TC`) y se renuevan con el actualizador del Ministerio cada día 10. El importador lee esa misma tabla.
* Cada gestión cerrada se registra en `closeges\closeges.dbf` (si contiene `ACTUAL`, la base está cerrada y es de solo lectura).

## 2.2 Tablas principales

| Tabla | Contenido | Clave lógica (índice `CODIGO`, etc.) |
|---|---|---|
| `ACTUAL` | Activos fijos vigentes (33 campos) | `entidad+unidad+codigo` |
| `REVAL` | Historial de revalúos técnicos | `entidad+unidad+codigo` |
| `BAJAS` | Activos dados de baja (con instantánea del cálculo) | `entidad+unidad+codigo` |
| `TRASFE` | Historial de transferencias | `entidad+unidad+codigo` |
| `OFICINA`, `RESP` | Oficinas y sus responsables | `entidad+unidad+codofic[+codresp]` |
| `AUXILIAR` | Auxiliares de cada grupo contable | `entidad+unidad+codcont+codaux` |
| `UNIDADADMIN` | Unidades administrativas | `entidad+unidad` |
| `CODCONT` | 39 grupos contables (D.S. 24051): vida útil, ¿se deprecia?, ¿se actualiza? | `codcont` |
| `BAJA`, `ESTADO`, `ORGANISMO_FIN`, `CLA_DEPTS`, `CTA_PAR` | Catálogos (motivos de baja, Bueno/Regular/Malo, organismos financiadores, departamentos, partidas) | — |
| `CONFIG` | Entidad y unidad activas, usuario | — |

## 2.3 Estados y banderas que usa el sistema

* `ACTUAL.API_ESTADO`: **1 = ELABORADO** (se puede modificar/eliminar; no entra en reportes; impide cerrar gestión) · **3 = APROBADO** (oficial; solo se corrigen textos).
* `OFICINA/RESP.API_ESTADO`: 1 = ACTIVO; otro valor = INACTIVO.
* `ACTUAL.BANDERAS`: `'0'` alta normal · `'1'` **Incorporación Especial** (vida útil distinta, autorizada por la DGCF).
* `ACTUAL.B_REV`: el activo fue revaluado.
* **Baja** = fila nueva en `BAJAS` + el registro de `ACTUAL` queda *marcado como borrado* (observación «DADO DE BAJA»).
* **Revalúo** = fila nueva en `REVAL` con el estado anterior y, en `ACTUAL`: nuevo costo, nueva vida útil, `DEPACU = 0`, `B_REV = .T.` y **fecha base = fecha del revalúo + 1 día**.
* **Transferencia** = cambia `CODOFIC`, `CODRESP` (y `UNIDAD` + `CODAUX` si es entre unidades) y agrega una fila en `TRASFE`.
* Al **iniciar**, el VSIAF ejecuta `UPDATE actual SET vidautil = <vida del grupo> WHERE banderas<>'1' AND ano>=2014 AND b_rev=.F.`. Por eso una vida útil distinta de la del grupo **se pierde** si el activo no es Incorporación Especial: el importador no la deja pasar.

## 2.4 Cómo calcula el VSIAF (y el importador)

Con los ejemplos del Manual de Usuario (págs. 16 y 24) y las rutinas internas (`ffactor`, `vvalact`, `ddepgestion`, `ddeprecia`, `act_da_gestion`) se dedujo y verificó:

| Concepto | Fórmula |
|---|---|
| Factor de actualización | `UFV(fecha de cálculo) ÷ UFV(fecha de incorporación)`, redondeado a **6 decimales**. Si el grupo no se actualiza, factor = 1. Si ya terminó la vida útil, se usa la UFV del fin de la vida útil. |
| Valor actualizado | `costo × factor` (2 decimales) |
| % de depreciación | `1 ÷ vida útil` (0 si el grupo no se deprecia: terrenos, otros activos, museológicos) |
| Días | corridos e **inclusive** (11/04 → 14/10 = 187 días), nunca más allá del último día de la vida útil |
| Depreciación de la gestión | `valor actualizado × % × días de la gestión ÷ 365` |
| Depreciación acumulada | `dep. acum. inicial × factor + valor actualizado × % × días totales ÷ 365` (tope = valor actualizado) |
| Valor neto | `valor actualizado − depreciación acumulada` |
| Actualización de la dep. acumulada (gestión) | `dep. acum. final − dep. acum. al inicio de la gestión − dep. de la gestión` |

**Comprobación con el manual** (las pruebas automáticas la repiten):

| Caso | Resultado del manual | Resultado de la herramienta |
|---|---|---|
| Bs 620,00 · 11/04/2013 · vida 10 · al 14/10/2013 | factor 1,025906 · valor actual 636,06 · dep. 32,59 · neto 603,47 | idéntico |
| Bs 1.380,00 · 29/08/2011 · vida 10 · al 10/10/2013 | factor 1,123211 · valor actual 1.550,03 · dep. acumulada 328,69 · neto 1.221,34 · 774 días | idéntico (la dep. de la gestión, 120,18, se ve «120,16» en la captura del manual) |
| Registros `REVAL` y `BAJAS` guardados por el propio VSIAF en la base de ejemplo | `DEPGESTION 0,02 · DEPACU 0 · ACTUA 1,00 · COSBAJINI 1,00 …` | idéntico (prueba de integración) |

## 2.5 Qué se guarda en las «instantáneas» de `REVAL` y `BAJAS`

* `DEPGESTION` = depreciación de la gestión hasta la fecha · `DEPACU` = depreciación acumulada **sin** la de la gestión · `ACTUA` = valor actualizado − `DEPACU`.
* `BAJAS` además guarda `COSBAJINI` (costo actualizado al inicio de la gestión), `COSDAINI` y `DEPACU_ANT` (dep. acumulada inicial), `COSACTBAJ` (costo actualizado a la baja) y `ACTDABAJ` (actualización de la dep. acumulada).

# 3. Qué lenguaje se eligió y por qué

**Python 3.12 + Tkinter + openpyxl**, empaquetado con PyInstaller y un instalador Inno Setup.

| Criterio | Decisión |
|---|---|
| Leer/escribir DBF sin depender de FoxPro | Visual FoxPro 9 está descontinuado y los controladores OLE DB de VFP son solo de 32 bits y difíciles de instalar; en Python se implementó una lectura/escritura propia, mínima y probada de DBF/FPT (`dbf.py`), sin controladores. |
| Excel | `openpyxl` lee/crea `.xlsx` **sin tener Excel instalado**. |
| Interfaz de escritorio | Tkinter viene con Python y se ve nativo en Windows; no requiere .NET ni librerías extra. |
| Instalación | PyInstaller genera un `.exe` autocontenido (no hace falta instalar Python en la PC del usuario); Inno Setup genera `Setup_ImportadorVSIAF_1.0.0.exe`. |
| Pruebas | El núcleo (DBF, cálculo, validaciones) se prueba de forma automática, y se verificó con lectores DBF independientes (`dbfread`). |

# 4. Instalación

## 4.1 Requisitos

Windows 7/10/11 (64 bits) · VSIAF 2.0 ya instalado (normalmente `C:\vsiaf`) y con la **entidad y al menos una unidad administrativa creadas** · permiso de escritura en `C:\vsiaf\dbfs` y `C:\vsiaf\backups`. **No hace falta tener Excel ni Python.**

## 4.2 Obtener el instalador

Opción A — **GitHub Actions** (sin instalar nada): en el repositorio, pestaña *Actions → Importador VSIAF (Windows) → Run workflow*. Al terminar, descargue el artefacto **Setup_ImportadorVSIAF** y ejecute `Setup_ImportadorVSIAF_1.0.0.exe`.

Opción B — **compilar en una PC con Windows**: instale Python 3.12 (64 bits) e Inno Setup 6, abra la carpeta `vsiaf-importador` y haga doble clic en `packaging\build_windows.bat`. Deja el instalador en `dist\`. (La carpeta `dist\ImportadorVSIAF` también funciona como versión portable.)

Opción C — **desde el código** (técnicos): `pip install -r requirements.txt` y `python run_importador.py`.

El instalador crea el acceso *Importador Excel a VSIAF* en el menú Inicio (y opcionalmente en el escritorio) e incluye esta guía y las plantillas.

# 5. Antes de importar (lista de verificación)

1. ☐ **Cierre el VSIAF** en esta y en todas las PC (si trabaja en red, importe en la PC servidor con todos los usuarios fuera).
2. ☐ **Actualice las UFV** con el actualizador del Ministerio (se publica el día 10 de cada mes). Si las UFV están desactualizadas, el importador lo advierte (*«las UFV parecen desactualizadas»*): las fechas sin UFV se rechazan igual que en el VSIAF.
3. ☐ En el VSIAF, **seleccione la entidad** (primer ingreso) y cree la **Unidad Administrativa** (*Administrar Unidad*) si no lo hizo; o incluya la unidad en la hoja `UNIDADES`.
4. ☐ Haga un **respaldo manual** desde el VSIAF (*Respaldos BD → Respaldar*). El importador además crea el suyo, pero dos respaldos no sobran.
5. ☐ Confirme que la **gestión no esté cerrada** (en la pantalla principal no debe decir «GESTION CERRADA»).
6. ☐ Tenga a mano las **resoluciones / disposiciones de respaldo** de revalúos y bajas.

# 6. El libro Excel

Use **siempre la plantilla** (botón *Crear plantilla…* o `plantilla_importacion_vsiaf.xlsx`). Reglas generales:

* La **fila 1** son los encabezados — **no cambie sus nombres ni los reordene**. Los de color **naranja** son obligatorios. Pase el cursor sobre un encabezado para ver su ayuda.
* Los datos empiezan en la **fila 2**. Las hojas que no necesite déjelas vacías o elimínelas.
* **Fechas:** `dd/mm/aaaa` (también acepta celdas de fecha de Excel). **Números:** `10000.50` o `10.000,50`; sin símbolo Bs.
* Los **códigos** (`unidad`, `codigo`, `cod_rube`…) deben ir como **texto**; la plantilla ya viene así (conserva ceros a la izquierda).
* La hoja `CATALOGOS` lista los valores válidos (grupos contables con su vida útil, estados, motivos de baja, organismos financiadores, departamentos).
* Si `unidad` se deja vacía se usa la **unidad por defecto** elegida en la ventana.
* Las hojas se procesan en este orden: `UNIDADES → OFICINAS → RESPONSABLES → AUXILIARES → ACTIVOS → REVALUOS → TRANSFERENCIAS → BAJAS`. Así, una fila de `ACTIVOS` puede usar la oficina o el auxiliar creados en el mismo libro, y una baja puede referirse a un activo cargado en el mismo libro (si se cargó como APROBADO).

## 6.1 `UNIDADES`

| Columna | Oblig. | Descripción |
|---|:-:|---|
| `unidad` | ✔ | Código (máx. 5). Si ya existe en el VSIAF la fila se omite. |
| `descripcion` | ✔ | Máx. 120 caracteres. |
| `ciudad` | | Máx. 20. |

## 6.2 `OFICINAS`

| Columna | Oblig. | Descripción |
|---|:-:|---|
| `unidad` | | Unidad (vacía = por defecto). |
| `oficina` | ✔ | Nombre (máx. 65). El código lo asigna el importador (correlativo por unidad). Si ya existe una con el mismo nombre (sin distinguir mayúsculas/acentos) se omite. |
| `observacion` | | Texto libre. |

## 6.3 `RESPONSABLES`

| Columna | Oblig. | Descripción |
|---|:-:|---|
| `unidad` | | |
| `oficina` | ✔ | Debe existir en el VSIAF o en la hoja `OFICINAS`. |
| `responsable` | ✔ | Nombre (máx. 35). |
| `cargo` | ✔ | Máx. 35. |
| `ci` | | Carnet (máx. 20). |
| `expedido` | | `LPZ, CBB, SCZ, ORU, PTS, CHQ, TAR, BEN, PAN, OTR` (o nombre del departamento). |
| `observacion` | | |

## 6.4 `AUXILIARES`

| Columna | Oblig. | Descripción |
|---|:-:|---|
| `unidad` | | |
| `grupo_contable` | ✔ | Código (1–40) o nombre exacto del grupo. |
| `auxiliar` | ✔ | Máx. 50. Código correlativo por grupo y unidad. |
| `observacion` | | |

## 6.5 `ACTIVOS` (altas)

| Columna | Oblig. | Descripción y reglas |
|---|:-:|---|
| `unidad` | | |
| `codigo` | ✔ | Único por unidad, máx. 15; se guarda en MAYÚSCULAS. |
| `codigo_adicional` | | «Código ADI» del VSIAF (máx. 15). |
| `descripcion` | ✔ | Máx. 150. |
| `grupo_contable` | ✔ | Código o nombre. |
| `auxiliar` | ✔ | Debe existir en ese grupo y unidad (VSIAF o hoja `AUXILIARES`). |
| `oficina` | ✔ | Oficina **activa**. |
| `responsable` | ✔ | Responsable **activo** de esa oficina. |
| `estado_bien` | ✔ | `Bueno`, `Regular` o `Malo`. |
| `fecha_incorporacion` | ✔ | No futura; debe tener UFV. Si es de una gestión anterior se emite un aviso. |
| `costo_inicial` | ✔ | Costo histórico en Bs, mayor a 0. |
| `vida_util` | | Vacía = la del grupo. Si es distinta → **error** (solo con Incorporación Especial habilitada). |
| `dep_acumulada_inicial` | | Solo Incorporaciones Especiales. En un alta normal → **error**. |
| `cod_rube` | | Opcional (máx. 15). |
| `organismo_financiador` | ✔ | Código de 3 dígitos del clasificador (111, 113… o `NC`/000). |
| `nro_convenio` | | Máx. 10. |
| `observaciones` | | Texto libre (memo). |
| `estado_registro` | | `ELABORADO` (por defecto) o `APROBADO`. |
| `incorporacion_especial` | | `SI`/`NO`. Solo funciona si **esa PC tiene habilitadas** las Incorporaciones Especiales (llave de la DGCF). |

## 6.6 `REVALUOS`

| Columna | Oblig. | Descripción y reglas |
|---|:-:|---|
| `unidad`, `codigo` | ✔ | Activo **APROBADO** existente. |
| `fecha_revaluo` | ✔ | ≥ fecha base del activo y no futura; deben existir UFV de esa fecha y del día siguiente. |
| `nuevo_costo` | ✔ | > 0. |
| `nueva_vida_util` | ✔ | > 0 (años). |
| `disposicion_respaldo` | ✔ | Resolución (máx. 16). No puede repetirse para el mismo activo. |
| `motivo` | | Va al memo de `REVAL`. |

## 6.7 `TRANSFERENCIAS`

| Columna | Oblig. | Descripción y reglas |
|---|:-:|---|
| `unidad_origen`, `codigo` | ✔ | Activo **APROBADO** (el VSIAF no transfiere ELABORADOS). |
| `unidad_destino` | | Vacía = misma unidad. |
| `oficina_destino`, `responsable_destino` | ✔ | Existentes y activos **en la unidad destino**. |
| `auxiliar_destino` | | **Obligatorio si cambia de unidad**; no puede existir el mismo código en la unidad destino. |

## 6.8 `BAJAS`

| Columna | Oblig. | Descripción y reglas |
|---|:-:|---|
| `unidad`, `codigo` | ✔ | Activo **APROBADO**. |
| `fecha_baja` | ✔ | ≥ fecha base del activo, no futura, con UFV. |
| `motivo_baja` | ✔ | Código 1–9 o texto (ver anexo A.2). El motivo 9 «Error de transcripción» solo vale para activos de la gestión vigente. |
| `disposicion_respaldo` | ✔ | Resolución (máx. 16). |
| `observaciones` | | «Observaciones o motivos» (máx. 120). |

# 7. Paso a paso

## Paso 1 — Abrir el importador y leer la instalación

Abra *Importador Excel a VSIAF*. Pulse **Detectar** (busca `C:\vsiaf` y el registro de Windows) o **Examinar…** para elegir la carpeta que contiene `vsiaf.exe` y `dbfs`. Debajo aparecerán la **entidad**, el número de **unidades**, el último día con **UFV** y una advertencia si las UFV están desactualizadas o la gestión está cerrada.

## Paso 2 — Crear y llenar la plantilla

**Crear plantilla…** → elija si desea filas de ejemplo (solo para practicar) o plantilla vacía → se guarda un `.xlsx` y se pregunta si desea abrirlo. Llene las hojas necesarias (§6) y guarde el libro (Excel cerrado antes de validar).

## Paso 3 — Opciones

* **Unidad por defecto**: unidad para las filas con `unidad` vacía.
* **Usuario**: queda en los campos `USUAR` (máx. 8; por defecto el de la instalación).
* **Fecha de cálculo**: fecha de la vista previa (hoy por defecto).
* **Estado de activos sin dato**: `ELABORADO` (recomendado) o `APROBADO`.
* **Crear respaldo automático** (recomendado).
* **Importar solo las filas válidas**: si está desmarcado (recomendado), **un solo error cancela toda la importación**; así nunca queda una carga a medias.

## Paso 4 — ① Validar (no escribe nada)

Revise la lista de **errores** (rojo) y **avisos** (amarillo): hoja, fila, columna y mensaje. Corrija el Excel y repita hasta que no haya errores. Se genera el **informe** `informe_validacion_AAAAMMDD_HHMMSS.xlsx` junto al libro (botón *Abrir informe*):

* `RESUMEN`: filas leídas / a importar / con error, y **totales por grupo contable** (costo histórico, actualización, costo total actualizado, depreciación, valor neto).
* `INCIDENCIAS`: todos los errores y avisos.
* `CALCULO_ACTIVOS`, `REVALUOS`, `TRANSFERENCIAS`, `BAJAS`: lo que se registrará, con los valores calculados.

## Paso 5 — ② Importar al VSIAF

Confirme el mensaje. El importador comprueba que **el VSIAF esté cerrado**, crea el respaldo `C:\vsiaf\backups\VSIMPXLddmmyyhhmm.zip` (+ `.gtz` con la descripción), escribe las tablas, relee los archivos para verificarlos y genera `informe_importacion_….xlsx`. Si ocurre cualquier error, los archivos vuelven a su estado original.

## Paso 6 — Re-indexar (obligatorio)

El importador escribe las tablas pero **no los índices `.CDX`** (son archivos propios de FoxPro). Abra el VSIAF → **Administradores → Re-indexar**. Hasta que lo haga, los registros nuevos pueden no aparecer en las búsquedas, en la navegación (Primero/Anterior/Siguiente/Último) ni en los reportes.

## Paso 7 — Verificar y aprobar

1. En el VSIAF abra *Activos Fijos → Buscar* y revise algunos registros.
2. Genere el **Reporte 6 «Resumen de Activos Fijos Ordenado por Grupo Contable»** y compare cantidad y totales con la hoja `RESUMEN` del informe (los activos ELABORADOS no aparecen en los reportes hasta aprobarse).
3. Los activos importados como **ELABORADO** deben **aprobarse** en el VSIAF (botón *Aprobar*, tras verificar la información) antes de poder revaluarlos, transferirlos, darlos de baja o cerrar la gestión.

## Deshacer una importación

*Respaldos BD → Restaurar* en el VSIAF y elija el `VSIMPXL…zip` creado antes de la importación (restaura **toda** la base a ese momento). Reinicie el VSIAF.

# 8. Mensajes de error frecuentes

| Mensaje | Causa y solución |
|---|---|
| *El VSIAF está abierto* | Cierre el sistema en todas las PC (revise el Administrador de tareas: `vsiaf.exe`). |
| *La gestión de esta base está CERRADA* | Use *Cambiar gestión* en el VSIAF para volver a la gestión vigente. |
| *La unidad «X» no existe…* | Cree la unidad en el VSIAF o agréguela en la hoja `UNIDADES`. |
| *El código «X» ya existe…* | Código repetido en la unidad (en el VSIAF o en otra fila del libro). |
| *No hay UFV registrada para dd/mm/aaaa* | Fecha fuera del rango de UFV de `tipocambio.app`: actualice las UFV o corrija la fecha. |
| *La fecha … no puede ser futura* | El VSIAF no admite operaciones con fecha posterior a hoy. |
| *La vida útil (n) difiere de la del grupo…* | Deje `vida_util` vacía. Solo una Incorporación Especial autorizada por la DGCF puede tener otra. |
| *Este equipo no tiene habilitadas las Incorporaciones Especiales* | La habilita la DGCF con una llave; la herramienta **no** puede (ni debe) eludirla. |
| *dep_acumulada_inicial solo en incorporaciones especiales* | En altas normales el VSIAF calcula la depreciación desde la fecha de incorporación. |
| *El auxiliar «X» no existe en el grupo…* | Agregue el auxiliar en la hoja `AUXILIARES` (o créelo en el VSIAF). |
| *La oficina/el responsable está INACTIVO* | Actívelo en *Oficinas y Responsables*. |
| *El activo está ELABORADO: apruébelo primero* | Revalúos, transferencias y bajas solo para APROBADOS: apruébelo en el VSIAF o cárguelo con `estado_registro = APROBADO`. |
| *Ya existe un revalúo con la disposición «X»* | Cada revalúo de un activo requiere una disposición distinta. |
| *Error de transcripción solo en la gestión vigente* | Regla del VSIAF; regularice con la DGCF. |
| *Hay N error(es) en el libro* | Corrija o active «Importar solo las filas válidas». |
| *No se pudo escribir X.DBF: está en uso o sin permisos* | VSIAF abierto o carpeta protegida: ejecute como usuario con permisos sobre `C:\vsiaf`. |

# 9. Practicar sin riesgo

1. En una carpeta de pruebas copie **toda** la carpeta `C:\vsiaf` (por ejemplo a `D:\prueba\vsiaf`).
2. En el importador elija esa copia en el paso 1 y use la plantilla **con ejemplos** (que crea su propia unidad `901`, oficinas, responsables, tres activos, un revalúo, una transferencia y una baja).
3. Importe, abra la **copia** del VSIAF (ejecute `vsiaf.exe` de esa carpeta), **Re-indexar** y revise.
4. Cuando todo cuadre, repita con su libro real sobre la base real.

# 10. Línea de comandos (opcional)

```
ImportadorVSIAF-consola plantilla salida.xlsx [--vsiaf C:\vsiaf] [--ejemplos]
ImportadorVSIAF-consola info      --vsiaf C:\vsiaf
ImportadorVSIAF-consola validar   libro.xlsx --vsiaf C:\vsiaf --unidad 1
ImportadorVSIAF-consola importar  libro.xlsx --vsiaf C:\vsiaf --unidad 1 [--solo-validas] [--sin-respaldo]
```

Útil para automatizar o desde servidores sin escritorio. Códigos de salida: 0 = correcto, 1 = errores / no importado, 2 = VSIAF no encontrado.

# 11. Límites, supuestos y recomendaciones

* **Índices `.CDX`:** no se reescriben (formato propietario de FoxPro); se regeneran con *Re-indexar*. Esta es una decisión de seguridad: un índice mal escrito podría dañar la base.
* **Pruebas realizadas:** el motor se verificó con los ejemplos del manual, con los registros `REVAL`/`BAJAS` que el propio VSIAF guardó en la base de ejemplo y con lectores DBF independientes; no se pudo ejecutar el VSIAF dentro del entorno de desarrollo, por lo que **la primera importación debe hacerse sobre una copia** (§9) y comparar con el *Reporte 6*.
* **Campos «instantánea»** de `REVAL`/`BAJAS` (§2.5): su significado se dedujo del código y de los datos de ejemplo; para activos de gestiones anteriores revise en el VSIAF un caso (Reporte de bajas / revaluados) antes de cargar lotes grandes.
* **Fin de vida útil:** cuando un activo ya terminó su vida útil, el factor usa la UFV de ese día (según las rutinas `TCVUTIL` del sistema). Si su Reporte 6 difiere en activos totalmente depreciados, avise para ajustar.
* **Incorporaciones Especiales** y **cierre de gestión** son controles de la DGCF/MEFP: la herramienta los respeta.
* **UFV:** son las de `tipocambio.app`. Si el Ministerio publicó UFV nuevas, ejecute primero su actualizador.
* **Red/multiusuario:** importe con todos los usuarios fuera; la herramienta solo detecta `vsiaf.exe` en el equipo local.
* **Datos personales:** el informe y los respaldos contienen datos de su entidad; guárdelos con el mismo cuidado que la base.

# Anexos

## A.1 Mapa de campos Excel → DBF (`ACTIVOS` → `ACTUAL`)

| Excel | Campo DBF | Notas |
|---|---|---|
| `unidad` | `UNIDAD` C(5) | |
| *(entidad de la instalación)* | `ENTIDAD` C(4) | de `CONFIG.DBF` |
| `codigo` | `CODIGO` C(15) | MAYÚSCULAS |
| `codigo_adicional` | `CODIGOSEC` C(15) | |
| `descripcion` | `DESCRIP` C(150) | |
| `grupo_contable` | `CODCONT` N(2) | |
| `auxiliar` | `CODAUX` N(3) | |
| `oficina` / `responsable` | `CODOFIC` N(4) / `CODRESP` N(5) | |
| `estado_bien` | `CODESTADO` N(2) | 1 Bueno · 2 Regular · 3 Malo |
| `fecha_incorporacion` | `DIA`, `MES`, `ANO` | |
| `costo_inicial` | `COSTO` N(15,2) | |
| `vida_util` | `VIDAUTIL` N(6,2) | grupo contable si está vacía |
| `dep_acumulada_inicial` | `DEPACU` N(15,2) | 0 en altas normales |
| `cod_rube` | `COD_RUBE` C(15) | |
| `organismo_financiador` | `ORG_FIN` C(3) | |
| `nro_convenio` | `NRO_CONV` C(10) | |
| `observaciones` | `OBSERV` (memo) | |
| `estado_registro` | `API_ESTADO` N(1) | 1 ELABORADO · 3 APROBADO |
| `incorporacion_especial` | `BANDERAS` C(12) | `'0'` / `'1'` |
| *(automáticos)* | `B_REV=.F.`, `BAND_UFV=.F.`, `FEULT=hoy`, `USUAR=usuario` | |

## A.2 Catálogos

**Motivos de baja**

| Código | Motivo |
|---:|---|
| 1 | Disposición definitiva de bienes |
| 2 | Hurto, robo o perdida fortuita |
| 3 | Mermas |
| 4 | Vencimiento, descomposiciones, alteraciones y deterioros |
| 5 | Inutilización |
| 6 | Obsolescensia |
| 7 | Desmantelamiento total o parcial de edificaciones, excepto el terreno que no será dado |
| 8 | Siniestros |
| 9 | ERROR DE TRANSCRIPCION |

**Grupos contables (D.S. 24051)**

| Código | Grupo | Vida útil (años) | Se deprecia | Se actualiza |
|---:|---|---:|:-:|:-:|
| 1 | EDIFICACIONES | 40 | Sí | Sí |
| 2 | MUEBLES Y ENSERES DE OFICINA | 10 | Sí | Sí |
| 3 | MAQUINARIA EN GENERAL | 8 | Sí | Sí |
| 4 | EQUIPO MEDICO Y DE LABORATORIO | 8 | Sí | Sí |
| 5 | EQUIPO DE COMUNICACIONES | 8 | Sí | Sí |
| 6 | EQUIPO EDUCACIONAL Y RECREATIVO | 8 | Sí | Sí |
| 7 | BARCOS Y LANCHAS EN GENERAL | 10 | Sí | Sí |
| 8 | VEHICULOS AUTOMOTORES | 5 | Sí | Sí |
| 9 | AVIONES | 5 | Sí | Sí |
| 10 | MAQUINARIA PARA LA CONSTRUCCION | 5 | Sí | Sí |
| 11 | MAQUINARIA AGRICOLA | 4 | Sí | Sí |
| 12 | ANIMALES DE TRABAJO | 4 | Sí | Sí |
| 13 | HERRAMIENTAS EN GENERAL | 4 | Sí | Sí |
| 14 | REPRODUCTORES Y HEMBRAS DE PEDIGREE | 8 | Sí | Sí |
| 15 | EQUIPOS DE COMPUTACION | 4 | Sí | Sí |
| 16 | CANALES DE REGADIO Y POZOS | 20 | Sí | Sí |
| 17 | ESTANQUES, BAÑADEROS Y ABREVADEROS | 10 | Sí | Sí |
| 18 | ALAMBRADOS, TRANQUERAS Y VALLAS | 10 | Sí | Sí |
| 19 | VIVIENDAS PARA EL PERSONAL | 20 | Sí | Sí |
| 20 | MUEBLES Y ENSERES EN VIVIENDAS DE PERSONAL | 10 | Sí | Sí |
| 21 | SILOS, ALMACENES Y GALPONES | 20 | Sí | Sí |
| 22 | TINGLADOS Y COBERTIZOS DE MADERA | 5 | Sí | Sí |
| 23 | TINGLADOS Y COBERTIZOS DE METAL | 10 | Sí | Sí |
| 24 | INSTALACION DE ELECTRIFICACION Y TELEFONIA RURAL | 10 | Sí | Sí |
| 25 | CAMINOS INTERIORES | 10 | Sí | Sí |
| 26 | CAÑA DE AZUCAR | 5 | Sí | Sí |
| 27 | VIDES | 8 | Sí | Sí |
| 28 | FRUTALES | 10 | Sí | Sí |
| 29 | LINEAS DE RECOLECCION DE LA INDUSTRIA PETROLERA | 5 | Sí | Sí |
| 30 | POZOS PETROLEROS | 5 | Sí | Sí |
| 31 | EQUIPOS DE CAMPO DE LA INDUSTRIA PETROLERA | 8 | Sí | Sí |
| 32 | PLANTA DE PROCESAMIENTO DE LA INDUSTRIA PETROLERA | 8 | Sí | Sí |
| 33 | DUCTOS DE LA INDUSTRIA PETROLERA | 10 | Sí | Sí |
| 34 | TERRENOS | 0 | No | Sí |
| 36 | OTROS ACTIVOS FIJOS | 0 | No | No |
| 37 | ACTIVOS INTANGIBLES | 5 | Sí | Sí |
| 38 | EQUIPO E INSTALACIONES | 8 | Sí | Sí |
| 39 | OTRAS PLANTACIONES | 8 | Sí | Sí |
| 40 | ACTIVOS MUSEOLOGICOS Y CULTURALES | 0 | No | No |

**Estados del bien:** 1 Bueno · 2 Regular · 3 Malo.

**Expedido:** CHQ = Chuquisaca · LPZ = La Paz · CBB = Cochabamba · ORU = Oruro · PTS = Potosi · TAR = Tarija · SCZ = Santa Cruz · BEN = Beni · PAN = Pando · OTR = Otros
