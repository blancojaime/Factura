# SIGAA — Sistema Integrado de Gestión de Almacenes, Combustible y Activos Fijos

Consolida en **un solo sistema** (web y escritorio) los tres aplicativos Excel/VBA del GAM de Calamarca:

| Aplicativo original | Módulo SIGAA |
|---|---|
| `Sistema_Almacenes_DEMO.xlsm` — bienes de consumo | **Almacenes** (`/api/alm`) |
| `SICOMB_CAPACITACION.xlsm` — control de combustible | **Combustible** (`/api/com`) |
| `Sistema_Activos_Fijos_DEMO.xlsm` — activos fijos | **Activos Fijos** (`/api/af`) |

Los tres comparten maestros (funcionarios, unidades, proveedores, proyectos, aperturas, partidas), configuración de la entidad y firmantes, usuarios/roles, numeración correlativa por gestión y una única bitácora de auditoría.

## Tecnología

- **TypeScript** en todo el sistema.
- **Servidor**: Node 22 + Fastify + Knex. Base de datos **SQLite** (local/escritorio) o **PostgreSQL** (servidor): se elige con `DATABASE_URL`; el mismo código y las mismas pruebas corren en ambas.
- **Web**: React 18 + Vite (SPA en español, tema claro/oscuro, adaptable a pantallas pequeñas).
- **Escritorio**: Electron (`desktop/`) que ejecuta el servidor en el equipo con SQLite local.
- **Salidas**: PDF (pdfkit) y Excel (exceljs) generados desde los mismos datos que ve la pantalla.
- **Seguridad**: sesiones JWT, claves con scrypt, cambio obligatorio de la clave inicial, roles por módulo, bitácora de cada operación.

## Puesta en marcha

```bash
cd sigaa
npm install
npm run seed            # crea sigaa.sqlite en server/data con los datos demo importados de los 3 libros
npm run build           # compila web y servidor
npm start               # http://localhost:3000   (admin / Admin2026 → exige cambiar la clave)
```

Desarrollo: `npm run dev:server` y `npm run dev:web` (Vite en :5173 con proxy a la API).

**PostgreSQL**: `DATABASE_URL=postgres://usuario:clave@host:5432/sigaa npm start` (crea el esquema automáticamente). `SIGAA_DEMO=1` carga los datos demo si la base está vacía. Ver `.env.example`.

**Docker (servidor con PostgreSQL)**: `SIGAA_JWT_SECRET=<cadena-larga> docker compose up -d`.

**Escritorio (Windows/Linux/macOS)**:
```bash
npm run build && npm run desktop:install
npm run desktop            # abre la ventana; datos en la carpeta del usuario (SIGAA/sigaa.sqlite)
npm run desktop:dist       # genera el instalador con electron-builder (reconstruye better-sqlite3 para Electron)
```

## Roles

`ADMIN` (todo, usuarios, configuración, respaldo) · `ALMACEN`, `COMBUSTIBLE`, `ACTIVOS` (operan su módulo) · `CONSULTA` (solo lectura). Un usuario puede tener varios roles. Los catálogos compartidos los edita quien tenga rol en el módulo dueño del catálogo.

## Equivalencias con los sistemas originales

### Almacenes
| Hoja / macro original | En SIGAA |
|---|---|
| INICIO (indicadores y alertas) | Tablero general (mismos indicadores: 35 ítems, Bs 71.698 de existencias, 2 bajo mínimo, 1 por vencer…) |
| CATALOGO, BD_CATALOGO | Catálogo de ítems (código `Grupo-Subgrupo-Correlativo`) |
| INGRESO (CGI), DT_ING* | Ingresos: validaciones del art. 8-l/13-IV/31-f, documentos de respaldo `(*)`, confirmación que da de alta lotes |
| SALIDA (vale), DT_SAL* | Salidas: reglas del Manual 11 (plazo día 1–25, máx. pedidos/mes, cantidades elevadas, excepción), Vo.Bo., entrega PEPS/FEFO sin lotes vencidos |
| KARDEX, DT_MOV, DT_LOTES | Existencias y kardex valorado por lotes |
| INVENTARIO | Inventario físico (conteo ciego, corte de documentación, sobrantes → CGI de ajuste, faltantes → acta de reposición o baja) |
| BAJAS, BD_PASOS, BD_CAUSALES | Expedientes de baja con trámite por grupo de causal (A–D), RA obligatoria, plazo SICOES de 15 días hábiles |
| TRANSFERENCIA | Transferencias entre bodegas (conservan lote, vencimiento y costo) |
| REPOSICION | Cálculo de reposición y requerimiento de compra |
| SEGURIDAD, BD_EXTINT, BD_SEGUROS | Inspecciones (16 criterios), extintores y seguros con alertas |
| REPORTES (11) | `alm-inventario`, `alm-ingresos`, `alm-salidas`, `alm-por-unidad`, `alm-stock-minimo`, `alm-vencimientos`, `alm-sin-movimiento`, `alm-semestral`, `alm-por-partida`, `alm-catalogo`, `alm-bitacora` (PDF y Excel) |
| CIERRE | 10 verificaciones y generación de nueva gestión en la misma base (saldo inicial por lote) |
| IMPRESION (PDF) | CGI, verificación de documentos, vale, certificación de inexistencia, kardex, hoja de conteo, actas de inventario/reposición, inventario valorado, 8 documentos del expediente de baja, acta de transferencia, requerimiento, acta de inspección, nota de mantenimiento |

### Combustible
| Hoja / macro original | En SIGAA |
|---|---|
| MENU / TABLERO | Tablero de control (monto, litros, vales, contratos, descargos vencidos, ejecución por apertura) |
| RECEPCION, LOTES, CONTRATOS | Recepción de vales por contrato y rango de numeración (prepago/postpago, saldo del contrato) |
| EMITIR, EMISIONES | Emisión con todos los controles: litros máx. (16 L/día hábil ejecutivo; km×rendimiento operativo), licencia vigente, descargos vencidos, capacidad de tanque/turril, lectura no retrocede |
| DESCARGO, DESCARGOS | Descargo (Anexo 3): bitácora, vales de la emisión, rendimiento vs tolerancia → Conforme/Observado, devolución automática de vales sin usar |
| MOV_VALES | Devolución, anulación, vencimiento y extravío por rango; anulación de emisión |
| TURRILES | Ingreso por compra directa y despacho con costo promedio |
| VIAJE, VIAJES_DET | Viajes con fondo en avance (Anexos 4 y 6) |
| CONCILIACION, COBROS | Conciliación: se pega o carga el detalle del proveedor; resultados `CONFORME`, `DUPLICADO`, `NO REGISTRADO`, `NO ENTREGADO`, `MONTO DIFERENTE`, `PLACA DIFERENTE`, `SIN DESCARGO`, `NO COBRADO`… |
| INFORME | Informe mensual de descargo (Anexo 5) en PDF/Excel |
| REPORTES / CRONOGRAMA | `com-existencias`, `com-kardex`, `com-emisiones`, `com-consumo`, `com-turriles`, `com-contratos`, `com-rendimiento`, `com-pendientes`, `com-cronograma`, `com-viajes`, `com-informe-mensual` |
| IMP_VALE, planillas | Solicitud (Anexo 1) + vale (Anexo 2), planilla de descargo, notas de ingreso, actas, conciliación, viaje |

### Activos Fijos
| Hoja / macro original | En SIGAA |
|---|---|
| INICIO | Indicadores (total, almacén, asignados, bajas, valor, stickers pendientes, sin foto, solicitudes) |
| SOLICITUD | Solicitudes con saldo en almacén y formulario «sin existencia» |
| INGRESO | Ingreso (OC/contrato/donación/transferencia/inventario inicial), alerta de valor mínimo (RI-02), memorándum, acta de conformidad, formulario |
| CODIFICAR | Código `EEE-AA-CCXXX-NN` (15 caracteres, límite VSIAF), correlativo por ambiente (máx. 99), codificación directa para inventario inicial |
| FICHA | Ficha técnica con campos por cuenta (BD_CAMPOS), 4 fotografías, navegación |
| ETIQUETAS / STICKERS | Hoja carta de 30 stickers y marca de impresos |
| ASIGNAR | Asignación con preselección según solicitud y acta de entrega |
| MOVIMIENTOS | Devolución, transferencia y baja con acta y kardex por activo |
| REPORTES | `af-contabilidad` (informe semanal), `af-inv-funcionario`, `af-inv-ubicacion`, `af-kardex`, `af-resumen-cuentas` (con depreciación lineal), `af-incompletos`, `af-inventario-general` |

## Qué se mejoró al consolidar

- **Multiusuario y concurrencia** real (transacciones atómicas) en lugar de un libro Excel por equipo.
- **Maestros únicos**: un proveedor, funcionario o unidad se registra una vez para los tres módulos.
- **Entidad y firmantes únicos** (los tres libros tenían autoridades distintas en sus datos demo; se usaron las del libro de Almacenes).
- **Vehículo ↔ activo fijo**: el vehículo de combustible guarda el código del activo fijo.
- **Cierre de gestión sin copiar libros**: se abre la nueva gestión en la misma base con saldos iniciales por lote.
- **Auditoría uniforme** (`core_bitacora`) y numeración por gestión con series independientes por módulo.
- Depreciación lineal estimada por cuenta en el resumen de activos.

## Migración de datos desde los XLSM

`tools/extract_seed.py` convierte las tablas de los tres libros a JSON (`server/seed/*.json`) y `server/src/db/seed.ts` las carga normalizadas. Para migrar los datos reales de la entidad:

```bash
pip install openpyxl
python3 tools/extract_seed.py Sistema_Almacenes.xlsm SICOMB.xlsm Sistema_Activos_Fijos.xlsm server/seed
npm run seed -- --force   # recrea la base con esos datos
```

Notas: los NIT repetidos entre sistemas se unifican por razón social; las claves de usuario del libro de combustible no se migran (se crean usuarios nuevos con scrypt).

## Pruebas

```bash
npm test                                                      # 113 pruebas sobre SQLite en memoria
TEST_DATABASE_URL=postgres://u:p@host/db npm run test -w server -- --no-file-parallelism   # las mismas sobre PostgreSQL
npm run typecheck
```
Cubren el motor de existencias (PEPS/FEFO, anulaciones, integridad kardex↔lotes), cada flujo de negocio con sus reglas, la API con roles, y la generación de **todos** los documentos y reportes (PDF y Excel).

## Seguridad y respaldos

- Bloqueo de 15 minutos tras 5 intentos fallidos de ingreso.
- Copia diaria automática de SQLite en `<datos>/respaldos` (retención de 14 días; `SIGAA_BACKUP=0` la desactiva, `SIGAA_BACKUP_DIR` cambia la carpeta). Con PostgreSQL use `pg_dump`.
- En producción defina `SIGAA_JWT_SECRET` y publique detrás de HTTPS.
- Los stickers incluyen código QR con el código del activo.

## Limitaciones conocidas

- El empaquetado de escritorio (`desktop/`) compila y su servidor embebido fue verificado, pero la ventana Electron y el instalador no se ejecutaron en el entorno de desarrollo (sin pantalla): pruébelos en su equipo.
- Los documentos formales (vale, CGI, actas) se emiten en **PDF**; los reportes tabulares en PDF **y** Excel. No se portó la macro «Importar versión anterior» de SICOMB (use el procedimiento de migración de arriba).
- La conciliación de combustible acepta el detalle del proveedor en `.xlsx`, CSV/TSV o pegado desde Excel.
