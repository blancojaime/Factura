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

Las pruebas automáticas no recorren los formularios. Antes de producción realice, **en una copia del libro**, un caso completo con las pantallas, con tres usuarios de prueba (US, RC, PF), y registre el resultado:

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
