---
title: "CONTA JB 2.3 — Manual de Implementación"
subtitle: "Instalación, configuración, puesta en marcha, operación y mantenimiento"
lang: es
---

# 1. Visión general

**CONTA JB 2.1** es un sistema contable integrado para Bolivia (sector comercial y de costos), de escritorio para Windows. Está construido en **Python 3** con **PySide6 (Qt 6)** para la interfaz y **SQLite** como base de datos, elegidos por su estabilidad, su larga trayectoria y porque **no requieren instalar servidores ni motores adicionales**: el instalador incluye todo.

![Tablero de inicio con el logotipo y la barra de accesos rápidos](img/04_inicio.png){width=100%}

## 1.1 Qué incluye

| Área | Contenido |
|---|---|
| Contabilidad | Plan de cuentas boliviano, comprobantes bimonetarios (Bs/US$), libros diario y mayor, sumas y saldos, hoja de trabajo, bancos y conciliación, centros de costo, presupuesto |
| Impuestos | Libros de compras y ventas (LCV), IVA 13 %, IT 3 %, liquidación mensual con saldo a favor y mantenimiento de valor (UFV), exportación LCV, provisión de IUE 25 % |
| Comercial | Clientes, proveedores, notas de venta y compra con asiento automático, cobros y pagos, antigüedad de saldos |
| Inventarios | Costo promedio ponderado, kardex físico valorado, FEFO por vencimiento, traspasos, ajustes |
| Activos fijos | Depreciación D.S. 24051 y actualización por UFV |
| Planillas | Sueldos, bono de antigüedad, AFP, CNS, Pro-Vivienda, aporte solidario, ANS, RC-IVA, aguinaldo, finiquito |
| Costos | Órdenes de producción (materia prima, mano de obra, CIF) |
| **Auditoría (v2.2)** | **Auditoría Financiera (MAF)** y **Tributaria (MAI)**: planificación, ejecución con cédulas sumarias, comunicación de resultados, dictámenes y cierre inmutable con SHA-256 |
| **Estados financieros** | **Balance General, Estado de Resultados, Evolución del Patrimonio Neto, Flujo de Efectivo (método directo e indirecto) y Notas** |
| Informes | **79 informes** en pantalla, PDF y Excel |
| Administración | Multiempresa, multigestión, usuarios y permisos, auditoría, copias de seguridad verificables, consolidación |

## 1.2 Arquitectura

| Capa | Tecnología | Función |
|---|---|---|
| Interfaz | PySide6 (Qt 6) | Ventanas, formularios, tablero |
| Servicios | Python | Reglas contables, tributarias y laborales (sin dependencia de la interfaz) |
| Informes | ReportLab y openpyxl | PDF y Excel desde una sola definición |
| Datos | SQLite (modo WAL, claves foráneas, `synchronous=FULL`) | Un archivo por empresa y gestión + sistema maestro |

![Estructura de los archivos de datos](img/estructura_datos.png){width=85%}

**Ventajas para la estabilidad:** transacciones atómicas (un comprobante se guarda completo o no se guarda), journal WAL que tolera cortes de energía, verificación de integridad al abrir cada gestión, copias de seguridad en caliente con huella SHA-256 y separación por empresa/gestión (un problema en un archivo no afecta a los demás). SQLite no tiene el límite de 2 GB de Access: el tamaño práctico es de decenas de GB.

# 2. Requisitos

| Elemento | Mínimo | Recomendado |
|---|---|---|
| Sistema operativo | Windows 10 (64 bits) | Windows 11 |
| Procesador / RAM | 2 núcleos / 4 GB | 4 núcleos / 8 GB |
| Disco | 500 MB + datos y respaldos | SSD, 5 GB libres |
| Pantalla | 1280 × 720 | 1366 × 768 o superior |
| Visor de PDF y Excel | Cualquiera | Adobe Reader / Excel |
| Python u otro software | **No se requiere** | — |

# 3. Instalación

![Flujo de implementación](img/flujo_implementacion.png){width=100%}

## 3.1 Instalación con el instalador (un solo clic)

1. Descargue **`ContaJB_Setup.exe`** de la página de *Releases* del repositorio (https://github.com/blancojaime/Factura/releases/tag/ultima-version).
2. Haga doble clic. Si Windows muestra «Windows protegió su PC» (el instalador no está firmado digitalmente), pulse *Más información* → *Ejecutar de todas formas*.
3. Pulse **Instalar**. El asistente es deliberadamente sencillo: **sin preguntas**, sin elegir carpetas ni componentes y **sin pedir permisos de administrador** (se instala solo para el usuario actual en `%LOCALAPPDATA%\Programs\ContaJB`). Crea el acceso directo **CONTA JB** en el escritorio y en el menú Inicio.
4. Pulse **Finalizar** para abrir CONTA JB. La primera vez se crea la carpeta de datos del usuario:

```
%LOCALAPPDATA%\ContaJB\
    sistema.db          (usuarios, empresas, normativa, auditoría)
    datos\<EMPRESA>\<AÑO>.db   (contabilidad de cada gestión)
    backups\            (copias .cbk)
    reportes\           (PDF y Excel exportados)
    logs\contabol.log   (registro de errores)
```

Para usar **otra carpeta de datos** (otro disco), cree antes de abrir la aplicación la variable de entorno `CONTABOL_DATOS` con la ruta deseada.

## 3.2 Ejecutable portátil

La carpeta `dist\ContaJB\` generada por la compilación puede copiarse a un pendrive o a otro equipo y ejecutarse con `ContaJB.exe`, sin instalación.

## 3.3 Ejecución desde el código fuente (equipos técnicos)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m contabol
```

También puede usar `scripts\ejecutar.bat`.

## 3.4 Cómo generar el instalador

En un equipo Windows con Python 3.10+ e Inno Setup 6:

```
scripts\compilar.bat
```

El script crea un entorno virtual, instala dependencias, **ejecuta todas las pruebas**, genera `dist\ContaJB\ContaJB.exe` con PyInstaller y compila `dist\ContaJB_Setup.exe` con Inno Setup. Alternativamente, el flujo de GitHub Actions `.github/workflows/contabol-python.yml` hace lo mismo automáticamente en cada cambio y publica el instalador como artefacto o en *Releases* al crear una etiqueta `v2.1.0`.

## 3.5 Verificación posterior a la instalación

Ejecute `ContaJB.exe --autoprueba` desde una consola: debe imprimir **AUTOPRUEBA OK** (crea datos temporales, abre la ventana, genera el paquete de estados financieros en PDF y Excel y comprueba que el balance cuadra).

## 3.6 Actualización y desinstalación

Para **actualizar**, ejecute el nuevo instalador sobre el existente: conserva sus datos, que están fuera de la carpeta del programa. Haga antes una copia de seguridad. Al **desinstalar** desde *Configuración > Aplicaciones* los datos de `%LOCALAPPDATA%\ContaJB` **no se eliminan**.

# 4. Puesta en marcha de una empresa

## 4.1 Ingreso y seguridad inicial

Usuario inicial: `admin` / `admin`; el sistema obliga a cambiar la contraseña en el primer ingreso.

![Ingreso con el logotipo de Jaime Blanco](img/01_login.png){width=50%}

## 4.2 Crear la empresa

Tras ingresar, en *Seleccionar empresa y gestión* pulse **Nueva empresa…** y complete código, razón social, NIT, dirección, ciudad, actividad, representante legal y el **año de la primera gestión**. Se crean el archivo de la gestión y el **plan de cuentas boliviano base** (más de 260 cuentas con estructura 1.1.1.01.001), los tipos de comprobante (Ingreso, Egreso, Traspaso, Apertura, Ajuste, Cierre), los grupos de activos del D.S. 24051, un almacén, unidades de medida y centros de costo.

![Selección de empresa y gestión](img/03_selector_empresa.png){width=80%}

> Para conocer el sistema sin riesgo use **Empresa de demostración** (empresa ficticia con la gestión 2025 completa).

## 4.3 Checklist de configuración

| Paso | Dónde | Qué hacer |
|---|---|---|
| 1 | *Administración > Datos de la empresa y parámetros* | Revisar razón social, NIT, domicilio, representante legal |
| 2 | *Contabilidad > Tipos de cambio y UFV* | Cargar tipo de cambio del dólar y UFV (al menos al inicio y al cierre de la gestión) |
| 3 | *Administración > Datos de la empresa y parámetros* | Revisar los **puntos clave** (IVA, IT, IUE, salario mínimo) y las cuentas importantes por grupo (impuestos, clientes/proveedores, ventas/inventario, sueldos y aportes, cierre) |
| 4 | Misma pantalla, sección *Reglas de operación* | IT sin factura, stock negativo, control de presupuesto, provisión de IUE, notas de contingencias y hechos posteriores |
| 5 | Pestaña *Normativa vigente (todas)* | Verificar SMN, aportes, ANS y demás parámetros legales vigentes |
| 6 | *Administración > Usuarios y permisos* | Crear usuarios con su rol y permisos |
| 7 | Saldos iniciales | Asiento de apertura (traspaso), stock inicial, clientes y proveedores, activos fijos, empleados |
| 8 | *Administración > Copias de seguridad* | Hacer una primera copia y definir la política de respaldo |

![Datos de la empresa: puntos clave resaltados y cuentas por grupo](img/31_datos_empresa.png){width=100%}

## 4.4 Migración de saldos iniciales

- **Contabilidad:** un comprobante de *Traspaso* con los saldos al cierre anterior (o *Importar plan de cuentas* desde CSV `código;nombre` para cargar un plan propio).
- **Inventarios:** *Movimiento de inventario* tipo **Stock inicial** por almacén, con costo unitario, contabilizando contra la cuenta de capital o resultados acumulados.
- **Clientes y proveedores:** registre cada documento pendiente como nota de venta/compra a crédito con su fecha original, o utilice la apertura de una nueva gestión que los traslada automáticamente.
- **Activos fijos:** alta con fecha original y *depreciación acumulada previa*.
- **Empleados:** alta con fecha de ingreso real para el cálculo correcto del bono de antigüedad.

# 4 bis. Registro de comprobantes y libros de compras y ventas

El **comprobante contable** es la fuente de los estados financieros. El formulario de registro (versión 2.1) tiene la cabecera ordenada —tipo, **número automático**, fecha, mes, moneda, **T.C.**, **UFV**, **banco**, **Nº de cheque o depósito**, glosa, «cancelado a / recibido de» y Nº de documento—, botones de **Calculadora** y **Plan de cuentas**, y una grilla donde **cada celda es un campo editable** (sin botones para agregar o quitar filas: se llena la última y aparece otra).

![Registro de comprobantes](img/40_comprobante_nuevo.png){width=100%}

**Relación con los libros de compras y ventas.** Al grabar un **Egreso** o un **Ingreso** el sistema pregunta **«¿Existe factura?»**. Si la respuesta es *Sí*, se piden los datos de la factura (o del DUI en importaciones), se calcula el crédito/débito fiscal del 13 %, se agrega al asiento la línea de IVA (si no la tenía) y la factura se registra en el **Libro de Compras** (egresos) o en el **Libro de Ventas** (ingresos), **vinculada** al comprobante. Si el comprobante se anula, su factura se anula también. Las ventas y compras registradas desde sus propias notas ya generan su libro automáticamente.

![Pregunta «¿Existe factura?»](img/40b_comprobante_existe_factura.png){width=70%}

La **UFV** escrita en el comprobante se guarda para esa fecha (5 decimales) y se usa en liquidaciones, activos fijos y ajustes.

# 4 ter. Módulos de Auditoría Financiera (MAF) y Tributaria (MAI)

## Marco y alcance

- **Marco técnico:** Normas de Auditoría Generalmente Aceptadas y Normas Internacionales de Auditoría (NIA) — en particular NIA 300/315/320/330/500/530/700/705/706 —; Normas de Contabilidad del CTNAC (NC 1 a 14); Código de Comercio.
- **Marco tributario:** Ley 843 (IVA, IT, IUE, RC-IVA), D.S. 21530, 21531, 21532 y 24051, Ley 2492 (Código Tributario), normas del SIN sobre facturación, medios fehacientes de pago (bancarización) e Información Tributaria Complementaria.
- **Lo que hace el sistema:** organiza el encargo en las etapas **A Planificación**, **B Ejecución** y **C Comunicación**, conecta las pruebas con los saldos y módulos de CONTA JB y deja evidencia inmutable.
- **Lo que no hace:** no emite opinión por sí solo, no presenta información al SIN y no reemplaza el criterio del profesional. **Verifique** con el CAUB/CTNAC la adopción vigente de las NIA en Bolivia y con el SIN el modelo oficial de dictamen, los anexos ITC y los umbrales de obligatoriedad; los valores dependientes de norma son parámetros editables (*Administración > Parámetros y normativa*): `BANCARIZACION_MONTO`, `IUE_DONACION_PCT`, `IUE_PCT_AUD`, `AUD_TASA_INTERES_ANUAL`, `AUD_UMBRAL_EXTERNA`.

## Modelo de datos (esquema relacional)

Cada gestión (archivo `datos/<EMPRESA>/<AÑO>.db`) incluye las tablas de auditoría; se crean con la gestión y se agregan automáticamente al abrir gestiones de versiones anteriores (migración `VERSION_ESQUEMA = 3`).

| Tabla | Contenido y claves |
|---|---|
| `auditoria_encargo` | PK `id`; tipo F/T, código, período, estado ABIERTO/CERRADO, `sha256`, usuario y fecha de cierre |
| `auditoria_equipo` | FK `encargo_id`; nombre, rol, iniciales (para firmas de preparación y revisión) |
| `auditoria_memorando`, `auditoria_materialidad`, `auditoria_riesgo` | FK `encargo_id`; términos, riesgo inherente/control/aceptable/detección; materialidad global, de desempeño y trivial; riesgos por componente × aseveración |
| `auditoria_programa`, `auditoria_programa_paso` | Programas por componente y sus procedimientos (estado, referencia, conclusión) |
| `cedula_sumaria` | FK `encargo_id`; índice (A, B… / AA, BB…), cuentas, `saldo_sistema`, ajustes, reclasificaciones, `saldo_auditado`, preparado/revisado |
| `cedula_analitica` | FK `sumaria_id`; cuenta, `saldo_libros`, `saldo_verificado`, diferencia, marcas |
| `marca_auditoria` | Leyenda de marcas del encargo |
| `hallazgo_auditoria` | Condición, criterio, causa, efecto, recomendación, descargo de la Gerencia, nivel, impacto en Bs |
| `asiento_ajuste_propuesto` + `asiento_ajuste_det` | Ajustes (AJU) y reclasificaciones (REC) con estado PROPUESTO / ACEPTADO / NO_CORREGIDO; el detalle debe cuadrar |
| `gasto_no_deducible_iue` | Depuración del IUE: SUGERIDO / CONFIRMADO / DESCARTADO, motivo y base legal |
| `anexo_tributario_itc` | Anexos ITC generados (contenido JSON) |
| `auditoria_prueba` | Resultado de cada prueba sustantiva (parámetros, resultado, conforme) |
| `auditoria_dictamen` | Dictámenes e informes emitidos |
| `auditoria_trail` | Bitácora **encadenada**: `hash = SHA-256(hash_prev + usuario + fecha + acción…)`; solo se agrega |

## Inmutabilidad y trazabilidad

- Al **cerrar y firmar** (contraseña del usuario), disparadores (*triggers*) de la base de datos impiden `INSERT`, `UPDATE` y `DELETE` sobre todas las tablas del encargo y sus detalles; la bitácora no admite modificaciones ni borrados nunca.
- La huella **SHA-256** se calcula sobre una representación canónica (JSON ordenado) de todos los papeles de trabajo; *Verificar integridad* la recalcula y detecta cualquier alteración posterior, incluso hecha directamente en el archivo `.db`.
- Las copias de seguridad incluyen las tablas de auditoría.

## Lógica de negocio (resumen)

| Elemento | Regla |
|---|---|
| Riesgo | RA = RI × RC × RD ⇒ RD = RA / (RI × RC); factores Bajo 0,4 · Medio 0,7 · Alto 1,0 |
| Materialidad | Global = % de la base elegida (Activo total 1 %, Ingresos 0,5 %, Utilidad bruta 2 %, Patrimonio 2 %, Utilidad antes de impuestos 5 %; editables); desempeño 75 %; trivial 5 % de la global |
| Cédulas sumarias | Se alimentan de los saldos del sistema a la fecha de cierre del período; los ajustes ACEPTADOS recalculan el saldo auditado |
| Opinión sugerida | Desvíos no corregidos no triviales ≥ 3× materialidad ⇒ adversa; ≥ 1× ⇒ con salvedad; limitación de alcance de nivel alto ⇒ abstención; si no, limpia. Es una **sugerencia**; el auditor decide |
| Inventarios | Muestreo (mayor valor al 100 % + aleatorio con semilla), corte documental, VNR (menor entre costo y valor neto de realización), obsolescencia (sin salidas / lotes vencidos), kardex vs. contabilidad |
| Costos | MP, MOD, CIF por orden, cuota de aplicación del CIF sobre MOD y conciliación con cuentas 5.2.1.01 |
| Activos fijos | Recalcula la depreciación con los coeficientes del D.S. 24051 y cuantifica el exceso no deducible; el ajuste por UFV es contable solo si el parámetro está activo (suspendido desde 2020 por CTNAC 03/2020) |
| Planilla | Conciliación con aportes patronales, aguinaldo (provisión) y RC-IVA retenido (Formulario 110) |
| IVA / IT | Débito fiscal y crédito fiscal del libro vs. contabilidad por mes; IT = tasa × ventas del libro |
| Bancarización | Operaciones ≥ umbral deben tener pago con medio fehaciente (cheque, transferencia, depósito); las pagadas en efectivo o sin evidencia quedan «sin respaldo» (riesgo para crédito fiscal y deducibilidad) |
| IUE | Utilidad contable + gastos no deducibles confirmados = utilidad imponible × alícuota |
| Contingencias | Tributo omitido actualizado por UFV + intereses (tasa ingresada por el usuario, base 360) + sanción (ingresada) |

## Roles

El rol **Auditor** (nuevo) accede a los módulos de auditoría y a los informes; no registra comprobantes. **Administrador** y **Contador** también tienen acceso. El rol **Consulta** no accede a auditoría.

## API local de solo lectura (opcional)

```
python -m contabol.api --empresa DEMO --anio 2025
```

Escucha solo en `127.0.0.1`, exige token y no modifica datos. Rutas (prefijo `/api/v1`): `/auditoria/encargos`, `/auditoria/materialidad`, `/auditoria/resumen-desvios`, `/auditoria/integridad`, `/inventarios/muestreo-recuento`, `/inventarios/corte-documental`, `/inventarios/vnr-obsolescencia`, `/costos/conversion`, `/activos/depreciacion-vs-ds24051`, `/planillas/conciliacion`, `/tributario/conciliacion-iva-it`, `/tributario/bancarizacion`, `/tributario/depuracion-iue`, `/tributario/anexos-itc`, `/tributario/contingencia`.

# 4 quater. Control de comprobantes, envío a Word y activación (versión 2.3)

## Control de comprobantes

El menú *Contabilidad > Comprobantes (control)* (F2) y el botón *Comprobante* de la barra abren una tabla con **todos** los comprobantes: número, fecha, tipo, origen, beneficiario, Nº de documento, glosa, totales, estado y usuario. Al seleccionar uno se ven su T.C., UFV, banco y cheque, factura vinculada y líneas del asiento. Acciones: **Nuevo, Copiar, Eliminar, Revertir, Anular, Ver/Modificar, Imprimir, Enviar a Excel y a Word**. Reglas:

- **Eliminar** solo el último comprobante del tipo y mes (conserva la numeración correlativa), sin conciliación bancaria ni reversión. Requiere el permiso *Anular comprobantes*.
- **Revertir** genera un comprobante de traspaso (origen *Reversión*) con debe y haber invertidos; no se repite ni se revierte una reversión.
- **Anular** marca el comprobante y su factura vinculada; el comprobante queda visible en rojo.
- Toda acción queda en la auditoría del sistema.

## Envío a Word

Módulo `contabol/reports/word.py` (dependencia `python-docx`). Todo informe del catálogo se puede exportar a **.docx** desde el visor (botón *Word*) y el texto editado de los dictámenes desde la pantalla de auditoría. Para el empaquetado, el archivo `.spec` incluye los datos de `docx`; la autoprueba del instalador genera un Word de prueba.

## Activación de la licencia

CONTA JB funciona **30 días en modo de prueba**; después exige un **código de activación** emitido por el proveedor. Detalle de uso en el **Manual de Activación**. Aspectos de implementación:

| Tema | Detalle |
|---|---|
| Código de solicitud | `JB-` + 20 caracteres derivados de un hash del identificador del equipo (MachineGuid de Windows) |
| Código de activación | Firma **Ed25519** del código de solicitud y de la fecha de vencimiento (o perpetua). Funciona sin Internet |
| Dónde se guarda | Tabla `config` de `sistema.db` (`lic_codigo`, `lic_inicio`, `lic_ultimo_uso`); sobrevive a reinstalaciones y actualizaciones |
| Clave pública | Dentro del programa (`contabol/licencia.py`); solo verifica |
| **Clave privada** | Archivo `clave_privada_contajb.pem`, **solo en poder del proveedor**; nunca en el repositorio, instalador ni equipos de clientes |
| Emisión | *Ayuda > Emitir código de activación (proveedor)…* (solo administradores) |
| Datos al vencer | **No se bloquean ni se borran**: solo se pide activar para ingresar |
| Reloj | Si la fecha de Windows retrocede respecto del último uso, se pide corregirla |
| Instalaciones previas | Al actualizar desde una versión sin activación, comienza el período de prueba de 30 días |

# 5. Usuarios, roles y permisos

**Recuperación del administrador.** Si otro administrador puede ingresar, restablezca la clave en *Administración > Usuarios y permisos* (también desbloquea). Si no, use cualquiera de estas tres vías (en el equipo donde está instalado): (a) en la pantalla de ingreso, el botón **«Restablecer administrador»**; (b) *Inicio > CONTA JB > Restablecer contraseña de administrador*; (c) el archivo **`Restablecer_admin.bat`** de la página de descargas (o `ContaJB.exe --restablecer-admin`). En todas, escriba **RESTABLECER**: el usuario `admin` queda activo y desbloqueado con la clave temporal `admin` y cambio obligatorio. La acción queda en la bitácora de seguridad.

| Rol | Alcance |
|---|---|
| **Administrador** | Todo, incluida la gestión de usuarios y la restauración |
| **Contador** | Todo menos usuarios y restaurar |
| **Operador** | Registro de comprobantes, facturas, ventas, compras, cobros, inventario y sus informes |
| **Consulta** | Solo informes |

Los permisos se asignan **por empresa** y se pueden personalizar opción por opción. Las contraseñas se guardan con **PBKDF2-HMAC-SHA256** (200.000 iteraciones y sal aleatoria); tras 5 intentos fallidos el usuario se bloquea hasta que el administrador restablezca su clave.

![Usuarios y permisos](img/34_usuarios.png){width=100%}

# 6. Normativa y parámetros legales

Los parámetros legales **no están escritos en el código**: se guardan en la tabla `normativa` con **fecha de vigencia** y fuente, y pueden consultarse y ampliarse en *Administración > Datos de la empresa y parámetros > Normativa vigente*. Cuando una norma cambia, se agrega un nuevo valor con su fecha de inicio: los períodos anteriores siguen calculándose con el valor que regía entonces.

![Normativa vigente](img/33_parametros_normativa.png){width=100%}

<!--NORMATIVA-->

> **Responsabilidad:** el equipo contable de la empresa debe verificar estos valores en la Gaceta Oficial de Bolivia, el SIN y el MTEPS antes de cada cierre. Entre los puntos a vigilar: salario mínimo nacional, tasas del aporte solidario, tramos del Aporte Nacional Solidario, estado del ITF, aplicabilidad del aporte INFOCAL y la eventual reactivación del ajuste por inflación.

# 7. Operación diaria y cierre

| Frecuencia | Actividad |
|---|---|
| Diaria | Registro de comprobantes, facturas, ventas, compras, cobros y pagos; **copia de seguridad** al terminar |
| Mensual | Liquidación de IVA e IT, depreciación de activos, planilla de sueldos y su pago, conciliación bancaria, libros de compras y ventas |
| Anual | Diferencia de cambio, (ajuste por inflación si corresponde), asiento de cierre, **estados financieros**, cierre de gestión, apertura de la siguiente, aguinaldo |

Ciclo de cierre: registrar todo → diferencia de cambio → asiento de cierre → emitir estados financieros → **cerrar gestión** (solo lectura) → **abrir nueva gestión**.

![Ajustes y cierre de gestión](img/29_cierre_gestion.png){width=100%}

# 8. Copias de seguridad y recuperación

| Acción | Detalle |
|---|---|
| Respaldo manual | *Administración > Copias de seguridad*: de la empresa o de todo el sistema (archivo `.cbk` con huella SHA-256) |
| Respaldo automático | Al cerrar la aplicación, de todo el sistema (se conservan los 15 más recientes) |
| Verificación | *Verificar un respaldo…* comprueba la huella de cada archivo sin restaurar |
| Restauración | Solo administrador; crea antes una copia «PRE-RESTAURACION» de lo actual |

**Política recomendada:** copia diaria a otra unidad, semanal fuera del local (nube o disco externo cifrado), mensual archivada y gestión cerrada archivada de forma permanente. Pruebe una restauración al menos una vez por trimestre.

![Copias de seguridad](img/36_backup.png){width=100%}

# 9. Uso en red y concurrencia

SQLite está diseñado para **un escritor a la vez**. Recomendaciones:

- **Un solo equipo** (recomendado): la carpeta de datos local; es la configuración más rápida y segura.
- **Varios usuarios en turnos** o por escritorio remoto: instale CONTA JB en un servidor Windows con *Escritorio remoto* y deje que cada usuario ingrese a su propia sesión sobre la misma carpeta de datos; las escrituras se serializan sin riesgo de corrupción.
- **No** coloque la carpeta de datos en una unidad de red compartida para acceso simultáneo desde varias PC: el bloqueo de archivos en red puede fallar y dañar la base de datos.

La estructura por servicios permite sustituir en el futuro la capa de datos por un servidor (por ejemplo PostgreSQL) sin reescribir las reglas contables.

# 10. Rendimiento y límites

| Concepto | Valor práctico |
|---|---|
| Tamaño por archivo de gestión | Decenas de GB (límite teórico de SQLite: 281 TB) |
| Comprobantes por gestión | Cientos de miles sin pérdida notable de velocidad |
| Estados financieros | Se calculan en memoria desde saldos agregados (segundos) |

*Contabilidad > Utilitarios y verificación > Compactar base de datos* ejecuta VACUUM y reduce el archivo.

![Utilitarios y verificación](img/37_utilitarios.png){width=100%}

# 11. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| «No se pudo abrir la base de datos del sistema» | Carpeta sin permisos o disco lleno | Elegir otra carpeta con `CONTABOL_DATOS`; liberar espacio |
| «El archivo de datos presenta errores de integridad» | Apagado durante escritura en disco defectuoso | Restaurar la última copia (*Copias de seguridad*) |
| «La gestión … está cerrada» | Gestión cerrada | Abrir la gestión vigente o, el administrador, *Reabrir gestión* |
| Falta configurar la cuenta «CTA_…» | Parámetro apunta a una cuenta inexistente | *Parámetros > Cuentas* |
| PDF no se abre | Sin visor de PDF | Instalar un visor; el archivo queda en `reportes\` |
| Importes de planilla distintos a los esperados | Normativa desactualizada | *Parámetros > Normativa*; verificar SMN y tasas |
| Error inesperado | Defecto del programa | Enviar `logs\contabol.log` y captura al soporte |

# 12. Seguridad de la información

- Restrinja con permisos de Windows la carpeta `%LOCALAPPDATA%\ContaJB` al usuario operador.
- Cambie la contraseña inicial, use contraseñas distintas por persona y active el bloqueo de pantalla.
- Cifre las copias de seguridad que salgan del local (BitLocker, 7-Zip con contraseña).
- Revise periódicamente *Auditoría del sistema*.
- Mantenga Windows y el antivirus actualizados.

![Auditoría](img/35_auditoria.png){width=100%}

# 13. Mantenimiento del código y pruebas

El proyecto incluye **pruebas automáticas** (`python -m pytest`) que cubren las reglas contables, tributarias y laborales, los seis estados financieros, los 79 informes y la construcción de todas las pantallas; el flujo de integración continua las ejecuta en cada cambio y construye el instalador. Para añadir un informe, defínalo con el decorador `@reporte(...)` en el módulo correspondiente de `contabol/reports/`; aparecerá automáticamente en el Centro de reportes con sus parámetros. Las capturas de los manuales se regeneran con `python tools/capturas.py`.

# 14. Limitaciones conocidas

- Aplicación de escritorio de **un equipo a la vez** por carpeta de datos (ver capítulo 9).
- Las normas tributarias y laborales cambian con frecuencia: los valores incluidos deben ser verificados por el contador de la empresa.
- La emisión de **facturas electrónicas** se realiza en los sistemas del SIN; CONTA JB registra las facturas en los libros LCV y exporta su detalle, pero no las firma ni las transmite.
- El ajuste por inflación con UFV está disponible pero suspendido contablemente desde 2020; su uso es decisión de la empresa.
- El cálculo de finiquito es referencial.
- **Activación:** si el proveedor pierde la clave privada no podrá emitir códigos para las instalaciones existentes (habría que publicar una versión con otra clave pública). Conserve copias seguras.
- **Auditoría:** las pruebas y los borradores de dictamen son apoyo al juicio profesional; los anexos ITC son formatos referenciales; los umbrales y tasas dependientes de norma deben verificarse y, cuando corresponda, ingresarse por el usuario.

# Anexo A. Formato de solicitud de soporte

| Campo | Contenido |
|---|---|
| Empresa / usuario | |
| Versión (Ayuda > Acerca de) | 2.1.0 |
| Pasos para reproducir | |
| Resultado obtenido / esperado | |
| Adjuntos | Captura, `contabol.log`, copia de seguridad si procede |
