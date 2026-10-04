# SIC-MUNI — Sistema Integrado de Contrataciones Municipales (VBA / Excel)

Solución de escritorio en un único libro `.xlsm` para contratación menor en un GAM de Bolivia:
solicitud y cotización → validación Compro Hecho en Bolivia (CHB) y excepciones → reserva
presupuestaria (C-31 preventivo) → Orden de Compra/Servicio, con documentos PDF.

> **Estado:** el código fue escrito y revisado estáticamente, **no se pudo ejecutar** (no hay Excel en el
> entorno de desarrollo). Haga una prueba integral con los datos demo antes de usarlo en producción.

## Documentación

| Documento | Para quién |
| :-- | :-- |
| [`docs/MANUAL_USUARIO.docx`](docs/MANUAL_USUARIO.docx) ([md](docs/MANUAL_USUARIO.md)) | US, RC, PF y ADM: uso diario de cada pestaña |
| [`docs/MANUAL_IMPLEMENTACION.docx`](docs/MANUAL_IMPLEMENTACION.docx) ([md](docs/MANUAL_IMPLEMENTACION.md)) | Sistemas y ADM: instalación, configuración, pruebas, seguridad, operación y puesta en producción |
| [`docs/ARQUITECTURA_Y_PLANTILLAS.md`](docs/ARQUITECTURA_Y_PLANTILLAS.md) | Detalle técnico de tablas y plantillas |

Los `.docx` se generan desde los `.md` con `docs/_build/md2docx.js` (Node + paquete `docx`).

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
| `modPostAward.bas` | Anulación de Orden/solicitud, recepción con cálculo de multa |
| `modImport.bas` | Importación CSV de catálogo CHB y presupuesto (rol ADM) |
| `modUIBuilder.bas` | Crea `frmLogin` y `frmContratacionesConsolidado` por código e inyecta su código |
| `modSelfTest.bas` | Pruebas automáticas de la lógica de negocio (escribe `resultado_pruebas.txt`) |
| `modMain.bas` | Punto de entrada y macros de administración |
| `frmLogin.code.txt`, `frmContratacionesConsolidado.code.txt`, `ThisWorkbook.code.txt` | Código de eventos |

Detalle de tablas, estados, plantillas, rangos con nombre y fórmulas: [`docs/ARQUITECTURA_Y_PLANTILLAS.md`](docs/ARQUITECTURA_Y_PLANTILLAS.md).

## Instalación

**Automática (recomendada):** doble clic en `instalar/Instalar.cmd`; instala, corre las pruebas y deja el libro listo. Ver [`docs/MANUAL_IMPLEMENTACION.md`](docs/MANUAL_IMPLEMENTACION.md).

**Manual:**

1. Excel de escritorio para Windows (2010 o superior) con **.NET Framework 3.5** habilitado (Panel de control → Características de Windows). Libro nuevo → guardar como `C:\SIC-MUNI\SIC-MUNI.xlsm` (tipo *Libro de Excel habilitado para macros*). Copiar la carpeta `vba/` a `C:\SIC-MUNI\vba\`.
2. Archivo → Opciones → Centro de confianza → Configuración de macros → habilitar macros y **"Confiar en el acceso al modelo de objetos de proyectos de VBA"**. Si descargó un ZIP, desbloquee los archivos (Propiedades → Desbloquear).
3. Alt+F11. Importar (arrastrar desde el Explorador al panel del proyecto, o Archivo → Importar archivo) **todos los `.bas` excepto `modMain.bas`** (este va después: referencia a los formularios, que aún no existen). Antes de nada, cambie `PROT_PWD` en `modCore` (si lo cambia después de proteger, no podrá desproteger).
4. Depuración → *Compilar VBAProject*. Debe terminar sin errores. Prueba del hash: en la ventana Inmediato, `?modSecurity.SHA256Hex("a")` debe dar `ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb`.
5. Ejecutar (F5 dentro del procedimiento) `InstalarSistema` (pide usuario y contraseña del administrador), luego opcionalmente `CargarDatosDemo`, luego `modUIBuilder.ConstruirFormularios`.
6. Importar `modMain.bas` y pegar `ThisWorkbook.code.txt` en el módulo `ThisWorkbook`. Compilar de nuevo.
7. Completar `CONFIG`, cargar catálogo y presupuesto reales (`AdminImportarCatalogo` / `AdminImportarPresupuesto` o `AdminMantenimiento`) y proteger el proyecto VBA con contraseña.
8. Guardar, cerrar y reabrir (Habilitar contenido): `Workbook_Open` oculta/protege las hojas y abre el login. Con el rol ADM cree los demás usuarios con la macro `AdminCrearUsuario` (Alt+F8).

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
* Importación CSV: UTF-8, `,` o `;`, fila 1 con los nombres de columna de la hoja (`CAT_CHB`: CodigoUNSPSC, Descripcion, Unidad, FichaTecnicaCHB, Tipo, Vigencia, RequiereAutorizacionMDPyEP; `PRESUPUESTO`: Gestion, DA, UE, Programa, Proyecto, ActObra, Fuente, Organismo, Partida_ObjetoGasto, DescripcionPartida, PresupuestoAprobado). Macros `AdminImportarCatalogo` / `AdminImportarPresupuesto`.
* Cotizaciones registran monto total (no precio por ítem); la Orden lista ítems/cantidades y el monto total adjudicado.
