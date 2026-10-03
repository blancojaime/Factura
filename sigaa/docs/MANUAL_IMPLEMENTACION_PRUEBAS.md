# SIGAA — Manual de implementación y pruebas (piloto)

Sistema Integrado de Gestión de Almacenes, Combustible y Activos Fijos — GAM Calamarca.
Dirigido al responsable de implementación y a los tres encargados de área (Almacenes, Combustible, Activos Fijos).

---

## 1. Objetivo y duración

Probar el sistema con datos de demostración y luego con datos reales, y decidir si pasa a uso oficial.

| Fase | Qué se hace | Duración sugerida |
|---|---|---|
| A | Instalar y verificar que arranca | 1 día |
| B | Pruebas guiadas con datos demo (sección 5) | 3–5 días |
| C | Cargar datos reales y operar en paralelo con los Excel | 2–4 semanas |
| D | Decisión de aprobación y puesta en producción | 1 día |

Regla de oro del piloto: **los Excel siguen siendo el sistema oficial hasta firmar el acta de aprobación (sección 9).** Todo lo que se registre en SIGAA durante la fase C también se registra en el Excel.

---

## 2. Requisitos

- Una PC con Windows 10/11 y **Node.js 22 o superior** (LTS) instalado.
- Internet solo para la primera instalación.
- Navegador Chrome, Edge o Firefox actualizado.
- Impresora o visor PDF para revisar los documentos.
- Los tres archivos Excel originales a mano para comparar resultados.

---

## 3. Instalación (fase A)

1. Descargar el ZIP del proyecto y extraerlo en `C:\SIGAA`.
2. Entrar a la carpeta `sigaa` y hacer doble clic en **`INICIAR_SIGAA.bat`**.
3. La primera vez instala componentes (unos minutos). Al terminar abre el navegador en `http://localhost:3000`.
4. Ingresar con usuario **admin** y clave **Admin2026**. El sistema obliga a cambiar la clave: usar una de mínimo 8 caracteres y **anotarla en lugar seguro**.

Para usar el sistema después: doble clic en `INICIAR_SIGAA.bat` y **no cerrar la ventana negra** mientras se trabaja. Cerrarla apaga el sistema.

### Verificación de la instalación (marcar)

- [ ] Abre la pantalla de inicio de sesión.
- [ ] Entra con `admin` y obliga a cambiar la clave.
- [ ] El tablero (inicio) muestra cifras y no errores en rojo.
- [ ] El menú lateral muestra Almacenes, Combustible, Activos Fijos, Reportes, Catálogos y Administración.
- [ ] Cambiar entre modo claro y oscuro funciona.

### Reiniciar los datos de prueba

Con el sistema **cerrado**, borrar el archivo `sigaa\server\data\sigaa.sqlite` y volver a abrir `INICIAR_SIGAA.bat`. Se recrea la base con datos demo.
Para empezar **sin datos demo** (fase C), abrir PowerShell en la carpeta `sigaa\server` y ejecutar:
`npx tsx src/db/seed-cli.ts --force --sin-demo`

---

## 4. Configuración inicial (Administración)

Hacerla una sola vez, antes de las pruebas.

1. **Administración → Usuarios:** crear un usuario por persona. Roles:
   - `ALMACEN`, `COMBUSTIBLE`, `ACTIVOS`: operan su módulo.
   - `CONSULTA`: solo ve y descarga reportes.
   - `ADMIN`: todo, incluida la configuración.
   - Una persona puede tener varios roles.
2. **Administración → Configuración:** completar nombre de la entidad, gestión vigente y **firmantes/autoridades** (Máxima Autoridad, jefes de área). Aparecen en los PDF.
3. **Catálogos:** revisar unidades, proveedores, vehículos, conductores, contratos y precios de combustible, edificios/ambientes y cuentas contables de activos.
4. Copias de seguridad: el sistema genera una diaria automática en `sigaa\server\data\respaldos` (conserva 14). Copiar esa carpeta a un pendrive o a otra PC **cada semana**.

---

## 5. Plan de pruebas guiadas (fase B)

Cada prueba tiene: **acción → resultado esperado**. Marcar ✔ si coincide, ✘ si no (y anotar en la hoja de incidencias, sección 7).

### 5.1 Seguridad y usuarios (Administrador)

| # | Acción | Resultado esperado | ✔/✘ |
|---|---|---|---|
| S1 | Crear usuario con rol CONSULTA y entrar con él | Ve datos y reportes; no aparecen botones de registrar | |
| S2 | Escribir 5 veces mal la clave de un usuario | Cuenta bloqueada 15 minutos | |
| S3 | Entrar con un usuario ALMACEN e intentar abrir `/combustible/emitir` escribiendo la dirección | Mensaje de acceso denegado | |
| S4 | Administración → Bitácora | Quedan registradas las operaciones hechas arriba | |

### 5.2 Almacenes (encargado de Almacenes)

| # | Acción | Resultado esperado | ✔/✘ |
|---|---|---|---|
| A1 | Catálogo: crear un material nuevo | Se crea con código y unidad; aparece en búsquedas | |
| A2 | Ingresos: registrar un ingreso con proveedor, factura, 2 ítems y fecha de vencimiento en uno | Genera número correlativo de ingreso; existencias aumentan | |
| A3 | Ingresos: descargar el documento del ingreso (PDF) | PDF con firmantes, ítems y total | |
| A4 | Salidas: crear un pedido y despacharlo | Descuenta por lote; primero lo que vence antes (PEPS/FEFO); no usa lotes vencidos | |
| A5 | Salidas: intentar despachar más que la existencia | Rechaza con mensaje claro | |
| A6 | Salidas: pedido fuera de los días 1–25 o sobre el máximo mensual | Advierte/bloquea según Manual 11; permite excepción justificada | |
| A7 | Existencias / Kardex de un material | Saldo y valor coinciden con ingresos menos salidas | |
| A8 | Inventarios: iniciar conteo ciego, registrar cantidades distintas | Sobrante genera ajuste de ingreso; faltante genera acta de reposición o baja | |
| A9 | Bajas: iniciar expediente con causal | Exige los documentos obligatorios `(*)` y Resolución Administrativa | |
| A10 | Transferencias entre almacenes | Sale de un almacén y entra en el otro con documento | |
| A11 | Seguridad: inspección con los 16 criterios; extintores/seguros por vencer | Resultado de la inspección y alertas de vencimiento | |
| A12 | Reportes → Almacenes (kardex valorado, existencias, ingresos, salidas) en pantalla, PDF y Excel | Mismas columnas que el Excel original; totales iguales | |
| A13 | Cierre de gestión: ejecutar las verificaciones (**solo en copia de prueba, no con datos reales**) | Lista las 10 verificaciones; al cerrar crea la nueva gestión con saldo inicial por lote | |

### 5.3 Combustible (encargado de Combustible)

| # | Acción | Resultado esperado | ✔/✘ |
|---|---|---|---|
| C1 | Recepción: registrar recepción de combustible/vales de un contrato (rango de numeración) | Vales creados; no permite repetir número por proveedor/combustible/corte | |
| C2 | Emitir vale a un vehículo y conductor | Calcula litros según límites (p. ej. 16 L/día lun–sáb para ejecutivo; km × rendimiento) | |
| C3 | Emitir con conductor sin licencia vigente, o con descargo vencido pendiente | Advertencia o bloqueo; si es advertencia, pide confirmar | |
| C4 | Emitir con lectura de odómetro menor a la anterior | Rechaza | |
| C5 | Descargo (Anexo 3): registrar kilometraje y litros | Calcula rendimiento; Conforme u Observado según tolerancia | |
| C6 | Devolución, anulación, vencimiento y extravío de un vale | Cada uno cambia el estado y deja rastro | |
| C7 | Turriles: ingreso y consumo | Costo promedio y saldo correctos; no supera capacidad | |
| C8 | Viajes: fondo en avance y rendición (Anexos 4 y 6) | Documentos PDF generados con montos correctos | |
| C9 | Conciliación: subir el Excel de la estación | Resultados CONFORME / DUPLICADO / NO REGISTRADO / NO ENTREGADO / MONTO o PLACA DIFERENTE / SIN DESCARGO | |
| C10 | Informe mensual (Anexo 5) en PDF y Excel | Coincide con el Excel original del mismo mes | |
| C11 | Tablero y cronograma | Cifras coherentes con los movimientos registrados | |

### 5.4 Activos Fijos (encargado de Activos)

| # | Acción | Resultado esperado | ✔/✘ |
|---|---|---|---|
| F1 | Ingreso de un activo y codificación | Código con formato `EEE-AA-CCXXX-NN`; correlativo no se repite | |
| F2 | Ficha técnica con campos de la cuenta y 4 fotos | Se guarda y se imprime en PDF | |
| F3 | Solicitud → Asignación a un funcionario | Genera documento de asignación | |
| F4 | Devolución y transferencia entre funcionarios | Historial del activo actualizado | |
| F5 | Baja de un activo | Cambia estado y sale de la lista de activos vigentes | |
| F6 | Etiquetas: generar hoja 3×10 con código QR | PDF con 30 etiquetas por hoja; el QR al escanearlo identifica el activo | |
| F7 | Consulta por código, funcionario, ambiente | Resultados correctos; depreciación estimada lineal | |
| F8 | Reportes de Activos en PDF y Excel | Mismo contenido que el Excel original | |

### 5.5 Prueba transversal

| # | Acción | Resultado esperado | ✔/✘ |
|---|---|---|---|
| T1 | Reportes → ejecutar cada reporte en pantalla, PDF y Excel | Ninguno da error; PDF legible y paginado | |
| T2 | Cerrar la ventana negra y volver a abrir el sistema | Los datos siguen ahí | |
| T3 | Copiar `server\data\sigaa.sqlite` a otra PC con el sistema instalado y abrirlo | Mismos datos (prueba de respaldo y recuperación) | |
| T4 | Dos usuarios trabajando a la vez desde dos computadoras (ver sección 8) | Ambos operan sin errores | |

---

## 6. Carga de datos reales (fase C)

1. **Respaldar** antes de cualquier carga.
2. Arrancar sin datos demo (ver sección 3).
3. Importar maestros desde los Excel originales con la herramienta `tools/extract_seed.py` (necesita Python) siguiendo la guía entregada anteriormente, o cargarlos por **Catálogos** si son pocos.
4. Cargar saldos iniciales:
   - Almacenes: un ingreso por saldo inicial con la fecha de corte.
   - Activos: registrar los activos existentes con su código original.
   - Combustible: contratos, precios, vehículos, conductores y vales pendientes.
5. **Cuadre:** comparar contra el Excel (existencias totales y valor, cantidad de activos por cuenta, saldo de combustible). Diferencias → hoja de incidencias.
6. Operar en paralelo durante 2–4 semanas y comparar cifras cada semana.

**No se migran automáticamente** los movimientos históricos de Combustible (vales ya emitidos, descargos, kardex, viajes) ni los valores de configuración de Almacenes/Activos: se cargan los saldos y se opera desde la fecha de corte.

---

## 7. Hoja de incidencias

Una fila por problema. Enviar fotos de pantalla (incluida la barra de direcciones y los mensajes en rojo).

| N.º | Fecha | Quién | Módulo/pantalla | Qué hizo | Qué esperaba | Qué ocurrió | Gravedad (Alta/Media/Baja) |
|---|---|---|---|---|---|---|---|
| 1 | | | | | | | |

Gravedad **Alta** = impide trabajar o da cifras incorrectas. **Media** = tiene solución alternativa. **Baja** = estética o mejora.

---

## 8. Uso en red (varias computadoras)

1. En la PC donde corre SIGAA, abrir PowerShell y ejecutar `ipconfig`; anotar la «Dirección IPv4» (ej. `192.168.1.20`).
2. Dejar el sistema encendido (ventana negra abierta).
3. Si Windows muestra aviso de firewall, **Permitir acceso** en redes privadas.
4. Desde otra PC de la misma red escribir `http://192.168.1.20:3000`.
5. Esa PC debe estar encendida siempre en horario de trabajo.

Para uso oficial con muchos usuarios se recomienda instalarlo en un servidor con PostgreSQL (Docker, ver `README.md`), con acceso seguro HTTPS y una clave secreta propia (`SIGAA_JWT_SECRET`).

---

## 9. Criterios de aprobación

El piloto se aprueba si se cumple todo lo siguiente:

- [ ] Todas las pruebas de la sección 5 están en ✔, o las ✘ tienen solución acordada.
- [ ] No quedan incidencias de gravedad Alta abiertas.
- [ ] Durante la operación en paralelo, las cifras coinciden con el Excel (existencias, activos, saldos de combustible) o las diferencias están explicadas.
- [ ] Los PDF y Excel principales fueron revisados y aceptados por cada encargado.
- [ ] Se probó restaurar una copia de seguridad (T3).
- [ ] Cada encargado fue capacitado y puede operar solo.

**Acta de aprobación**

| Área | Responsable | Aprobado (Sí/No) | Observaciones | Firma | Fecha |
|---|---|---|---|---|---|
| Almacenes | | | | | |
| Combustible | | | | | |
| Activos Fijos | | | | | |
| Administración del sistema | | | | | |

---

## 10. Puesta en producción (después de aprobar)

1. Respaldar y guardar una copia del Excel final de cada área como archivo histórico.
2. Definir **quién administra** el sistema y quién hace la copia semanal fuera de la PC.
3. Cambiar todas las claves; eliminar usuarios de prueba.
4. Instalar en el equipo definitivo (de preferencia servidor con PostgreSQL y HTTPS).
5. Comunicar la fecha de corte: desde ese día solo se registra en SIGAA.

---

## 11. Problemas frecuentes

| Problema | Solución |
|---|---|
| El navegador no abre la página | Verificar que la ventana negra siga abierta; entrar a `http://localhost:3000` |
| «Puerto en uso» | Hay otra copia abierta; cerrar todas las ventanas negras y reabrir |
| Un usuario olvidó su clave | El administrador entra a Administración → Usuarios, edita al usuario y escribe una clave nueva |
| Olvidé la clave del propio admin | Pedir soporte; no borrar la base de datos, se perderían los datos |
| Un PDF sale en blanco | Probar con otro navegador y enviar foto del mensaje |
| La instalación falla | Enviar foto de toda la ventana, incluidas las líneas rojas |
