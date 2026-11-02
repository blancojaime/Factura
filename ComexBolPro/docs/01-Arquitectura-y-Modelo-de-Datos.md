# COMEX JB — Arquitectura y Modelo de Datos

## 1. Principios
1. **La norma es dato, no código.** Alícuotas, umbrales (Bs 50.000), IVA efectivo, plazos, tarifas y mapeos SUMA viven en tablas con *vigencia* (`ParametrosNormativos`, `MapeoSuma`). Un decreto nuevo = fila nueva, sin recompilar.
2. **Núcleo puro y testeable** (`ComexBol.Core`, sin UI ni BD): liquidación, Incoterms, CPM. Ya implementado y con tests en este repo.
3. **Offline-first**: SQLite local por defecto; sincronización opcional (cola de cambios) para tipo de cambio BCB, UFV y aranceles.
4. **Todo cálculo es auditable**: cada liquidación guarda los parámetros y el tipo de cambio usados (reproducible).

## 2. Capas (.NET 8)
```
ComexBol.App (WPF + Fluent, MVVM / CommunityToolkit.Mvvm)
 ├─ ComexBol.Core        dominio + cálculo (implementado)
 ├─ ComexBol.Data        EF Core 8 + SQLite (SQL Server Express opcional vía proveedor)
 ├─ ComexBol.Documentos  OCR (Tesseract), PDF (QuestPDF), XLSX (ClosedXML), compresión (PdfSharp/ImageSharp)
 └─ ComexBol.Suma        exportadores DIM/DEX/DIMS/DAM/DZFI según mapeo configurable
```
WPF se elige sobre MAUI/WinUI 3 por madurez en escritorio de alta densidad de datos (DataGrid, visor dual). Tema claro/oscuro con Segoe UI.

## 3. Modelo Entidad-Relación (texto)
```
Empresa 1─* Usuario
Empresa 1─* Operacion
Operacion (Id, Tipo[IMP|EXP], Carpeta, Estado, Incoterm, MonedaFactura, TipoCambioId,
           AduanaDespacho, Modalidad[GENERAL|ANTICIPADO|INMEDIATO], Regimen[CONSUMO|RITEX|ADM_TEMPORAL|MENAJE|ZF],
           ProveedorId, ConsignatarioId, DeclanteId, PaisProcedencia, ModoTransporte,
           FleteUsd, SeguroUsd, GastosOrigen, OtrosGastosFrontera, Deducciones,
           BancarizacionRequerida, EntidadFinanciera, NroComprobantePago, FechaCreacion)
Operacion 1─* ItemsMercancia
ItemsMercancia (Id, OperacionId, Numero, CodigoNandina[10], Descripcion, PaisOrigen, AcuerdoPreferencial,
           Embalaje, Bultos, Cantidad, UnidadMedida, PesoBruto, PesoNeto, ValorFactura,
           AlicuotaGA, Desgravacion, AlicuotaICE, ICEEspecifico, IEHDBsLitro, Litros)
Operacion 1─* TributosLiquidacion            -- una fila por ítem + fila total
TributosLiquidacion (Id, OperacionId, ItemId?, Version, FobBob, CifBob, GA, ICE, IEHD, OtrasErogaciones, IVA,
           Total, CifUfv, ParametrosJson, TipoCambioFecha, TipoCambioValor, CalculadoEn)
Operacion 1─* DocumentosSoporte
DocumentosSoporte (Id, OperacionId, Tipo[FACTURA|EMBARQUE|PACKING|AUT_PREVIA|SEGURO|ASPB|FLETE|ORIGEN|BANCARIO|OTRO],
           RutaArchivo, Hash, Paginas, Tamano, OcrJson, ConfianzaOcr, Validado, ItemsVinculados)
Operacion 1─* RutaCriticaEtapas
RutaCriticaEtapas (Id, OperacionId, Codigo, Nombre, Responsable, Predecesores, DuracionPlan, FechaInicioPlan,
           FechaFinPlan, FechaFinReal, Semaforo, EsHitoLegal, PlazoLegalDias, Holgura, EsCritica, Notas)
Operacion 1─* Alertas (Id, OperacionId, EtapaId?, Severidad, Mensaje, Vence, Atendida)

-- Catálogos / normativa (con vigencia)
ParametrosNormativos (Clave, Valor, VigenteDesde, VigenteHasta, BaseLegal)   -- IVA 14,94, Bs 50.000, límites CEDEIM...
Nandina (Codigo10, Descripcion, GA, ICE?, Unidad, Prohibida, RequiereAutorizacion[], Version)
AcuerdosComerciales (Codigo[CAN|ACE22|ACE36|ACE47], Nombre) 1─* Desgravaciones (Codigo10, Acuerdo, PorcentajeAnio, Anio)
TiposCambio (Fecha, Moneda, BobPorUnidad, Fuente[BCB|Manual]);  Ufv (Fecha, ValorBob)
TarifasAlmacenaje (Recinto, DiasLibres, BsTonDia, Minimo, Vigencia)
MapeoSuma (Formulario, CampoApp, CasillaOficial, Seccion, Tipo, Formato, Obligatorio, VigenteDesde)
```
Índices: `Operacion(Carpeta)` único por empresa; `Nandina(Codigo10)`; `TiposCambio(Fecha,Moneda)`.

## 4. Módulo 1 — reglas implementadas (`Liquidacion.cs`)
| Regla | Fórmula |
|---|---|
| Valor en aduana | Σ factura + adiciones que el Incoterm **no** incluye − deducciones post-frontera (DAP/DPU/DDP) |
| GA | `CIF_i × alícuota × (1 − desgravación)` (alícuota validada 0–40 %) |
| ICE | `(CIF_i + GA_i) × ad valorem + tasa específica × unidades` |
| IEHD | `Bs/litro × litros` |
| IVA | `14,94 % × (CIF + GA + ICE + IEHD + otras erogaciones)` |
| Bancarización | FOB en Bs ≥ 50.000 → exige respaldo (D.S. 772) |
| Prorrateo | flete/seguro/gastos por valor (o peso bruto), cada tributo redondeado por ítem |

Complementos: `Viabilidad` (costo puesto en almacén, margen neto de IVA), `Almacenaje`, `Exportacion.CedeimEstimado`, `Ufv.DeBob`.

## 5. Módulo 2 — ruta crítica
`RutaCritica.Calcular` implementa CPM (ES/EF/LS/LF/holgura, detección de ciclos). Plantillas de importación (I01–I12) y exportación (E01–E08) con duraciones **editables**. Semáforo: Cumplido / En curso / Alerta (< 20 % del plazo restante) / Vencido. Los plazos legales se leen de `ParametrosNormativos`.

## 6. Módulo 4 — expediente digital
Carpeta por embarque → clasificación por tipo (reglas por nombre + palabras clave OCR) → Tesseract (spa) extrae N.º factura, proveedor, Incoterm, pesos, bultos → los campos **se proponen**, el usuario confirma en el visor dual (nunca se precargan sin revisión) → compresión (JPG calidad adaptable / PDF reescalado) hasta el tope de cada portal (parámetro).

## 7. Supuestos a validar con un despachante antes de producción
- Base del ICE ad valorem y del IVA en importación, y redondeo (decimales vs. Bs enteros): configurable (`ModoRedondeo`).
- Qué gastos entran al valor en aduana (puerto → frontera) y el seguro presunto sin póliza.
- Límite porcentual del CEDEIM y alícuotas vigentes: son parámetros, no están fijos.
- Plazos legales de DIM/almacenaje y trámites VUCE: cargar desde la normativa vigente.
- Tipo de cambio aplicable a la fecha de la DIM: la tabla guarda la fecha.
