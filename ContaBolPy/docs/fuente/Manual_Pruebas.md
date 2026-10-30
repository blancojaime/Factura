---
title: "ContaBol 2.0 — Manual de Pruebas de Aceptación"
subtitle: "Guía paso a paso con datos de ejemplo, resultados esperados y capturas reales del aplicativo"
lang: es
---

# 1. Introducción

## 1.1 Objetivo

Este manual permite a un **contador, auditor o responsable de TI** comprobar, de forma ordenada y repetible, que ContaBol:

1. se instala y arranca correctamente en Windows;
2. registra las operaciones contables, tributarias, comerciales, de inventario, activos fijos, planillas y costos aplicando la **normativa boliviana vigente** (IVA 13 %, IT 3 %, IUE 25 %, RC-IVA, AFP, CNS, Pro-Vivienda, ANS, bono de antigüedad, aguinaldo e indemnización);
3. emite correctamente los **seis estados financieros** (Balance General, Estado de Resultados, Estado de Evolución del Patrimonio Neto, Flujo de Efectivo por método directo, Flujo de Efectivo por método indirecto y Notas a los Estados Financieros);
4. genera los **65 informes** del sistema en pantalla, **PDF** y **Excel**;
5. protege la información (usuarios, permisos, auditoría, copias de seguridad verificables).

## 1.2 Cómo están hechas las imágenes

Todas las imágenes de este manual son **capturas reales** del aplicativo, generadas automáticamente por la herramienta `tools/capturas.py` con la **empresa de demostración** (Distribuidora Andina S.R.L., gestión 2025). No son dibujos ni maquetas. Su pantalla puede diferir mínimamente en tipografía según su versión de Windows, pero la disposición y las cifras deben coincidir.

## 1.3 Qué ya está verificado automáticamente

Antes de entregar cada versión se ejecutan pruebas automáticas (paquete `tests/`) que cubren: partida doble, bimonetario, IVA/IT, inventario con costo promedio y FEFO, cobros y pagos, activos fijos, planillas con normativa vigente, producción, estados financieros, cierre y apertura de gestión, copias de seguridad, multiempresa, los 65 informes en PDF y Excel, y la construcción de **todas las pantallas** de la interfaz. Las cifras de la **Parte B** de este manual están además comprobadas por la prueba `tests/test_manual.py`: si el cálculo del sistema cambiara, esa prueba fallaría y el manual debería actualizarse.

Aun así, la aceptación en el equipo del cliente es necesaria: depende de su versión de Windows, impresoras, visor de PDF y de sus propios datos.

## 1.4 Roles y materiales

| Rol | Responsabilidad |
|---|---|
| Probador | Ejecuta los casos, registra resultado y evidencia |
| Contador validador | Confirma que los asientos, impuestos y estados son correctos |
| Responsable técnico | Analiza y corrige las incidencias |

**Materiales:** equipo con Windows 10/11 (64 bits); instalador `ContaBol_Setup_2.0.0.exe`; este manual; Excel o visor de hojas de cálculo; visor de PDF; unas 3 horas para la prueba completa (1 hora para la prueba rápida de la Parte A y B).

## 1.5 Criterios de aceptación

| Resultado | Significado |
|---|---|
| **✔ Aprobado** | El resultado coincide con lo esperado |
| **✘ Fallido** | Difiere; registre caso, paso, captura completa y hora |
| **⛔ Bloqueado** | No se pudo ejecutar por una falla previa |

La versión se **aprueba** si todos los casos marcados ★ (críticos) están ✔, no hay diferencias de cálculo y los seis estados financieros cuadran.

**Severidad de incidencias:** *Crítica* (pérdida de datos o cálculo contable/tributario incorrecto) · *Alta* (función principal inutilizable) · *Media* (afecta la comodidad, hay alternativa) · *Baja* (estética u ortografía).

# 2. Parte A — Preparación del entorno

## A1 ★ Instalación

**Objetivo:** instalar ContaBol.

**Pasos**

1. Haga doble clic en `ContaBol_Setup_2.0.0.exe` y acepte el permiso de administrador.
2. Elija la carpeta (por defecto `C:\Program Files\ContaBol`) y marque *Crear un acceso directo en el escritorio*.
3. Al finalizar deje marcada *Ejecutar ContaBol*.

**Resultado esperado:** el asistente termina sin errores, aparece el acceso directo y se abre la pantalla de ingreso. No se requiere instalar ni Python ni Access ni ningún otro programa: el instalador incluye todo lo necesario.

**Si falla:** anote el mensaje del instalador y la versión de Windows.

## A2 ★ Primer ingreso y cambio de contraseña

**Pasos**

1. En la pantalla de ingreso escriba usuario `admin` y contraseña `admin`; pulse **Ingresar**.
2. El sistema exige elegir una nueva contraseña (mínimo 6 caracteres; no se aceptan claves triviales como «admin» o «123456»). Escríbala dos veces y pulse **Guardar**.

![Pantalla de ingreso](img/01_login.png){width=55%}

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

**Resultado esperado:** los registros aparecen ordenados por fecha. El tipo de cambio rige desde su fecha hasta que se cargue otro.

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

## B1 ★ Comprobante contable de traspaso (partida doble)

**Objetivo:** registrar un asiento y comprobar numeración y saldos.

**Pasos**

1. *Contabilidad > Nuevo comprobante* (o **Ctrl + N** o el botón «Comprobante» de la barra).
2. Tipo **Traspaso**, fecha 02/01/2026, glosa «Aporte inicial».
3. En la primera línea escriba en *Cuenta* «1.1.1.01.001» (o parte del nombre: «caja»): el sistema sugiere cuentas mientras escribe; seleccione *Caja Moneda Nacional*. En *Debe* escriba **50.000** y pulse Enter.
4. En la segunda línea escriba la cuenta «3.1.1.01.001» *Capital Social* y en *Haber* **50.000**.
5. Observe el indicador inferior: **✔ Cuadra**. Pulse **Guardar comprobante**.

![Comprobante con ayuda de cuentas, totales en tiempo real e indicador de cuadre](img/40_comprobante_nuevo.png){width=95%}

**Resultado esperado:** el comprobante recibe el número **T-01/0001**; en *Contabilidad > Comprobantes* aparece vigente y el saldo de *Caja Moneda Nacional* es **Bs 50.000,00**.

**Pruebas negativas (deben rechazarse con un mensaje claro y sin guardar nada):**

| Intento | Mensaje esperado |
|---|---|
| Debe 100 / Haber 90 | «El comprobante no cuadra: Debe 100,00 / Haber 90,00» |
| Glosa vacía | «La glosa del comprobante es obligatoria.» |
| Fecha 31/12/2025 (gestión 2026) | «La fecha … está fuera de la gestión» |
| Cuenta de grupo (p. ej. 1.1.1.01) | «… no es de movimiento» |
| Importe negativo | «no se permiten importes negativos» |
| Línea con debe y haber a la vez | «no puede tener importe en el debe y en el haber» |

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
| C1 | Plan de cuentas (Contabilidad) | Árbol de 264 cuentas con saldos, buscar «caja», crear subcuenta, importar/exportar CSV | Fig. C1 |
| C2 | Comprobantes | Más de 400 comprobantes, filtro por fechas y tipo, anular, imprimir | Fig. C2 |
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

![C1. Plan de cuentas](img/07_plan_cuentas.png){width=100%}

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

# 6. Parte E — Informes (los 65 del sistema)

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

## F6 Parámetros y normativa

![Parámetros — datos de la empresa](img/31_parametros_empresa.png){width=100%}

![Parámetros — cuentas de las operaciones automáticas](img/32_parametros_cuentas.png){width=100%}

![Normativa laboral e impositiva vigente, con vigencia por fechas](img/33_parametros_normativa.png){width=100%}

En *Normativa vigente* están todos los parámetros legales (SMN, aportes, ANS, RC-IVA, escalas de antigüedad y vacaciones, recargos, IVA, IT, IUE) con su fecha de vigencia y fuente. **Prueba:** agregue un nuevo valor de *SMN* con vigencia desde el 01/07/2026 y recalcule una planilla de agosto: debe usar el nuevo valor, mientras que una planilla de enero conserva el anterior.

## F7 Utilitarios y verificación

*Contabilidad > Utilitarios y verificación*: muestra **[OK]/[AVISO]/[ERROR]** de comprobantes cuadrados, totales de cabecera vs. detalle, balance que cuadra, flujo de efectivo conciliado, cuentas parametrizadas, tipo de cambio y UFV cargados, stock negativo, inventario valorado vs. cuenta contable e integridad de la base de datos.

![Utilitarios y verificación](img/37_utilitarios.png){width=100%}

![Acerca de ContaBol](img/49_acerca_de.png){width=60%}

# 8. Parte G — Pruebas automáticas y verificación del instalador

## G1 Ejecutar las pruebas automáticas (equipo técnico)

Desde la carpeta del código fuente:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python -m pytest
```

**Esperado:** todas las pruebas en verde (más de 45), incluyendo `test_manual.py` (cifras de este manual), `test_estados.py` (los seis estados), `test_reportes.py` (65 informes en PDF y Excel) y `test_ui.py` (todas las pantallas).

## G2 Autoprueba del programa instalado

Desde una consola, en la carpeta de instalación:

```
ContaBol.exe --autoprueba
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
3. Para errores inesperados, adjunte el archivo de registro `%LOCALAPPDATA%\ContaBol\logs\contabol.log`.

# Anexo C. Formato de reporte de incidencias

| Campo | Contenido |
|---|---|
| Código | INC-001 |
| Caso y paso | Ej. B6, paso 3 |
| Severidad | Crítica / Alta / Media / Baja |
| Resultado esperado | |
| Resultado obtenido | |
| Evidencia | captura + `contabol.log` |
| Versión | 2.0.0 (Acerca de ContaBol) |
| Windows | versión y arquitectura |

# Anexo D. Normativa aplicada por el sistema

<!--NORMATIVA-->

> **Importante:** los porcentajes y montos reflejan la normativa conocida a octubre de 2026 y están **parametrizados con fecha de vigencia**. Debe verificarlos periódicamente en la Gaceta Oficial, el Servicio de Impuestos Nacionales y el Ministerio de Trabajo. En especial: el estado de la derogatoria del ITF, los tramos del Aporte Nacional Solidario y cualquier decreto que modifique el salario mínimo o los aportes.
