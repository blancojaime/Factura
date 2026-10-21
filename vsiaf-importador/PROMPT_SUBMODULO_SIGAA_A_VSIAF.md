# PROMPT PARA CLAUDE CODE — Submódulo de importación SIGAA → VSIAF 2.0

> Copie todo lo que sigue (desde «ROL») y péguelo en Claude Code, abierto en la raíz del proyecto del aplicativo de administración de activos fijos (SIGAA).
> El repositorio de referencia con la implementación ya probada es `blancojaime/Factura`, rama `claude/gracious-knuth-wkbtf5`, carpeta `vsiaf-importador/` (módulos `dbf.py`, `ufv.py`, `calc.py`, `importer.py`, `vsiafdb.py`, `excelio.py`, `tests/`, `GUIA_DE_USO.md`). **Léalo y reutilícelo/porte su lógica** en lugar de reinventarla.

---

## ROL

Eres un ingeniero senior con experiencia en Visual FoxPro/DBF, contabilidad pública boliviana (activos fijos, actualización por UFV, depreciación) y en el stack de este proyecto. Vas a construir, dentro del aplicativo SIGAA existente, un **submódulo «Exportación/Importación a VSIAF»** que toma los activos fijos (y sus movimientos) registrados en SIGAA y los **registra directamente en la base de datos del VSIAF 2.0** (Sistema de Activos Fijos del Ministerio de Economía y Finanzas Públicas de Bolivia), reproduciendo exactamente lo que hacen las pantallas del VSIAF.

## OBJETIVO

Permitir que el usuario, desde SIGAA, seleccione activos/movimientos (altas, revalúos, transferencias, bajas, y los maestros que necesiten: unidades, oficinas, responsables, auxiliares), los **valide**, vea una **vista previa de cálculos**, y los **importe** a una instalación local de VSIAF (`C:\vsiaf\dbfs`), con respaldo previo, reversión automática si algo falla y un informe auditable. El resultado debe ser indistinguible de haberlos registrado a mano en el VSIAF.

## PRIMEROS PASOS OBLIGATORIOS (antes de escribir código)

1. Explora el proyecto SIGAA: stack, base de datos, modelos/tablas de activos fijos, grupos/clasificadores, ubicaciones/oficinas, responsables/funcionarios, estados, bajas, revalúos, transferencias, centros de costo/proyectos/fuentes de financiamiento, usuarios y permisos. **No asumas el modelo de datos de SIGAA: léelo** y elabora una tabla de mapeo SIGAA→VSIAF (ver §7) que me presentes antes de implementar; marca lo que no tenga equivalente y propón una solución (valor por defecto, tabla de equivalencias editable, o columna que el usuario debe completar).
2. Lee el código de referencia `vsiaf-importador/vsiaf_importer/*` y los tests. Decide si portas la lógica a tu lenguaje o la invocas (si SIGAA es Python, importa/porta los módulos; si es otro lenguaje, reimplementa con los mismos tests numéricos de §10).
3. Presenta un plan corto (arquitectura, archivos, riesgos) y recién entonces implementa.

---

## 1. LO QUE ES VSIAF (hechos verificados)

* Hecho en **Visual FoxPro 9** (`vsiaf.exe` + `VFP9R.DLL`). Datos: tablas `.DBF` + memos `.FPT` + índices compuestos `.CDX`, en `<instalación>\dbfs` (normalmente `C:\vsiaf\dbfs`).
* Rutas en el registro (HKCU `SOFTWARE\MEFP\SIAF`): `APPinstall` (carpeta de instalación), `APPDBFS`, `APPIncEsp` (`'1'` = incorporaciones especiales habilitadas), `Llave`, `Updated`, `version`.
* **Las UFV NO están en `dbfs`**: están embebidas en `<instalación>\tipocambio.app` (tabla `TIPCAMB`: `DIA N2, MES N2, ANO N4, TC N(8,5), FEULT D, USUAR C8`; ~14.600 registros diarios 1987→…). El `.app` puede contener una copia vieja y otra nueva: se carga la de mayor fecha. Se extrae buscando el descriptor de campo `DIA` (`N`,2,0) y leyendo el DBF embebido (cabecera `hlen=225`, `rlen=33`). Fuente alternativa: `dbfs\tipcamb.dbf` si existiera. La tabla se renueva cada mes (día 10) con el actualizador del Ministerio; **SIGAA/el submódulo nunca modifica las UFV**. Sin UFV para una fecha, el VSIAF dice «Tipo de cambio NO registrado» y no opera; el submódulo debe rechazar esa fila igual.
* **Gestión cerrada:** si `<instalación>\closeges\closeges.dbf` tiene un registro con `NOM_ARCH = 'ACTUAL'`, la base está cerrada (solo lectura) → el submódulo **no escribe**.
* La entidad está en `dbfs\config.dbf` (`ENTIDAD C4`, `DESCENT C120`, `UNIDAD`, `DESCUNI`, `USUARIO C10`; la fila con `ENTIDAD` no vacía; la fila `USUARIO='VSIAF'` es residual). Todas las tablas se filtran por `ENTIDAD`.
* Usuario de sesión por defecto: `admin` (el campo `USUAR` es C8).

## 2. ESTRUCTURA DE TABLAS (campo tipo longitud,decimales)

Todas las tablas de datos tienen `ENTIDAD C4` y `UNIDAD C5` (código de unidad administrativa, texto, **sin rellenar con ceros**; ej. `'1'`, `'025'`).

**ACTUAL** (activos vigentes; memo `ACTUAL.FPT`):
`UNIDAD C5, ENTIDAD C4, CODIGO C15, CODCONT N2, CODAUX N3, VIDAUTIL N6.2, DESCRIP C150, COSTO N15.2, DEPACU N15.2, MES N2, ANO N4, B_REV L, DIA N2, CODOFIC N4, CODRESP N5, OBSERV M10, DIA_ANT N2, MES_ANT N2, ANO_ANT N4, VUT_ANT N3, COSTO_ANT N15.2, BAND_UFV L, CODESTADO N2, COD_RUBE C15, NRO_CONV C10, ORG_FIN C3, FEULT D, USUAR C8, API_ESTADO N1, CODIGOSEC C15, BANDERAS C12, FEC_MOD D, USU_MOD C8`
Índices CDX (no se escriben): `CODIGO = entidad+unidad+codigo` (clave lógica única), `CODAUX = STR(codcont)+STR(codaux)`, `CODRESP = entidad+unidad+STR(codofic)+STR(codresp)`, `TIPCAMB = STR(ano)+STR(mes)+STR(dia)`, `CODCONT`, `CODOFIC`, `CODESTADO`, etc.

**REVAL** (historial de revalúos; memo): `ENTIDAD C4, UNIDAD C5, CODIGO C15, COSTO N15.2, DEPACU_ANT N15.2, D_REVAL N2, DIA N2, M_REVAL N2, MES N2, A_REVAL N4, ANO N4, VIDAUTIL N5.2, RESOLUCION C16, OBSERV M, USUAR C8, FEULT D, DEPACU N15.2, ACTUA N15.2, DEPGESTION N15.2, FEC_MOD D, USU_MOD C8`

**BAJAS** (memo): `ENTIDAD C4, UNIDAD C5, CODIGO C15, CODBAJA N2, CODCONT N2, CODAUX N3, CODOFIC N4, CODRESP N5, COSTO N15.2, DEPACU_ANT N15.2, DESCRIP C120, D_BAJA N2, DIA N2, M_BAJA N2, MES N2, A_BAJA N4, ANO N4, B_REV L, VIDAUTIL N5.2, RESOLUCION C16, OBSERV M, MOTIVO C120, DEPACU N15.2, ACTUA N15.2, DEPGESTION N15.2, COSBAJINI N15.2, COSDAINI N15.2, COSACTBAJ N15.2, ACTDABAJ N15.2, USUAR C8, FEULT D, FEC_MOD D, USU_MOD C8`

**TRASFE**: `ENTIDAD C4, UNIDAD C5, CODIGO C15, CODOFIC N4, CODRESP N5, FEULT D, USUAR C8, UNIDADINI C5` (UNIDAD = destino, UNIDADINI = origen).

**OFICINA** (memo): `ENTIDAD C4, UNIDAD C5, CODOFIC N4, NOMOFIC C65, OBSERV M, FEULT D, USUAR C8, API_ESTADO N1` (1 = ACTIVO).
**RESP** (memo): `ENTIDAD C4, UNIDAD C5, CODOFIC N4, CODRESP N5, NOMRESP C35, CARGO C35, OBSERV M, CI C20, FEULT D, USUAR C8, COD_EXP N2, API_ESTADO N1` (COD_EXP → `CLA_DEPTS`: 1 CHQ, 2 LPZ, 3 CBB, 4 ORU, 5 PTS, 6 TAR, 7 SCZ, 8 BEN, 9 PAN, 10 OTROS; 0 = sin dato).
**AUXILIAR** (memo; **página de códigos cp850**, lang byte 0x02): `ENTIDAD C4, UNIDAD C5, CODCONT N2, CODAUX N3, NOMAUX C50, OBSERV M, FEULT D, USUAR C8`.
**UNIDADADMIN**: `ENTIDAD C4, UNIDAD C5, DESCRIP C120, CIUDAD C20, ESTADOUNI N1` (1 = vigente).
**Catálogos (solo lectura):** `CODCONT` (grupos: `CODCONT N2, NOMBRE C50, VIDAUTIL N4, OBSERV M, DEPRECIAR L, ACTUALIZAR L`), `ESTADO` (1 Bueno, 2 Regular, 3 Malo), `BAJA` (`CODBAJA N2, DESCBAJA C120`), `ORGANISMO_FIN` (`GESTION N4, OF C3, DES C100, SIGLA C15`), `CLA_DEPTS`, `CTA_PAR` (grupo→partida).

**Grupos contables (D.S. 24051, vida útil en años):** 1 Edificaciones 40 · 2 Muebles y enseres de oficina 10 · 3 Maquinaria en general 8 · 4 Equipo médico y de laboratorio 8 · 5 Equipo de comunicaciones 8 · 6 Equipo educacional y recreativo 8 · 7 Barcos y lanchas 10 · 8 Vehículos automotores 5 · 9 Aviones 5 · 10 Maquinaria para la construcción 5 · 11 Maquinaria agrícola 4 · 12 Animales de trabajo 4 · 13 Herramientas en general 4 · 14 Reproductores y hembras de pedigrí 8 · 15 Equipos de computación 4 · 16 Canales de regadío y pozos 20 · 17 Estanques, bañaderos y abrevaderos 10 · 18 Alambrados, tranqueras y vallas 10 · 19 Viviendas para el personal 20 · 20 Muebles y enseres en viviendas de personal 10 · 21 Silos, almacenes y galpones 20 · 22 Tinglados y cobertizos de madera 5 · 23 Tinglados y cobertizos de metal 10 · 24 Instalación de electrificación y telefonía rural 10 · 25 Caminos interiores 10 · 26 Caña de azúcar 5 · 27 Vides 8 · 28 Frutales 10 · 29 Líneas de recolección (petróleo) 5 · 30 Pozos petroleros 5 · 31 Equipos de campo (petróleo) 8 · 32 Planta de procesamiento (petróleo) 8 · 33 Ductos (petróleo) 10 · **34 Terrenos 0 (no se deprecia, sí se actualiza)** · **36 Otros activos fijos 0 (ni deprecia ni actualiza)** · 37 Activos intangibles 5 · 38 Equipo e instalaciones 8 · 39 Otras plantaciones 8 · **40 Activos museológicos y culturales 0 (ni deprecia ni actualiza)**. **Lee siempre `CODCONT.DBF` de la instalación**; esto es solo referencia.

**Motivos de baja (`BAJA`):** 1 Disposición definitiva de bienes · 2 Hurto, robo o pérdida fortuita · 3 Mermas · 4 Vencimiento, descomposiciones, alteraciones y deterioros · 5 Inutilización · 6 Obsolescencia · 7 Desmantelamiento total o parcial de edificaciones · 8 Siniestros · 9 **Error de transcripción** (depuración; no cuenta como baja contable).

## 3. REGLAS DE NEGOCIO Y ESTADOS (replicar tal cual)

* `ACTUAL.API_ESTADO`: **1 = ELABORADO**, **3 = APROBADO** (no existe 2). Elaborado: modificable/eliminable, no sale en reportes, impide cerrar gestión. Aprobado: oficial. **Revalúo, transferencia y baja solo sobre APROBADOS.**
* `ACTUAL.BANDERAS`: `'0'` alta normal; `'1'` Incorporación Especial. Al iniciar, el VSIAF ejecuta `UPDATE actual SET vidautil=<vida del grupo> WHERE banderas<>'1' AND ano>=2014 AND b_rev=.F.` → **una vida útil distinta de la del grupo se pierde** salvo `BANDERAS='1'` o revalúo (`B_REV=.T.`). Por eso: alta normal ⇒ `VIDAUTIL = CODCONT.VIDAUTIL` y `DEPACU = 0`.
* **Incorporación Especial es un control de la DGCF** (llave con vigencia en `data.dbf` + `APPIncEsp='1'`). El submódulo **solo** puede crear `BANDERAS='1'`/vida distinta/`DEPACU>0` si `APPIncEsp='1'` (lectura del registro); **jamás** debe escribir ni falsificar esa llave ni el registro. Si no está habilitada → error de validación explícito.
* Alta (`Nuevo`): `CODIGO` en MAYÚSCULAS, único por (entidad, unidad); `B_REV=.F.`, `BAND_UFV=.F.`, `DEPACU=0`, `BANDERAS='0'`, `FEULT=hoy`, `USUAR=usuario`, `ORG_FIN` obligatorio (código de 3 dígitos del clasificador vigente; `000`=NC), `CODESTADO` 1/2/3, oficina y responsable **ACTIVOS** y responsable perteneciente a esa oficina, auxiliar del mismo grupo y unidad. Fecha de incorporación ≤ hoy y con UFV registrada. Costo > 0. `OBSERV` es memo.
* **Revalúo técnico:** inserta en `REVAL`: `COSTO`=costo actual (viejo), `VIDAUTIL`=vida actual, `DIA/MES/ANO`=fecha base actual del activo, `D_REVAL/M_REVAL/A_REVAL`=fecha del revalúo, `DEPACU_ANT`=`ACTUAL.DEPACU`, `RESOLUCION` (disposición, C16, obligatoria), `OBSERV`=motivo, `USUAR`, `FEULT`, y la **instantánea** `DEPGESTION`, `DEPACU`, `ACTUA` (ver §4.4). Actualiza `ACTUAL`: `DIA/MES/ANO` = **fecha del revalúo + 1 día**, `B_REV=.T.`, `COSTO`=nuevo costo, `VIDAUTIL`=nueva vida, `DEPACU=0`. Requiere UFV del día y del día siguiente; la fecha ≥ fecha base y ≤ hoy; no repetir (`codigo`,`resolucion`).
* **Transferencia:** `ACTUAL.CODOFIC`, `CODRESP` ← destino; si cambia de unidad también `UNIDAD` y `CODAUX` (auxiliar de destino obligatorio; no puede existir el mismo código en la unidad destino). Inserta en `TRASFE` (`UNIDAD`=destino, `UNIDADINI`=origen, `CODOFIC`, `CODRESP`, `FEULT`, `USUAR`). Nada más (no toca REVAL/BAJAS).
* **Baja:** inserta en `BAJAS` (ver mapeo §6.6) y **marca como borrado (flag `*`) el registro de ACTUAL**, escribiendo `OBSERV='DADO DE BAJA'` en ese registro. `BAJAS.OBSERV='DADO DE BAJA'`, `BAJAS.MOTIVO` = texto libre «observaciones o motivos» (C120), `RESOLUCION` obligatoria. `CODBAJA=9` solo si el activo se incorporó en la misma gestión que la baja. Fecha baja ≥ fecha base y ≤ hoy, con UFV. `BAJAS.DESCRIP` = `ACTUAL.DESCRIP` truncada a 120.
* Oficinas/Responsables: códigos correlativos `max+1` (oficina por unidad; responsable por unidad+oficina). Auxiliar: `max+1` por unidad+grupo. Se comparan nombres sin distinguir mayúsculas/acentos; si ya existe → reutilizar (no duplicar).
* Unidades: `UNIDADADMIN` con `ESTADOUNI=1`.
* No se pueden inactivar oficinas/responsables con activos; no se puede cerrar gestión con ELABORADOS.

## 4. CÁLCULO (UFV, depreciación) — implementación verificada

Con `ufv(d)` = índice del día `d`; `inc` = fecha de incorporación/base; `calc` = fecha de cálculo (hoy por defecto); `vida` en años; `depreciar`/`actualizar` = flags del grupo (`CODCONT`).

1. `fin_vida`: si `vida` es entera → `inc + vida años − 1 día` (si `inc` es 29/02 → 28/02 del año destino, sin restar el día); si no → `inc + int(365×vida)` días. `ufv_vida` = UFV del aniversario (`inc + vida años`) (o `inc + int(365×vida)`).
2. `ufv_at(d)` = `ufv_vida` si `depreciar` y `d > fin_vida`; si no `ufv(d)`.
3. `factor(d)` = `round(ufv_at(d)/ufv(inc), 6)`; si `actualizar=false` → 1.
4. `valact` = `round2(costo × factor(calc))`. `pct` = `1/vida` si deprecia y vida>0, si no 0.
5. Días **inclusive**: `dias(a,b) = max(0,(b−a).days+1)`. `fin = min(calc, fin_vida)`. `dias_tot = dias(inc, fin)`; `dias_ges = dias(max(inc, 1/ene/año(calc)), fin)`.
6. `dep_ges = round2(valact×pct×dias_ges/365)`; `dep_acu = round2(depacu×factor) + round2(valact×pct×dias_tot/365)`, con tope `valact`; `valor_neto = round2(valact − dep_acu)`.
7. Situación al inicio de gestión: si `inc.year < calc.year`: `F_prev = factor(31/12 del año anterior)`, `valact_ini = round2(costo×F_prev)`, `dep_ini = round2(depacu×F_prev)+round2(valact_ini×pct×dias(inc, min(31/12 año ant., fin_vida))/365)` (tope `valact_ini`); si no: `valact_ini = costo`, `dep_ini = depacu`.
8. `actualizacion_gestion = valact − valact_ini`; `actualizacion_dep = round2(dep_acu − dep_ini − dep_ges)`.
9. **Redondeo**: mitad hacia arriba a 2 decimales (`ROUND` de FoxPro). Usa `Decimal`.

### 4.4 Instantáneas en REVAL y BAJAS (calculadas a la fecha de la operación)
* `DEPGESTION = dep_ges`; `DEPACU = round2(dep_acu − dep_ges)`; `ACTUA = round2(valact − DEPACU)`.
* Solo BAJAS: `COSBAJINI = valact_ini`; `COSDAINI = dep_ini`; `DEPACU_ANT = dep_ini`; `COSACTBAJ = valact`; `ACTDABAJ = actualizacion_dep`.
* Verificado contra registros reales del VSIAF (costo 1,00; vida 4; inc 21/09/2026; baja 20/10/2026 → `DEPGESTION 0,02, DEPACU 0, ACTUA 1,00, COSBAJINI 1,00, COSDAINI 0, COSACTBAJ 1,00, ACTDABAJ 0`).
* Supuesto documentado: el significado de estas instantáneas se dedujo del código y de datos de ejemplo; incluye un aviso en la UI para activos de gestiones anteriores y una prueba de contraste con un caso real.

## 5. FORMATO FÍSICO DBF/FPT (si escribes los archivos directamente)

* Cabecera DBF: `byte0` versión (0xF5 = FoxPro con memo; 0x03/0x30 sin memo), bytes 1–3 fecha (año−1900 o YY: respeta la convención del archivo), bytes 4–7 nº registros (LE uint32), 8–9 `hlen`, 10–11 `rlen`, 28 flag CDX, **29 language driver** (0x03→cp1252, 0x02→cp850, 0x01→cp437). Descriptores de campo de 32 bytes desde el offset 32 hasta `0x0D`. Registros desde `hlen`; el byte 0 del registro es `' '` (válido) o `'*'` (borrado). El archivo termina en `0x1A`.
* Codificación: usa el language driver **de cada tabla** (AUXILIAR = cp850; el resto cp1252). Si el texto no cabe en el largo del campo (en bytes) → error de validación, no truncar en silencio (excepción VSIAF: `BAJAS.DESCRIP` se recorta a 120).
* Tipos: `C` relleno con espacios a la derecha; `N` ASCII alineado a la derecha con espacios (decimales fijos); `D` `YYYYMMDD` o 8 espacios; `L` `T`/`F`/`?`; `M` = número de bloque FPT en ASCII alineado a la derecha (largo 10) o 4 bytes LE.
* **FPT:** cabecera de 512 bytes: bytes 0–3 = próximo bloque libre (**big-endian**), bytes 6–7 = tamaño de bloque (**big-endian**, 64). Bloque de memo: `tipo(4 BE)=1` + `longitud(4 BE)` + datos + relleno hasta completar bloques; actualizar el próximo bloque libre.
* Añadir registro: escribir en `hlen + nrec×rlen`, luego `0x1A`, y actualizar `nrec`. Modificar: sobrescribir los campos. Borrar: byte0=`0x2A`.
* **No reescribir `.CDX`** (formato propietario; riesgo de corrupción). Tras importar, el usuario ejecuta **VSIAF → Administradores → Re-indexar** (el VSIAF recompone todos los índices). El submódulo debe mostrar ese paso como obligatorio en la UI y en el informe.
* Escritura atómica por archivo (temporal + `replace`; quitar atributo solo-lectura si corresponde) y **reversión** de todos los archivos tocados si algo falla; luego **releer y verificar** (nº de registros, decodificar lo escrito, incluidos memos).
* Alternativa aceptable solo si es mejor para SIGAA: generar un paquete `.zip` de exportación nativa del VSIAF («Importar/Exportar»: zip con las 8 tablas `actual, bajas, reval, auxiliar, oficina, resp, trasfe, unidadadmin` de **una** unidad; el VSIAF lo importa con *Administradores → Importar/Exportar → Importar*, reemplazando los datos de esa unidad y detectando códigos duplicados). Esa vía delega los índices al VSIAF pero reemplaza la unidad completa; evalúa y justifica.

## 6. ALCANCE FUNCIONAL DEL SUBMÓDULO

### 6.1 Flujo del usuario
1. **Configurar destino**: detectar `C:\vsiaf` (registro `APPinstall`, rutas típicas) o elegir carpeta; mostrar entidad, unidades, última UFV, estado de gestión y advertencias (UFV sin variación > 75 días, gestión cerrada, VSIAF abierto, `APPIncEsp`).
2. **Selección** en SIGAA de los activos/movimientos a enviar (filtros por unidad, fecha, estado, grupo; marcar «ya enviados»).
3. **Mapeo** SIGAA→VSIAF (§7) con pantalla de equivalencias editable y persistente (grupo, oficina, responsable, auxiliar, estado del bien, organismo financiador, motivo de baja, unidad).
4. **Validar** (sin escribir): grilla de errores/avisos por registro con hoja/entidad, identificador, campo, mensaje y severidad; informe exportable (Excel/CSV/PDF).
5. **Vista previa de cálculo** por activo y totales por grupo contable (costo histórico, costo actualizado inicial, actualización gestión, costo total actualizado, dep. gestión, actualización dep. acumulada, dep. acumulada, valor neto) para contrastar con el **Reporte 6 del VSIAF** («Resumen de Activos Fijos Ordenado por Grupo Contable»).
6. **Importar**: confirmación explícita, verificación de que `vsiaf.exe` no corre, respaldo previo, escritura transaccional, verificación posterior, informe, y registro en SIGAA de qué se envió (id SIGAA ↔ `entidad+unidad+codigo` VSIAF, fecha, usuario, resultado) para evitar reenvíos duplicados.
7. Mensaje final: «Abra el VSIAF → Administradores → Re-indexar y verifique con el Reporte 6; apruebe los activos ELABORADOS».

### 6.2 Orden de proceso (dependencias)
`UNIDADES → OFICINAS → RESPONSABLES → AUXILIARES → ACTIVOS → REVALUOS (cronológico por activo) → TRANSFERENCIAS → BAJAS (cronológico)`. Una operación posterior ve el estado resultante de las anteriores (simula la BD en memoria).

### 6.3 Políticas
* Por defecto **un solo error cancela todo** (atomicidad); opción «importar solo filas válidas».
* Estado de alta por defecto **ELABORADO**; `APROBADO` solo si el usuario lo elige (y entonces se aplican todas las validaciones).
* Idempotencia: un activo ya existente (mismo `entidad+unidad+codigo`) es **error de duplicado**, nunca se sobrescribe; maestros existentes se reutilizan.
* Respaldo previo compatible con «Respaldos BD → Restaurar» del VSIAF: `.zip` **plano** con todos los archivos de `dbfs` + `.gtz` (comentario en cp1252: `Backup de la entidad «<ENTIDAD>» en fecha dd/mm/aaaa: <descripción>`), nombre p. ej. `VSIMPXL<ddmmyyHHMM>.zip` en `<instalación>\backups`.
* Seguridad/permiso: solo roles autorizados en SIGAA pueden importar; todo queda auditado; nunca guardar contraseñas; respetar la ley de datos personales (CI de responsables) — el informe no se sube a servicios externos.
* Concurrencia: exigir VSIAF cerrado (en Windows, `tasklist` por `vsiaf.exe`; advertir que en red/multiusuario deben salir todos los usuarios).
* El submódulo **no** aprueba, no cierra gestión, no toca UFV, no toca llaves de Incorporación Especial.

### 6.4 Mapeo campo a campo (destino = VSIAF)

**Activo → ACTUAL:** `UNIDAD`; `ENTIDAD` (de config); `CODIGO` (MAYÚSC., ≤15, único); `CODIGOSEC` (código adicional ≤15); `DESCRIP` (≤150); `CODCONT`; `CODAUX`; `CODOFIC`; `CODRESP`; `CODESTADO` (1/2/3); `DIA/MES/ANO` (fecha de incorporación); `COSTO`; `VIDAUTIL` (= grupo); `DEPACU`=0; `COD_RUBE` (≤15); `NRO_CONV` (≤10); `ORG_FIN` (3); `OBSERV` (memo); `API_ESTADO` 1|3; `BANDERAS` `'0'`; `B_REV`=F; `BAND_UFV`=F; `FEULT`=hoy; `USUAR`; campos `*_ANT`, `FEC_MOD` vacíos; `USU_MOD`=''.
**Revalúo → REVAL + update ACTUAL**, **Transferencia → TRASFE + update ACTUAL**, **Baja → BAJAS + borrado lógico en ACTUAL** (§3 y §4.4).

## 7. MAPEO SIGAA → VSIAF (a completar tras explorar SIGAA)

Presenta una tabla con columnas: *Concepto VSIAF | Campo/tabla SIGAA origen | Transformación | ¿Obligatorio? | Si falta*. Cubre como mínimo: unidad administrativa; código del activo (¿SIGAA usa otro formato? definir regla de generación/normalización y unicidad); descripción; grupo contable (equivalencias con los 39 grupos); auxiliar; oficina/ubicación; responsable (nombre, cargo, CI, expedido); estado del bien; fecha de incorporación/alta; costo; organismo financiador (de fuente de financiamiento/proyecto → código del clasificador); RUBE; convenio; observaciones; revalúos (fecha, valor, vida, resolución, motivo); transferencias (origen/destino, fecha); bajas (fecha, motivo → 1..9, resolución, observaciones). Para todo dato sin equivalente propone: valor por defecto configurable, tabla de equivalencias editable, o columna obligatoria en la pantalla de mapeo. **Prohibido inventar datos**: si falta un obligatorio, la fila queda en error.

## 8. ARQUITECTURA SUGERIDA

* Capas: `acceso DBF/FPT` (lectura/escritura mínima, sin dependencias de FoxPro) · `UFV` (extracción de `tipocambio.app`) · `cálculo` · `catálogos/estado virtual de la BD` · `validación + plan de operaciones` · `aplicar (backup, escritura, verificación, rollback)` · `informe` · `adaptador SIGAA` (lee los modelos de SIGAA y produce filas normalizadas) · `UI`.
* El motor debe ser **independiente de SIGAA** (puede ejecutarse con filas normalizadas), con una API del tipo `plan(filas) → Resultado(issues, operaciones, cálculos)` y `apply(plan)`; así se prueba sin la UI.
* Resultado de validación: lista de `Issue(hoja/entidad, fila/id, columna, nivel ERROR|AVISO, mensaje)`.
* UI en español, accesible, con progreso, cancelación segura antes de escribir, y sin bloquear el hilo principal.
* Registro (log) técnico en archivo, sin datos sensibles innecesarios.

## 9. VALIDACIONES (todas con mensaje claro en español)

Unidad inexistente · código vacío/>15/duplicado (en VSIAF o en el lote) · grupo no reconocido · auxiliar inexistente en el grupo/unidad · oficina/responsable inexistente, **inactivo** o de otra oficina · estado del bien inválido · fecha inválida/futura/sin UFV · costo ≤ 0 · vida útil distinta del grupo (error salvo incorporación especial habilitada) · `DEPACU>0` en alta normal (error) · organismo financiador fuera del clasificador · textos que exceden el largo · gestión cerrada · VSIAF abierto · activo inexistente/ya dado de baja/ELABORADO para revalúo-transferencia-baja · revalúo: fecha < fecha base, nuevo costo ≤ 0, vida ≤ 0 (si el grupo deprecia), resolución vacía/repetida · transferencia: auxiliar destino obligatorio entre unidades, código ya existente en destino, sin cambios (aviso) · baja: fecha < base, motivo desconocido, `CODBAJA=9` fuera de la gestión de incorporación, resolución vacía · aviso: activo de gestión anterior (el VSIAF recalcula desde la fecha) · aviso: UFV desactualizadas (último cambio > 75 días antes de la fecha de cálculo).

## 10. PRUEBAS DE ACEPTACIÓN (obligatorias)

**Numéricas (deben dar exactamente):**
* Costo 620,00 · vida 10 · incorporación 11/04/2013 · cálculo 14/10/2013 (UFV 1,82467 → 1,87194): `factor 1,025906 · valor actualizado 636,06 · días 187 · dep. gestión 32,59 · valor neto 603,47`.
* Costo 1.380,00 · vida 10 · incorporación 29/08/2011 (UFV 1,66535) · cálculo 10/10/2013 (UFV 1,87054): `factor 1,123211 · valor actualizado 1.550,03 · días 774 (gestión 283) · dep. acumulada 328,69 · valor neto 1.221,34`.
* Costo 5.500 · vida 5 · incorporación = cálculo (1 día): dep. 3,01.
* Activo con vida terminada: dep. acumulada = valor actualizado, neto 0, dep. gestión 0. Grupo 34/36/40: sin depreciación.
* Instantánea BAJAS del ejemplo real (§4.4).
**De formato/E2E:** crear una instalación sintética (tablas vacías con la estructura de §2 + catálogos) → importar un lote que incluya unidades, oficinas, responsables, auxiliares, activos (aprobados y elaborados), un revalúo, una transferencia (misma unidad y entre unidades) y una baja → releer con un lector DBF **independiente** (p. ej. `dbfread`) y comprobar campos, memos (con tildes/ñ), flag de borrado y contadores; probar rollback (fallo simulado a mitad de escritura), validación sin escritura (archivos idénticos byte a byte), respaldo restaurable, gestión cerrada, duplicados, y que la importación de un lote ya importado falle por duplicados.
**Manual en Windows (checklist para el usuario):** copiar `C:\vsiaf` a una carpeta de prueba → importar → abrir esa copia → Re-indexar → ver activos, aprobar, revalúo/transferencia/baja en reportes, comparar Reporte 6, restaurar el respaldo.

## 11. ENTREGABLES

1. Código del submódulo integrado en SIGAA, con tests automatizados (los de §10) y CI.
2. Documento de mapeo SIGAA→VSIAF aprobado por mí **antes** de implementar.
3. Guía de uso (español) con capturas/pasos, errores frecuentes y la advertencia de Re-indexar.
4. Informe de importación exportable (resumen, incidencias, cálculo por activo, totales por grupo).
5. Lista de supuestos y riesgos abiertos (índices CDX, significado de instantáneas de REVAL/BAJAS en gestiones anteriores, UFV desactualizadas, incorporaciones especiales) y cómo se mitigan.

## 12. REGLAS DE TRABAJO

* No toques datos reales del VSIAF durante el desarrollo: usa instalaciones sintéticas o **copias**.
* No elimines ni sobrescribas nada sin respaldo; no escribas fuera de `dbfs`/`backups` de la instalación elegida.
* No expongas datos personales ni los subas a terceros.
* Si algo de este documento contradice lo que observes en el código de SIGAA o en una instalación real del VSIAF, **detente, reporta la discrepancia y propón el ajuste**; no adivines.
* Entrega por etapas: (1) plan + mapeo, (2) motor + tests, (3) adaptador SIGAA, (4) UI, (5) guía y empaquetado; y espera mi visto bueno entre la 1 y la 2.
