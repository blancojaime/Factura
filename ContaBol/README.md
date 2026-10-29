# ContaBol — Sistema Contable Integrado (Bolivia)

Sistema contable comercial y de costos para Windows, inspirado en Orion4 y conforme a la normativa
contable e impositiva boliviana. VB.NET (.NET 8, WinForms) sobre bases de datos MS Access.

## Características
- **Multiempresa y multigestión**: una base Access por empresa y gestión (`Datos\<EMPRESA>\<AÑO>.accdb`) más `Sistema.accdb` maestro. Evita el límite de 2 GB de Access.
- **Contabilidad** bimonetaria Bs/US$: plan de cuentas, comprobantes (ingreso/egreso/traspaso), libro diario, mayor, sumas y saldos, balance general, estado de resultados, flujo de efectivo, índices, bancos y conciliación, centros de costo, presupuesto.
- **Impuestos**: libros de compras y ventas IVA (13%), IT 3%, débito/crédito fiscal, RC-IVA de dependientes.
- **Comercial**: clientes/proveedores, notas de venta y compra con asiento automático, cobros y pagos, kardex de terceros.
- **Inventarios**: costo promedio ponderado, lotes con vencimiento (FEFO), kardex físico valorado, traspasos, ajustes, listas de precios.
- **Activos fijos**: depreciación (D.S. 24051) y actualización por UFV. **Planillas**: sueldos, antigüedad, AFP, aguinaldo, RC-IVA.
- **Costos**: órdenes de producción (MP, MOD, CIF).
- **Cierre**: ajuste por inflación, diferencia de cambio, asiento de cierre, apertura de nueva gestión con saldos trasladados, consolidación de empresas.
- **Reportes PDF y Excel** en todos los módulos (57 informes, Centro de reportes F9).
- **Seguridad**: usuarios, roles y permisos por empresa, auditoría. **Respaldo** `.cbk` con verificación SHA-256 y restauración. **Importador** desde Orion4.

## Requisitos
- Windows 10/11 y [Microsoft Access Database Engine](https://www.microsoft.com/download/details.aspx?id=54920) (la edición x64/x86 debe coincidir con la de la aplicación).
- Para compilar: SDK de .NET 8.

## Compilar y publicar
```
dotnet test ContaBol.Tests
publicar.bat x64
```

## Primer uso
1. Ingrese con usuario `admin` / clave `admin`; se obliga a cambiar la clave.
2. Cree la empresa (razón social, NIT, año de la gestión); se carga el plan de cuentas boliviano.
3. Cargue el tipo de cambio y la UFV (Contabilidad > Tipos de cambio y UFV).
4. Revise Administración > Parámetros (cuentas contables y datos de planillas).

## Estado de verificación
El núcleo (servicios y reportes) está cubierto por 57 pruebas automáticas ejecutadas sobre SQLite.
El proveedor Access/ACE y la interfaz WinForms compilan pero **no se han podido ejecutar en este entorno (sin Windows/Access)**; pruébelos antes de uso productivo.
Los parámetros legales de planillas (SMN, tasas AFP, etc.) son editables y deben validarse con la normativa vigente.
