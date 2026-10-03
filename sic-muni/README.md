# SIC-MUNI — Sistema Integrado de Contrataciones Municipales (VBA / Excel)

Solución de escritorio en un único libro `.xlsm` para contratación menor en un GAM de Bolivia:
solicitud y cotización → validación Compro Hecho en Bolivia (CHB) y excepciones → reserva
presupuestaria (C-31 preventivo) → Orden de Compra/Servicio, con documentos PDF.

> **Estado:** el código fue escrito y revisado estáticamente, **no se pudo ejecutar** (no hay Excel en el
> entorno de desarrollo). Haga una prueba integral con los datos demo antes de usarlo en producción.

## Contenido

| Archivo (`vba/`) | Qué es |
| :-- | :-- |
| `modCore.bas` | Acceso a hojas por nombre de columna, CONFIG, correlativos, auditoría, protección |
| `modSecurity.bas` | SHA-256 con sal + 1000 iteraciones, login/bloqueo/timeout, matriz RBAC, ABM de usuarios |
| `modValidationCHB.bas` | Consulta de catálogo CHB, validación de excepción, puerta de bloqueo a la Orden |
| `modProcurement.bas` | Módulo 1: modalidad por monto, solicitud/ítems, cotizaciones, cuadro comparativo, adjudicación, monto en literal |
| `modBudgetEngine.bas` | Módulo 3: saldos, emisión de C-31 (todo-o-nada), asociación SIGEP, reversión parcial/total, Orden |
| `modDocumentAutomation.bas` | Volcado a plantillas `Doc_*` y exportación a PDF |
| `modSetup.bas` / `modSetupTemplates.bas` | Instalación: tablas, CONFIG, administrador, datos demo, 5 plantillas con rangos con nombre y fórmulas |
| `modUIBuilder.bas` | Crea `frmLogin` y `frmContratacionesConsolidado` por código e inyecta su código |
| `modMain.bas` | Punto de entrada y macros de administración |
| `frmLogin.code.txt`, `frmContratacionesConsolidado.code.txt`, `ThisWorkbook.code.txt` | Código de eventos |

Detalle de tablas, estados, plantillas, rangos con nombre y fórmulas: [`docs/ARQUITECTURA_Y_PLANTILLAS.md`](docs/ARQUITECTURA_Y_PLANTILLAS.md).

## Instalación

1. Excel (Windows, con **.NET Framework 3.5** habilitado para el hash) → libro nuevo → guardar como `SIC-MUNI.xlsm`.
2. Copiar la carpeta `vba/` junto al `.xlsm`. Habilitar *Confiar en el acceso al modelo de objetos de proyectos de VBA*.
3. En el editor VBA (Alt+F11): *Archivo → Importar archivo…* y cargar los 9 `.bas`. Pegar `ThisWorkbook.code.txt` en `ThisWorkbook`.
4. Ejecutar `InstalarSistema` (pide usuario y contraseña del administrador; no hay contraseña por defecto), luego opcionalmente `CargarDatosDemo`, luego `ConstruirFormularios`.
5. Completar `CONFIG` (Entidad, DA, UE, Gestión), cargar `CAT_CHB` y `PRESUPUESTO` reales (vía `AdminMantenimiento`), **cambiar `PROT_PWD` en `modCore`** y proteger el proyecto VBA con contraseña.
6. Guardar y reabrir: `Workbook_Open` oculta/protege las hojas y abre el login.

## Flujo y roles

`US` crea solicitud e ítems → `RC` evalúa CHB, registra cotizaciones, evalúa el cuadro → `PF` emite C-31 preventivo
(y lo asocia al N° de SIGEP) → `RC` adjudica y emite la Orden → documentos PDF. `ADM` administra usuarios/configuración y
audita; **no transacciona** (segregación de funciones).

## Supuestos y límites que debe conocer

* **Normativa:** los topes (Bs 50.000 / Bs 20.000, 3 cotizaciones), los artículos citados (43, 85, 86 NB-SABS, art. 22 de Contabilidad Integrada, D.S. 4505, R.B.M. 012/2024), la multa por mil y su tope **se tomaron de su especificación y no se verificaron contra los textos vigentes**. Los números están en `CONFIG` (marcados VERIFICAR) para ajustarlos sin tocar código; el texto de las cláusulas y la declaración del C-1 debe validarlo su Asesoría Legal.
* **Formato del Código Único de Excepción:** desconocido; `PatronCodigoExcepcion` (patrón `Like`) arranca en `*` y debe ajustarse.
* **El C-31 de este sistema es un registro interno de reserva.** El C-31 oficial lo genera y aprueba el SIGEP; aquí solo se asocia su número. No hay integración con SIGEP/SICOES.
* **Seguridad:** la protección de hojas de Excel y del proyecto VBA es disuasiva, no criptográfica (quien tenga el archivo y tiempo puede eludirla). Para datos sensibles o multiusuario concurrente use una base de datos real; Excel no maneja bien la escritura simultánea.
* El hash usa objetos COM de .NET (`SHA256Managed`); en equipos sin .NET 3.5 el login falla.
* Cotizaciones registran monto total (no precio por ítem); la Orden lista ítems/cantidades y el monto total adjudicado.
