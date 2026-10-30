# ContaBol — Manual de pruebas (aceptación) con ejemplos

Use una empresa de prueba nueva: **PRUEBA SRL**, gestión del año en curso. Marque ✔/✘ en cada caso. Cualquier ✘ debe reportarse con captura y el mensaje de error.

## A. Pruebas automáticas
```
dotnet test ContaBol.Tests      # esperado: Passed 57, Failed 0
```

## B. Humo (15 min)

| # | Acción | Resultado esperado |
|---|---|---|
| B1 | Abrir app, ingresar `admin/admin` | Pide cambio de clave |
| B2 | Crear empresa PRUEBA SRL | Se carga plan de cuentas; abre pantalla de inicio |
| B3 | Contabilidad > Plan de cuentas | Árbol de cuentas visible |
| B4 | Reportes > Centro de reportes (F9) | Lista de reportes por módulo |
| B5 | Abrir "Plan de cuentas" y exportar PDF y Excel | Ambos archivos se abren con encabezado de empresa |

## C. Tipo de cambio
Cargue 01/01: T.C. 6,96 y UFV 2,50000. Esperado: aparecen en el listado y en el reporte "Tipos de cambio y UFV".

## D. Contabilidad — ejemplo de comprobante
**Ingreso de capital**: Nuevo comprobante (Ctrl+N), tipo Traspaso, glosa "Aporte inicial".

| Cuenta | Debe | Haber |
|---|---|---|
| Caja moneda nacional | 50.000,00 | |
| Capital social | | 50.000,00 |

Esperado: no permite guardar si Debe ≠ Haber; guarda con número 1; el Libro diario y el Balance de sumas y saldos muestran 50.000 en cada lado.

**Prueba negativa**: Debe 100 / Haber 90 → mensaje de comprobante descuadrado, no se guarda.
**Anulación**: anular el comprobante → desaparece de saldos; permanece en listado como anulado.

## E. IVA — ejemplo del manual Orion
**Venta de Bs 1.000 con factura** (libro de ventas, con cuenta): Esperado en el asiento:

| Cuenta | Debe | Haber |
|---|---|---|
| Caja | 1.000,00 | |
| IVA débito fiscal (13%) | | 130,00 |
| Ventas | | 870,00 |
| Gasto IT | 30,00 | |
| IT por pagar | | 30,00 |

**Compra de Bs 500 con factura**: crédito fiscal 65,00 y gasto/compras 435,00. Verificar *Libro de compras*, *Libro de ventas* y *Resumen mensual de IVA e IT* (IVA a pagar = 130 − 65 = 65,00).
Prueba: NIT y número de autorización/factura duplicados deben ser advertidos.

## F. Inventarios
1. Cree almacén ALM1, unidad UN, ítem "Arroz 1kg".
2. Stock inicial: 100 u a costo 5,00 → existencias 100, valor 500.
3. Compra de 100 u a 7,00 (nota de compra) → existencias 200, **costo promedio 6,00**.
4. Venta de 50 u a 10,00 → costo de ventas 300,00 (50 × 6); existencias 150.
5. Kardex físico valorado: 3 movimientos, saldo final 150 u / 900,00.
6. Venta de más que el stock → advertencia/bloqueo según parámetro.
7. Ítem con vencimiento: dos lotes; la venta consume primero el que vence antes (FEFO). Reporte "Productos por vencer".

## G. Comercial
- Cliente "Cliente Uno" (crédito). Venta a crédito 1.000 → saldo por cobrar 1.000.
- Cobro parcial 400 → saldo 600; "Saldos por cobrar" y "Kardex de cliente" coinciden.
- Proveedor: compra a crédito 500, pago 500 → saldo 0.

## H. Activos fijos
Alta: "Computadora", costo 7.000, fecha 01/01, grupo Equipo de computación (vida útil 4 años, 25 %).
Depreciación del mes: 7.000 × 25 % / 12 = **145,83**. Verificar vista previa, registro (comprobante) y *Cuadro de activos fijos*. La actualización por UFV requiere UFV cargada en ambas fechas.

## I. Planillas
Empleado: sueldo 5.000, ingreso 2020. Genere planilla del mes.
Verificar: AFP laboral (aprox. 12,71 %, parámetro editable) ≈ 635,50; bono de antigüedad según escala; líquido pagable = ganado − descuentos; aportes patronales (≈ 16,71 %); boleta de pago PDF. *Valide las tasas contra la normativa vigente.*

## J. Costos / producción
Orden de producción: MP 300, MOD 100, CIF 50, cantidad 10 → costo total 450, **unitario 45,00**; al terminar, ingresa el producto terminado al inventario a 45.

## K. Bancos, centros de costo y presupuesto
Conciliación: marque los cheques cobrados; saldo según libros − pendientes = saldo banco. Presupuesto: asigne 1.000 a un gasto, contabilice 400 → ejecución 40 %.

## L. Cierre de gestión
1. *Cierre y ajustes > Ajuste por inflación*: **Vista previa**, revisar, luego Registrar.
2. *Diferencia de cambio* con T.C. final distinto: vista previa y registro.
3. *Generar asiento de cierre*: cuentas de resultado quedan en 0.
4. *Cerrar la gestión*: intente registrar un comprobante → debe rechazarlo (solo lectura).
5. *Abrir nueva gestión* (año siguiente): verifique asiento de apertura, existencias iniciales y saldos de clientes/proveedores iguales a los del cierre. El balance de apertura debe cuadrar.

## M. Multiempresa
Cree empresa 2 y registre un comprobante distinto; cambie entre empresas (Archivo > Cambiar). Los datos no deben mezclarse. *Consolidación*: marque ambas y compare el total con la suma manual.

## N. Seguridad
- Cree usuario con rol "Consulta": no debe poder crear comprobantes (opciones del menú deshabilitadas).
- Intente 3 ingresos con clave errónea → mensaje de credenciales inválidas, queda en auditoría.
- *Auditoría*: aparecen los comprobantes creados/anulados con usuario y hora.

## O. Respaldo y recuperación
1. Respaldo completo → archivo `.cbk`.
2. Registre un comprobante nuevo (y anote el total del libro diario).
3. Restaure el respaldo → el comprobante nuevo ya no existe.
4. Dañe un byte del `.cbk` (copia) → la restauración debe rechazarlo por falla de verificación.
5. Salga de la app: se genera respaldo automático.

## P. Importación Orion4
Con una carpeta de gestión Orion4 real: importar → comparar total de cuentas, cantidad de comprobantes y balance de sumas y saldos contra Orion. Anotar diferencias.

## Q. Reportes PDF/Excel — lista de control
Para cada módulo abra al menos un reporte y verifique: encabezado (empresa, NIT, período), totales correctos, paginación con encabezado repetido, firmas, exportación Excel con columnas numéricas (no texto) y que PDF/Excel coincidan.

## R. Rendimiento y límites
Genere 20.000 comprobantes de prueba (script o importación): el listado debe abrir en < 5 s, el mayor de una cuenta en < 10 s. Revise *Utilitarios > Verificación* para el tamaño del archivo.

## Registro de resultados

| Caso | Fecha | Probador | ✔/✘ | Observaciones |
|---|---|---|---|---|
