# Wireframe textual — Ventana principal

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ COMEX JB   [Carpeta: IMP-2026-0142 ▾]  Empresa: ACME SRL        TC BCB 6,96 (01/11) 🔄 ☀/🌙 │
├───────────┬──────────────────────────────────────────────────────────────────────────────────┤
│ NAVEGACIÓN│  Pestañas: [Resumen] [Ítems] [Liquidación] [Ruta crítica] [Expediente] [SUMA]     │
│           ├───────────────────────────────┬──────────────────────────────────────────────────┤
│ ▸ Panel   │  VISOR DE DOCUMENTO           │  FORMULARIO DE CAPTURA (DIM)                     │
│ ▸ Operac. │  ┌─────────────────────────┐  │  Cabecera ▸ Factura ▸ Valor ▸ Ítems ▸ Tributos   │
│   Import. │  │  Factura.pdf  p.1/2     │  │  Proveedor      [ SHENZHEN TECH ]  ◔ OCR 94%     │
│   Export. │  │  (zoom, rotar, resaltar │  │  N.º factura    [ INV-88213    ]  ✔ confirmado   │
│ ▸ Simulad.│  │   zona → asigna campo)  │  │  Incoterm       [ FOB ▾ ]                        │
│ ▸ Ruta    │  │                         │  │  Valor factura  [ 10.000,00 USD ]                │
│ ▸ Catálog.│  └─────────────────────────┘  │  ⚠ FOB ≥ Bs 50.000: complete bancarización       │
│ ▸ Config. │  Miniaturas: [Fact][B/L][PL]… │  [Guardar] [Calcular] [Exportar borrador SUMA ▾]  │
├───────────┴───────────────────────────────┴──────────────────────────────────────────────────┤
│ RUTA CRÍTICA ●Clasif ●VUCE ●Compra ●Flete ◐Embarque ○Manifiesto ○Tránsito ○PRM ○DIM ○Pago ○Canal │
│ Semáforo: 🟢 6  🟡 1  🔴 0   Próximo vencimiento: Autorización SENASAG en 3 d   Crítica: 31 d      │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ Estado: Guardado 14:32 · Offline · Última sync 01/11 · Parámetros normativos v2026.11          │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Interacciones clave
- **Visor dual**: arrastrar una selección del documento sobre un campo del formulario lo rellena (OCR de la zona) y lo marca *pendiente de confirmar*; nada se acepta sin check manual.
- **Simulador** (pestaña Liquidación): panel izquierdo con entradas (Incoterm, flete, seguro, TC); derecho con cascada FOB → CIF → GA → ICE → IEHD → IVA → total, costo unitario y margen; modo "comparar escenarios" (p. ej. FOB vs. CIF vs. DAP).
- **Ruta crítica**: Gantt con barras críticas en rojo, hitos legales con rombo, arrastre para replanificar (recalcula CPM), alertas en centro de notificaciones.
- **Expediente**: lista de requisitos del legajo con ✔/✖ según tipo de operación y régimen; compresión por lote con tamaño objetivo.
- **Teclado**: Ctrl+K paleta de comandos, F5 calcular, Ctrl+E exportar, Ctrl+1…6 pestañas. Densidad compacta/normal, contraste AA, tablas con ordenar/filtrar/pegar desde Excel.
