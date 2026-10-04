# SIC-MUNI — Manual de implementación

Sistema Integrado de Contrataciones Municipales (Excel/VBA). Este manual cubre instalación, puesta en marcha,
operación por rol, mantenimiento y solución de problemas.

> El sistema fue escrito y revisado de forma estática; **nunca se había ejecutado en Excel** antes de este manual.
> Por eso el instalador corre una batería de pruebas automáticas (sección 4). Si alguna falla, no ponga el sistema
> en producción: envíe `resultado_pruebas.txt` para corregirlo.

## 1. Requisitos

| Requisito | Detalle |
| :-- | :-- |
| Sistema operativo | Windows 10/11 |
| Excel | Escritorio, 2010 o superior (no Mac, no Excel web). Fórmula `AGGREGATE` requiere ≥ 2010 |
| .NET Framework 3.5 | Panel de control → Programas → *Activar o desactivar características de Windows*. Lo usa el hash SHA-256 |
| Permisos | Usuario con permiso de escritura en `C:\SIC-MUNI`; no requiere administrador salvo para habilitar .NET 3.5 |
| Impresora | No es obligatoria; el PDF usa el exportador de Excel |
| Uso | **Un solo usuario a la vez** sobre el mismo archivo (Excel no maneja escritura concurrente) |

## 2. Instalación automática (recomendada)

1. Descargue el repositorio (GitHub → rama `claude/tender-einstein-76nc7n` → *Code → Download ZIP*) y descomprímalo en cualquier carpeta. Si Windows bloquea el ZIP: clic derecho → Propiedades → *Desbloquear*, antes de descomprimir.
2. Cierre todos los libros de Excel.
3. Doble clic en `sic-muni\instalar\Instalar.cmd`.
4. Responda lo que pide: contraseña del administrador (≥ 10 caracteres con mayúsculas, minúsculas y números).
5. Excel se abre visible y trabaja solo. **No lo toque.** Si aparece un cuadro de error de VBA, anote el texto y la línea resaltada.
6. Al terminar verá `LISTO` y el resultado de las pruebas (`PASS`/`FAIL`).

Qué hace el instalador: crea `C:\SIC-MUNI\SIC-MUNI.xlsm`; copia `vba\`; genera una clave de protección aleatoria
(`CLAVE_PROTECCION.txt`); habilita temporalmente el acceso al modelo de objetos VBA (y lo restaura); importa los
módulos; crea tablas, configuración, usuario administrador y las 6 plantillas; construye los formularios; instala los
eventos de `ThisWorkbook`; carga datos demo; **ejecuta las pruebas**; si todo pasa, borra los datos demo y de prueba y
protege el libro.

Opciones: `Instalar.cmd -Destino D:\SIC-MUNI -AdminUsuario jperez`; `-Reemplazar` reinstala (guarda copia `.bak`).

Después de instalar: **mueva `CLAVE_PROTECCION.txt` a un lugar seguro y bórrelo de `C:\SIC-MUNI`.**

## 3. Instalación manual (si el instalador falla)

Siga el apartado *Instalación* del `README.md` (pasos 1-8). Resumen del orden, que importa:
importar todos los `.bas` **menos `modMain`** → `InstalarSistema` → `CargarDatosDemo` → `ConstruirFormularios` →
importar `modMain` y pegar `ThisWorkbook.code.txt` → `modSelfTest.EjecutarPruebas` → `modSelfTest.LimpiarDatosPrueba` → `modCore.ProtectDB`.

## 4. Pruebas automáticas (`modSelfTest`)

Se ejecutan sin interfaz, con usuarios `t_us`, `t_rc`, `t_pf` y datos demo. Resultado en `C:\SIC-MUNI\resultado_pruebas.txt`.
Cubren (≈ 80 verificaciones):

| Bloque | Qué verifica |
| :-- | :-- |
| Seguridad | SHA-256 contra valor conocido, hash con sal, política de contraseñas, login, bloqueo a los 3 intentos, desbloqueo, matriz de permisos por rol |
| Reglas | Modalidad por monto (15.000 / 30.000 / 60.000), cotizaciones requeridas, monto en literal, redondeo |
| CHB | Código en catálogo con/sin ficha, fuera de catálogo, excepción incompleta/completa/fecha futura |
| Flujo completo | Solicitud → CHB → cotización → cuadro → C-31 (rechazo por saldo) → adjudicación → exigencia de C-31 SIGEP → Orden → bloqueo de reversión → anulación → reemisión → recepción con 10 días de retraso y multa de 19,50 |
| Reversiones | Parcial y total devuelven saldo; no se revierte dos veces; anulación de solicitud |
| Documentos | Volcado a las 6 plantillas, fórmulas (totales, neto a pagar, cláusulas con rangos con nombre), filas ocultas, exportación PDF |
| Importación | CSV de catálogo (`;`, campos entre comillas, upsert) y de presupuesto (duplicados rechazados) |

Criterio de aceptación: **0 FAIL**. Con fallos el instalador conserva los datos de prueba para diagnosticarlos.

## 5. Puesta en marcha (después de instalar)

1. Abra `C:\SIC-MUNI\SIC-MUNI.xlsm` → *Habilitar contenido* → aparece el login.
2. Ingrese como administrador. Aparece el **Menú Administrador** (1 crear usuario, 2 desbloquear, 3 cambiar contraseña, 4 importar catálogo, 5 importar presupuesto, 6 mostrar hojas de datos, 7 ocultar y proteger, 8 auditoría, 0 cerrar sesión). Para reabrirlo: Alt+F8 → `MenuAdmin`. El ADM no opera transacciones.
3. Menú → opción **1** por cada persona: usuario, nombre, rol (`US`, `RC`, `PF`, `ADM`), código de DA y contraseña inicial.
   Un usuario de rol `US` solo ve solicitudes de su propia DA.
4. Menú → opción **6** para mostrar las hojas de datos y editar `CONFIG`. Al terminar, opción **7** (o cierre y reabra el libro).
5. Cargue el **catálogo CHB** y el **presupuesto** con las opciones **4** y **5** (CSV UTF-8, columnas con los nombres de la hoja; ver README).
6. Proteja el proyecto VBA: Alt+F11 → clic derecho en *VBAProject* → *Propiedades → Protección* → *Bloquear proyecto para su visualización* + contraseña.
7. Configure copia de seguridad (sección 8).

### Parámetros de `CONFIG`
| Clave | Por defecto | Significado |
| :-- | :-- | :-- |
| Entidad | GOBIERNO AUTONOMO MUNICIPAL DE (COMPLETAR) | Membrete de los documentos |
| Gestion | año actual | Gestión fiscal; se usa en correlativos y en la búsqueda presupuestaria |
| CodDA / CodUE | vacío | Códigos de la entidad |
| TopeContratacionMenor | 50000 | Bs. **Verificar** contra la norma vigente |
| TopeSinCuadroComparativo | 20000 | Bs. Sobre este monto exige invitación y cuadro comparativo |
| MinCotizaciones | 3 | Cotizaciones mínimas sobre el tope sin cuadro |
| TolerCotizacionPct | 20 | % sobre el referencial que dispara un aviso |
| CHB_NivelMatch | 8 | Dígitos UNSPSC a comparar (8 exacto, 6 familia) |
| PatronCodigoExcepcion | `*` | Patrón `Like` del Código Único de Excepción. **Ajustar al formato real** |
| MinCaracteresJustificacion | 80 | Longitud mínima de la justificación de excepción |
| ExigirC31SIGEPParaOrden | SI | Si `SI`, la Orden exige el N° de C-31 de SIGEP asociado |
| PenalidadPorMil / PenalidadMaxPct | 3 / 10 | Multa por mil por día de retraso y su tope. **Verificar** con la norma/reglamento |
| MaxIntentosLogin | 3 | Intentos antes del bloqueo |
| TimeoutSesionMin | 20 | Minutos de inactividad antes de cerrar la sesión |

## 6. Operación por rol

| Rol | Pasos |
| :-- | :-- |
| **US** | Pestaña 1: *Crear solicitud* (DA, UE, justificación ≥ 20 caracteres) → agregar ítems (código UNSPSC, descripción, cantidad, precio referencial; aparece la alerta CHB si corresponde) → *Enviar a cotización* → *Generar C-1 (PDF)* |
| **RC** | Cargar la solicitud por su N°. Pestaña 2: evaluar cada ítem CHB (por catálogo, o fuera de catálogo con excepción completa). Pestaña 3: registrar cotizaciones → *Evaluar cuadro* → *Cuadro comparativo (PDF)* → tras la reserva de PF, *Adjudicar*. Pestaña 5: *Generar Orden*, PDF, *Registrar recepción*, *Acta de recepción*; anulaciones |
| **PF** | Pestaña 4: ingresar la estructura programática de cada línea → *Consultar saldo* → *Agregar línea* → *Emitir C-31 Preventivo* → registrarlo en SIGEP y *Asociar C-31* con su número → reversiones parcial/total con motivo → *C-31 (PDF)* |
| **ADM** | Usuarios, desbloqueos, importaciones, mantenimiento, consulta de `AUDITORIA` |

Estados de la solicitud: `BORRADOR → EN_COTIZACION → EVALUADA → PRESUPUESTADA → ADJUDICADA → ORDEN_EMITIDA` (o `ANULADA`).
Bloqueos principales: monto sobre el tope no pasa a cotización; la Orden exige CHB habilitado, adjudicación, C-31 vigente que
cubra el monto y (si está activo) C-31 asociado a SIGEP; un C-31 con Orden vigente no se revierte.

## 7. Mantenimiento

- **Cambio de contraseña:** el propio usuario o el ADM mediante `CambiarPassword` (desde el editor, Ctrl+G).
- **Usuario bloqueado:** ADM → `AdminDesbloquear`.
- **Inicio de gestión:** editar `Gestion` en `CONFIG`, importar el presupuesto nuevo y, si desea reiniciar la numeración, vaciar las filas de la hoja `SECUENCIAS` (solo con todos los procesos cerrados). Los correlativos incluyen la gestión.
- **Auditoría:** hoja `AUDITORIA` (fecha, usuario, rol, acción, detalle). No se borra desde el sistema.
- **Actualizar el sistema:** reinstale con `-Reemplazar` en una copia, y migre datos importando CSV; no sobrescriba el libro en uso.

## 8. Respaldo y seguridad

- Copia diaria de `SIC-MUNI.xlsm` (cerrado) a una carpeta de red o medio externo, con versiones por fecha. Guarde también `C:\SIC-MUNI\PDF\`.
- El libro contiene datos de la entidad: restrinja el acceso a la carpeta con permisos de Windows.
- La protección de hojas y del proyecto VBA **disuade pero no es criptografía**. No lo trate como un sistema multiusuario seguro.
- No comparta usuarios. Cambie la contraseña del ADM al implantar.

## 9. Solución de problemas

| Síntoma | Causa probable | Solución |
| :-- | :-- | :-- |
| `El hash SHA-256 no funciona` / error al iniciar sesión | .NET 3.5 no habilitado | Habilitarlo (sección 1) y reinstalar con `-Reemplazar` |
| `No se puede obtener acceso mediante programación al proyecto` | Confianza del modelo de objetos VBA | Archivo → Opciones → Centro de confianza → Configuración de macros → marcar *Confiar en el acceso al modelo de objetos de proyectos de VBA* |
| Cuadro `Error de compilación` durante la instalación | Error en el código | Anote módulo, procedimiento y línea resaltada y envíelos |
| `Variable no definida: frmLogin` | `modMain` importado antes de crear formularios | Ejecutar `ConstruirFormularios` y recién importar `modMain` |
| Hojas no visibles | Están ocultas a propósito | ADM → `AdminMantenimiento` |
| `No se pudo exportar el PDF` | Excel sin exportador PDF o carpeta sin permisos | Verificar permisos de `C:\SIC-MUNI\PDF`; instalar el complemento PDF en Excel 2010 |
| Fórmulas en documentos muestran `#NOMBRE?` | Rangos con nombre dañados | Ejecutar `modSetupTemplates.BuildTemplates` |
| Sesión expirada | Inactividad | Volver a ingresar |

## 10. Lista de verificación previa a producción

- [ ] Pruebas automáticas con 0 FAIL.
- [ ] `CONFIG` completada (Entidad, DA, UE, Gestión).
- [ ] Topes, penalidades, formato del código de excepción y artículos citados **validados por Asesoría Legal**.
- [ ] Catálogo CHB y presupuesto reales importados y cotejados contra los reportes oficiales.
- [ ] Usuarios creados por rol; contraseña del ADM cambiada.
- [ ] Prueba de aceptación con un caso real en un libro de ensayo (no el definitivo).
- [ ] Proyecto VBA bloqueado con contraseña; `CLAVE_PROTECCION.txt` resguardada y borrada del equipo.
- [ ] Respaldo automático configurado y restauración probada.
- [ ] Capacitación a US, RC, PF y ADM.
