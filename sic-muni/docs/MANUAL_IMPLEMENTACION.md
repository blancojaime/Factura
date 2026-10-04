# SIC-MUNI — Manual de Implementación

Sistema Integrado de Contrataciones Municipales — Contratación Menor (Excel / VBA)

Versión 1.0 · Octubre 2026 · Dirigido al personal de sistemas, al Administrador del sistema y a quien lidere la puesta en marcha

---

## 1. Introducción

### 1.1 Objetivo del documento

Este manual describe cómo instalar, configurar, verificar, poner en producción, operar y mantener SIC-MUNI en un Gobierno Autónomo Municipal. Complementa al **Manual de Usuario**, que explica cómo se usa el sistema en el día a día.

### 1.2 Qué es SIC-MUNI

Una aplicación de escritorio construida como **un solo libro de Excel con macros (`.xlsm`)**. Las hojas del libro actúan como tablas de base de datos, el código VBA contiene las reglas de negocio y dos formularios (inicio de sesión y pantalla de contrataciones) forman la interfaz. Cubre:

1. **Módulo 1 — Solicitud y cotización:** solicitud con ítems, formulario C-1, cotizaciones, cuadro comparativo y adjudicación.
2. **Módulo 2 — Validador CHB:** verificación contra el catálogo "Compro Hecho en Bolivia" y registro de excepciones de ficha técnica, con bloqueo a la Orden.
3. **Módulo 3 — Presupuesto y Orden:** control de saldo, C-31 Preventivo, asociación al N° de SIGEP, reversiones, Orden de Compra o de Servicio, recepción con multa y acta.

### 1.3 Alcance y limitaciones que debe conocer la dirección

| Tema | Situación |
| :-- | :-- |
| Integración con SIGEP / SICOES | **No existe.** El C-31 del sistema es un registro interno de reserva; el oficial se registra en SIGEP y aquí solo se asocia su número |
| Usuarios simultáneos | **Uno a la vez** sobre el mismo archivo (limitación de Excel) |
| Seguridad | La protección de hojas y del proyecto VBA es disuasiva, no criptográfica. Ver sección 10 |
| Normativa | Los topes, multas y artículos citados provienen de la especificación del proyecto y **deben validarse contra los textos vigentes** por Asesoría Legal antes de producción (sección 15) |
| Madurez | Probado en una instalación real de Excel 16.0 el 04/10/2026 (ver sección 9.4); no tiene historial de uso en producción |

## 2. Arquitectura

### 2.1 Capas

| Capa | Componentes |
| :-- | :-- |
| Interfaz | `frmLogin` (inicio de sesión), `frmContratacionesConsolidado` (5 pestañas), Menú del Administrador (`MenuAdmin`) |
| Reglas de negocio | Módulos VBA: seguridad, validación CHB, procura, motor presupuestario, post-adjudicación, documentos, importación |
| Datos | 13 hojas del libro (tablas), ocultas y protegidas |
| Documentos | 6 hojas plantilla `Doc_*` con rangos con nombre y fórmulas; exportación a PDF |
| Instalación y pruebas | Instalador PowerShell, módulos de instalación y batería de pruebas automáticas |

### 2.2 Módulos VBA

| Módulo | Responsabilidad |
| :-- | :-- |
| `modCore` | Acceso a hojas por nombre de columna, configuración, correlativos, auditoría, redondeo decimal, protección de hojas, modo silencioso |
| `modSecurity` | Hash SHA-256 con sal e iteraciones, inicio de sesión, bloqueo, tiempo de inactividad, matriz de permisos, alta y cambio de usuarios |
| `modValidationCHB` | Consulta al catálogo, validación de excepción, puerta de bloqueo a la Orden |
| `modProcurement` | Modalidad por monto, solicitud, ítems, cotizaciones, cuadro comparativo, adjudicación, monto en literal |
| `modBudgetEngine` | Saldos, emisión de C-31 (todo o nada), asociación SIGEP, reversión parcial y total, generación de la Orden |
| `modPostAward` | Anulación de Orden y de solicitud, recepción con cálculo de multa |
| `modDocumentAutomation` | Volcado de datos a las plantillas y exportación a PDF |
| `modImport` | Importación CSV de catálogo y presupuesto |
| `modSetup`, `modSetupTemplates` | Instalación de tablas, configuración, administrador, datos demo y construcción de las 6 plantillas |
| `modUIBuilder` | Crea por código los dos formularios e inyecta su código |
| `modMain` | Punto de entrada y Menú del Administrador |
| `modSelfTest` | Batería de pruebas automáticas y limpieza de datos de prueba |

Además, el código de los formularios y de `ThisWorkbook` se entrega como archivos de texto (`frmLogin.code.txt`, `frmContratacionesConsolidado.code.txt`, `ThisWorkbook.code.txt`).

### 2.3 Hojas del libro

| Hoja | Contenido |
| :-- | :-- |
| `CONFIG` | Parámetros de la entidad y de las reglas (clave, valor, descripción) |
| `SECUENCIAS` | Último número usado por cada correlativo |
| `SYS_AUTH` | Usuarios: hash con sal de la contraseña, rol, DA, estado, intentos |
| `CAT_CHB` | Catálogo CHB: código UNSPSC, ficha técnica, vigencia, necesidad de autorización MDPyEP |
| `PRESUPUESTO` | Presupuesto por estructura programática: aprobado, comprometido, saldo |
| `SOLICITUDES`, `SOLICITUDES_DET` | Cabecera y detalle de solicitudes, con el resultado CHB y la excepción por ítem |
| `COTIZACIONES` | Ofertas, evaluación, recomendada y adjudicada |
| `ORDENES_GASTO` | Órdenes con su estado (EMITIDA, RECIBIDA, ANULADA) |
| `C31`, `C31_DET` | Preventivos y su detalle por partida |
| `RECEPCIONES` | Recepciones con días de retraso y multa |
| `AUDITORIA` | Registro de acciones con usuario, rol, fecha y hora |
| `Doc_*` (6) | Plantillas de impresión: C-1, cuadro comparativo, justificación de excepción, C-31, Orden, acta |

Todas se ocultan como *muy ocultas* y se protegen con la clave de protección del libro. El detalle de columnas está en el anexo A.

### 2.4 Estados y reglas de bloqueo

Solicitud: `BORRADOR → EN_COTIZACION → EVALUADA → PRESUPUESTADA → ADJUDICADA → ORDEN_EMITIDA` (o `ANULADA`).
C-31: `PREVENTIVO → ASOCIADO → REVERTIDO_PARCIAL | REVERTIDO_TOTAL`.
Orden: `EMITIDA → RECIBIDA` (o `ANULADA`).
Ítem CHB: `N/A`, `SI`, `EXCEPCION` o `NO` (bloquea).

| Regla | Dónde se aplica |
| :-- | :-- |
| Un monto sobre el tope de contratación menor no pasa a cotización | Enviar a cotización |
| Sobre el tope sin cuadro se exigen tres cotizaciones | Evaluar cuadro, documento de cuadro |
| Un empate en el precio más bajo no se resuelve automáticamente | Evaluar cuadro |
| La reserva solo se emite con la solicitud EVALUADA y valida **todas** las líneas antes de aplicar | Emitir C-31 |
| Adjudicar exige oferta recomendada, CHB habilitado y C-31 vigente que cubra el monto | Adjudicar |
| La Orden exige solicitud ADJUDICADA, CHB habilitado (se reconsulta la vigencia de la ficha) y, si está activo, C-31 asociado a SIGEP | Generar Orden |
| No se revierte un C-31 con Orden vigente | Reversión total |
| No se anula una Orden con recepción conforme | Anular Orden |

## 3. Requisitos

### 3.1 Equipo del usuario

| Requisito | Detalle |
| :-- | :-- |
| Sistema operativo | Windows 10 u 11 |
| Microsoft Excel | **De escritorio**, 2010 o superior (probado en 16.0). No funciona en Mac ni en Excel web |
| .NET Framework 3.5 | Lo usan las funciones de hash SHA-256. Activar en *Panel de control → Programas → Activar o desactivar características de Windows → .NET Framework 3.5* |
| PowerShell | 5.1 (viene con Windows 10/11) para el instalador automático |
| Espacio | Menos de 50 MB; crecen con los PDF y el volumen de trámites |
| Permisos | Escritura en la carpeta de instalación (`C:\SIC-MUNI`). Administrador de Windows solo para habilitar .NET 3.5 |

### 3.2 Seguridad del entorno

- Si Excel está configurado para bloquear macros, habilite las macros del libro (o ubique la carpeta como *ubicación de confianza*).
- La instalación activa **temporalmente** la opción "Confiar en el acceso al modelo de objetos de proyectos de VBA" y la **restaura** al terminar.

## 4. Contenido del paquete

```
sic-muni/
├─ README.md                       Resumen técnico
├─ instalar/
│   ├─ Instalar.cmd                Doble clic: lanza el instalador
│   └─ Instalar-SICMUNI.ps1        Instalador automático
├─ vba/                            Módulos .bas y archivos .code.txt
└─ docs/                           Manuales y arquitectura (este documento)
```

Obtención: en GitHub, rama `claude/tender-einstein-76nc7n` → *Code → Download ZIP*. Si Windows marca el archivo como descargado de Internet, haga clic derecho en el ZIP → *Propiedades → Desbloquear* **antes** de descomprimir. Descomprima en una carpeta nueva, sin mezclar versiones anteriores.

## 5. Instalación automática (recomendada)

### 5.1 Antes de empezar

1. Active .NET Framework 3.5 y reinicie si Windows lo pide.
2. Cierre **todos** los libros y ventanas de Excel.
3. Compruebe que dispone de una contraseña de administrador que cumpla la política: al menos 10 caracteres con mayúsculas, minúsculas y números, sin comillas dobles.

### 5.2 Ejecución

1. Abra la carpeta `sic-muni\instalar` y haga doble clic en **`Instalar.cmd`**. Si Windows muestra una advertencia de SmartScreen, elija *Más información → Ejecutar de todas formas*.
2. Responda lo que se pide en la ventana negra:
   - Contraseña del administrador (dos veces).
   - Si ya existe una instalación anterior en `C:\SIC-MUNI`, el instalador pregunta si debe **reinstalar**; responda `s`. Se conserva una copia `.bak` del libro anterior.
3. Excel se abre **visible** y trabaja solo. **No lo toque** hasta que termine. Si aparece un cuadro de error de VBA, anote el texto y la línea resaltada (sección 12).

### 5.3 Qué hace el instalador, paso a paso

| Paso | Acción | Salida esperada |
| :-- | :-- | :-- |
| 1 | Verifica archivos, .NET 3.5 y la versión de Excel | `[OK]` en cada comprobación |
| 2 | Pide y valida la contraseña del administrador | — |
| 3 | Crea `C:\SIC-MUNI`, copia `vba\` y genera una **clave de protección aleatoria** que escribe en `CLAVE_PROTECCION.txt` | Mensaje con la ruta |
| 4 | Habilita temporalmente el acceso al modelo de objetos VBA (guarda el valor anterior) | `AccessVBOM = 1` |
| 5 | Crea `SIC-MUNI.xlsm` e importa 12 módulos | "12 módulos importados" |
| 6 | Comprueba el hash SHA-256 de la letra "a" | "SHA-256 correcto" |
| 7 | Crea tablas, configuración, administrador y 6 plantillas; carga datos demo | Mensajes `[OK]` |
| 8 | Construye los dos formularios, importa `modMain` e instala los eventos de `ThisWorkbook` | Mensaje `[OK]` |
| 9 | Ejecuta la batería de pruebas y muestra `PASS` / `FAIL` | `RESUMEN: PASS=… FAIL=…` |
| 10 | Si no hubo fallos: borra datos demo y de prueba. Protege el libro, lo guarda y restaura la configuración de Excel | `LISTO` |

**Criterio de aceptación de la instalación: `FAIL=0`.** Si hay fallos, el instalador conserva los datos de prueba para diagnosticarlos y termina con una advertencia: no use ese libro en producción, envíe `C:\SIC-MUNI\resultado_pruebas.txt` al equipo de desarrollo y reinstale con la versión corregida.

### 5.4 Después de la instalación

1. **Resguarde la clave de protección:** mueva `C:\SIC-MUNI\CLAVE_PROTECCION.txt` a un lugar seguro (gestor de contraseñas o caja fuerte) y **bórrelo** de la carpeta. Esa clave se necesita para desproteger hojas y para reinstalar sobre el mismo libro.
2. Abra `C:\SIC-MUNI\SIC-MUNI.xlsm`, pulse **Habilitar contenido** e ingrese como administrador (usuario `admin`, o el que eligió, con la contraseña que definió).
3. Siga la sección 8 (configuración inicial).

### 5.5 Opciones del instalador

Desde una ventana de PowerShell, en la carpeta `sic-muni\instalar`:

```
powershell -ExecutionPolicy Bypass -File .\Instalar-SICMUNI.ps1 -Destino D:\SIC-MUNI -AdminUsuario jperez -Reemplazar
```

| Parámetro | Efecto |
| :-- | :-- |
| `-Destino` | Carpeta de instalación (por defecto `C:\SIC-MUNI`) |
| `-AdminUsuario` | Nombre del administrador inicial (por defecto `admin`) |
| `-Reemplazar` | Reinstala sin preguntar sobre un libro existente (guarda copia `.bak`) |

## 6. Instalación manual (si el instalador no puede usarse)

Siga este orden exacto. Importa porque `modMain` hace referencia a formularios que aún no existen.

1. Cree un libro de Excel y guárdelo como **Libro de Excel habilitado para macros** en `C:\SIC-MUNI\SIC-MUNI.xlsm`. Copie la carpeta `vba` a `C:\SIC-MUNI\vba`.
2. *Archivo → Opciones → Centro de confianza → Configuración del Centro de confianza → Configuración de macros*: habilite las macros y marque **"Confiar en el acceso al modelo de objetos de proyectos de VBA"**.
3. Abra el editor VBA (**Alt+F11**). Importe (arrastrar desde el Explorador, o *Archivo → Importar archivo*) **todos los `.bas` excepto `modMain.bas`**.
4. En `modCore`, cambie el valor de `PROT_PWD` por una clave propia, larga y secreta. **Hágalo ahora**: si lo cambia después de proteger las hojas, no podrá desprotegerlas.
5. *Depuración → Compilar VBAProject*. Debe terminar sin errores.
6. Abra la ventana Inmediato (**Ctrl+G**) y escriba `?modSecurity.SHA256Hex("a")`. Debe responder `ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb`. Si da error, falta .NET 3.5.
7. Ejecute `InstalarSistema` (ponga el cursor dentro del procedimiento en `modSetup` y pulse **F5**). Pide usuario y contraseña del administrador.
8. Ejecute `CargarDatosDemo` (opcional, para probar).
9. Ejecute `ConstruirFormularios` (en `modUIBuilder`). Deben aparecer `frmLogin` y `frmContratacionesConsolidado` en la carpeta *Formularios*.
10. Importe `modMain.bas`. Haga doble clic en `ThisWorkbook` y pegue allí el contenido de `ThisWorkbook.code.txt`. Compile de nuevo.
11. Ejecute `modSelfTest.EjecutarPruebas` y revise `C:\SIC-MUNI\resultado_pruebas.txt`. Debe haber 0 `FAIL`.
12. Ejecute `modSelfTest.LimpiarDatosPrueba` para dejar la base limpia y luego `modCore.ProtectDB`.
13. Guarde, cierre y reabra el libro. Aparece el inicio de sesión.

## 7. Actualización y reinstalación

| Situación | Procedimiento |
| :-- | :-- |
| Nueva versión del sistema, **sin datos que conservar** | Descargue el ZIP nuevo y ejecute `Instalar.cmd`; responda `s` a reinstalar |
| Nueva versión **con datos en producción** | 1) Respaldo del libro. 2) Instale la versión nueva en **otra carpeta** (`-Destino D:\SIC-MUNI-NUEVO`). 3) Migre catálogo y presupuesto por CSV. 4) Recién entonces traslade el uso. No sobrescriba el libro en uso |
| Cambio de un solo módulo | En Alt+F11: clic derecho sobre el módulo → *Quitar* (sin exportar) → *Archivo → Importar archivo* del módulo nuevo. Compile y pruebe. Si el módulo fue `modMain`, reimporte también el código de `ThisWorkbook` solo si cambió |
| Se perdió la clave de protección | No es recuperable desde el sistema. Restaure desde respaldo o reinstale y migre por CSV |

## 8. Configuración inicial (puesta en marcha)

Ejecútela con el libro recién instalado, antes de que lo usen los demás usuarios.

### 8.1 Ingresar como administrador

Abra el libro → *Habilitar contenido* → inicie sesión. Se muestra el **Menú Administrador**:

| Opción | Función |
| :-- | :-- |
| 1 | Crear usuario |
| 2 | Desbloquear usuario |
| 3 | Cambiar contraseña de un usuario |
| 4 | Importar catálogo CHB (CSV) |
| 5 | Importar presupuesto (CSV) |
| 6 | Mostrar hojas de datos (mantenimiento y `CONFIG`) |
| 7 | Ocultar y proteger hojas de datos |
| 8 | Ver auditoría |
| 0 | Cerrar sesión |

Para reabrirlo: **Alt+F8** → `MenuAdmin` → *Ejecutar*.

### 8.2 Completar la hoja CONFIG

Opción 6 del menú, luego abra la hoja `CONFIG` y edite la columna **Valor**:

| Clave | Por defecto | Descripción |
| :-- | :-- | :-- |
| Entidad | GOBIERNO AUTONOMO MUNICIPAL DE (COMPLETAR) | Nombre que sale en el membrete de todos los documentos |
| Gestion | año actual | Gestión fiscal; se usa en los correlativos y en la búsqueda presupuestaria |
| CodDA, CodUE | vacío | Códigos de la entidad |
| TopeContratacionMenor | 50000 | Bs. Monto máximo que admite el sistema. **Validar con la norma vigente** |
| TopeSinCuadroComparativo | 20000 | Bs. Sobre este monto se exigen invitación y cuadro comparativo |
| MinCotizaciones | 3 | Cotizaciones mínimas sobre el tope sin cuadro |
| TolerCotizacionPct | 20 | % sobre el referencial que dispara un aviso |
| CHB_NivelMatch | 8 | Dígitos del código UNSPSC que se comparan (8 = exacto, 6 = familia) |
| PatronCodigoExcepcion | `*` | Patrón (operador `Like` de VBA) del Código Único de Excepción. **Ajustar al formato real** |
| MinCaracteresJustificacion | 80 | Longitud mínima de la justificación de excepción |
| ExigirC31SIGEPParaOrden | SI | Con `SI`, la Orden exige el número de C-31 de SIGEP asociado |
| PenalidadPorMil | 3 | Multa por mil, por día de retraso. **Validar** con la norma y el reglamento |
| PenalidadMaxPct | 10 | Tope de la multa en % del monto. **Validar** |
| MaxIntentosLogin | 3 | Intentos antes del bloqueo |
| TimeoutSesionMin | 20 | Minutos de inactividad antes de cerrar la sesión |

Al terminar, opción 7 del menú.

### 8.3 Crear los usuarios

Opción 1 por cada persona: usuario, nombre completo, rol (`US`, `RC`, `PF`, `ADM`), código de **DA** y contraseña inicial. El rol `US` solo ve solicitudes de su propia DA. Recomendaciones:

- Al menos **dos** usuarios con rol ADM (titular y suplente).
- Un usuario por persona; prohibir las cuentas compartidas.
- Entregar la contraseña inicial en privado y pedir su cambio (opción 3 del menú, a cargo del ADM).

### 8.4 Cargar catálogo y presupuesto

Prepare los archivos en Excel, guárdelos como **CSV UTF-8** y use las opciones 4 y 5. Primera fila con los nombres exactos:

Catálogo (`CAT_CHB`): `CodigoUNSPSC, Descripcion, Unidad, FichaTecnicaCHB, Tipo, Vigencia, RequiereAutorizacionMDPyEP`

Presupuesto (`PRESUPUESTO`): `Gestion, DA, UE, Programa, Proyecto, ActObra, Fuente, Organismo, Partida_ObjetoGasto, DescripcionPartida, PresupuestoAprobado`

| Aspecto | Regla |
| :-- | :-- |
| Delimitador | Coma o punto y coma (se detecta en la primera fila). Los campos con ese carácter van entre comillas |
| Codificación | UTF-8 |
| Fechas | `AAAA-MM-DD` |
| Booleanos | `SI`, `NO`, `TRUE`, `FALSE`, `1`, `0` |
| Códigos | Se importan como texto, por lo que se conservan los ceros a la izquierda (`01`, `0000`) |
| Catálogo | Código existente: se **actualiza**. Nuevo: se agrega |
| Presupuesto | Estructura existente: se **rechaza** (no se pisa lo comprometido). Nueva: se agrega con comprometido 0. Se ignoran `PreventivoComprometido` y `SaldoDisponible` del archivo |
| Límite | No se admiten saltos de línea dentro de un campo |

El resultado muestra registros nuevos, actualizados y rechazados, con el motivo de las primeras líneas rechazadas.

**Control obligatorio:** coteje el presupuesto importado contra el reporte oficial (aprobado por partida) antes de operar.

### 8.5 Proteger el proyecto VBA

Alt+F11 → clic derecho en *VBAProject (SIC-MUNI)* → *Propiedades de VBAProject → Protección* → marque *Bloquear proyecto para su visualización* y defina una contraseña. Guárdela junto con la clave de protección del libro.

## 9. Verificación y pruebas

### 9.1 Pruebas automáticas (`modSelfTest`)

Se ejecutan sin interfaz, con usuarios `t_us`, `t_rc` y `t_pf` y datos demo. El resultado queda en `C:\SIC-MUNI\resultado_pruebas.txt`. Pueden repetirse en cualquier momento con `modSelfTest.EjecutarPruebas` y limpiarse con `modSelfTest.LimpiarDatosPrueba` (**ejecútelas en una copia, no en el libro con datos reales**: `LimpiarDatosPrueba` borra todas las solicitudes, órdenes, C-31 y recepciones).

| Bloque | Verificaciones principales |
| :-- | :-- |
| Seguridad | SHA-256 contra un valor conocido, hash con sal, política de contraseñas, inicio de sesión, bloqueo a los 3 intentos, desbloqueo, permisos por rol |
| Reglas | Modalidad (Bs 15.000, 30.000 y 60.000), cotizaciones requeridas, monto en literal, redondeo comercial |
| CHB | Código con ficha vigente, sin ficha, fuera de catálogo; excepción incompleta, completa y con fecha futura |
| Flujo completo | Solicitud → CHB → cotización → cuadro → C-31 (rechazo por saldo) → adjudicación → exigencia de C-31 SIGEP → Orden → bloqueo de reversión → anulación y reemisión → recepción con 10 días de retraso y multa de 19,50 |
| Reversiones | Parcial y total devuelven saldo; no se revierte dos veces; anulación de solicitud; no se anula con Orden vigente |
| Documentos | Volcado a las plantillas, totales por fórmula, filas sobrantes ocultas, cláusulas con rangos con nombre, exportación a PDF |
| Importación | CSV de catálogo (punto y coma, campo entre comillas, actualización) y de presupuesto (duplicado rechazado) |

Total: 87 verificaciones. **Criterio de aceptación: 0 `FAIL`.**

### 9.2 Prueba de aceptación manual (pantallas)

Las pruebas automáticas no recorren los formularios. Antes de producción realice, **en una copia del libro**, los **cinco ejemplos guiados del Anexo E** (preparación más cinco casos con datos exactos, cifras de control y documentos esperados). Como resumen, las comprobaciones mínimas son:

| N° | Prueba | Resultado esperado |
| :-- | :-- | :-- |
| 1 | US crea solicitud con un ítem presente en el catálogo CHB | Aparece la alerta CHB en rojo y se completan descripción y unidad |
| 2 | US intenta enviar una solicitud de más de Bs 50.000 | El sistema la rechaza |
| 3 | US intenta crear una solicitud con otra DA | Rechazo |
| 4 | RC deja un ítem de catálogo sin evaluar y trata de adjudicar | Bloqueo por CHB |
| 5 | RC registra una excepción incompleta | Mensaje de qué falta; ítem en NO |
| 6 | RC registra una excepción completa | Ítem en EXCEPCION; se genera el PDF de justificación |
| 7 | RC registra una cotización y evalúa el cuadro | Oferta recomendada; PDF del cuadro |
| 8 | PF intenta reservar más que el saldo | Rechazo por saldo insuficiente |
| 9 | PF emite el C-31 y lo asocia a un número SIGEP | Estado ASOCIADO; PDF del C-31 |
| 10 | RC adjudica y genera la Orden | Número de Orden; PDF |
| 11 | RC registra una recepción con retraso | Días y multa correctos; acta en PDF |
| 12 | PF intenta revertir con Orden vigente | Rechazo |
| 13 | ADM crea un usuario, lo bloquea con 3 contraseñas erróneas y lo desbloquea | Funciona |
| 14 | Todos los PDF | Membrete, totales, montos en literal y firmas correctos |

### 9.3 Qué hacer si falla una prueba

1. No ponga el libro en producción.
2. Conserve `resultado_pruebas.txt` y, si hubo un cuadro de error de VBA, una captura con el mensaje y la línea resaltada.
3. Envíelos al equipo de desarrollo; reinstale con la versión corregida.

### 9.4 Registro de verificación

| Fecha | Entorno | Resultado | Observación |
| :-- | :-- | :-- | :-- |
| 04/10/2026 | Windows, Excel 16.0, .NET 3.5 | 86 de 87 | Fallo único: redondeo comercial de 2,675 (error de coma flotante en `RoundM`). Corregido con aritmética decimal. **Pendiente reconfirmar con 0 FAIL** en una reinstalación con la versión corregida |
| 04/10/2026 | Idem | Hallazgo previo | La instalación abortó por nombres de rango que empezaban con `C1_` (Excel los toma por una columna). Renombrados a `RQ_` |

## 10. Seguridad

### 10.1 Modelo

| Control | Implementación |
| :-- | :-- |
| Autenticación | Usuario y contraseña. La contraseña se guarda como `sal$hash`: SHA-256 con sal aleatoria de 32 caracteres y 1.000 iteraciones. Nunca se almacena la contraseña |
| Política de contraseñas | Mínimo 10 caracteres con mayúsculas, minúsculas y números |
| Bloqueo | Tras `MaxIntentosLogin` intentos fallidos la cuenta pasa a BLOQUEADO; solo el ADM la desbloquea |
| Sesión | Se cierra tras `TimeoutSesionMin` minutos de inactividad |
| Autorización | Matriz de permisos por rol validada **dentro de cada rutina de negocio**, no solo en los botones |
| Segregación de funciones | El ADM no opera transacciones; solo PF reserva y revierte presupuesto; solo RC adjudica y emite Órdenes |
| Aislamiento por DA | Un usuario US solo accede a solicitudes de su DA |
| Auditoría | Cada ingreso, intento fallido, cambio de estado, documento generado, importación y anulación queda en `AUDITORIA` |
| Protección de datos | Hojas muy ocultas y protegidas con la clave de protección; estructura del libro protegida; proyecto VBA protegible con contraseña |

### 10.2 Límites (leer con atención)

- La protección de hojas, del libro y del proyecto VBA **no es criptografía**: quien tenga el archivo y tiempo suficiente puede eludirla. No almacene información clasificada.
- Al abrir el libro con una versión de Excel o herramienta externa, los datos pueden leerse. Restrinja el acceso al archivo con **permisos de Windows**.
- No hay cifrado del archivo. Si lo necesita, use BitLocker en el disco o un contenedor cifrado.
- El sistema no impide que alguien con acceso al proyecto VBA y la clave modifique el código.

### 10.3 Recomendaciones de endurecimiento

1. Guardar el libro en una carpeta con permisos solo para los usuarios autorizados.
2. Bloquear el proyecto VBA con contraseña distinta de la clave de protección.
3. Borrar `CLAVE_PROTECCION.txt` después de resguardarla.
4. Cambiar la contraseña del administrador al implantar y cada seis meses.
5. Revisar la hoja `AUDITORIA` periódicamente (intentos fallidos, accesos denegados, anulaciones).
6. Mantener la firma o ubicación de confianza de macros solo para esta carpeta.

## 11. Operación y mantenimiento

### 11.1 Respaldo y recuperación

| Tema | Procedimiento |
| :-- | :-- |
| Copia diaria | Con el libro **cerrado**, copie `SIC-MUNI.xlsm` a una carpeta de red o medio externo con la fecha en el nombre (por ejemplo `SIC-MUNI_20261004.xlsm`) |
| Qué respaldar | El libro, la carpeta `PDF`, y los archivos CSV de carga |
| Retención | Guarde al menos 30 copias diarias y una mensual por gestión |
| Restauración | Cierre el libro en uso, copie la versión elegida y ábrala. Se pierde lo trabajado después de esa copia |
| Prueba | Pruebe una restauración al menos una vez por trimestre |

### 11.2 Cierre de gestión e inicio de la siguiente

1. Verifique que no queden trámites abiertos (o decida cuáles pasan a la nueva gestión).
2. Haga un respaldo completo y archive una copia como histórico de la gestión.
3. En `CONFIG`, cambie `Gestion`.
4. Importe el presupuesto de la nueva gestión (opción 5).
5. Si desea reiniciar la numeración, vacíe las filas de la hoja `SECUENCIAS` (solo con todos los procesos cerrados). Los correlativos incluyen el año, por ejemplo `SOL-2027-000001`.
6. Actualice el catálogo CHB (opción 4).

### 11.3 Tareas periódicas

| Frecuencia | Tarea | Responsable |
| :-- | :-- | :-- |
| Diaria | Respaldo del libro cerrado | ADM / Sistemas |
| Semanal | Revisión de `AUDITORIA` (accesos denegados, bloqueos) | ADM |
| Mensual | Actualizar catálogo CHB y comprobar vigencia de fichas | ADM / RC |
| Mensual | Contrastar saldos del sistema con SIGEP | PF |
| Trimestral | Prueba de restauración y revisión de usuarios activos (altas y bajas) | ADM |
| Anual | Cierre de gestión; cambio de contraseñas | ADM |

### 11.4 Altas y bajas de usuarios

Alta: opción 1 del menú. Baja: no existe opción de eliminación; mediante la opción 6 (hojas visibles) cambie el estado del usuario a `INACTIVO` en `SYS_AUTH` y vuelva a proteger con la opción 7. Esto conserva la trazabilidad en la auditoría.

### 11.5 Crecimiento y rendimiento

El sistema recorre las tablas completas en cada consulta; funciona bien con miles de registros, pero se vuelve lento con decenas de miles. Si el volumen anual supera esa magnitud, o necesita varios usuarios simultáneos, plantee migrar a una base de datos (Access, SQL Server) conservando las reglas de negocio de este manual.

## 12. Solución de problemas

| Síntoma | Causa probable | Solución |
| :-- | :-- | :-- |
| El instalador dice que no se pudo iniciar Excel | Excel de escritorio no instalado, o instalación dañada | Instale o repare Microsoft Office; no sirve Excel web |
| `.NET Framework 3.5 NO esta habilitado` | Característica de Windows desactivada | Actívela (sección 3.1) y reinstale |
| `El hash SHA-256 no funciona` o error al iniciar sesión | .NET 3.5 inactivo o dañado | Habilitar o reparar .NET 3.5 y reinstalar |
| `No se puede obtener acceso mediante programación al proyecto` | Falta la confianza en el modelo de objetos VBA (instalación manual) | Marcarla en el Centro de confianza |
| `Ya existe …SIC-MUNI.xlsm` | Instalación previa | Responda `s` a reinstalar |
| Error `1004` en `NombreRango` durante la instalación | Nombre de rango no válido (versión anterior con prefijo `C1_`) | Use la versión actual del paquete |
| `Variable no definida: frmLogin` | `modMain` se importó antes de crear los formularios | Ejecute `ConstruirFormularios` y recién importe `modMain` |
| Cuadro `Error de compilación` | Error en el código | Anote módulo, procedimiento y línea resaltada; envíelos al desarrollo |
| `Redondeo comercial … FAIL` | Versión anterior de `RoundM` | Actualice `modCore` a la versión con `CDec` |
| La ventana de inicio de sesión no aparece | Macros deshabilitadas o `ThisWorkbook` sin el código | *Habilitar contenido*; verifique `ThisWorkbook.code.txt` pegado |
| Después de iniciar sesión como ADM no hay menú | `modMain` antiguo | Reimporte `modMain.bas` de la versión actual |
| Las hojas no se ven | Están ocultas a propósito | Menú opción 6; al terminar, opción 7 |
| No se puede desproteger una hoja | Clave de protección distinta de la del libro | Use la clave guardada de `CLAVE_PROTECCION.txt` |
| `No se pudo exportar el PDF` | Falta el exportador PDF o permisos en `PDF` | Verificar permisos de la carpeta; en Excel 2010 instalar el complemento de PDF |
| Fórmulas de documentos con `#NOMBRE?` | Rangos con nombre dañados | Ejecutar `modSetupTemplates.BuildTemplates` (en una copia) |
| Sesión expirada | Inactividad | Ingrese nuevamente |
| Usuario bloqueado | Intentos fallidos | Menú opción 2 |
| "El archivo está en uso" | Otra persona lo tiene abierto | Espere a que lo cierre |

## 13. Plan de implantación sugerido

| Fase | Actividades | Responsable | Duración estimada |
| :-- | :-- | :-- | :-- |
| 1. Preparación | Validar requisitos, activar .NET 3.5, designar ADM titular y suplente, definir equipo y carpeta de instalación | Sistemas / Dirección Administrativa | 1 día |
| 2. Instalación | Instalación automática en el equipo definido; resultado con 0 `FAIL` | Sistemas | 0,5 día |
| 3. Validación normativa | Revisar topes, penalidades, formato del código de excepción, cláusulas y declaración del C-1 | Asesoría Legal / RC | 2–5 días |
| 4. Configuración | Completar `CONFIG`; crear usuarios; importar catálogo y presupuesto; cotejar contra reportes oficiales; proteger el proyecto VBA | ADM / PF | 1–2 días |
| 5. Prueba piloto | Recorrido completo (sección 9.2) con casos reales en una **copia**; ajustes | RC, PF, US | 2–3 días |
| 6. Capacitación | Un taller por rol con el Manual de Usuario | ADM / RC | 1 día |
| 7. Puesta en producción | Respaldo inicial; inicio de uso con trámites nuevos | Dirección Administrativa | 1 día |
| 8. Acompañamiento | Revisión semanal de auditoría y de incidencias durante el primer mes | ADM / Sistemas | 4 semanas |

Plan de contingencia: durante el primer mes mantenga el procedimiento manual vigente en paralelo para los trámites críticos. Si el sistema deja de estar disponible, restaure el último respaldo y continúe con el procedimiento manual.

## 14. Lista de verificación previa a producción

| ☐ | Control | Responsable | Fecha / firma |
| :-- | :-- | :-- | :-- |
| ☐ | Pruebas automáticas con 0 `FAIL` | Sistemas | |
| ☐ | Prueba de aceptación manual (sección 9.2) completa y firmada | RC / PF / US | |
| ☐ | `CONFIG` completada (entidad, gestión, DA, UE) | ADM | |
| ☐ | Topes, penalidades, formato del código de excepción y artículos citados validados por Asesoría Legal | Asesoría Legal | |
| ☐ | Catálogo CHB y presupuesto importados y cotejados con los reportes oficiales | PF / RC | |
| ☐ | Usuarios creados por rol; dos ADM; contraseña inicial cambiada | ADM | |
| ☐ | Proyecto VBA bloqueado con contraseña; clave de protección resguardada y borrada del equipo | Sistemas | |
| ☐ | Permisos de Windows sobre la carpeta del libro | Sistemas | |
| ☐ | Respaldo automático configurado y restauración probada | Sistemas | |
| ☐ | Capacitación realizada a todos los roles | ADM | |
| ☐ | Procedimiento de contingencia definido | Dirección Administrativa | |
| ☐ | Autorización formal de puesta en producción | Máxima autoridad administrativa | |

## 15. Normativa y supuestos pendientes de validación

El sistema fue diseñado a partir de la especificación del proyecto, que cita el siguiente marco. **Ningún artículo ni cifra fue verificado contra el texto vigente**; la entidad debe confirmarlos:

| Marco citado | Dónde se refleja en el sistema | Qué validar |
| :-- | :-- | :-- |
| Ley 1178 (SAFCO) | Control y auditoría | Alcance general |
| D.S. 0181 (NB-SABS) y modificaciones | Contratación menor, topes, cuadro comparativo, órdenes | Topes de Bs 50.000 y Bs 20.000, número de cotizaciones, contenido de las órdenes |
| Art. 43 NB-SABS | Declaración de no impedimento del C-1 | Texto de la declaración |
| Arts. 85 y 86 NB-SABS | Cláusulas de la Orden | Contenido y numeración |
| D.S. 4505 y R.B.M. 012/2024 (CHB) | Catálogo, ficha técnica, excepción, autorización MDPyEP | Reglas de excepción, formato del código único, plazos |
| Art. 22 Normas de Contabilidad Integrada | Reserva presupuestaria previa a adjudicar | Condiciones del registro preventivo |
| Manual SICOES / SIGEP (formularios 100, 110, 200; perfiles 991, 1014, 1109, 1111) | Estructura del C-31, asociación del N° SIGEP, nombres de roles | Correspondencia con los procedimientos reales |
| Penalidades | `PenalidadPorMil` = 3 y `PenalidadMaxPct` = 10 por defecto | Porcentajes y topes aplicables a la entidad |

## Anexo A. Estructura de las tablas

Las columnas marcadas con (+) se agregaron a las requeridas por la especificación porque el flujo las necesita.

| Hoja | Columnas |
| :-- | :-- |
| `CONFIG` | Clave, Valor, Descripcion |
| `SECUENCIAS` | Clave, Ultimo |
| `SYS_AUTH` | Usuario, PasswordHash, NombreCompleto, Rol, Dependencia_DA, Estado, (+) Intentos, (+) UltimoAcceso |
| `CAT_CHB` | CodigoUNSPSC, Descripcion, Unidad, FichaTecnicaCHB, Tipo, Vigencia, RequiereAutorizacionMDPyEP |
| `PRESUPUESTO` | Gestion, DA, UE, Programa, Proyecto, ActObra, Fuente, Organismo, Partida_ObjetoGasto, DescripcionPartida, PresupuestoAprobado, PreventivoComprometido, SaldoDisponible (fórmula) |
| `SOLICITUDES` | ID_Solicitud, Correlativo, Fecha, Cod_DA, Cod_UE, Solicitante, Justificacion, Estado, (+) Modalidad, (+) MontoReferencial |
| `SOLICITUDES_DET` | ID_Solicitud, Item, CodigoUNSPSC, Descripcion, Cantidad, Unidad, PrecioRefUnitario, PrecioRefTotal, CumpleCHB, CodigoExcepcionMDPyEP, (+) JustificacionExcepcion, (+) NroAutorizacionMDPyEP, (+) FechaAutorizacion |
| `COTIZACIONES` | ID_Cotizacion, ID_Solicitud, Proveedor_NIT, RazonSocial, (+) FechaCotizacion, ValidezOferta, MontoTotalCotizado, CumplimientoTecnico, Recomendado, (+) Adjudicada |
| `ORDENES_GASTO` | NroOrden, Tipo, CUCE_SICOES, ID_Solicitud, (+) ID_Cotizacion, Proveedor_Adjudicado, NIT, MontoTotal, NroPreventivo_C31, EstadoC31, FechaEmision, (+) PlazoDias, (+) LugarEntrega, (+) EstadoOrden, (+) MotivoAnulacion, (+) Usuario |
| `C31` (+) | NroInterno, Fecha, ID_Solicitud, DA, UE, MontoTotal, MontoRevertido, Estado, NroC31_SIGEP, Usuario |
| `C31_DET` (+) | NroInterno, Linea, Programa, Proyecto, ActObra, Fuente, Organismo, Partida, Importe, ImporteRevertido |
| `RECEPCIONES` (+) | NroRecepcion, NroOrden, FechaRecepcion, FechaLimite, DiasRetraso, MontoMulta, Resultado, Observaciones, Usuario |
| `AUDITORIA` (+) | Fecha, Usuario, Rol, Accion, Detalle |

Las columnas de códigos (DA, UE, programa, partida, NIT, UNSPSC, N° SIGEP) tienen formato de texto para conservar los ceros a la izquierda.

## Anexo B. Plantillas de documentos y rangos con nombre

Cada plantilla tiene el membrete en la fila 1, el título en la fila 2 y la gestión en la fila 3. La tabla de detalle tiene capacidad fija; las filas sobrantes se ocultan. Las columnas calculadas son **fórmulas de la plantilla** y no se sobrescriben desde el código.

| Hoja (prefijo) | Campos con nombre (celda) | Tabla de detalle | Fórmulas |
| :-- | :-- | :-- | :-- |
| `Doc_Solicitud_C1` (`RQ_`) | Solicitud C5, Fecha G5, DA C6, UE G6, Solicitante C7, Modalidad G7, Justificacion C8, Literal A27 | `RQ_ItemsIni` = A11, 15 filas, 8 columnas | `G11:G25 =IF(E11="","",ROUND(E11*F11,2))`; `G26 =SUM(G11:G25)` |
| `Doc_CuadroComparativo` (`CC_`) | Solicitud C5, Fecha G5, Modalidad C6, Referencial G6, Criterio C7, Recomendacion A22 | `CC_OfertasIni` = A10, 10 filas, 7 columnas | `H10:H19` variación sobre el referencial; `F20` menor oferta hábil con `AGGREGATE` |
| `Doc_JustificacionExcepcionCHB` (`EX_`) | Solicitud C5, Fecha G5, DA C6, Solicitante G6 | `EX_ItemsIni` = A13, 10 filas, 7 columnas | Ajuste automático de alto de fila al volcar |
| `Doc_Preventivo_C31` (`PV_`) | Nro C5, Sigep H5, Fecha C6, Estado H6, DA C7, UE H7, Solicitud C8, Literal A22 | `PV_LineasIni` = A11, 10 filas, 9 columnas | `J11:J20` vigente; `H21:J21` totales |
| `Doc_OrdenCompraServicio` (`OC_`) | Titulo A2, Nro C4, Fecha F4, CUCE C5, Solicitud F5, Proveedor C6, NIT C7, C31 F7, Plazo C8, Lugar C9, Monto F27, Literal A28, PenPorMil H2, PenMaxPct I2 | `OC_ItemsIni` = A12, 15 filas, 4 columnas | Cláusulas 1, 2, 3 y 5 son fórmulas que concatenan los rangos con nombre y los parámetros de `CONFIG` |
| `Doc_ActaRecepcion` (`AR_`) | Nro C4, Fecha F4, Orden C5, Solicitud F5, Proveedor C6, Limite C7, Dias F7, Monto C8, Multa F8, Conformidad C9, Obs C10 | — | `C11 =IF(AR_Monto="","",AR_Monto-AR_Multa)` |

Los nombres llevan prefijo por documento para que no se repitan en el libro. No use prefijos que Excel pueda interpretar como referencia de celda (como `C1_`, `R1_`).

## Anexo C. Macros de administración y mantenimiento

Se ejecutan desde Alt+F8 (o desde el editor con F5). Las marcadas con (*) requieren sesión de ADM.

| Macro | Función |
| :-- | :-- |
| `IniciarSistema` | Inicio de sesión y apertura de la pantalla o del menú según el rol |
| `MenuAdmin` (*) | Menú del Administrador |
| `AdminCrearUsuario` (*), `AdminDesbloquear` (*), `AdminCambiarPassword` (*) | Gestión de usuarios |
| `AdminImportarCatalogo` (*), `AdminImportarPresupuesto` (*) | Importación CSV |
| `AdminMantenimiento` (*), `AdminProteger` (*), `AdminVerAuditoria` (*) | Mostrar o proteger hojas; ver la auditoría |
| `modSetup.InstalarSistema` | Instalación interactiva (solo en libro nuevo) |
| `modSetupTemplates.BuildTemplates` | Reconstruye las 6 plantillas (hágalo en una copia) |
| `modSelfTest.EjecutarPruebas` / `LimpiarDatosPrueba` | Pruebas automáticas y limpieza (solo en una copia) |
| `modCore.ProtectDB` | Oculta y protege las hojas de datos y plantillas |

## Anexo D. Glosario

| Término | Significado |
| :-- | :-- |
| ADM | Administrador del sistema |
| ANPE | Apoyo Nacional a la Producción y Empleo, modalidad de contratación |
| C-1 | Formulario de requerimiento y especificaciones técnicas |
| C-31 | Comprobante de ejecución presupuestaria; el preventivo reserva el presupuesto |
| CHB | Catálogo "Compro Hecho en Bolivia" |
| CUCE | Código Único de Contratación Estatal |
| DA / UE | Dirección Administrativa / Unidad Ejecutora |
| MDPyEP | Ministerio de Desarrollo Productivo y Economía Plural |
| NB-SABS | Normas Básicas del Sistema de Administración de Bienes y Servicios |
| PF | Presupuesto / Finanzas |
| RBAC | Control de acceso basado en roles |
| RC | Responsable de Contrataciones |
| SIGEP | Sistema de Gestión Pública |
| SICOES | Sistema de Contrataciones Estatales |
| UNSPSC | Clasificación estándar de productos y servicios |
| US | Unidad Solicitante |
| VBA | Visual Basic para Aplicaciones, el lenguaje de macros de Excel |

## Anexo E. Ejemplos guiados de prueba de aceptación

Cinco casos completos, con datos exactos y resultados esperados, que recorren **todos los módulos desde el ingreso hasta la generación de documentos**. Úselos para validar la instalación, capacitar a los usuarios y dejar constancia de la aceptación (columna ☐: marque cuando el resultado coincida).

### E.1 Reglas para realizar los ejemplos

- Trabaje **solo en una copia de ensayo** del libro recién instalado (`SIC-MUNI-ENSAYO.xlsm`). Los ejemplos crean usuarios, trámites y reservas ficticias; nunca los haga en el libro de producción.
- Realícelos **en orden (E0, E1 … E5)** sobre una base limpia: los ejemplos posteriores usan datos creados por los anteriores y los números de trámite que se indican (por ejemplo `SOL-2026-000001`) solo coinciden si se siguen en ese orden. Si su numeración difiere, use la que muestre el sistema.
- Los archivos de práctica están en la carpeta `sic-muni\ejemplos\` del paquete (`catalogo_ejemplo.csv`, `presupuesto_ejemplo.csv`, `catalogo_actualizacion.csv`, `presupuesto_con_duplicado.csv`). Todos los datos son **ficticios**.
- "HOY" es la fecha del día; "HOY+30" es esa fecha más 30 días. Escriba las fechas en el formato de su Windows (normalmente `dd/mm/aaaa`).
- Los importes que muestra el sistema usan el separador de miles y decimales de su configuración regional; aquí se escriben con punto decimal.
- Antes de cada ejemplo, **cierre sesión** y entre con el usuario indicado. Cuando el paso diga "cargar la solicitud", escriba su número en **Solicitud N°** y pulse **Cargar**.
- Códigos presupuestarios de las pruebas (ilustrativos): DA `01`, UE `001`, Programa `01`, Proyecto `0000`, Act./Obra `001`, Fuente `20`, Organismo `230`.

### E.2 Mapa de cobertura

| Función a probar | E0 | E1 | E2 | E3 | E4 | E5 |
| :-- | :-: | :-: | :-: | :-: | :-: | :-: |
| Inicio de sesión, roles y permisos | ● | ● | ● | ● | ● | ● |
| Bloqueo por intentos, desbloqueo y cambio de contraseña | | | | | | ● |
| Aislamiento por DA | | | | | | ● |
| Alta de usuarios, importación CSV y configuración | ● | | | | | ● |
| Solicitud con ítems y modalidad por monto | | ● | ● | ● | ● | ● |
| Alerta CHB y evaluación por catálogo | | ● | ● | | ● | |
| Excepción CHB (incompleta, completa, bloqueo) | | | | ● | | |
| Cotizaciones y cuadro comparativo (1 y 3 ofertas) | | ● | ● | ● | ● | |
| Control de saldo y C-31 con varias partidas | | ● | ● | ● | ● | |
| Asociación del N° de SIGEP y sus validaciones | | ● | ● | ● | ● | |
| Reversión parcial y total | | ● | | | ● | |
| Adjudicación y Orden de Compra | | ● | ● | ● | | |
| Orden de Servicio, anulación y reemisión | | | | | ● | ● |
| Recepción con multa y acta | | ● | | | | ● |
| Anulación de solicitud | | | | | | ● |
| Documentos PDF (C-1, cuadro, excepción, C-31, Orden, acta) | | ● | ● | ● | ● | ● |
| Auditoría | ● | | | | | ● |

### E.3 Ejemplo 0 — Preparación (usuarios, configuración y datos)

**Objetivo:** dejar la copia de ensayo lista. **Usuario:** administrador.

**Usuarios de práctica** (contraseña inicial de todos: `Ejemplo#2026A`; bórrelos o inactívelos al terminar):

| Usuario | Nombre | Rol | DA |
| :-- | :-- | :-- | :-- |
| us_ejemplo | Usuario Solicitante Uno | US | 01 |
| us_dos | Usuario Solicitante Dos | US | 02 |
| rc_ejemplo | Responsable de Contrataciones | RC | 01 |
| pf_ejemplo | Presupuesto y Finanzas | PF | 01 |

| N° | Rol y pantalla | Qué hacer (datos exactos) | Resultado esperado | ☐ |
| :-- | :-- | :-- | :-- | :-: |
| 0.1 | Sistemas | Cierre Excel, copie `SIC-MUNI.xlsm` como `SIC-MUNI-ENSAYO.xlsm` y abra la copia. Habilite el contenido | Aparece la ventana de inicio de sesión | ☐ |
| 0.2 | Inicio de sesión | Escriba un usuario inexistente (`nadie`) y cualquier clave. Pulse Ingresar | Mensaje "Usuario o contrasena incorrectos." sin dar pistas | ☐ |
| 0.3 | Inicio de sesión | Ingrese como `admin` con su contraseña | Aparece directamente el Menú Administrador | ☐ |
| 0.4 | ADM, menú 6 | Mostrar hojas (aparecen como pestañas en la parte inferior de Excel; cierre el menú con Cancelar para trabajar en ellas y reábralo con Alt+F8 → `MenuAdmin`). En la hoja `CONFIG` cambie **Entidad** a `GOBIERNO AUTONOMO MUNICIPAL DE EJEMPLO` y compruebe que **Gestion** sea `2026` | Valores guardados. (El membrete de los PDF usará este nombre) | ☐ |
| 0.5 | ADM, hoja `SYS_AUTH` | Observe la columna `PasswordHash` del administrador | Texto largo con formato `32 caracteres$64 caracteres`: **no** se ve la contraseña | ☐ |
| 0.6 | ADM, menú 7 | Ocultar y proteger las hojas | Aviso "Hojas de datos ocultas y protegidas"; ya no se ven las pestañas de datos | ☐ |
| 0.7 | ADM, menú 4 | Importar `catalogo_ejemplo.csv` | "Nuevos: 5 / Actualizados: 0 / Rechazados: 0" | ☐ |
| 0.8 | ADM, menú 5 | Importar `presupuesto_ejemplo.csv` | "Nuevos: 4 / Actualizados: 0 / Rechazados: 0" | ☐ |
| 0.9 | ADM, menú 1 | Cree los cuatro usuarios de la tabla anterior (rol y DA exactos) | "Usuario creado." cuatro veces | ☐ |
| 0.10 | ADM, menú 1 | Intente crear `us_ejemplo` otra vez con la clave `Ejemplo#2026A`; luego un usuario nuevo `prueba` con la clave `corta` | Rechazos: "El usuario ya existe." y "La contrasena debe tener al menos 10 caracteres." | ☐ |
| 0.11 | ADM, menú 8 | Ver auditoría. Cuando termine use el menú 7 | Filas `USUARIO_CREADO` ×4, `IMPORT_CSV` ×2, `SHOW_DB` y `LOGIN_OK` (el intento con un usuario inexistente no se registra) | ☐ |
| 0.12 | ADM, menú 0 | Cerrar sesión | Vuelve al inicio; en la auditoría queda `LOGOUT` | ☐ |

### E.4 Ejemplo 1 — Compra menor simple de punta a punta (Bs 1.150)

**Objetivo:** el camino feliz con una sola cotización: solicitud → CHB → cotización → C-31 → SIGEP → adjudicación → Orden de Compra → recepción → todos los documentos. Incluye una reversión parcial.

**Datos del caso**

| Dato | Valor |
| :-- | :-- |
| Solicitud | DA `01`, UE `001`. Justificación: `Reposicion de material de oficina para las unidades administrativas` |
| Ítem 1 | Código `44121600` (en catálogo, ficha vigente), Papel bond tamaño carta, Paquete, cantidad 20, precio 45.00 → 900.00 |
| Ítem 2 | Código `44121701` (fuera de catálogo), Bolígrafos azules, Unidad, cantidad 100, precio 2.50 → 250.00 |
| Cotización | NIT `1020304050`, `LIBRERIA EJEMPLO S.R.L.`, validez HOY+30, monto 1080.00, cumple |
| C-31 | Estructura `01 / 0000 / 001 / 20 / 230`, partida `31120`, importe 1150.00 |
| SIGEP | N° `250001` |
| Orden | Tipo COMPRA, CUCE `EJEMPLO-CUCE-001`, plazo 10 días, lugar `Almacen Municipal` |

**Cifras de control:** referencial **1.150,00** · modalidad **CONTRATACION MENOR** · cotizaciones requeridas 1 · saldo partida 31120 antes 12.000,00 → después de reservar 10.850,00 → tras reversión parcial de 70,00: **10.920,00** · monto de la Orden **1.080,00** · retraso 0 días, multa 0,00, neto a pagar 1.080,00.

| N° | Rol y pantalla | Qué hacer (datos exactos) | Resultado esperado | ☐ |
| :-- | :-- | :-- | :-- | :-: |
| 1.1 | US `us_ejemplo`, pestaña 1 | Compruebe que **DA** muestra `01`. Escriba UE `001`, la justificación del cuadro y pulse **Crear solicitud** | Se asigna `SOL-2026-000001` y aparece en **Solicitud N°** | ☐ |
| 1.2 | US, pestaña 1 | Ítem 1: escriba el código `44121600` y salga del campo | Alerta **roja** CHB; se completan descripción y unidad desde el catálogo | ☐ |
| 1.3 | US, pestaña 1 | Complete cantidad 20 y precio 45 y pulse **Agregar item** | Aviso de alerta CHB; el ítem aparece en la lista con total 900.00 y CHB `NO` (pendiente) | ☐ |
| 1.4 | US, pestaña 1 | Ítem 2: código `44121701`, descripción `Boligrafos azules`, unidad `Unidad`, cantidad 100, precio 2.50. **Agregar item** | Sin alerta CHB (código fuera de catálogo); CHB `N/A`; el estado muestra Referencial **1.150,00** y modalidad **CONTRATACION MENOR** | ☐ |
| 1.5 | US, pestaña 1 | Intente agregar un ítem con cantidad `0` | Rechazo: "Cantidad y precio referencial deben ser mayores a cero." | ☐ |
| 1.6 | US, pestaña 1 | Pulse **Enviar a cotizacion**, luego **Generar C-1 (PDF)** | Estado `EN_COTIZACION`. PDF en `PDF\` con los 2 ítems, total 1.150,00 y "Son: MIL CIENTO CINCUENTA 00/100 BOLIVIANOS", declaración de no impedimento y firmas | ☐ |
| 1.7 | US, pestaña 3 | Observe los botones | **Deshabilitados** (el rol US no cotiza) | ☐ |
| 1.8 | RC `rc_ejemplo` | Cargue `SOL-2026-000001`. Pestaña 2: **N de item** `1`, casilla de excepción **sin marcar**, **Registrar evaluacion CHB** | Mensaje CHB. En la pestaña 1 el ítem 1 queda en CHB **`SI`** | ☐ |
| 1.9 | RC, pestaña 3 | NIT `1020304050`, razón social `LIBRERIA EJEMPLO S.R.L.`, validez HOY+30, monto `1080`, marque **Cumple tecnicamente**, **Registrar** | Aparece la cotización `COT-2026-000001` en la lista | ☐ |
| 1.10 | RC, pestaña 3 | Pulse **Evaluar cuadro** | Mensaje "Recomendada: LIBRERIA EJEMPLO S.R.L. por Bs 1,080.00"; estado `EVALUADA`; en la lista la columna recomendada dice `SI` | ☐ |
| 1.11 | RC, pestaña 3 | Pulse **Adjudicar seleccionada** con la fila seleccionada | Rechazo: "No existe C-31 Preventivo vigente…" (falta la reserva) | ☐ |
| 1.12 | PF `pf_ejemplo`, pestaña 4 | Cargue la solicitud. Ingrese Programa `01`, Proyecto `0000`, Act./Obra `001`, Fuente `20`, Organismo `230`, Partida `31120`, Importe `1150`. **Consultar saldo** | "Saldo disponible: Bs 12,000.00" | ☐ |
| 1.13 | PF, pestaña 4 | **Agregar linea** y **Emitir C-31 Preventivo** | Mensaje con `C31P-2026-000001`; el estado pasa a `PRESUPUESTADA`; la lista de líneas se limpia | ☐ |
| 1.14 | PF, pestaña 4 | Con el N° interno en la casilla, escriba SIGEP `ABC` y pulse **Asociar C-31** | Rechazo: "N de C-31 SIGEP invalido (numerico, hasta 10 digitos)." | ☐ |
| 1.15 | PF, pestaña 4 | Escriba SIGEP `250001` y **Asociar C-31** | "C-31 SIGEP asociado." | ☐ |
| 1.16 | RC, pestaña 3 | Cargue la solicitud, seleccione la cotización y **Adjudicar seleccionada** | "Adjudicada."; estado `ADJUDICADA` | ☐ |
| 1.17 | RC, pestaña 5 | Tipo `COMPRA`, CUCE `EJEMPLO-CUCE-001`, plazo `10`, lugar `Almacen Municipal`. **Generar Orden** | Orden `OC-2026-000001`; estado `ORDEN_EMITIDA` | ☐ |
| 1.18 | RC, pestaña 5 | **Orden (PDF)** | PDF "ORDEN DE COMPRA": proveedor, NIT, ítems (sin precios unitarios), monto **1.080,00**, "Son: MIL OCHENTA 00/100 BOLIVIANOS", plazo 10 días, N° del preventivo (`C31P-2026-000001`) y 6 cláusulas con el plazo y las penalidades (3 por mil, tope 10 %) | ☐ |
| 1.19 | PF, pestaña 4 | Reversión parcial: N° interno `C31P-2026-000001`, Línea `1`, Monto `70`, Motivo `Ajuste de reserva al monto adjudicado`. **Reversion parcial** | "Reversion parcial registrada." | ☐ |
| 1.20 | PF, pestaña 4 | Con la solicitud cargada, escriba Programa `01`, Proyecto `0000`, Act./Obra `001`, Fuente `20`, Organismo `230`, Partida `31120` e importe `1` y pulse **Consultar saldo** | Saldo **10,920.00** (12.000 − 1.150 + 70) | ☐ |
| 1.21 | PF, pestaña 4 | **C-31 (PDF)** | PDF con la línea: Importe 1.150,00, Revertido 70,00, Vigente 1.080,00; total en literal "MIL OCHENTA"; estado `REVERTIDO_PARCIAL` | ☐ |
| 1.22 | RC, pestaña 5 | Fecha recepción HOY, casilla **Recepcion CONFORME** marcada, **Registrar recepcion** | Mensaje con `REC-2026-000001`; la Orden queda `RECIBIDA` | ☐ |
| 1.23 | RC, pestaña 5 | **Acta de recepcion (PDF)** | Acta con 0 días de retraso, multa 0,00 y neto a pagar **1.080,00** | ☐ |
| 1.24 | RC, pestaña 3 | **Cuadro comparativo (PDF)** | PDF con una oferta, "Cumple", recomendada, menor oferta hábil 1.080,00 y variación −6,1 % sobre el referencial | ☐ |
| 1.25 | RC, pestaña 5 | Pulse **Anular Orden** con motivo `Prueba de anulacion de orden recibida` | Rechazo: "No se anula una Orden con recepcion conforme." | ☐ |

### E.5 Ejemplo 2 — Contratación con cuadro comparativo y dos partidas (Bs 26.000)

**Objetivo:** monto sobre Bs 20.000 (exige tres cotizaciones e invitación), criterio Cumple/No cumple con precio más bajo, C-31 con **dos partidas** y Orden con plazo de 30 días.

**Datos del caso**

| Dato | Valor |
| :-- | :-- |
| Solicitud | DA `01`, UE `001`. Justificación: `Renovacion del equipo de computo de la unidad de sistemas` |
| Ítem único | Código `43211500` (en catálogo, ficha vigente), Computadoras de escritorio, Unidad, cantidad 5, precio 5200.00 → 26.000,00 |
| Cotización A | NIT `3030303030`, `COMPUTACION ANDINA EJEMPLO S.R.L.`, 25400.00, cumple |
| Cotización B | NIT `4040404040`, `TECNOLOGIA BOLIVIA EJEMPLO S.A.`, 24800.00, cumple |
| Cotización C | NIT `5050505050`, `IMPORTADORA ORIENTE EJEMPLO`, 24100.00, **No cumple** técnicamente |
| C-31 | Línea 1: partida `43130` importe 15000. Línea 2: partida `43120` importe 9800 (total 24.800) |
| SIGEP | N° `250002` |
| Orden | COMPRA, CUCE `EJEMPLO-CUCE-002`, plazo 30 días, lugar `Oficinas Centrales` |

**Cifras de control:** referencial **26.000,00** · modalidad **CONTRATACION MENOR CON INVITACION Y CUADRO COMPARATIVO** · 3 cotizaciones requeridas · recomendada **B (24.800,00)** · saldos tras reservar: 43130 = 65.000,00 y 43120 = 50.200,00 · literal del C-31 "VEINTICUATRO MIL OCHOCIENTOS".

| N° | Rol y pantalla | Qué hacer (datos exactos) | Resultado esperado | ☐ |
| :-- | :-- | :-- | :-- | :-: |
| 2.1 | US `us_ejemplo`, pestaña 1 | Cree la solicitud (`SOL-2026-000002`) y agregue el ítem `43211500`, cantidad 5, precio 5200 | Alerta CHB roja. Referencial **26.000,00**; modalidad **con invitación y cuadro comparativo** | ☐ |
| 2.2 | US | **Enviar a cotizacion** y **Generar C-1 (PDF)** | Estado `EN_COTIZACION`; C-1 con "Son: VEINTISEIS MIL 00/100 BOLIVIANOS" | ☐ |
| 2.3 | RC `rc_ejemplo`, pestaña 2 | Cargue la solicitud. Ítem `1`, sin marcar excepción, **Registrar evaluacion CHB** | Ítem 1 en `SI` | ☐ |
| 2.4 | RC, pestaña 3 | Registre las cotizaciones A y B (validez HOY+30; A y B cumplen). Pulse **Evaluar cuadro** | "Se requieren 3 cotizaciones; hay 2." | ☐ |
| 2.5 | RC, pestaña 3 | Registre la cotización C **sin** marcar "Cumple tecnicamente". **Evaluar cuadro** | "Recomendada: TECNOLOGIA BOLIVIA EJEMPLO S.A. por Bs 24,800.00" (C es la más barata pero no cumple). Estado `EVALUADA` | ☐ |
| 2.6 | RC, pestaña 3 | **Cuadro comparativo (PDF)** | PDF con 3 ofertas; C "No cumple"; B "RECOMENDADA"; menor oferta hábil **24.800,00**; variaciones: A −2,3 %, B −4,6 %, C −7,3 % | ☐ |
| 2.7 | PF `pf_ejemplo`, pestaña 4 | Cargue la solicitud. Estructura `01/0000/001/20/230`, Partida `43130`, Importe `15000`. **Agregar linea** | La línea aparece en la lista | ☐ |
| 2.8 | PF, pestaña 4 | Cambie la partida a `43120`, importe `9800`, **Agregar linea**. Pulse **Emitir C-31 Preventivo** | `C31P-2026-000002`; estado `PRESUPUESTADA` | ☐ |
| 2.9 | PF, pestaña 4 | Con ese N° escriba SIGEP `250001` y **Asociar C-31** | Rechazo: "Ese N de C-31 SIGEP ya esta asociado a otro preventivo." | ☐ |
| 2.10 | PF, pestaña 4 | SIGEP `250002`, **Asociar C-31**, luego **C-31 (PDF)** | PDF con **2 líneas** (15.000,00 y 9.800,00), total **24.800,00** y "VEINTICUATRO MIL OCHOCIENTOS" | ☐ |
| 2.11 | RC, pestaña 3 | Seleccione la cotización **A** (no recomendada) y **Adjudicar seleccionada** | Rechazo: "Solo puede adjudicarse la oferta recomendada…" | ☐ |
| 2.12 | RC, pestaña 3 | Seleccione la cotización **B** y **Adjudicar seleccionada** | "Adjudicada."; estado `ADJUDICADA` | ☐ |
| 2.13 | RC, pestaña 5 | COMPRA, CUCE `EJEMPLO-CUCE-002`, plazo `30`, lugar `Oficinas Centrales`. **Generar Orden** | `OC-2026-000002`; estado `ORDEN_EMITIDA` | ☐ |
| 2.14 | RC, pestaña 5 | **Orden (PDF)** | Orden por **24.800,00**, plazo 30 días y proveedor TECNOLOGIA BOLIVIA EJEMPLO S.A. | ☐ |
| 2.15 | PF, pestaña 4 | **Consultar saldo** con partidas `43130` y luego `43120` (cualquier importe) | **65,000.00** y **50,200.00** | ☐ |

(La recepción de esta Orden se hace en el Ejemplo 5, con retraso y multa.)

### E.6 Ejemplo 3 — Excepciones del catálogo CHB (Bs 17.500)

**Objetivo:** probar el Módulo 2: ítems que no pueden comprarse por catálogo (sin ficha, ficha vencida, plazo insuficiente), excepción incompleta y completa, el **bloqueo** a la adjudicación y el documento de justificación.

**Datos del caso**

| Dato | Valor |
| :-- | :-- |
| Solicitud | DA `01`, UE `001`. Justificación: `Equipamiento urgente de la nueva oficina de atencion al ciudadano` |
| Ítem 1 | `56101500` Escritorios metálicos (en catálogo, **sin ficha**), Unidad, cantidad 10, precio 850.00 → 8.500,00 |
| Ítem 2 | `14111507` Papel para impresora (en catálogo, **ficha vencida** el 31/01/2026), Resma, cantidad 100, precio 38.00 → 3.800,00 |
| Ítem 3 | `43211500` Computadoras (**ficha vigente**), Unidad, cantidad 1, precio 5200.00 → 5.200,00 (se comprará fuera de catálogo por plazo) |
| Excepción ítem 1 | Código `EXC-2026-0147`, N° autorización `MDPyEP-AUT-0391`, fecha (un día anterior a HOY, por ejemplo 01/09/2026) |
| Excepción ítem 2 | Código `EXC-2026-0148`, N° `MDPyEP-AUT-0392`, misma fecha |
| Excepción ítem 3 | Código `EXC-2026-0149`, N° `MDPyEP-AUT-0393`, misma fecha |
| Justificación (usar en las tres; supera los 80 caracteres) | `El proveedor del catalogo no puede cumplir el plazo de entrega requerido por la unidad ni la cantidad solicitada, por lo que se requiere comprar fuera del mercado virtual.` |
| Cotización | NIT `6060606060`, `MUEBLES Y SISTEMAS EJEMPLO S.A.`, 17100.00, cumple |
| C-31 | Partida `43120`, importe 17500.00. SIGEP `250003` |
| Orden | COMPRA, CUCE `EJEMPLO-CUCE-003`, plazo 15 días, lugar `Almacen Municipal` |

**Cifras de control:** referencial **17.500,00** · modalidad **CONTRATACION MENOR** (1 cotización) · saldo 43120 después: 50.200,00 − 17.500,00 = **32.700,00**.

| N° | Rol y pantalla | Qué hacer (datos exactos) | Resultado esperado | ☐ |
| :-- | :-- | :-- | :-- | :-: |
| 3.1 | US `us_ejemplo` | Cree la solicitud `SOL-2026-000003` y agregue los 3 ítems. Observe la alerta al digitar cada código | Alerta roja en los tres (los tres están en catálogo). Referencial 17.500,00. Los 3 ítems en CHB `NO` | ☐ |
| 3.2 | US | **Enviar a cotizacion** | Estado `EN_COTIZACION` | ☐ |
| 3.3 | RC `rc_ejemplo`, pestaña 2 | Cargue la solicitud. Ítem `1`, marque **Comprar FUERA del catalogo**, Cod. Excepción `EXC-1` (solo ese dato). **Registrar evaluacion CHB** | Mensaje: "Codigo Unico de Excepcion … ausente o con formato invalido." Ítem 1 sigue en `NO` | ☐ |
| 3.4 | RC, pestaña 2 | Ítem `1`: Cod. `EXC-2026-0147`, N° `MDPyEP-AUT-0391`, fecha, pero Justificación `Muy corta`. Registrar | Mensaje: justificación insuficiente (mínimo 80 caracteres). Sigue `NO` | ☐ |
| 3.5 | RC, pestaña 2 | Repita con la fecha **de mañana** y la justificación completa | Mensaje: "La fecha de autorizacion no puede ser futura." | ☐ |
| 3.6 | RC, pestaña 2 | Repita con fecha anterior a HOY y la justificación completa | Ítem 1 queda en **`EXCEPCION`** | ☐ |
| 3.7 | RC, pestaña 2 | Ítem `2` (ficha vencida): **sin** marcar la casilla de excepción y sin datos. Registrar | Se exige excepción aunque no la haya marcado (ficha no vigente): mensaje de código ausente. Ítem 2 en `NO` | ☐ |
| 3.8 | RC, pestaña 2 | Ítem `2`: marque la casilla y complete `EXC-2026-0148`, `MDPyEP-AUT-0392`, fecha y justificación. Registrar | Ítem 2 en `EXCEPCION` | ☐ |
| 3.9 | RC, pestaña 3 | Registre la cotización (NIT `6060606060`, 17100, cumple) y **Evaluar cuadro** | "Recomendada: MUEBLES Y SISTEMAS EJEMPLO S.A. por Bs 17,100.00". Estado `EVALUADA` | ☐ |
| 3.10 | RC, pestaña 3 | Con el **ítem 3 todavía pendiente**, seleccione la cotización y **Adjudicar seleccionada** | **Bloqueo**: "Bloqueado por CHB: - Item 3: sin Ficha Tecnica CHB vigente ni Codigo de Excepcion autorizado." | ☐ |
| 3.11 | RC, pestaña 2 | Ítem `3` (ficha vigente): marque la casilla de excepción y complete `EXC-2026-0149`, `MDPyEP-AUT-0393`, fecha y justificación | Ítem 3 en `EXCEPCION` | ☐ |
| 3.12 | RC, pestaña 2 | **Justificacion de excepcion (PDF)** | PDF "Justificación de excepción de ficha técnica": 3 ítems con código de excepción, N° de autorización, fecha y justificación; filas sin recortes | ☐ |
| 3.13 | PF `pf_ejemplo`, pestaña 4 | Cargue la solicitud; partida `43120`, importe `17500`. **Agregar linea**, **Emitir C-31 Preventivo** | `C31P-2026-000003` | ☐ |
| 3.14 | PF | SIGEP `250003`, **Asociar C-31** | "C-31 SIGEP asociado." | ☐ |
| 3.15 | RC, pestaña 3 | **Adjudicar seleccionada** | Ahora sí: "Adjudicada." | ☐ |
| 3.16 | RC, pestaña 5 | COMPRA, CUCE `EJEMPLO-CUCE-003`, plazo `15`, lugar `Almacen Municipal`. **Generar Orden** | `OC-2026-000003` | ☐ |
| 3.17 | RC, pestaña 1 | **Generar C-1 (PDF)** (desde la pestaña 1) | La columna CHB del C-1 muestra `EXCEPCION` en los 3 ítems; total 17.500,00 | ☐ |
| 3.18 | PF, pestaña 4 | **Consultar saldo** de la partida `43120` | **32,700.00** | ☐ |

### E.7 Ejemplo 4 — Orden de Servicio, saldo insuficiente, reversiones y anulación (Bs 28.000)

**Objetivo:** el Módulo 3 en profundidad: validación de saldo, estructura inexistente, doble C-31, validaciones del número de SIGEP, reversión parcial y total, el efecto sobre la adjudicación, y una **Orden de Servicio** que se anula y se emite de nuevo.

**Datos del caso**

| Dato | Valor |
| :-- | :-- |
| Solicitud | DA `01`, UE `001`. Justificación: `Mantenimiento correctivo de las instalaciones electricas del edificio municipal` |
| Ítem único | `72101500` Mantenimiento de instalaciones eléctricas del edificio municipal, unidad `Servicio`, cantidad 1, precio 28000.00 |
| Cotización A | NIT `7070707070`, `ELECTRO SERVICIOS EJEMPLO S.R.L.`, 27500.00, cumple |
| Cotización B | NIT `8080808080`, `INSTALACIONES BOLIVIA EJEMPLO`, 28900.00, cumple |
| Cotización C | NIT `9090909090`, `MANTENIMIENTO INTEGRAL EJEMPLO`, 29300.00, cumple |
| Partida | `25800` (saldo inicial 30.000,00) |
| SIGEP | `250004` (primer C-31) y `250005` (segundo) |
| Orden | SERVICIO, CUCE `EJEMPLO-CUCE-004`, plazo 20 días, lugar `Edificio Municipal` |

**Cifras de control:** referencial **28.000,00** · recomendada A **27.500,00** · saldo 25800 tras el C-31 definitivo: **2.500,00**.

| N° | Rol y pantalla | Qué hacer (datos exactos) | Resultado esperado | ☐ |
| :-- | :-- | :-- | :-- | :-: |
| 4.1 | US `us_ejemplo` | Cree `SOL-2026-000004`, agregue el ítem, envíe a cotización | Modalidad con cuadro comparativo; estado `EN_COTIZACION` | ☐ |
| 4.2 | RC `rc_ejemplo` | Evalúe el ítem 1 por catálogo (`SI`). Registre las tres cotizaciones y **Evaluar cuadro** | "Recomendada: ELECTRO SERVICIOS EJEMPLO S.R.L. por Bs 27,500.00"; estado `EVALUADA` | ☐ |
| 4.3 | RC | **Cuadro comparativo (PDF)** | 3 ofertas; A recomendada; variación de A −1,8 % | ☐ |
| 4.4 | PF `pf_ejemplo`, pestaña 4 | Partida `25800`, importe `31000`, **Agregar linea**, **Emitir C-31 Preventivo** | Rechazo: "Saldo insuficiente en partida 25800: disponible Bs 30,000.00, requerido Bs 31,000.00". Las líneas se limpian y no se reserva nada | ☐ |
| 4.5 | PF | Partida `99999`, importe `1000`, agregar línea y emitir | Rechazo: "La estructura programatica (partida 99999) no existe en el presupuesto de la gestion." | ☐ |
| 4.6 | PF | Partida `25800`, importe `27500`, agregar línea y **Emitir C-31 Preventivo** | `C31P-2026-000004`. Saldo 25800 = 2.500,00 | ☐ |
| 4.7 | PF | Intente emitir **otro** C-31 para la misma solicitud (partida `25800`, importe `100`) | Rechazo: "La solicitud debe estar EVALUADA … (estado: PRESUPUESTADA)": una solicitud ya presupuestada no admite otra reserva | ☐ |
| 4.8 | PF | Asocie el SIGEP `250004` | "C-31 SIGEP asociado." | ☐ |
| 4.9 | PF | **Reversion parcial**: N° `C31P-2026-000004`, línea `1`, monto `500`, motivo `Correccion del importe reservado` | Registrada. Estado del preventivo `REVERTIDO_PARCIAL`; vigente 27.000,00 | ☐ |
| 4.10 | RC | Cargue la solicitud, seleccione la cotización A y **Adjudicar seleccionada** | Rechazo: "El preventivo … no cubre el monto cotizado." (27.000 < 27.500) | ☐ |
| 4.11 | PF | **Reversion total**: mismo N°, motivo `Reserva insuficiente: se reemite el preventivo`. Confirme | Registrada. La solicitud vuelve a `EVALUADA`; saldo de 25800 = **30,000.00** | ☐ |
| 4.12 | PF | **C-31 (PDF)** del `C31P-2026-000004` | Estado `REVERTIDO_TOTAL`: importe 27.500,00, revertido 27.500,00, vigente 0,00 | ☐ |
| 4.13 | PF | Emita un C-31 nuevo: partida `25800`, importe `27500` | `C31P-2026-000005` | ☐ |
| 4.14 | PF | Intente asociar SIGEP `250004` | Rechazo por número repetido ("…ya esta asociado a otro preventivo") | ☐ |
| 4.15 | PF | Asocie SIGEP `250005` | "C-31 SIGEP asociado." | ☐ |
| 4.16 | RC | **Adjudicar seleccionada** (cotización A) | "Adjudicada." | ☐ |
| 4.17 | RC, pestaña 5 | Tipo **SERVICIO**, CUCE `EJEMPLO-CUCE-004`, plazo `20`, lugar `Edificio Municipal`. **Generar Orden** | `OS-2026-000001` (la numeración de servicios es independiente de la de compras) | ☐ |
| 4.18 | RC | **Orden (PDF)** | Título **"ORDEN DE SERVICIO"**, monto 27.500,00 en letras "VEINTISIETE MIL QUINIENTOS" | ☐ |
| 4.19 | PF | Intente **Reversion total** de `C31P-2026-000005` con motivo `Intento de reversion con orden vigente` | Rechazo: "Existe una Orden emitida con cargo a este preventivo; anule la Orden primero." | ☐ |
| 4.20 | RC, pestaña 5 | Motivo `Error en el plazo de ejecucion consignado`, pulse **Anular Orden** y confirme | Orden anulada; estado de la solicitud `ADJUDICADA`; el número de Orden desaparece de la pantalla | ☐ |
| 4.21 | RC, pestaña 5 | Plazo `25`, mismo CUCE y lugar. **Generar Orden** | `OS-2026-000002` | ☐ |
| 4.22 | RC | **Orden (PDF)** | Orden de Servicio con plazo **25 días** | ☐ |
| 4.23 | PF | **Consultar saldo** de la partida `25800` | **2,500.00** | ☐ |

### E.8 Ejemplo 5 — Seguridad, recepción con multa, anulaciones, importación con observaciones y auditoría

**Objetivo:** cerrar el recorrido: contraseñas y bloqueo, aislamiento por DA, recepción **observada** y luego **conforme** con retraso y multa, límites de anulación, importaciones con filas rechazadas y revisión de la auditoría.

**Cifras de control de la recepción** (Orden `OC-2026-000002` del Ejemplo 2, monto 24.800,00, plazo 30 días, emitida hace 45 días): fecha límite = emisión + 30 → **15 días de retraso** · multa = 24.800 × 3 por mil × 15 = **1.116,00** (menor que el tope de 10 % = 2.480,00) · neto a pagar = 24.800,00 − 1.116,00 = **23.684,00**.

| N° | Rol y pantalla | Qué hacer (datos exactos) | Resultado esperado | ☐ |
| :-- | :-- | :-- | :-- | :-: |
| 5.1 | ADM `admin`, menú 6 | Mostrar hojas. En `ORDENES_GASTO` busque la fila de `OC-2026-000002`, compruebe `PlazoDias` = 30 y cambie **FechaEmision** a la fecha de **hace 45 días** (HOY−45) | Celda actualizada. *(Es la única forma de simular un retraso sin esperar; solo en la copia de ensayo)* | ☐ |
| 5.2 | ADM, menú 7 | Ocultar y proteger | Hojas ocultas | ☐ |
| 5.3 | ADM, menú 3 | Cambie la contraseña de `us_dos` a `Nueva#Clave2026B` | "Contrasena actualizada." | ☐ |
| 5.4 | Inicio de sesión | Entre como `us_dos` con la contraseña **antigua** (`Ejemplo#2026A`) | Rechazo "Usuario o contrasena incorrectos." (intento 1) | ☐ |
| 5.5 | Inicio de sesión | Dos intentos más erróneos | Al tercero: "Usuario bloqueado por intentos fallidos." | ☐ |
| 5.6 | Inicio de sesión | Entre con la contraseña **correcta** (`Nueva#Clave2026B`) | "Usuario inactivo o bloqueado. Contacte al Administrador." | ☐ |
| 5.7 | ADM, menú 2 | Desbloquee `us_dos` | "Usuario desbloqueado." | ☐ |
| 5.8 | Inicio de sesión | Entre como `us_dos` con `Nueva#Clave2026B` | Ingresa a la pantalla principal (rol US, DA 02) | ☐ |
| 5.9 | US `us_dos`, pestaña 1 | Escriba `SOL-2026-000001` en **Solicitud N°** y pulse **Cargar** | Rechazo: "Sin acceso a solicitudes de otra Direccion Administrativa." | ☐ |
| 5.10 | US `us_dos`, pestaña 1 | Intente **Crear solicitud** con DA `01` | Rechazo: "Solo puede crear solicitudes de su propia Direccion Administrativa." | ☐ |
| 5.11 | US `us_dos`, pestaña 1 | DA `02`, UE `001`, justificación `Solicitud de prueba para verificar la anulacion de tramites`. Cree y agregue el ítem `44121701`, `Cinta adhesiva`, `Unidad`, cantidad 5, precio 10 | Se asigna `SOL-2026-000005`; referencial 50,00 | ☐ |
| 5.12 | US `us_dos`, pestaña 5 | Motivo `Prueba de anulacion de una solicitud en borrador`, **Anular solicitud** y confirme | Estado `ANULADA` (se ve al cargarla de nuevo) | ☐ |
| 5.13 | RC `rc_ejemplo`, pestaña 5 | Cargue `SOL-2026-000001` (Ejemplo 1, ya recibida). Motivo `Intento de anular solicitud con orden`, **Anular solicitud** | Rechazo: "Hay una Orden vigente; anulela primero." | ☐ |
| 5.14 | RC, pestaña 5 | Cargue `SOL-2026-000002`. Fecha recepción **HOY**, **sin** marcar conforme, observaciones `Dos de las cinco computadoras llegaron sin garantia ni manual` y **Registrar recepcion** | `REC-2026-000002` (observada). La Orden **sigue** `EMITIDA` | ☐ |
| 5.15 | RC, pestaña 5 | Intente registrar otra recepción **sin** marcar conforme y **sin** observaciones | Rechazo: "Detalle las observaciones (min. 10 caracteres)." | ☐ |
| 5.16 | RC, pestaña 5 | Fecha **mañana**, conforme marcado | Rechazo: "La fecha de recepcion no puede ser futura." | ☐ |
| 5.17 | RC, pestaña 5 | Fecha HOY, marque **Recepcion CONFORME**, observaciones vacías, **Registrar recepcion** | `REC-2026-000003`; la Orden pasa a `RECIBIDA` | ☐ |
| 5.18 | RC, pestaña 5 | **Acta de recepcion (PDF)** | Acta: **15 días de retraso**, multa **1.116,00**, resultado CONFORME, monto de la Orden 24.800,00 y neto a pagar **23.684,00** | ☐ |
| 5.19 | RC, pestaña 5 | Cargue `SOL-2026-000004` y pulse **Anular Orden** con motivo `Prueba de anulacion tras reemision` | Se anula la `OS-2026-000002` y la solicitud vuelve a `ADJUDICADA` (puede emitirse otra, pero no es necesario) | ☐ |
| 5.20 | PF `pf_ejemplo`, pestaña 5 | Observe los botones **Generar Orden**, **Anular Orden**, **Registrar recepcion** | **Deshabilitados** (el rol PF no los puede usar) | ☐ |
| 5.21 | RC `rc_ejemplo`, pestaña 4 | Observe **Emitir C-31 Preventivo** y las reversiones | **Deshabilitados** (el rol RC no reserva presupuesto) | ☐ |
| 5.22 | ADM, menú 4 | Importar `catalogo_actualizacion.csv` | "Nuevos: 1 / Actualizados: 1 / Rechazados: 0" | ☐ |
| 5.23 | ADM, menú 5 | Importar `presupuesto_con_duplicado.csv` | "Nuevos: 1 / Actualizados: 0 / Rechazados: 1" y el detalle "Linea 2: estructura/clave repetida, no se importa." | ☐ |
| 5.24 | ADM, menú 6 | Mostrar hojas. En `PRESUPUESTO` compruebe que la partida `31120` **no** cambió su aprobado (12.000,00) y que `22100` quedó con 5.000,00. En `CAT_CHB` compruebe la descripción actualizada del `44121600` | Datos correctos: el duplicado no pisó lo existente | ☐ |
| 5.25 | ADM, menú 6 | En `PRESUPUESTO` verifique `PreventivoComprometido` y `SaldoDisponible` de cada partida | Comprometido / saldo: 31120 → 1.080,00 / 10.920,00 · 43120 → 27.300,00 / 32.700,00 · 43130 → 15.000,00 / 65.000,00 · 25800 → 27.500,00 / 2.500,00 · 22100 → 0,00 / 5.000,00 | ☐ |
| 5.26 | ADM, menú 7 y menú 8 | Proteger y luego ver auditoría | Filas de todas las acciones realizadas (ver tabla siguiente) | ☐ |

Nota 5.25: el comprometido de 25800 sigue en 27.500,00 aunque la Orden de servicio se haya anulado en el paso 5.19, porque el C-31 vigente mantiene la reserva; si no habrá nueva Orden, Presupuesto debe revertirlo. El de 43120 es 9.800,00 + 17.500,00 = 27.300,00.

**Acciones que debe encontrar en `AUDITORIA` al terminar** (con usuario, rol, fecha y hora):

| Acción | Cuándo aparece |
| :-- | :-- |
| `LOGIN_OK`, `LOGIN_FALLIDO`, `LOGIN_BLOQUEO`, `LOGOUT` | Ingresos, intentos erróneos y bloqueo de `us_dos` |
| `USUARIO_CREADO`, `PASSWORD_CAMBIADO`, `USUARIO_DESBLOQUEADO` | Ejemplos 0 y 5 |
| `IMPORT_CSV` | Cuatro importaciones |
| `SOLICITUD_CREADA`, `SOLICITUD_ESTADO`, `SOLICITUD_ANULADA` | Cada cambio de estado de las solicitudes |
| `CHB_EVAL` | Cada evaluación de ítem, incluidas las rechazadas del Ejemplo 3 |
| `COTIZACION_REGISTRADA` | 8 cotizaciones |
| `C31_EMITIDO`, `C31_ASOCIADO`, `C31_REV_PARCIAL`, `C31_REV_TOTAL` | Ejemplos 1, 2, 3 y 4 |
| `ORDEN_EMITIDA`, `ORDEN_ANULADA`, `RECEPCION` | Ejemplos 1 a 5 |
| `DOC_GENERADO` | Cada PDF emitido |
| `SHOW_DB`, `PROTECT_DB` | Cada vez que el administrador mostró o protegió las hojas |

### E.9 Resumen de documentos que debe haber en la carpeta `PDF`

| Documento | Ejemplo y paso | Cantidad mínima |
| :-- | :-- | :-: |
| Formulario C-1 | 1.6, 2.2, 3.17 | 3 |
| Cuadro comparativo | 1.24, 2.6, 4.3 | 3 |
| Justificación de excepción CHB | 3.12 | 1 |
| C-31 Preventivo | 1.21, 2.10, 4.12 | 3 |
| Orden de Compra | 1.18, 2.14 | 2 |
| Orden de Servicio | 4.18, 4.22 | 2 |
| Acta de recepción | 1.23, 5.18 | 2 |

Revise en cada PDF: membrete con el nombre de la entidad de ejemplo, número de trámite, fechas, totales, montos en letras, firmas y pie con el usuario que lo generó.

### E.10 Criterio de aceptación y registro

La prueba de aceptación manual se da por aprobada cuando **todos los resultados esperados coinciden** y los documentos de E.9 están completos y legibles. Registre:

| Dato | Valor |
| :-- | :-- |
| Fecha de la prueba | |
| Versión del paquete / commit | |
| Equipo y versión de Excel | |
| Realizada por | |
| Pasos con diferencia (N° y descripción) | |
| Resultado final | ☐ Aprobado  ☐ Aprobado con observaciones  ☐ No aprobado |
| Firma de Sistemas / RC / PF / ADM | |

**Limitaciones conocidas que verá durante las pruebas** (no son errores de uso):

- Un **empate** en el precio más bajo detiene el trámite: el sistema avisa y no elige; hoy no existe una opción para resolverlo. La salida es anular la solicitud y repetirla, o pedir una mejora al desarrollo.
- Los ítems, cotizaciones y reservas **no se editan ni se borran** una vez cargados; se corrigen anulando, o con reversión en el caso del C-31.
- El número de acta que se muestra tras registrar una recepción no se puede volver a consultar desde la pantalla: anótelo (queda también en la hoja `RECEPCIONES`).
- Para el retraso en la recepción hace falta que la Orden haya sido emitida en el pasado; en las pruebas se simula con el paso 5.1.
