# ComexBol Pro — Manual de implementación y de pruebas

Versión del arancel soportada: **Arancel Aduanero de Importaciones 2026** (RM N° 557, vigente desde 01/01/2026).
Fecha de los ejemplos: 02/11/2026 · Tipo de cambio de los ejemplos: **Bs 6,96 por USD** (dato de prueba; use el oficial del día).

> **Estado.** La lógica (cálculo, catálogo, OCR, seguimiento, expediente) está probada con pruebas automáticas.
> La ventana WPF **no se ha compilado ni ejecutado** (se construyó en Linux). Los pasos de pantalla de este manual son la
> primera prueba real: si algo difiere, anótelo en la sección 6.

---

## 1. Implementación

### 1.1 Requisitos (PC con Windows 10/11 de 64 bits)
| Componente | Para qué | Cómo obtenerlo |
|---|---|---|
| .NET 8 SDK | compilar y ejecutar | https://dotnet.microsoft.com/download/dotnet/8.0 |
| Tesseract OCR con idioma **Spanish** | leer facturas escaneadas | instalador UB-Mannheim; marcar *Spanish* en "Additional language data"; ruta por defecto `C:\Program Files\Tesseract-OCR\` |
| Poppler (`pdftoppm`) | leer facturas en PDF y mostrar su primera página | Windows: poppler-windows; agregar su carpeta `bin\` al PATH |
| Archivos del arancel (3 `.md`) | catálogo NANDINA | los que usted ya tiene |

### 1.2 Compilar y ejecutar
```bash
git clone <repositorio> && cd Factura/ComexBolPro
dotnet build ComexBol.sln
dotnet run --project src/ComexBol.App
```
Si hay errores de XAML o de compilación en `ComexBol.App`, copie el mensaje completo: es lo primero que debe corregirse.

### 1.3 Pruebas automáticas (antes de usar el sistema)
```bash
for t in tests/*/; do (cd $t && dotnet test); done
```
Resultado esperado: todas en verde (Core 21, Data 19, Documentos 9, Presentación 7). Las pruebas de OCR/PDF se omiten solas si Tesseract o Poppler no están instalados. Con el arancel completo:
```bash
cd tests/ComexBol.Data.Tests
COMEXBOL_ARANCEL_DIR=<carpeta con los 3 .md> dotnet test      # PowerShell: $env:COMEXBOL_ARANCEL_DIR="C:\arancel"; dotnet test
```
El caso 9 verifica 8.121 partidas y 97 capítulos.

### 1.4 Datos y copias de seguridad
- Base de datos: `%LocalAppData%\ComexBolPro\comex.db` (SQLite). **Una copia de ese archivo es la copia de seguridad completa** (operaciones, bitácora, liquidaciones, catálogo).
- Los documentos no se copian a la base: se guarda su ruta y su huella SHA-256. Conserve los archivos en una carpeta por embarque.
- La base se crea sola al primer arranque. Aún no hay migraciones: ante un cambio de versión del programa, exporte los expedientes y recree la base.

### 1.5 Instalación para otros usuarios
```bash
dotnet publish src/ComexBol.App -c Release -r win-x64 --self-contained -o publicar
```
Copie la carpeta `publicar` y asegúrese de que cada PC tenga Tesseract.

### 1.6 Carga anual del arancel
1. Barra superior → **Importar catálogo…** → seleccione **los 3 archivos `.md` a la vez** (Ctrl+clic).
2. El importador **reemplaza todo el catálogo**. No altera las operaciones ya creadas.
3. Lea el mensaje de la barra de estado y el cuadro de avisos (ver 2.1).

### 1.7 Parámetros que debe validar un despachante antes de usar en producción
| Parámetro | Valor por defecto | Dónde |
|---|---|---|
| IVA efectivo en aduana | 14,94 % | `ParametrosTributarios.TasaIvaEfectiva` |
| Base del ICE ad valorem | (CIF + GA) × tasa | `CalculadoraTributaria` |
| Redondeo | 2 decimales (alternativa: Bs enteros) | `ModoRedondeo` |
| Umbral de bancarización | Bs 50.000 | `UmbralBancarizacionBob` |
| Seguro presunto sin póliza | 0 % (solo advierte) | `SeguroPresuntoPct` |
| Límite del CEDEIM | se exige como argumento | `Exportacion.CedeimEstimado` |
| Tipo de cambio | se digita (campo de la barra superior) | UI |

---

## 2. Qué trae y qué no trae el importador del arancel

Resultado con **sus** 3 archivos: **8.121 partidas** de 10 dígitos, **97 capítulos**, **268 avisos**.

| Dato | Estado |
|---|---|
| Código, descripción, GA (0–40 %), unidad de medida | Leídos de la tabla |
| Documento adicional (AP, AP y C, C, C\*, DJ, CITES, CCRT, CRTM), entidad (SENASAG, AGEMED, IBMETRO…), disposición legal | Leídos |
| **Prohibida (tipo P)** | Detectada: el sistema bloquea la partida |
| Marca ICE / IEHD | Detectada (497 ICE, 20 IEHD). **La tasa de IEHD no viene en el arancel** |
| **ICE de vehículos por antigüedad** (Apéndice I) | Solo las filas con las 6 tasas legibles (17 partidas). **Para las demás, el sistema avisa y usted ingresa el ICE % a mano** |
| Preferencias arancelarias (CAN, ACE…) | Se guardan los porcentajes impresos pero **no se asignan a cada acuerdo** (las columnas se desplazan en el original). La desgravación se aplica a mano |

**Los 268 avisos** (cada uno con archivo y línea): 227 filas del Apéndice ICE con tasas ilegibles; 2 filas sin unidad; el resto, documentos sin tipo. Ninguna partida se descarta en silencio ni se corrige adivinando.
**Verificación recomendada:** revise por muestreo 20–30 partidas de su interés contra el PDF original (sección 4, prueba P-02).

---

## 3. Manual de pruebas con ejemplos completos

Convenciones: *TC = 6,96*. Las cifras en pantalla usan formato regional (p. ej. `291.972,00`). "Aplicar" significa el botón indicado.
Las cifras de cada caso están verificadas por pruebas automáticas (`ManualDePruebasTests`).

### Preparación común
1. Abra ComexBol Pro. Barra superior: **TC USD→Bs = 6,96**.
2. **Importar catálogo…** con los 3 `.md` → barra de estado: *«Catálogo: 8121 partidas…»*.

### Caso 1 — Tablets, Incoterm FOB (importación típica)
**Datos:** 200 tablets con IMEI, partida **8471.30.00.10**, valor factura USD 40.000, peso bruto 800 kg, flete USD 1.800, seguro USD 150.
1. Panel izquierdo: carpeta `IMP-2026-001`, Incoterm **FOB**, **Crear**.
2. Pestaña *Ítems y documento*: Partida `8471.30.00.10`, Descripción `Tablets`, Valor `40000`, Peso `800`, Flete `1800`, Seguro `150` → **Agregar ítem** → **Calcular (F5)**.
3. Pestaña *Liquidación*, valores esperados:

| Concepto | Bs |
|---|---|
| Valor FOB | 278.400,00 |
| + Adiciones (flete + seguro) | 13.572,00 |
| **CIF aduana** | **291.972,00** |
| Gravamen arancelario (10 %) | 29.197,20 |
| IVA (14,94 %) | 47.982,68 |
| **Total tributos** | **77.179,88** |

4. Avisos: *«FOB ≥ Bs 50.000: complete el respaldo bancario»*. Pestaña *Legajo*: Factura, Embarque, Packing, Seguro, Bancario, Flete → todos ✖.
5. Bitácora: «Ítem 1…», «Catálogo: GA 10 %…», «Liquidación v1…».
**Costo y margen** (gastos locales Bs 4.500, 200 unidades, precio de mercado Bs 2.800 con IVA): costo puesto en almacén Bs 325.669,20; unitario Bs 1.628,35; margen 34,3 %. Se ve en la pestaña **Decisión** (Caso 2).

### Caso 2 — ¿Conviene FOB, CIF o DAP? (decisión)
Misma mercancía, tres ofertas: **FOB** USD 40.000 + flete 1.800 + seguro 150 · **CIF** USD 42.000 · **DAP** USD 44.000 (con USD 1.200 de transporte posterior a la frontera).

| Escenario | CIF aduana Bs | Tributos Bs | Costo unitario Bs | Veredicto |
|---|---|---|---|---|
| FOB + flete propio | 291.972,00 | 77.179,88 | **1.628,35** | Viable |
| CIF del proveedor | 292.320,00 | 77.271,87 | 1.630,26 | Viable |
| DAP del proveedor | 297.888,00 | 78.743,71 | 1.660,88 | Viable |

Lectura: FOB es el más barato por unidad; DAP cuesta Bs 32,53 más por unidad pero traslada el riesgo al proveedor.

**En pantalla (pestaña *Decisión*):** con la operación del Caso 1 seleccionada, Unidades `200`, Gastos locales `4500`, Precio de mercado `2800`, Margen objetivo `15`. **Agregar escenario** tres veces y llene:

| Escenario | Incoterm | Valor oferta | Flete | Seguro | Deduc. post-frontera |
|---|---|---|---|---|---|
| FOB + flete propio | FOB | 40000 | 1800 | 150 | 0 |
| CIF del proveedor | CIF | 42000 | 0 | 0 | 0 |
| DAP del proveedor | DAP | 44000 | 0 | 0 | 1200 |

**Comparar** → la tabla de resultados debe coincidir con la de arriba, con la fila de menor costo unitario en verde. Los ítems de la operación se escalan proporcionalmente al valor de cada oferta. Si deja el precio de mercado en 0, el sistema avisa que no puede calcular margen. Pruebe también un precio de Bs 1.600: el veredicto debe pasar a *No viable*.

### Caso 3 — Animales vivos, CFR (permiso sanitario)
**Datos:** reproductores de raza pura, partida **0101.21.00.00**, valor USD 25.000, peso 3.000 kg, seguro USD 250. Incoterm **CFR** (el flete ya viene en el precio; **no** lo digite).
- Esperado: CIF **175.740,00** (FOB 174.000 + seguro 1.740) · GA 5 % = **8.787,00** · IVA **27.568,33** · total **36.355,33**.
- Avisos: *«documento adicional C\* — MDPRyA (SENASAG) Ley 830-Dec. 515»*. En *Legajo* aparece **Autorización previa** exigida con SENASAG.
- Si digita un flete con CFR, el aviso dirá que fue ignorado por el Incoterm.

### Caso 4 — Tractor usado con ICE por antigüedad
**Datos:** partida **8701.21.00.00**, valor USD 20.000, peso 4.000 kg, **antigüedad 3 años**, Incoterm FOB, flete USD 2.500, seguro USD 200. Deje *ICE %* en 0.
- Aviso: *«ICE 30 % (Apéndice I, antigüedad 3 años)»*.
- Esperado: CIF **157.992,00** · GA 5 % **7.899,60** · ICE 30 % sobre (CIF+GA) **49.767,48** · IVA **32.219,47** · total **89.886,55**.
- Repita con antigüedad 0: el ICE debe pasar a 15 %.

### Caso 5 — Umbral de bancarización (D.S. 772)
| Valor FOB | Resultado |
|---|---|
| USD 7.000 (Bs 48.720) partida 8471.30.00.90 | **Sin** aviso de bancarización · tributos Bs 12.878,64 |
| FOB equivalente a Bs 50.000,00 | **Con** aviso · tributos Bs 13.217,00 |

### Caso 6 — Whisky: el ICE no viene en el arancel
**Datos:** partida **2208.30.00.00**, valor USD 10.000, Incoterm CIF.
- GA **40 %**. Avisos: *«partida sujeta a ICE… ingrese manualmente»* y *«documento adicional C — SENASAG»*.
- Prueba: ingrese en *ICE %* la tasa que le indique su despachante y verifique que la liquidación la use sobre (CIF+GA). El sistema **no inventa** la tasa.

### Caso 7 — Mercancía prohibida y medicamento
- Partida **8703.23.10.10** (vehículo a GLP, tipo **P**): al agregar el ítem el sistema debe mostrar *«… figura como mercancía prohibida»* y **no** liquidar.
- Partida **3004.90.10.00** (plasma sintético): aviso con **AGEMED**, y el *Legajo* exige la autorización.

### Caso 8 — Seguimiento de la ruta con fechas
Crear la operación el 02/11/2026. En *Ruta crítica* debe verse: I01 plan 02/11 → 04/11. Marque **I01 cumplida**; la etapa pasa a ● verde y la bitácora anota «a tiempo». Con fecha de hoy posterior a un plazo, la etapa pasa a **Vencido** (rojo); a ≤ 2 días del fin, **Alerta** (amarillo). La barra inferior resume 🟢🔵🟡🔴 y el próximo vencimiento.

### Caso 9 — Arancel completo
Verificado en 1.3: 8.121 partidas / 97 capítulos. En la aplicación: tras importar, la barra de estado dice *«Catálogo: 8121 partidas, 268 avisos/rechazos»*.

### Caso 10 — OCR de factura
1. Operación abierta → *Ítems y documento* → **Abrir y leer con OCR** → `docs/ejemplos/factura-ejemplo.png`.
2. Debe aparecer *«Propuesta del OCR»* con (puede variar algún dígito, por eso se confirma a mano):

| Campo | Valor esperado | Confianza |
|---|---|---|
| N.º factura | INV-88213 | Media |
| Proveedor | Shenzhen Tech Co., Ltd | Alta |
| Incoterm | FOB | Alta |
| Moneda | USD | Media |
| Valor total | 10000 | Media |
| Peso bruto kg | 1250.5 | Media |

3. Corrija un campo a propósito (p. ej. valor `10500`) → **Confirmar datos**. Compruebe: la operación toma el Incoterm confirmado; el *Legajo* marca **Factura ✔**; la bitácora registra «Confirmado por el usuario»; el campo *Valor* del formulario queda en 10500 listo para **Agregar ítem**.
4. Prueba negativa: abra una foto sin texto → no debe proponer valores inventados.

### Caso 11 — Contraste con una DIM real (prueba P-09 en pantalla)
Con la operación del Caso 1 liquidada, pestaña **Contraste con DIM**. Escriba como si la Aduana hubiera liquidado: GA `29197,20`, IVA `47982,68` → **Contrastar** → todas las filas **OK** y mensaje «Coincide con la DIM».
Cambie el IVA a `47990` → la fila IVA debe marcar **REVISAR** (diferencia 7,32) y el mensaje sugiere revisar parámetros. Cada contraste queda en la bitácora. **Para su prueba real:** cargue la operación con los mismos datos de la DIM (valores, flete, seguro, TC de esa fecha) y use los tributos del formulario liquidado.

### Caso 12 — Factura en PDF
Igual que el Caso 10, pero con `docs/ejemplos/factura-ejemplo.pdf` (cópielo de `tests/ComexBol.Documentos.Tests/fixtures/`). El visor muestra la **primera página**; el OCR lee **todas** (hasta 20). Sin Poppler instalado, el mensaje debe decir cómo instalarlo.

### Caso 13 — Exportar a Excel
**Excel…** → abra el `.xlsx`: hojas *Resumen, Ítems, Liquidación, Ruta crítica, Bitácora*. En *Liquidación* los totales son **fórmulas** (cambie un valor y se recalculan). Para el Caso 1: CIF 291.972,00; total tributos 77.179,88.

### Caso 14 — Expediente
**Expediente (.md)…** → guarda `Expediente-IMP-2026-001.md` con: resumen, mercancías, liquidación vigente, ruta, legajo y bitácora. Ábralo y compare con lo visto en pantalla.

---

## 4. Pruebas de aceptación (marque cada una)

| # | Prueba | Resultado esperado | ☐ |
|---|---|---|---|
| P-01 | Importar los 3 `.md` | 8.121 partidas / 97 capítulos | ☐ |
| P-02 | Contrastar 20 partidas con el PDF | GA, unidad y documento coinciden | ☐ |
| P-03 | Casos 1, 3, 4, 5 | cifras idénticas a las de este manual | ☐ |
| P-04 | Caso 7 | prohibida bloqueada; AGEMED exigida | ☐ |
| P-05 | Cambiar el TC y recalcular | la v2 de la liquidación queda en bitácora; la v1 se conserva | ☐ |
| P-06 | Cerrar y reabrir la aplicación | operaciones, ruta y bitácora persisten | ☐ |
| P-07 | Caso 10 con una factura real escaneada | propuesta razonable, nada se aplica sin confirmar | ☐ |
| P-08 | Exportar expediente y Excel | `.md` con 6 secciones; `.xlsx` con 5 hojas | ☐ |
| P-10 | Casos 2 y 11 en pantalla | tablas idénticas a las del manual | ☐ |
| P-11 | Caso 12 (PDF) | propuesta OCR igual que con la imagen | ☐ |
| P-09 | Contraste con una DIM real ya despachada | tributos de la app = tributos pagados (diferencia ≤ redondeo) | ☐ |

**P-09 es la más importante:** tome 3 importaciones ya liquidadas por la Aduana y repita el cálculo. Cualquier diferencia indica un parámetro normativo (sección 1.7) por corregir.

---

## 5. Limitaciones conocidas
- **Ventana WPF sin compilar** (ver estado). El visor muestra imágenes y la primera página de un PDF (no es un visor de PDF completo).
- **No hay pantalla** para: almacenaje, exportación (DEX/CEDEIM), moneda distinta de USD, gastos de origen / hasta frontera, ni para guardar los escenarios (se pierden al cerrar). Existen en el código y están probados.
- **Preferencias arancelarias** y **ICE** (salvo vehículos con las 6 tasas) y **IEHD**: entrada manual.
- **Mapeo a casillas SUMA**: no completado (requiere el instructivo vigente de la ANB). La compresión de imágenes y la exportación a PDF están pendientes (el Excel y el Markdown ya funcionan; el `.md` se imprime a PDF desde cualquier editor).
- El OCR depende de la calidad del escaneo; se equivoca con dígitos: siempre se confirma a mano.

## 6. Registro de hallazgos (llénelo durante las pruebas)
| Fecha | Caso | Qué pasó | Esperado | Captura |
|---|---|---|---|---|
| | | | | |
