# Mapeo COMEX JB → SUMA

> **Importante.** Las casillas oficiales (F8…F14, E11, E12, etc.) cambian con cada versión del formulario y no pueden asumirse de memoria. Por eso el mapeo es **datos** (`MapeoSuma`, archivo `suma-mapping.json`), no código. La columna *Casilla* debe completarse con el instructivo vigente de la ANB; la exportación falla con aviso si una casilla obligatoria queda sin asignar.

| Sección SUMA | Campo de la app | Origen | Validación | Casilla oficial |
|---|---|---|---|---|
| Cabecera | Aduana de despacho | `Operacion.AduanaDespacho` | catálogo ANB | _por asignar_ |
| Cabecera | Declarante / despachante | `Operacion.DeclaranteId` | NIT activo | _por asignar_ |
| Cabecera | Consignatario / importador | `Operacion.ConsignatarioId` | NIT activo | _por asignar_ |
| Cabecera | Modalidad (General/Anticipado/Inmediato) | `Operacion.Modalidad` | enum | _por asignar_ |
| Cabecera | Régimen (consumo, RITEX, adm. temporal, menaje) | `Operacion.Regimen` | enum + docs requeridos | _por asignar_ |
| Factura | Proveedor y país de adquisición | `Proveedor` | obligatorio | _por asignar_ |
| Factura | N.º y fecha de factura | `DocumentosSoporte` (OCR) | confirmado por usuario | _por asignar_ |
| Valor | Valor FOB / factura | Σ `ItemsMercancia.ValorFactura` | > 0 | _por asignar_ |
| Valor | Flete internacional (I y II), seguro, recargos | `Operacion.Flete/Seguro/Gastos` | según Incoterm | _por asignar_ |
| Valor | Bancarización (entidad, comprobante) | `Operacion.EntidadFinanciera` | obligatorio si FOB ≥ Bs 50.000 | _por asignar_ |
| Ítem | Código arancelario | `CodigoNandina` | 10 dígitos, existe en catálogo | _por asignar_ |
| Ítem | Descripción comercial | `Descripcion` | no genérica | _por asignar_ |
| Ítem | País de origen / acuerdo preferencial | `PaisOrigen`, `AcuerdoPreferencial` | certificado de origen adjunto | _por asignar_ |
| Ítem | Embalaje (pallet GNN-REG-07), bultos | `Embalaje`, `Bultos` | coincide con packing list | _por asignar_ |
| Ítem | Cantidad, peso bruto y neto | `Cantidad`, `PesoBruto`, `PesoNeto` | neto ≤ bruto | _por asignar_ |
| Liquidación | GA, ICE, IEHD, IVA, total | `TributosLiquidacion` | recalcula y compara | _por asignar_ |

**Formularios:** DIM, DIMS, DEX, DAM, DZFI comparten el motor; cada uno es un conjunto de filas de `MapeoSuma` con su `Formulario`.
**Salidas:** (1) PDF borrador homologado, (2) XLSX/CSV campo-por-campo para copiar, (3) JSON estructurado. Nunca se envía nada a SUMA automáticamente: es un borrador para transcripción revisada.
