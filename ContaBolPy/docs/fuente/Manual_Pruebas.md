---
title: "CONTA JB 2.4 — Manual de Pruebas de Aceptación"
subtitle: "Guía paso a paso con datos de ejemplo, resultados esperados y capturas reales del aplicativo"
lang: es
---

# 1. Introducción

## 1.1 Objetivo

Este manual permite a un **contador, auditor o responsable de TI** comprobar, de forma ordenada y repetible, que CONTA JB:

1. se instala y arranca correctamente en Windows;
2. registra las operaciones contables, tributarias, comerciales, de inventario, activos fijos, planillas y costos aplicando la **normativa boliviana vigente** (IVA 13 %, IT 3 %, IUE 25 %, RC-IVA, AFP, CNS, Pro-Vivienda, ANS, bono de antigüedad, aguinaldo e indemnización);
3. emite correctamente los **seis estados financieros** (Balance General, Estado de Resultados, Estado de Evolución del Patrimonio Neto, Flujo de Efectivo por método directo, Flujo de Efectivo por método indirecto y Notas a los Estados Financieros);
4. genera los **79 informes** del sistema en pantalla, **PDF** y **Excel**;
5. protege la información (usuarios, permisos, auditoría, copias de seguridad verificables).

## 1.2 Cómo están hechas las imágenes

Todas las imágenes de este manual son **capturas reales** del aplicativo, generadas automáticamente por la herramienta `tools/capturas.py` con la **empresa de demostración** (Distribuidora Andina S.R.L., gestión 2025). No son dibujos ni maquetas. Su pantalla puede diferir mínimamente en tipografía según su versión de Windows, pero la disposición y las cifras deben coincidir.

## 1.3 Qué ya está verificado automáticamente

Antes de entregar cada versión se ejecutan pruebas automáticas (paquete `tests/`) que cubren: partida doble, bimonetario, IVA/IT, inventario con costo promedio y FEFO, cobros y pagos, activos fijos, planillas con normativa vigente, producción, estados financieros, cierre y apertura de gestión, copias de seguridad, multiempresa, los 79 informes en PDF y Excel, y la construcción de **todas las pantallas** de la interfaz. Las cifras de la **Parte B** de este manual están además comprobadas por la prueba `tests/test_manual.py`: si el cálculo del sistema cambiara, esa prueba fallaría y el manual debería actualizarse.

Aun así, la aceptación en el equipo del cliente es necesaria: depende de su versión de Windows, impresoras, visor de PDF y de sus propios datos.

## 1.4 Roles y materiales

| Rol | Responsabilidad |
|---|---|
| Probador | Ejecuta los casos, registra resultado y evidencia |
| Contador validador | Confirma que los asientos, impuestos y estados son correctos |
| Responsable técnico | Analiza y corrige las incidencias |

**Materiales:** equipo con Windows 10/11 (64 bits); instalador `ContaJB_Setup.exe`; este manual; Excel o visor de hojas de cálculo; visor de PDF; unas 3 horas para la prueba completa (1 hora para la prueba rápida de la Parte A y B).

## 1.5 Criterios de aceptación

| Resultado | Significado |
|---|---|
| **✔ Aprobado** | El resultado coincide con lo esperado |
| **✘ Fallido** | Difiere; registre caso, paso, captura completa y hora |
| **⛔ Bloqueado** | No se pudo ejecutar por una falla previa |

La versión se **aprueba** si todos los casos marcados ★ (críticos) están ✔, no hay diferencias de cálculo y los seis estados financieros cuadran.

**Severidad de incidencias:** *Crítica* (pérdida de datos o cálculo contable/tributario incorrecto) · *Alta* (función principal inutilizable) · *Media* (afecta la comodidad, hay alternativa) · *Baja* (estética u ortografía).

# 2. Parte A — Preparación del entorno

## A1 ★ Instalación (un solo clic)

**Objetivo:** instalar CONTA JB.

**Pasos**

1. Descargue `ContaJB_Setup.exe` desde la página de descargas (*Releases* de GitHub) y haga doble clic.
2. Si Windows muestra «Windows protegió su PC» (el instalador no está firmado digitalmente), pulse **Más información → Ejecutar de todas formas**.
3. Pulse **Instalar**. No hay más preguntas: se instala solo para su usuario (**no pide permisos de administrador**), crea el acceso directo **CONTA JB** en el escritorio y en el menú Inicio.
4. Al terminar pulse **Finalizar** (deja marcada la opción *Abrir CONTA JB ahora*).

**Resultado esperado:** el asistente tiene solo tres pasos (Instalar → progreso → Finalizar), aparece el acceso directo con el icono **JB** y se abre la pantalla de ingreso con el logotipo de Jaime Blanco. No se requiere instalar ni Python ni Access ni ningún otro programa.

**Si falla:** anote el mensaje del instalador y la versión de Windows. Alternativa sin instalar: `ContaJB_portable.zip` (descomprimir y ejecutar `ContaJB.exe`).

## A1b ★ Instalación en Windows 7 (edición Windows 7)

**Objetivo:** comprobar que CONTA JB funciona en un equipo con **Windows 7 SP1 de 64 bits** con la misma apariencia que en Windows 10/11.

**Pasos**

1. Descargue `ContaJB_Setup_Win7.exe` desde *Releases* y haga doble clic. Pulse **Instalar** y luego **Finalizar**.
2. En la pantalla de ingreso, mire el pie: debe decir **«Versión 2.4.0 · Edición Windows 7»**. Ingrese (`admin` / `admin`) y elija una contraseña nueva.
3. Cree la empresa de demostración (*Crear empresa de demostración*) y recorra: **Control de comprobantes** (F2), **Balance General** y **Notas a los Estados Financieros** (botones PDF, Excel y Word), **Auditoría financiera (MAF)**, **Planilla de sueldos** y **Ayuda > Activación de la licencia**.
4. Compare con las capturas de este manual (tomadas en la edición Windows 10/11).

| Verificación | Esperado |
|---|---|
| Instalación | 3 pasos, sin permisos de administrador; acceso directo **CONTA JB** con el icono JB |
| Apariencia | Barra de menús azul oscuro, barra de accesos con iconos de colores, tablas con encabezado azul, botones redondeados, fuente Segoe UI: igual que en las capturas |
| Funciones | Todos los casos de las Partes B a F dan los mismos resultados que en Windows 10/11 (mismas cifras) |
| Informes | PDF, Excel y Word se generan y abren |
| Copias de seguridad | Una copia hecha en Windows 7 se restaura en Windows 10/11 y viceversa |

**Si falla:** anote el mensaje exacto. Si Windows indica que falta `api-ms-win-crt-…`, instale la actualización **KB2999226** (Universal C Runtime) y reintente. Verifique que sea Windows 7 **con Service Pack 1** y de **64 bits** (*Panel de control > Sistema*).

> **Nota sobre la verificación:** la edición Windows 7 se prueba automáticamente con las mismas pruebas que la de Windows 10/11 (Python 3.8 + PySide2) y con la autoprueba del paquete en cada publicación. La comprobación final en un equipo real con Windows 7 es la de este caso A1b.

## A2 ★ Primer ingreso y cambio de contraseña

**Pasos**

1. En la pantalla de ingreso escriba usuario `admin` y contraseña `admin`; pulse **Ingresar**.
2. El sistema exige elegir una nueva contraseña (mínimo 6 caracteres; no se aceptan claves triviales como «admin» o «123456»). Escríbala dos veces y pulse **Guardar**.

![Pantalla de ingreso con el logotipo JB Jaime Blanco](img/01_login.png){width=55%}

![Cambio obligatorio de contraseña en el primer ingreso](img/02_cambio_clave.png){width=55%}

**Resultado esperado:** tras guardar aparece la selección de empresa. **Prueba negativa:** escriba mal la contraseña: el sistema indica «Usuario o contraseña incorrectos» sin revelar cuál es el dato erróneo; tras 5 intentos fallidos el usuario queda bloqueado hasta que el administrador restablezca su clave.

## A3 ★ Empresa de demostración (recomendada para la prueba)

La forma más rápida de tener datos completos es crear la empresa de demostración.

1. En *Seleccionar empresa y gestión* pulse **Empresa de demostración** y confirme.
2. Seleccione «Distribuidora Andina S.R.L.», gestión **2025**, y pulse **Abrir**.

![Selección de empresa y gestión](img/03_selector_empresa.png){width=80%}

**Resultado esperado:** se abre la ventana principal con el tablero de inicio. Con la semilla determinista de la demostración las cifras de referencia son siempre las mismas:

| Dato | Valor de referencia |
|---|---|
| Ventas de diciembre | Bs 286.258,56 |
| Total activo al 31/12/2025 | Bs 2.048.383,01 |
| Total pasivo | Bs 394.971,58 |
| Total patrimonio (con resultado) | Bs 1.653.411,43 |
| Resultado antes de impuestos | Bs 504.111,43 |

![Tablero de inicio con indicadores, gráfico de ventas y compras, accesos rápidos y avisos](img/04_inicio.png){width=100%}

> **Nota:** la empresa de demostración es ficticia (nombre, NIT y datos). Puede eliminarla restaurando una copia de seguridad previa o ignorarla; no afecta a sus empresas reales.

## A4 Crear una empresa propia (para la Parte B)

La Parte B usa una empresa vacía. Pulse **Nueva empresa…** y complete:

| Campo | Valor de prueba |
|---|---|
| Código | PRUEBA |
| Razón social | PRUEBA S.R.L. |
| NIT | 1020304050 |
| Dirección / ciudad | Av. Camacho 123, La Paz |
| Año de la primera gestión | 2026 |
| Numeración | Por tipo y mes (recomendado) |

**Resultado esperado:** se crean la empresa, la gestión 2026 y el plan de cuentas boliviano base (más de 260 cuentas); la barra inferior muestra «PRUEBA S.R.L. · Gestión 2026».

## A5 Tipo de cambio y UFV

*Contabilidad > Tipos de cambio y UFV* → **Agregar / modificar**:

| Fecha | Dólar (Bs) | UFV |
|---|---|---|
| 01/01/2026 | 6,96 | 2,50000 |
| 31/12/2026 | 6,96 | 2,60000 |

![Tipos de cambio y UFV](img/09_tipo_cambio.png){width=100%}

**Resultado esperado:** los registros aparecen ordenados por fecha y la **UFV conserva sus 5 decimales** (escriba `2,61234`: debe verse `2,61234`, no un número entero ni redondeado). El tipo de cambio rige desde su fecha hasta que se cargue otro. La UFV también puede escribirse directamente en el comprobante.

## A6 Recorrido por el menú

Despliegue cada menú y verifique que existen las opciones del mapa siguiente. Las opciones que su usuario no pueda usar aparecen deshabilitadas (gris).

| Menú | Opciones principales |
|---|---|
| **Archivo** | Cambiar de empresa o gestión · Cambiar mi contraseña · Cerrar sesión · Salir |
| **Contabilidad** | Plan de cuentas · Nuevo comprobante · Comprobantes · Tipos de cambio y UFV · Conciliación bancaria · Presupuesto · Ajustes y cierre · Consolidación · Utilitarios |
| **Impuestos** | Libro de compras · Libro de ventas · Liquidación mensual de IVA e IT · Informes (LCV, liquidación, exportación SIN) |
| **Comercial** | Clientes · Proveedores · Nota de venta (F5) · Ventas realizadas · Nota de compra (F6) · Compras realizadas · Cobros y pagos |
| **Inventarios** | Ítems y precios · Movimiento de inventario · Movimientos registrados · Tablas auxiliares · Informes |
| **Activos fijos** | Registro de activos · Depreciación y actualización · Cuadro de activos |
| **Planillas** | Empleados · Planilla de sueldos · Anticipos · Aguinaldo y finiquitos · Informes |
| **Costos** | Órdenes de producción · Informe |
| **Estados financieros** | Los seis estados y el paquete completo |
| **Reportes** | Centro de reportes (F9) · Libro diario · Libro mayor · Sumas y saldos · Hoja de trabajo · Índices |
| **Administración** | Parámetros y normativa · Usuarios y permisos · Auditoría · Copias de seguridad |

![Menú Contabilidad](img/05_menu_contabilidad.png){width=100%}

![Menú Estados financieros](img/06_menu_estados_financieros.png){width=100%}

# 3. Parte B — Pruebas guiadas con datos propios

Use la empresa **PRUEBA S.R.L.** (gestión 2026). Los resultados esperados de estos casos están verificados automáticamente.

## B1 ★ Registro de un comprobante contable (nuevo formulario)

**Objetivo:** registrar un asiento y comprobar numeración automática y saldos. El formulario se reorganizó para facilitar el registro: **cabecera ordenada**, **sin botones de agregar/quitar filas** y **campos siempre editables** (se escribe directamente en la grilla).

**La cabecera (de izquierda a derecha)**

| Campo | Cómo funciona |
|---|---|
| Tipo de comprobante | Ingreso, Egreso, Traspaso o Ajuste |
| **Nº (automático)** | Solo lectura: el sistema muestra el número que recibirá (p. ej. `E-12/0014`); **no se digita** |
| Fecha / Mes | El mes se muestra según la fecha |
| Moneda · **T.C.** · **UFV** | T.C. es un campo corto; la **UFV** se puede escribir aquí (5 decimales) y queda registrada para esa fecha |
| **Banco** y **Nº de cheque / depósito** | Aparecen en egresos e ingresos; el banco se elige de las cuentas bancarias |
| Glosa | Descripción general (obligatoria); la casilla *Glosa por línea* habilita una glosa en cada fila |
| Cancelado a / Recibido de · Nº de documento | Dimensionados por separado (nombre amplio, documento corto) |
| **Calculadora** | Abre una calculadora; *Usar resultado* pega el valor en el campo Debe/Haber activo |
| **Plan de cuentas** | Abre el plan de cuentas sin salir del comprobante para crear o modificar una cuenta |

**Pasos**

1. *Contabilidad > Nuevo comprobante* (o **Ctrl + N** o el botón **Comprobante** de la barra).
2. Tipo **Traspaso**, fecha 02/01/2026, glosa «Aporte inicial». Observe el número automático **T-01/0001**.
3. En la primera fila escriba en *Código* «1.1.1.01.001» o parte del nombre («caja»): aparece la lista de sugerencias; pulse **Enter** y el sistema completa el *Nombre de la cuenta*. En *Debe* escriba **50000** y pulse Enter.
4. En la segunda fila escriba «3.1.1.01.001» (*Capital Social*) y en *Haber* **50000**. Las filas nuevas se agregan solas.
5. Las columnas *Debe $us / Haber $us* muestran el equivalente en la otra moneda. Abajo aparece **✔ Cuadra**. Pulse **Grabar**.

![Registro de un comprobante de egreso con banco y cheque, equivalentes en dólares e indicador de cuadre](img/40_comprobante_nuevo.png){width=100%}

**Resultado esperado:** el comprobante recibe el número **T-01/0001**; en *Contabilidad > Comprobantes* aparece vigente y el saldo de *Caja Moneda Nacional* es **Bs 50.000,00**.

**Atajos:** Enter avanza al siguiente campo; ↑ ↓ cambian de fila; **Supr** limpia la fila activa; **Igualar** coloca la diferencia en la línea activa o, si se eligió banco, en una nueva línea con la cuenta del banco.

![Calculadora integrada](img/40d_calculadora.png){width=35%}

![Plan de cuentas abierto desde el comprobante](img/40c_plan_cuentas_desde_comprobante.png){width=85%}

**Pruebas negativas (deben rechazarse con un mensaje claro y sin guardar nada):**

| Intento | Mensaje esperado |
|---|---|
| Debe 100 / Haber 90 | «El comprobante no cuadra: la diferencia es 10,00…» |
| Glosa vacía | «La glosa del comprobante es obligatoria.» |
| Fecha 31/12/2025 (gestión 2026) | «La fecha … está fuera de la gestión» |
| Código inexistente | La fila muestra «(cuenta no encontrada)» y al grabar: «la cuenta … no existe o no es de movimiento» |
| Cuenta de grupo (p. ej. 1.1.1.01) | «… no es de movimiento» |
| Línea con debe y haber a la vez | Al escribir en un lado, el otro se vacía |

## B1b ★ ¿Existe factura? — vínculo con los libros de compras y ventas

**Objetivo:** que los comprobantes de **Egreso** e **Ingreso** alimenten los **Libros de Compras y Ventas** (como pregunta Orion: «¿Existe factura?»).

**Pasos (egreso con factura de compra)**

1. Nuevo comprobante tipo **Egreso**, fecha 10/02/2026, glosa «Compra de servicios». Fila 1: *5.3.1.02.001 Energía Eléctrica*, Debe **500**; fila 2: *1.1.1.01.001 Caja*, Haber **500**. Pulse **Grabar**.
2. Aparece la pregunta **«¿Existe factura?»** con las opciones *Sí, hay factura*, *No* y *Volver*. Elija **Sí**.
3. En el cuadro de la factura (para egresos se elige *Compra de mercado interno* o *Importación (DUI)*) complete NIT 1003220026, razón social, Nº de factura 991, autorización/CUF e importe total **500**. Deje marcada la casilla *Agregar al comprobante la línea de crédito fiscal IVA*. Pulse **Aceptar**.

![Pregunta «¿Existe factura?»: datos que alimentan el libro de compras (o de ventas en los ingresos)](img/40b_comprobante_existe_factura.png){width=75%}

**Resultado esperado**

| Verificación | Valor |
|---|---|
| Asiento final | Energía Eléctrica **435,00** (debe) · **Crédito Fiscal IVA 65,00** (debe) · Caja 500,00 (haber) |
| Libro de Compras (febrero) | Una factura Nº 991 con base 500,00 y **crédito fiscal 65,00**, vinculada al comprobante |
| Anular el comprobante | La factura del libro pasa a **Anulada** (importes en cero) y la liquidación de IVA ya no la considera |

**Ingreso con factura de venta:** igual, con tipo **Ingreso**: se registra en el **Libro de Ventas** y el asiento separa el **débito fiscal** (13 % del importe de la factura) del ingreso principal. Si el asiento ya incluye una línea de IVA, el sistema no la duplica. Si elige **No**, el comprobante se graba sin vínculo.

## B2 Comprobante en dólares

1. Nuevo comprobante tipo **Egreso**, fecha 15/01/2026, moneda **Dólares**, T.C. 6,96, glosa «Pago en dólares».
2. Debe: *5.3.1.02.001 Energía eléctrica* **100**; Haber: *1.1.1.01.001 Caja* **100**.

**Resultado esperado:** al reabrirlo en bolivianos figura **Bs 696,00** por lado y **US$ 100,00** por lado. El balance de sumas y saldos puede emitirse en bolivianos o dólares.

## B3 ★ Venta con factura: débito fiscal e IT (ejemplo del manual de Orion)

**Objetivo:** comprobar el tratamiento del IVA 13 % (sobre el importe total de la factura) y del IT 3 % en una venta.

**Pasos**

1. *Impuestos > Libro de ventas IVA (registro)* → **Nueva factura**.
2. Fecha 15/01/2026 · NIT 1006341022 · Razón social «Minimarket El Ahorro» · Nº factura **1001** · Autorización/CUF «CUF1».
3. **Importe total de la factura: 1.000,00**. El sistema calcula *Importe base 1.000,00* y *Débito fiscal (13 %) 130,00*.
4. Deje marcado *Generar el comprobante contable* con contrapartida **Caja Moneda Nacional** y cuenta de ingreso **Ventas de Mercaderías**. Pulse **Registrar**.

![Registro de una factura de venta: cálculo del débito fiscal en tiempo real](img/42_factura_ventas.png){width=75%}

**Resultado esperado — asiento generado (tipo Ingreso):**

| Cuenta | Debe | Haber |
|---|---:|---:|
| Caja Moneda Nacional | 1.000,00 | |
| Débito Fiscal IVA | | 130,00 |
| Ventas de Mercaderías | | 870,00 |
| Impuesto a las Transacciones (gasto) | 30,00 | |
| IT por Pagar | | 30,00 |

![Un comprobante generado automáticamente por una venta (solo consulta)](img/41_comprobante_automatico_venta.png){width=95%}

## B4 ★ Compra con factura: crédito fiscal

*Libro de compras (registro)* → Nueva factura: 16/01/2026, NIT 1003220026, «Industrias Alimenticias», Nº **5001**, total **500,00**, contrapartida *Caja*, cuenta de gasto *5.3.1.02.001 Energía Eléctrica*.

**Resultado esperado:** *Crédito Fiscal IVA* **65,00** (13 % de 500) y gasto **435,00** contra Caja 500,00. Caja queda en 50.000 + 1.000 − 500 = **50.500,00**.

**Validaciones:** intentar registrar de nuevo la misma factura (mismo NIT, número y autorización) → «Ya está registrada la factura …». Registrar una factura con estado *Anulada* la guarda con importes en cero.

## B5 ★ Liquidación mensual del IVA e IT

*Impuestos > Liquidación mensual de IVA e IT…* → mes **Enero**.

| Concepto | Valor esperado |
|---|---:|
| Débito fiscal IVA | 130,00 |
| Crédito fiscal del mes | 65,00 |
| **IVA a pagar (Form. 200)** | **65,00** |
| Saldo a favor siguiente mes | 0,00 |
| IT devengado (Form. 400) | 30,00 |

![Liquidación mensual](img/43_liquidacion_iva.png){width=70%}

Pulse **Generar asiento de liquidación**: se salda el débito fiscal contra el crédito fiscal y se registra el pago de **Bs 65,00** desde la cuenta elegida. *Regla de saldo a favor:* si el crédito supera al débito, el exceso pasa al mes siguiente y se actualiza con la variación de la UFV (mantenimiento de valor).

## B6 ★ Inventario con costo promedio, compra con IVA y venta a crédito

**Preparación:** *Comercial > Clientes*: «Cliente Uno», NIT 1234567, límite de crédito 5.000. *Proveedores*: «Proveedor SA», NIT 2. *Inventarios > Ítems y precios*: código **ARZ01** «Arroz 1 kg», precio de venta 10,00.

| Paso | Operación | Resultado esperado |
|---|---|---|
| 1 | *Inventarios > Movimiento de inventario*: **Stock inicial** 100 u a costo 5,00, fecha 05/01/2026, contabilizar | Existencias 100 · costo promedio 5,00 |
| 2 | *Nota de compra* (F6) a Proveedor SA, factura 7001, **100 u a precio 8,00** (total 800) | Crédito fiscal 104,00 · costo neto de IVA 6,96 por unidad · existencias **200** · **costo promedio 5,98** |
| 3 | *Nota de venta* (F5) a Cliente Uno, factura 1002, **crédito**, 50 u a 10,00 (total 500) | Débito fiscal 65,00 · **costo de ventas 299,00** (50 × 5,98) · existencias **150** · inventario contable **897,00** |
| 4 | *Cobros y pagos*: cobro de **200** a Cliente Uno | Saldo del cliente **300,00** |
| 5 | Anular el cobro | Saldo vuelve a **500,00** |

![Nota de venta con ayuda de ítems, totales y monto en letras](img/44_nota_venta.png){width=95%}

![Cobro aplicado a documentos pendientes](img/45_cobro.png){width=80%}

**Pruebas negativas:** vender más que el stock → «Stock insuficiente de …»; vender a crédito más que el límite → «Se excede el límite de crédito del cliente».

![Kardex físico valorado en PDF](img/pdf_kardex.png){width=90%}

## B7 Movimientos de inventario: traspaso, ajuste y vencimientos

*Inventarios > Movimiento de inventario* (tipo **Traspaso** entre dos almacenes): las existencias totales no cambian, el kardex muestra salida del origen y entrada al destino. Un **ajuste de salida** (merma) reduce existencias y genera un asiento a *Mermas y pérdidas de inventario*. En ítems con control de vencimiento, la venta consume primero el lote que vence antes (FEFO) y el informe *Productos por vencer* lista los lotes.

![Movimiento de inventario](img/46_movimiento_inventario.png){width=90%}

## B8 ★ Activos fijos y depreciación

1. *Activos fijos > Registro de activos* → **Nuevo activo**: código PC1, «Computadora», grupo **Equipo de Computación (25 %)**, alta 10/01/2026, valor **12.000**.
2. *Activos fijos > Depreciación y actualización*: mes Enero → **Vista previa**.

**Resultado esperado:** depreciación del mes **Bs 250,00** (12.000 × 25 % ÷ 12). Pulse **Registrar depreciación**: se genera un comprobante (gasto 250,00 / depreciación acumulada 250,00); si repite el mes, no duplica.

![Depreciación mensual con vista previa](img/23_depreciacion.png){width=100%}

Grupos del D.S. 24051 precargados: edificaciones 40 años (2,5 %), muebles y enseres 10 años (10 %), maquinaria y equipo / equipo de oficina / instalaciones 8 años (12,5 %), vehículos 5 años (20 %), equipos de computación y herramientas 4 años (25 %).

## B9 ★ Planilla de sueldos con la normativa vigente

**Normativa utilizada (verificar contra la Gaceta Oficial):** SMN 2026 = **Bs 3.300** (D.S. 5516); aportes laborales: 10 % cotización + 1,71 % riesgo común + 0,5 % comisión + 0,5 % aporte solidario = **12,71 %**; patronal: CNS 10 % + riesgo profesional 1,71 % + Pro-Vivienda 2 % + aporte patronal solidario **3,5 %**; ANS 1,15 % > Bs 13.000, 5,74 % > Bs 25.000, 11,48 % > Bs 35.000; RC-IVA 13 % sobre lo que excede de 4 SMN, con crédito de 13 % de 2 SMN.

**Pasos:** *Planillas > Empleados* → Nuevo: «Ana Mamani», CI 111, ingreso 01/01/2020, cargo Contadora, haber **6.000**. Luego *Planillas > Planilla de sueldos* → mes Enero → **Generar**.

**Resultado esperado (6 años de antigüedad = 11 % de 3 SMN):**

| Concepto | Valor |
|---|---:|
| Haber básico | 6.000,00 |
| Bono de antigüedad (11 % × 3 × 3.300) | 1.089,00 |
| **Total ganado** | **7.089,00** |
| AFP – cotización 10 % | 708,90 |
| AFP – riesgo común 1,71 % | 121,22 |
| AFP – comisión 0,5 % | 35,45 |
| AFP – aporte solidario 0,5 % | 35,45 |
| ANS | 0,00 |
| RC-IVA (neto 6.187,98 < 13.200) | 0,00 |
| **Total descuentos** | **901,02** |
| **Líquido pagable** | **6.187,98** |
| Patronal: CNS 10 % | 708,90 |
| Patronal: riesgo profesional 1,71 % | 121,22 |
| Patronal: Pro-Vivienda 2 % | 141,78 |
| Patronal: solidario 3,5 % | 248,12 |

![Planilla de sueldos con aportes, ANS, RC-IVA y líquido pagable](img/25_planilla.png){width=100%}

**Caso de sueldo alto** (verifique con un empleado de 20.000): total ganado 21.089,00 → ANS **93,02**; neto 18.408,58; base RC-IVA 5.208,58; impuesto 677,12 con crédito de 2 SMN (858) → **RC-IVA a pagar 0,00**; líquido **18.315,56**.

Pulse **Cerrar y contabilizar**: se genera el comprobante con gastos, aportes y obligaciones (sueldos por pagar, AFP, CNS, Pro-Vivienda, solidario, RC-IVA). **Registrar pago** salda *Sueldos por pagar* contra caja. *Variables del empleado…* permite días trabajados, horas extra (pago doble), recargo nocturno (25 %), domingos (100 %), otros bonos/descuentos y facturas del Form. 110.

![Variables del mes por empleado](img/47_planilla_variables.png){width=65%}

![Planilla de sueldos en PDF](img/pdf_planilla.png){width=95%}

![Boleta de pago](img/pdf_boleta.png){width=75%}

## B10 Aguinaldo y finiquito

*Planillas > Aguinaldo y finiquitos*: para un empleado con 360 días en la gestión el aguinaldo es **un sueldo promedio** (7.089,00 para Ana Mamani). El *segundo aguinaldo* («Esfuerzo por Bolivia») está desactivado y se habilita en *Parámetros > Normativa* solo cuando el decreto lo disponga.

*Finiquito* (menú Planillas o botón en Empleados): despido intempestivo al 30/06/2026 con 10 días de vacación pendientes → antigüedad 6 años 6 meses; indemnización **46.078,50**; desahucio **21.267,00** (3 meses); aguinaldo proporcional **3.544,50**; vacaciones **2.363,00**; sueldo pendiente **6.000,00**; **total 79.253,00**. *El cálculo es referencial; la liquidación definitiva debe validarse con el Ministerio de Trabajo.*

![Aguinaldo de Navidad](img/26_aguinaldo.png){width=100%}

## B11 Orden de producción (costos)

*Costos > Órdenes de producción* → **Nueva orden** (producto, cantidad, almacenes) → en la ventana de la orden agregue *consumo de materia prima* (sale del inventario al costo promedio), *mano de obra* (horas × tarifa) y *costos indirectos*. Al **cerrar la orden** con la cantidad producida, el producto terminado ingresa al inventario al costo total unitario.

*Ejemplo:* MP 20 u × 3,00 = 60 + mano de obra 8 h × 12,50 = 100 + CIF 40 = **costo 200,00**; 10 u producidas → **costo unitario 20,00**.

![Órdenes de producción](img/28_produccion.png){width=100%}

# 4. Parte C — Recorrido por los módulos con la empresa de demostración

Abra la empresa **DEMO 2025** y verifique cada pantalla. En todas puede **buscar** escribiendo en el cuadro superior, **ordenar** y usar los botones de acción.

| Nº | Pantalla (menú) | Qué verificar | Imagen |
|---|---|---|---|
| C1 | Plan de cuentas (Contabilidad) | Árbol de 264 cuentas **en colores por tipo** (activo azul, pasivo rojo, patrimonio verde, ingresos turquesa, costos y gastos ámbar), columnas Mov./Presup./Ajust./M.E., buscar «caja», crear subcuenta, importar/exportar CSV | Fig. C1 |
| C2 | **Control de comprobantes** (menú *Comprobantes (control)*, tecla F2 o botón «Comprobante») | 445 comprobantes; detalle y líneas del seleccionado; botones Nuevo, Copiar, Eliminar, Revertir, Anular, Ver/Modificar, Imprimir, Enviar a Excel y a Word (ver Parte J) | Fig. C2 |
| C3 | Conciliación bancaria | Seleccione *Banco Unión*; marque movimientos; diferencia con extracto | Fig. C3 |
| C4 | Presupuesto | Asigne montos por mes a una cuenta de gasto y vea la ejecución | Fig. C4 |
| C5 | Libros de ventas y compras | Facturas con débito/crédito fiscal, estado, anular | Fig. C5 |
| C6 | Clientes / proveedores | Saldo, límite de crédito, estado de cuenta | Fig. C6 |
| C7 | Ventas / compras | Notas con estado, saldo, impresión | Fig. C7 |
| C8 | Cobros y pagos | Aplicación automática a los documentos más antiguos | Fig. C8 |
| C9 | Ítems | Costo promedio, stock, alerta en rojo bajo el mínimo | Fig. C9 |
| C10 | Activos fijos | 4 activos con depreciación acumulada | Fig. C10 |
| C11 | Empleados / planilla | 6 empleados, bono de antigüedad, planillas cerradas y pagadas | Fig. C11 |
| C12 | Órdenes de producción | Costos por orden | Fig. B11 |
| C13 | Cierre de gestión | Vista previa de ajustes, cierre, apertura de nueva gestión | Fig. C13 |
| C14 | Consolidación | Marque dos empresas y consolide | Fig. C14 |

![C1. Plan de cuentas con colores por tipo de cuenta](img/07_plan_cuentas.png){width=100%}

![C2. Comprobantes](img/08_comprobantes.png){width=100%}

![C3. Conciliación bancaria](img/10_conciliacion.png){width=100%}

![C4. Presupuesto y ejecución](img/11_presupuesto.png){width=100%}

![C5. Libro de ventas IVA](img/12_libro_ventas.png){width=100%}

![C5. Libro de compras IVA](img/13_libro_compras.png){width=100%}

![C6. Clientes](img/14_clientes.png){width=100%}

![C7. Ventas realizadas](img/16_ventas.png){width=100%}

![C8. Cobros y pagos](img/18_cobros_pagos.png){width=100%}

![C9. Ítems y precios](img/19_items.png){width=100%}

![Movimientos de inventario](img/20_movimientos_inventario.png){width=100%}

![C10. Activos fijos](img/22_activos.png){width=100%}

![C11. Empleados](img/24_empleados.png){width=100%}

![C13. Ajustes y cierre de gestión](img/29_cierre_gestion.png){width=100%}

![C14. Consolidación de empresas](img/30_consolidacion.png){width=100%}

# 5. Parte D — Estados financieros

Abra *Estados financieros* y emita cada uno con el período **01/01/2025 al 31/12/2025** de la empresa de demostración. Cada informe se ve en pantalla y se exporta con los botones **PDF**, **Excel** e **Imprimir**.

## D1 ★ Balance General

![Balance General en pantalla](img/51_visor_balance_general.png){width=100%}

**Verificaciones**

1. **Total activo = Total pasivo + Total patrimonio** → 2.048.383,01 = 394.971,58 + 1.653.411,43.
2. El patrimonio incluye el *Resultado de la gestión* (504.111,43) mientras no se haya hecho el cierre.
3. Las cuentas regularizadoras (depreciación acumulada) aparecen negativas dentro del activo no corriente.
4. Pruebe el detalle por nivel de cuenta (parámetro «Hasta nivel»).

![Balance General en PDF](img/pdf_balance_general.png){width=85%}

## D2 ★ Estado de Resultados

![Estado de Resultados](img/52_visor_estado_resultados.png){width=100%}

| Concepto | Valor de referencia |
|---|---:|
| Ventas netas | 3.651.628,17 |
| Costo de ventas | 2.336.385,70 |
| **Utilidad bruta** | **1.315.242,47** |
| Utilidad operativa | 513.711,43 |
| Resultado antes de impuestos | 504.111,43 |
| IUE estimado (25 %) | 126.027,86 |
| **Resultado neto** | **378.083,57** |

La línea del IUE se muestra porque la demostración tiene activada la opción *Parámetros > Reglas > Mostrar provisión estimada del IUE*; es informativa y no genera asiento.

![Estado de Resultados en PDF](img/pdf_estado_resultados.png){width=85%}

## D3 ★ Estado de Evolución del Patrimonio Neto

![Evolución del patrimonio neto](img/53_visor_evolucion_patrimonio.png){width=100%}

**Verificación:** la fila *Saldos al 31/12/2025* en la columna **Total** (1.653.411,43) es **igual al total patrimonio del Balance General**. Las columnas son: Capital social, Ajuste de capital, Reservas, Resultados acumulados y Resultado del ejercicio.

## D4 ★ y D5 ★ Estado de Flujo de Efectivo — métodos directo e indirecto

![Flujo de efectivo — método directo](img/54_visor_flujo_directo.png){width=100%}

![Flujo de efectivo — método indirecto](img/55_visor_flujo_indirecto.png){width=100%}

**Verificaciones cruzadas (las tres deben coincidir):**

| Concepto | Directo | Indirecto |
|---|---:|---:|
| Flujo de actividades de operación | 572.082,87 | 572.082,87 |
| Flujo de actividades de inversión | −150.000,00 | −150.000,00 |
| Flujo de actividades de financiamiento | 954.000,00 | 954.000,00 |
| **Variación neta del efectivo** | **1.376.082,87** | **1.376.082,87** |

La variación coincide además con el saldo de *Caja y bancos* del Balance (el efectivo inicial es 0 porque la gestión comienza en cero). El método directo muestra cobros a clientes, pagos a proveedores y gastos, pagos al personal, impuestos pagados netos y otros; el indirecto parte del resultado neto y lo concilia con depreciaciones y variaciones de cuentas por cobrar, inventarios, cuentas por pagar, obligaciones fiscales y laborales. Las transacciones de inversión y financiamiento **sin efectivo** (por ejemplo, aportes en especie) se excluyen de ambos y se informan por separado.

## D6 ★ Notas a los Estados Financieros

![Notas a los Estados Financieros](img/56_visor_notas.png){width=100%}

**Verificaciones:** las 14 notas incluyen naturaleza y objeto de la empresa, bases de preparación y políticas contables (moneda, efecto de la inflación y UFV, inventarios, activos fijos, indemnizaciones, impuestos), el detalle de disponible, exigible, inventarios, activos fijos, pasivos corrientes y no corrientes, patrimonio, ingresos, costos y gastos, posición en moneda extranjera, contingencias y hechos posteriores. El *total del disponible* de la Nota 3 coincide con *Caja y bancos* del Balance. Los textos de contingencias y hechos posteriores se editan en *Administración > Parámetros > Reglas*.

## D7 Paquete completo de estados financieros

*Estados financieros > Todos los estados financieros (paquete completo)*: genera un solo PDF con los **seis estados** en este orden: Balance General, Estado de Resultados, Evolución del Patrimonio, Flujo directo, Flujo indirecto y Notas, con **encabezado de empresa**, **paginación «Página x de y»** y **firmas** de Contador y Representante Legal. El archivo de ejemplo `ejemplo_estados_financieros.pdf` se incluye con el manual.

# 6. Parte E — Informes (los 79 del sistema)

Abra el **Centro de reportes** (F9). Los informes están agrupados por módulo y filtrados según los permisos del usuario.

![Centro de reportes](img/38_centro_reportes.png){width=100%}

Para **cada informe** de la tabla siguiente verifique la lista de control: (1) abre sin errores con los parámetros por defecto; (2) el encabezado muestra razón social, NIT y período; (3) los totales son coherentes con la pantalla de origen; (4) el **PDF** tiene encabezado repetido, numeración «Página x de y» y firmas donde corresponde; (5) el **Excel** tiene los importes como números (se pueden sumar) y columnas legibles.

<!--CATALOGO-->

![Parámetros de un informe](img/50_parametros_informe.png){width=60%}

![Libro de ventas IVA en pantalla](img/57_visor_libro_ventas.png){width=100%}

![Libro de ventas IVA en PDF](img/pdf_libro_ventas.png){width=95%}

![Liquidación de IVA e IT en PDF](img/pdf_liquidacion_iva.png){width=95%}

![Comprobante en PDF, con espacios para cuatro firmas](img/pdf_comprobante.png){width=85%}

# 7. Parte F — Seguridad, respaldo, cierre y multiempresa

## F1 ★ Usuarios, roles y permisos

1. *Administración > Usuarios y permisos* → **Nuevo usuario**: «operador1», rol **Operador**.
2. Seleccione el usuario → **Permisos…**: marque o desmarque opciones; el rol **Consulta** deja solo informes.
3. Cierre sesión e ingrese como `operador1`: las opciones sin permiso aparecen **deshabilitadas** y cualquier intento directo muestra «No tiene permiso para realizar esta operación».

![Usuarios](img/34_usuarios.png){width=100%}

![Permisos de un usuario](img/48_permisos_usuario.png){width=65%}

## F1b Recuperar el acceso de administrador

**Recuperación del administrador.** Si otro administrador puede ingresar, restablezca la clave en *Administración > Usuarios y permisos* (también desbloquea). Si no, use cualquiera de estas tres vías (en el equipo donde está instalado): (a) en la pantalla de ingreso, el botón **«Restablecer administrador»**; (b) *Inicio > CONTA JB > Restablecer contraseña de administrador*; (c) el archivo **`Restablecer_admin.bat`** de la página de descargas (o `ContaJB.exe --restablecer-admin`). En todas, escriba **RESTABLECER**: el usuario `admin` queda activo y desbloqueado con la clave temporal `admin` y cambio obligatorio. La acción queda en la bitácora de seguridad.

**Esperado:** tras la confirmación aparece «Listo»; al ingresar con `admin` / `admin` el sistema obliga a elegir una nueva contraseña. Si se escribe otra palabra, no se cambia nada.

## F2 Auditoría

*Administración > Auditoría*: aparecen los ingresos (correctos y fallidos), comprobantes creados y anulados, aperturas de gestión, copias y demás acciones con usuario, fecha, hora y equipo. Pruebe el filtro por fechas.

![Auditoría del sistema](img/35_auditoria.png){width=100%}

## F3 ★ Copia de seguridad y restauración

1. *Administración > Copias de seguridad* → **Respaldar esta empresa**: se crea un archivo `.cbk` (zip con huella SHA-256 de cada archivo).
2. Registre un comprobante nuevo y anote cuántos hay.
3. **Restaurar desde archivo…** y elija la copia: el sistema crea antes una copia de seguridad de lo actual y luego restaura.
4. **Resultado esperado:** el comprobante nuevo ya no existe y el resto de los datos permanece.
5. **Integridad:** copie el `.cbk`, modifique un byte con un editor y use **Verificar un respaldo…**: debe rechazarlo («La copia está dañada: falla la verificación…»).
6. Cierre la aplicación: se genera una copia **automática** en la carpeta de respaldos.

![Copias de seguridad](img/36_backup.png){width=100%}

## F4 ★ Cierre de gestión y apertura de la siguiente

1. *Contabilidad > Ajustes y cierre de gestión…*
2. **Diferencia de cambio:** fecha 31/12, T.C. final; use **Vista previa** y luego **Registrar** (actualiza en bolivianos las cuentas en dólares).
3. **Ajuste por inflación (UFV):** solo si su política lo exige; la Norma Contable N° 3 está suspendida contablemente desde 2020 (CTNAC 03/2020) y el sistema lo recuerda.
4. **Asiento de cierre:** salda ingresos y gastos contra *Resultado de la gestión*. Los estados financieros previos **no cambian**.
5. **Cerrar gestión:** intente luego crear un comprobante → «La gestión 2025 está cerrada: solo permite consultas y reportes».
6. **Abrir nueva gestión…** → se crea la gestión 2026 con: asiento de apertura (el resultado pasa a *Resultados acumulados*), existencias iniciales al costo promedio, saldos de clientes y proveedores, activos fijos con su depreciación acumulada y empleados.

**Resultado esperado:** el Balance General al 01/01/2026 **cuadra** y su total activo es igual al del cierre 2025; el efectivo inicial del flujo de efectivo 2026 es igual al saldo de caja y bancos al 31/12/2025.

## F5 Multiempresa y consolidación

Cree una segunda empresa y registre un comprobante distinto. Cambie entre empresas con *Archivo > Cambiar de empresa o gestión*: **los datos no se mezclan** (cada empresa y gestión tiene su propio archivo `datos\EMPRESA\AÑO.db`). Luego, *Contabilidad > Consolidación de empresas*: marque ambas, rango anual y nivel de detalle; el saldo consolidado de cada cuenta es la suma de ambas.

## F6 Datos de la empresa, parámetros y normativa

La pantalla *Administración > Datos de la empresa y parámetros* se rediseñó al estilo de los «Datos empresariales» de Orion, con los **puntos clave resaltados**:

1. **Datos de la empresa:** nombre, NIT, dirección, ciudad, teléfono, correo, actividad, representante legal, matrícula, gestión y archivo de datos.
2. **Recuadro amarillo «Puntos clave»:** **% IVA, % IT, % IUE, salario mínimo nacional, aporte patronal solidario y mínimo no imponible del RC-IVA**. Al modificarlos y pulsar **Grabar** se guarda un nuevo valor de normativa con vigencia desde el inicio de la gestión.
3. **Cuentas importantes por grupo** (Impuestos; Clientes, proveedores y caja; Ventas, compras e inventario; Sueldos, aportes y beneficios; Cierre, ajustes y activos): cada una con código, autocompletado y nombre visible.
4. **Reglas de operación** y notas de los estados financieros.

![Datos de la empresa con los puntos clave resaltados](img/31_datos_empresa.png){width=100%}

**Prueba:** cambie el salario mínimo a 3.500 y grabe; abra una planilla nueva: el bono de antigüedad se calcula con el nuevo valor. Escriba un código de cuenta inexistente en un grupo: el campo muestra «⚠ cuenta no encontrada» y al grabar el sistema lo rechaza.

![Normativa laboral e impositiva vigente, con vigencia por fechas](img/33_parametros_normativa.png){width=100%}

En *Normativa vigente (todas)* están todos los parámetros legales con su fecha de vigencia y fuente. **Prueba:** agregue un valor de *SMN* con vigencia desde el 01/07/2026 y recalcule una planilla de agosto: usa el nuevo valor, mientras que la de enero conserva el anterior.

## F7 Utilitarios y verificación

*Contabilidad > Utilitarios y verificación*: muestra **[OK]/[AVISO]/[ERROR]** de comprobantes cuadrados, totales de cabecera vs. detalle, balance que cuadra, flujo de efectivo conciliado, cuentas parametrizadas, tipo de cambio y UFV cargados, stock negativo, inventario valorado vs. cuenta contable e integridad de la base de datos.

![Utilitarios y verificación](img/37_utilitarios.png){width=100%}

![Acerca de CONTA JB](img/49_acerca_de.png){width=60%}

# 8. Parte H — Verificación de las modificaciones solicitadas (versión 2.1)

Esta parte comprueba, punto por punto, la «Solicitud de modificaciones» recibida.

| Nº | Modificación solicitada | Cómo verificarla | Esperado |
|---|---|---|---|
| 1 | Nombre **CONTA JB** y logotipo | Abrir el programa; ver la ventana de ingreso, el título de la ventana, *Ayuda > Acerca de*, el icono del escritorio y los PDF | Todo dice **CONTA JB**; el logotipo JB Jaime Blanco aparece en el ingreso, el tablero y *Acerca de*; el icono es el monograma **JB** |
| 2 | Diseño más profesional (colores y estructura de formularios) | Abrir cualquier formulario (cliente, ítem, activo, empleado…) y las pantallas principales | Cabecera de formulario con título y ayuda, campos agrupados en dos columnas, botones primarios en azul, tablas con encabezado azul |
| 3 | UFV con **5 decimales** | *Tipos de cambio y UFV*: registrar `2,61234`; también en el comprobante | Se guarda y muestra `2,61234` |
| 4 | Iconos del menú más profesionales | Observar la barra de accesos rápidos y los menús desplegados | Iconos vectoriales por categoría (comprobante, ventas, compras, libros, plan de cuentas, ítems, planilla, estados financieros, calculadora, respaldo) |
| 5 | Datos de la empresa con puntos clave resaltados | *Administración > Datos de la empresa y parámetros* | Recuadro amarillo con IVA, IT, IUE, salario mínimo, aporte solidario; cuentas importantes agrupadas (ver F6) |
| 6 | Plan de cuentas con mejor diseño en colores | *Contabilidad > Plan de cuentas* | Colores por tipo y por nivel, columnas de indicadores (ver C1) |
| 7 | Nuevo registro de comprobantes | Ver caso **B1**: UFV en la cabecera, T.C. corto, banco y Nº de cheque, acceso directo al plan de cuentas, calculadora, campos «A nombre de» y «Nº de documento» redimensionados, **numeración automática**, grilla sin botones de filas y con celdas siempre editables | Todos los elementos presentes y funcionales |
| 8 | Relación de ingresos y egresos con los libros de compras y ventas | Ver caso **B1b** («¿Existe factura?») | La factura queda en el Libro de Compras/Ventas, vinculada al comprobante, con IVA correcto; al anular el comprobante se anula la factura |

![Tablero de inicio con el nuevo logotipo, iconos y barra de accesos rápidos](img/04_inicio.png){width=100%}

![Acerca de CONTA JB](img/49_acerca_de.png){width=65%}

# 9. Parte I — Módulos de Auditoría Financiera (MAF) y Tributaria (MAI) — versión 2.2

Estos módulos se abren desde el menú **Auditoría**. Requieren el permiso *Auditoría financiera / tributaria* (rol **Auditor**, **Contador** o **Administrador**). La empresa de demostración incluye dos encargos de ejemplo: **AF-2025-001** (financiera) y **AT-2025-001** (tributaria), con los papeles de trabajo ya iniciados. Las cifras siguientes corresponden a esa empresa y están verificadas por las pruebas automáticas.

> **Alcance y advertencias.** CONTA JB **organiza y calcula** los papeles de trabajo; **no sustituye el juicio profesional** del auditor. Los borradores de dictamen deben ser revisados y firmados por el profesional responsable. Los formatos de los anexos de la Información Tributaria Complementaria (ITC) son **referenciales**: deben adecuarse al formato oficial vigente del SIN antes de presentarse. Los umbrales y tasas marcados «verificar» (bancarización, tope de donaciones, tasa de interés de contingencias, umbral de auditoría externa) se encuentran en *Administración > Parámetros y normativa* y deben confirmarse con la norma vigente.

## I1 ★ Encargo y planificación (Etapa A)

1. *Auditoría > Auditoría financiera (MAF)*. Seleccione el encargo **AF-2025-001**.
2. Pestaña **A · Planificación**: revise los *términos del encargo*, la comprensión del negocio y el control interno.
3. Cambie **Riesgo inherente = Alto** y **Riesgo de control = Alto**, con riesgo aceptable 0,05, y pulse **Guardar memorándum y calcular RD**.

| Verificación | Esperado |
|---|---|
| Fórmula | RA = RI × RC × RD ⇒ **RD = RA / (RI × RC)** (factores Bajo 0,4 · Medio 0,7 · Alto 1,0) |
| RI = Medio, RC = Medio, RA = 5 % | RD = **10,20 %** («riesgo de detección bajo: ampliar el alcance de las pruebas»); con RI y RC en *Bajo* el RD sube a 31,25 % («medio») |
| RI = Alto, RC = Alto, RA = 5 % | RD = **5,00 %** («riesgo de detección bajo: ampliar alcance y muestra») |
| Materialidad (base Activo total Bs 2.048.383,01, 1 %) | Global **20.483,83** · Desempeño (75 %) **15.362,87** · Trivial (5 %) **1.024,19** |
| Matriz de riesgos | 29 filas componente × aseveración (Existencia, Integridad, Valuación/asignación, Derechos y obligaciones, Presentación y revelación); doble clic para cambiar nivel y respuesta |

![Planificación: memorándum, riesgo y materialidad](img/60_aud_planificacion.png){width=100%}

![Programas de auditoría por componente](img/61_aud_programas.png){width=100%}

**Programas (pestaña «A · Programas»):** 45 procedimientos para Disponibilidades, Cuentas por cobrar, Inventarios (MP, productos en proceso y terminados), Activos fijos y depreciaciones, Planillas y pasivos laborales, Costos de conversión, Patrimonio, Ingresos y Gastos. Doble clic en un procedimiento: registre estado, referencia al papel de trabajo y conclusión; el avance se actualiza en la parte superior.

## I2 ★ Cédulas sumarias, analíticas y marcas (Etapa B)

1. Pestaña **B · Cédulas** > **Generar desde saldos del sistema** (ya generadas en el demo).
2. Compare con el *Balance General* y *Estado de Resultados*.

| Cédula | Rubro | Saldo según sistema (Bs) |
|---|---|---|
| A | Disponible | **1.376.082,87** |
| B | Exigible | **106.161,90** |
| C | Inventarios | **458.254,90** |
| E | Activos fijos y depreciación | **107.883,34** |
| AA / BB / CC | Cuentas por pagar / Obligaciones fiscales / Sociales y laborales | 56.324,22 / 125.918,26 / 128.729,10 |
| PP · II · GG | Patrimonio · Ingresos · Costos y gastos | 1.149.300,00 · 3.651.628,17 · 3.147.516,74 |

Indexación: **A, B, C…** para activos y **AA, BB, CC…** para pasivos. Doble clic en una cédula: se abren las **analíticas** (una por cuenta); registre el *saldo verificado* y las **marcas** de la leyenda (V verificado, S sumado, M cotejado con Mayor, D con documentación, C confirmado por terceros, F inspección física, R recalculado, T rastreado, N no conforme, A con ajuste). Una marca que no está en la leyenda se rechaza. Use **Firmar preparación** y **Firmar revisión** (la revisión debe hacerla otra persona del equipo).

![Cédulas sumarias](img/62_aud_cedulas.png){width=100%}

## I3 ★ Pruebas sustantivas conectadas a los módulos (Etapa B)

Pestaña **B · Pruebas sustantivas**. Seleccione la prueba, pulse **Ejecutar y guardar como papel de trabajo**.

| Prueba | Conecta con | Resultado en el demo |
|---|---|---|
| Muestreo para recuento | Inventarios | 10 de 12 ítems seleccionados, **cobertura 99,1 %** del valor (los de mayor valor al 100 % + muestra aleatoria reproducible con *semilla* 2025) |
| Corte documental (±5 días) | Ventas, compras, movimientos de inventario y comprobantes | 3 documentos revisados, **0 diferencias** |
| VNR y obsolescencia | Ítems, precios, lotes y kardex | Sin ítems observados (costo ≤ valor neto de realización) |
| Kardex vs. contabilidad | Inventarios y cuenta 1.1.3 | Diferencia 0,01 (redondeo) ⇒ **conciliado** |
| Costos de conversión | Órdenes de producción (MP, MOD, CIF) | Cuota de aplicación del CIF sobre MOD y variaciones contra las cuentas 5.2.1.01 |
| Depreciación vs. D.S. 24051 | Activos fijos | 4 activos, **exceso 0,08** (redondeo, tolerancia 0,50) ⇒ conforme; lista altas y bajas del período |
| Planilla vs. aportes | Planillas | **1 partida con diferencia**: la *provisión de aguinaldo* (Bs 32.100,00 esperados) no está contabilizada ⇒ da origen al hallazgo H-01 |
| Antigüedad de cuentas por cobrar | Ventas y cobros | Todo el saldo (Bs 106.161,90) está en el tramo 0–30 días; previsión sugerida 0,00 |

![Pruebas sustantivas: muestreo para recuento](img/63_aud_pruebas.png){width=100%}

## I4 ★ Hallazgos, ajustes y desvíos (Etapa C)

1. Pestaña **C · Hallazgos**: el hallazgo **H-01** (aguinaldo no provisionado) tiene los cuatro elementos — **Condición, Criterio, Causa, Efecto** — más Recomendación y **Descargo de la Gerencia**. Intente guardar uno nuevo sin *Causa*: el sistema lo rechaza.
2. Pestaña **C · Ajustes y desvíos**: el asiento propuesto **AJU-1** (Debe 5.3.1.01.004 Aguinaldos / Haber 2.1.3.02.001 Provisión de aguinaldos, **Bs 32.100,00**) está en estado *No corregido*.
3. Cambie su estado a **Aceptado**: la cédula **CC** muestra el ajuste y el saldo auditado cambia; vuelva a dejarlo *No corregido*.

| Verificación | Esperado |
|---|---|
| Efecto de desvíos no corregidos | **−32.100,00** en resultados |
| Frente a la materialidad global (20.483,83) | «**SUPERA** la materialidad global: evaluar opinión modificada» |
| Opinión sugerida (NIA 705) | **Con salvedad** (no vinculante; el auditor decide) |

![Hallazgos](img/64_aud_hallazgos.png){width=100%}

![Ajustes propuestos y resumen de desvíos](img/65_aud_ajustes.png){width=100%}

## I5 ★ Dictamen y cierre inmutable

1. Pestaña **C · Dictamen / informe**: elija la opinión y **Generar borrador** (NIA 700; con salvedad o adversa según NIA 705; énfasis y cuestiones clave según NIA 706/701). Edite el texto y pulse **Emitir**.
2. **Cerrar y firmar**: se pide la contraseña del usuario. El encargo queda **CERRADO**: los papeles de trabajo pasan a **solo lectura** (también a nivel de base de datos) y se guarda la huella **SHA-256** de toda la evidencia.
3. **Verificar integridad**: confirma que el contenido actual coincide con la huella firmada.

| Prueba | Esperado |
|---|---|
| Intentar cerrar sin dictamen | Se rechaza |
| Contraseña de firma incorrecta | Se rechaza |
| Editar cualquier papel tras el cierre | «El encargo está CERRADO… solo lectura» |
| Bitácora (*Informes > Bitácora de auditoría*) | Cada acción con usuario, fecha y huella encadenada; si alguien altera un registro, la cadena se marca **ALTERADA** |

![Dictamen](img/66_aud_dictamen.png){width=100%}

## I6 ★ Auditoría tributaria (MAI) — conciliaciones

*Auditoría > Auditoría tributaria (MAI)*, encargo **AT-2025-001**, pestaña **B · Pruebas tributarias**.

| Prueba | Esperado en el demo |
|---|---|
| Conciliación Débito Fiscal / Crédito Fiscal / IT vs. Libros de Ventas y Compras | 12 meses, **0 con diferencia** (IT: diferencia acumulada 0,03 por redondeo; tolerancia 1,00) |
| Bancarización (umbral Bs 50.000, parámetro *BANCARIZACION_MONTO*) | **35 operaciones** ≥ umbral: 17 respaldadas, 1 pendiente de pago, **17 sin respaldo** por **Bs 1.144.950,86** (crédito fiscal en riesgo ≈ Bs 148.843,61) |

![Bancarización](img/67_aud_mai_pruebas.png){width=100%}

Para experimentar una diferencia: registre una factura en el Libro de Ventas **sin** generar asiento (IVA 13 % de Bs 1.000 = 130,00): la conciliación de ese mes muestra DF libro 130,00 vs. contabilidad 0,00.

## I7 ★ Depuración de gastos e IUE

Pestaña **B · Depuración IUE** > **Depurar**. El sistema **sugiere** gastos no deducibles (D.S. 24051): compras sin factura, operaciones sin respaldo bancario, depreciación en exceso, multas y recargos, IUE registrado como gasto, previsiones por verificar. Cada sugerencia debe ser **Confirmada o Descartada** por el auditor; también puede **agregar gastos manuales** (p. ej. donaciones por encima del tope del 10 % de la utilidad imponible).

| Verificación (demo) | Esperado |
|---|---|
| Utilidad contable antes de impuestos | **504.111,43** |
| Sugerencias pendientes | 2 (operaciones sin respaldo bancario Bs 1.144.950,86; depreciación en exceso Bs 0,08) |
| Confirmar la primera | Utilidad imponible = 504.111,43 + 1.144.950,86 = **1.649.062,29**; IUE 25 % = **412.265,57** |
| Descartar la segunda | Queda sin sugerencias pendientes (la cédula pasa a «conforme») |

![Depuración del IUE](img/68_aud_mai_iue.png){width=100%}

## I8 Anexos ITC e informes tributarios

1. Pestaña **B · Anexos ITC** > **Llenar anexos automáticamente**: se generan los **15 anexos** referenciales (ingresos, costos y gastos, conciliaciones de DF/CF/IT, depuración del IUE, activos fijos, inventarios, cuentas por cobrar y por pagar, planilla, bancarización, patrimonio, retenciones, hallazgos).
2. **Calculadora de contingencias**: tributo omitido Bs 10.000 con vencimiento 20/03/2025, cálculo 31/12/2025, tasa 10 % (ingresada por el usuario), sin sanción.

| Resultado de la calculadora | Esperado |
|---|---|
| UFV al vencimiento / al cálculo | 2,49600 / 2,61600 (según los valores cargados en el demo) |
| Tributo actualizado (× 1,048077) | **10.480,77** |
| Intereses (286 días, 10 % anual, base 360) | **832,64** |
| Deuda tributaria | **11.313,41** |

> La tasa de interés y la sanción **no vienen precargadas** (valor 0): el usuario debe ingresarlas según la Ley 2492 (Código Tributario) y las disposiciones del SIN vigentes.

Pestaña **C · Dictamen / informe** en MAI: genere el **Dictamen Tributario**, el **Informe de procedimientos mínimos tributarios** o el **Informe sobre la situación tributaria** (con la liquidación de contingencias de los hallazgos con impacto en monto).

![Anexos ITC](img/69_aud_mai_anexos.png){width=100%}

## I9 Informes PDF / Excel de auditoría

Desde *Auditoría > …* o el botón **Informes…** de cada pantalla: memorándum de planificación, matriz de riesgos, programas, cédulas sumarias y analíticas, pruebas ejecutadas, hallazgos, resumen de desvíos, dictamen, bitácora (MAF) y conciliación IVA/IT, bancarización, depuración del IUE, anexos ITC y contingencias (MAI). Todos se exportan a **PDF y Excel** y, si el encargo está cerrado, imprimen su huella SHA-256 al pie.

![Memorándum de planificación en PDF](img/pdf_aud_mpa.png){width=70%}

![Cédulas sumarias en PDF](img/pdf_aud_sumarias.png){width=100%}

![Cédula de depuración del IUE en PDF](img/pdf_aud_iue.png){width=70%}

## I10 Consulta por API local (opcional, equipo técnico)

`python -m contabol.api --empresa DEMO --anio 2025` abre una **API de solo lectura** en `127.0.0.1:8765` con un token aleatorio (cabecera `Authorization: Bearer <token>`). Rutas principales (parámetro `encargo`): `/api/v1/inventarios/corte-documental`, `/api/v1/tributario/conciliacion-iva-it`, `/api/v1/activos/depreciacion-vs-ds24051`, `/api/v1/tributario/bancarizacion`, `/api/v1/auditoria/integridad`. La ruta `/api/v1/` lista todas.

# 10. Parte J — Control de comprobantes, envío a Word y activación (versión 2.3)

## J1 ★ Control de comprobantes

Se abre con el menú **Contabilidad > Comprobantes (control)** (F2) o con el botón **Comprobante** de la barra. Muestra **todos** los comprobantes de la gestión.

![Control de comprobantes](img/08_comprobantes.png){width=100%}

| Elemento | Qué verificar |
|---|---|
| Tabla | Columnas: Cbte., Fecha, Tipo, Origen (Manual, Venta, Compra, Cobro, Planilla, Activo, Ajuste, Reversión…), Beneficiario / a nombre de, Nº doc., Glosa, Total debe y haber en Bs, Estado y Usuario. En el demo: **445 comprobantes**, total debe = total haber = **Bs 16.639.555,05** |
| Filtros | Desde, Hasta, Tipo, Estado (Todos / Vigentes / Anulados), **Ordenar por** (Fecha, Número, Tipo y número, Importe, Beneficiario) y buscador por glosa, beneficiario o Nº de documento |
| Detalle (al seleccionar) | Cbte., fecha, **dólar**, **UFV**, estado, origen (con referencia), banco y Nº de cheque, usuario, a nombre de, Nº de documento, **factura vinculada** (libro de compras o ventas, con su IVA), glosa y las **líneas del asiento** (cuenta, glosa, debe, haber) |
| **Nuevo** | Abre el formulario de comprobante; al guardar, la tabla se actualiza y queda seleccionado |
| **Copiar** | Abre un comprobante nuevo con el mismo tipo, glosa, beneficiario y líneas; usted corrige la fecha o los importes y lo guarda con número nuevo |
| **Revertir** | Pide la fecha del contra-asiento y genera un comprobante de traspaso con **debe y haber invertidos**. Ambos quedan en los libros; el original muestra «Revertido por…». No se puede revertir dos veces ni revertir una reversión |
| **Eliminar** | Borra definitivamente **solo el último comprobante de su tipo y mes** (para no dejar saltos en la numeración), si no está conciliado ni revertido. En otro caso explica que debe usar Anular o Revertir |
| **Anular** | Marca el comprobante como anulado (sin efecto contable), anula su factura vinculada y lo muestra en rojo |
| **Ver / Modificar** (o doble clic) | Abre el comprobante; los generados por otros módulos son de solo consulta |
| **Imprimir** | Comprobante en PDF listo para firmar |
| **Enviar a Excel / Enviar a Word** | Exporta **toda la tabla con los filtros actuales** (informe «Control de comprobantes»), con totales |
| Actualizar / Salir | Recarga la tabla / cierra la pestaña |

**Prueba guiada.**

1. Filtre *Tipo = Egreso*, *Estado = Vigentes*: la leyenda inferior cambia de totales.
2. Seleccione un egreso con factura: en «Factura vinculada» aparecen el Nº, el proveedor y el IVA.
3. Pulse **Copiar**, cambie la fecha y el importe y guarde: aparece un comprobante nuevo con el número siguiente.
4. Seleccione ese comprobante nuevo y pulse **Revertir**: aparece otro de tipo Traspaso con origen *Reversión*; el *Balance de sumas y saldos* queda igual que antes de ambos.
5. Pulse **Eliminar** sobre un comprobante que no es el último de su tipo: el sistema lo rechaza explicando por qué.
6. Pulse **Enviar a Excel** y abra el archivo: columnas numéricas con formato y fila de totales.

## J2 ★ Enviar a Word

Todos los informes (en especial los que tienen **texto**) tienen el botón **Word** junto a *PDF*, *Excel* e *Imprimir*: *Notas a los Estados Financieros*, *Memorándum de planificación*, hallazgos, dictámenes e informes de auditoría, etc. En la pantalla de **Dictamen / informe** de auditoría, el botón **Enviar a Word** exporta el texto **tal como usted lo editó**.

![Visor con el botón Word](img/56_visor_notas.png){width=100%}

| Prueba | Esperado |
|---|---|
| *Estados financieros > Notas a los Estados Financieros* → **Word** | Archivo `.docx` con encabezado de la empresa, título, notas numeradas y tablas con encabezado azul, importes a la derecha |
| *Auditoría > Memorándum de planificación* → **Word** | Documento con los títulos, textos y tablas de riesgo y materialidad |
| *Auditoría financiera > C · Dictamen* → generar borrador → editar → **Enviar a Word** | El Word contiene el texto editado |
| Abrir el `.docx` en Word | Se puede editar, cambiar fuentes y agregar membrete propio |

![Notas a los estados financieros exportadas a Word](img/word_notas_eeff.png){width=70%}

![Memorándum de planificación exportado a Word](img/word_memorando.png){width=70%}

## J3 ★ Activación de la licencia

El procedimiento completo está en el **Manual de Activación**. Verificación rápida:

| Prueba | Esperado |
|---|---|
| Primer ingreso | Pantalla de activación: «Modo de prueba: quedan 30 días» y un código de solicitud `JB-…` |
| **Continuar en modo de prueba** | Entra al sistema |
| Pegar un código inválido y **Activar** | Mensaje de error; sigue en prueba |
| (Proveedor) *Ayuda > Emitir código de activación* con su clave privada | Genera el código para una solicitud |
| Pegar el código y **Activar** | «CONTA JB quedó activado»; ya no se pide al iniciar |

![Activación](img/70_activacion.png){width=70%}

# 11. Parte G — Pruebas automáticas y verificación del instalador

## G1 Ejecutar las pruebas automáticas (equipo técnico)

Desde la carpeta del código fuente:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python -m pytest
```

**Esperado:** todas las pruebas en verde (más de 70), incluyendo `test_manual.py` (cifras de este manual), `test_estados.py` (los seis estados), `test_reportes.py` (79 informes en PDF y Excel) y `test_ui.py` (todas las pantallas).

## G2 Autoprueba del programa instalado

Desde una consola, en la carpeta de instalación:

```
ContaJB.exe --autoprueba
```

**Esperado:** imprime **AUTOPRUEBA OK**. La autoprueba crea datos temporales, abre la ventana principal, genera el paquete de estados financieros en PDF y Excel y verifica que el balance cuadra, sin tocar sus datos reales.

# Anexo A. Registro de resultados

| Caso | Fecha | Probador | ✔ / ✘ / ⛔ | Evidencia (nombre de captura) | Observaciones |
|---|---|---|---|---|---|
| A1 Instalación | | | | | |
| A2 Primer ingreso | | | | | |
| A3 Demostración | | | | | |
| B1 Comprobante | | | | | |
| B3 Venta con IVA/IT | | | | | |
| B4 Compra | | | | | |
| B5 Liquidación IVA | | | | | |
| B6 Inventario | | | | | |
| B8 Activos fijos | | | | | |
| B9 Planilla | | | | | |
| B10 Aguinaldo/finiquito | | | | | |
| B11 Producción | | | | | |
| D1 Balance General | | | | | |
| D2 Estado de Resultados | | | | | |
| D3 Evolución del Patrimonio | | | | | |
| D4 Flujo directo | | | | | |
| D5 Flujo indirecto | | | | | |
| D6 Notas | | | | | |
| E Informes (65) | | | | | |
| F1 Usuarios y permisos | | | | | |
| F3 Respaldo y restauración | | | | | |
| F4 Cierre y apertura | | | | | |
| F5 Multiempresa | | | | | |
| G Pruebas automáticas | | | | | |

**Conclusión:** ☐ Aprobado  ☐ Aprobado con observaciones  ☐ Rechazado

Firma del contador validador: ______________________  Firma del responsable técnico: ______________________  Fecha: ____________

# Anexo B. Cómo tomar evidencia

1. **Alt + ImprPant** copia solo la ventana activa; péguela en Word o Paint. También sirve *Recortes* de Windows (**Win + Mayús + S**).
2. Nombre cada captura con el caso: `B3_factura_venta.png`.
3. Para errores inesperados, adjunte el archivo de registro `%LOCALAPPDATA%\ContaJB\logs\contabol.log`.

# Anexo C. Formato de reporte de incidencias

| Campo | Contenido |
|---|---|
| Código | INC-001 |
| Caso y paso | Ej. B6, paso 3 |
| Severidad | Crítica / Alta / Media / Baja |
| Resultado esperado | |
| Resultado obtenido | |
| Evidencia | captura + `contabol.log` |
| Versión | 2.1.0 (Acerca de CONTA JB) |
| Windows | versión y arquitectura |

# Anexo D. Normativa aplicada por el sistema

<!--NORMATIVA-->

> **Importante:** los porcentajes y montos reflejan la normativa conocida a octubre de 2026 y están **parametrizados con fecha de vigencia**. Debe verificarlos periódicamente en la Gaceta Oficial, el Servicio de Impuestos Nacionales y el Ministerio de Trabajo. En especial: el estado de la derogatoria del ITF, los tramos del Aporte Nacional Solidario y cualquier decreto que modifique el salario mínimo o los aportes.
