---
title: "ContaBol 2.0 — Manual de Implementación"
subtitle: "Instalación, configuración, puesta en marcha, operación y mantenimiento"
lang: es
---

# 1. Visión general

**ContaBol 2.0** es un sistema contable integrado para Bolivia (sector comercial y de costos), de escritorio para Windows. Está construido en **Python 3** con **PySide6 (Qt 6)** para la interfaz y **SQLite** como base de datos, elegidos por su estabilidad, su larga trayectoria y porque **no requieren instalar servidores ni motores adicionales**: el instalador incluye todo.

![Tablero de inicio](img/04_inicio.png){width=100%}

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
| **Estados financieros** | **Balance General, Estado de Resultados, Evolución del Patrimonio Neto, Flujo de Efectivo (método directo e indirecto) y Notas** |
| Informes | **65 informes** en pantalla, PDF y Excel |
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

## 3.1 Instalación con el instalador (recomendada)

1. Copie `ContaBol_Setup_2.0.0.exe` al equipo y ejecútelo como administrador.
2. Siga el asistente (carpeta por defecto `C:\Program Files\ContaBol`; marque el acceso directo del escritorio).
3. Abra ContaBol. La primera vez se crea la carpeta de datos del usuario:

```
%LOCALAPPDATA%\ContaBol\
    sistema.db          (usuarios, empresas, normativa, auditoría)
    datos\<EMPRESA>\<AÑO>.db   (contabilidad de cada gestión)
    backups\            (copias .cbk)
    reportes\           (PDF y Excel exportados)
    logs\contabol.log   (registro de errores)
```

Para usar **otra carpeta de datos** (otro disco o una ruta de red de un solo usuario), cree antes de abrir la aplicación la variable de entorno `CONTABOL_DATOS` con la ruta deseada.

## 3.2 Ejecutable portátil

La carpeta `dist\ContaBol\` generada por la compilación puede copiarse a un pendrive o a otro equipo y ejecutarse con `ContaBol.exe`, sin instalación.

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

El script crea un entorno virtual, instala dependencias, **ejecuta todas las pruebas**, genera `dist\ContaBol\ContaBol.exe` con PyInstaller y compila `dist\ContaBol_Setup_2.0.0.exe` con Inno Setup. Alternativamente, el flujo de GitHub Actions `.github/workflows/contabol-python.yml` hace lo mismo automáticamente en cada cambio y publica el instalador como artefacto o en *Releases* al crear una etiqueta `v2.0.0`.

## 3.5 Verificación posterior a la instalación

Ejecute `ContaBol.exe --autoprueba` desde una consola: debe imprimir **AUTOPRUEBA OK** (crea datos temporales, abre la ventana, genera el paquete de estados financieros en PDF y Excel y comprueba que el balance cuadra).

## 3.6 Actualización y desinstalación

Para **actualizar**, ejecute el nuevo instalador sobre el existente: conserva sus datos, que están fuera de la carpeta del programa. Haga antes una copia de seguridad. Al **desinstalar** desde *Configuración > Aplicaciones* los datos de `%LOCALAPPDATA%\ContaBol` **no se eliminan**.

# 4. Puesta en marcha de una empresa

## 4.1 Ingreso y seguridad inicial

Usuario inicial: `admin` / `admin`; el sistema obliga a cambiar la contraseña en el primer ingreso.

![Ingreso](img/01_login.png){width=50%}

## 4.2 Crear la empresa

En *Seleccionar empresa y gestión* pulse **Nueva empresa…** y complete código, razón social, NIT, dirección, ciudad, actividad, representante legal y el **año de la primera gestión**. Se crean el archivo de la gestión y el **plan de cuentas boliviano base** (más de 260 cuentas con estructura 1.1.1.01.001), los tipos de comprobante (Ingreso, Egreso, Traspaso, Apertura, Ajuste, Cierre), los grupos de activos del D.S. 24051, un almacén, unidades de medida y centros de costo.

![Selección de empresa y gestión](img/03_selector_empresa.png){width=80%}

> Para conocer el sistema sin riesgo use **Empresa de demostración** (empresa ficticia con la gestión 2025 completa).

## 4.3 Checklist de configuración

| Paso | Dónde | Qué hacer |
|---|---|---|
| 1 | *Administración > Parámetros > Empresa* | Revisar razón social, NIT, domicilio, representante legal |
| 2 | *Contabilidad > Tipos de cambio y UFV* | Cargar tipo de cambio del dólar y UFV (al menos al inicio y al cierre de la gestión) |
| 3 | *Administración > Parámetros > Cuentas* | Verificar las cuentas de caja, IVA, IT, clientes, proveedores, inventario, ventas, costo, sueldos y aportes |
| 4 | *Administración > Parámetros > Reglas* | IT sin factura, stock negativo, control de presupuesto, provisión de IUE, notas de contingencias y hechos posteriores |
| 5 | *Administración > Parámetros > Normativa* | Verificar SMN, aportes, ANS y demás parámetros legales vigentes |
| 6 | *Administración > Usuarios y permisos* | Crear usuarios con su rol y permisos |
| 7 | Saldos iniciales | Asiento de apertura (traspaso), stock inicial, clientes y proveedores, activos fijos, empleados |
| 8 | *Administración > Copias de seguridad* | Hacer una primera copia y definir la política de respaldo |

![Parámetros — cuentas de las operaciones automáticas](img/32_parametros_cuentas.png){width=100%}

## 4.4 Migración de saldos iniciales

- **Contabilidad:** un comprobante de *Traspaso* con los saldos al cierre anterior (o *Importar plan de cuentas* desde CSV `código;nombre` para cargar un plan propio).
- **Inventarios:** *Movimiento de inventario* tipo **Stock inicial** por almacén, con costo unitario, contabilizando contra la cuenta de capital o resultados acumulados.
- **Clientes y proveedores:** registre cada documento pendiente como nota de venta/compra a crédito con su fecha original, o utilice la apertura de una nueva gestión que los traslada automáticamente.
- **Activos fijos:** alta con fecha original y *depreciación acumulada previa*.
- **Empleados:** alta con fecha de ingreso real para el cálculo correcto del bono de antigüedad.

# 5. Usuarios, roles y permisos

| Rol | Alcance |
|---|---|
| **Administrador** | Todo, incluida la gestión de usuarios y la restauración |
| **Contador** | Todo menos usuarios y restaurar |
| **Operador** | Registro de comprobantes, facturas, ventas, compras, cobros, inventario y sus informes |
| **Consulta** | Solo informes |

Los permisos se asignan **por empresa** y se pueden personalizar opción por opción. Las contraseñas se guardan con **PBKDF2-HMAC-SHA256** (200.000 iteraciones y sal aleatoria); tras 5 intentos fallidos el usuario se bloquea hasta que el administrador restablezca su clave.

![Usuarios y permisos](img/34_usuarios.png){width=100%}

# 6. Normativa y parámetros legales

Los parámetros legales **no están escritos en el código**: se guardan en la tabla `normativa` con **fecha de vigencia** y fuente, y pueden consultarse y ampliarse en *Administración > Parámetros > Normativa vigente*. Cuando una norma cambia, se agrega un nuevo valor con su fecha de inicio: los períodos anteriores siguen calculándose con el valor que regía entonces.

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
- **Varios usuarios en turnos** o por escritorio remoto: instale ContaBol en un servidor Windows con *Escritorio remoto* y deje que cada usuario ingrese a su propia sesión sobre la misma carpeta de datos; las escrituras se serializan sin riesgo de corrupción.
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

- Restrinja con permisos de Windows la carpeta `%LOCALAPPDATA%\ContaBol` al usuario operador.
- Cambie la contraseña inicial, use contraseñas distintas por persona y active el bloqueo de pantalla.
- Cifre las copias de seguridad que salgan del local (BitLocker, 7-Zip con contraseña).
- Revise periódicamente *Auditoría del sistema*.
- Mantenga Windows y el antivirus actualizados.

![Auditoría](img/35_auditoria.png){width=100%}

# 13. Mantenimiento del código y pruebas

El proyecto incluye **pruebas automáticas** (`python -m pytest`) que cubren las reglas contables, tributarias y laborales, los seis estados financieros, los 65 informes y la construcción de todas las pantallas; el flujo de integración continua las ejecuta en cada cambio y construye el instalador. Para añadir un informe, defínalo con el decorador `@reporte(...)` en el módulo correspondiente de `contabol/reports/`; aparecerá automáticamente en el Centro de reportes con sus parámetros. Las capturas de los manuales se regeneran con `python tools/capturas.py`.

# 14. Limitaciones conocidas

- Aplicación de escritorio de **un equipo a la vez** por carpeta de datos (ver capítulo 9).
- Las normas tributarias y laborales cambian con frecuencia: los valores incluidos deben ser verificados por el contador de la empresa.
- La emisión de **facturas electrónicas** se realiza en los sistemas del SIN; ContaBol registra las facturas en los libros LCV y exporta su detalle, pero no las firma ni las transmite.
- El ajuste por inflación con UFV está disponible pero suspendido contablemente desde 2020; su uso es decisión de la empresa.
- El cálculo de finiquito es referencial.

# Anexo A. Formato de solicitud de soporte

| Campo | Contenido |
|---|---|
| Empresa / usuario | |
| Versión (Ayuda > Acerca de) | 2.0.0 |
| Pasos para reproducir | |
| Resultado obtenido / esperado | |
| Adjuntos | Captura, `contabol.log`, copia de seguridad si procede |
