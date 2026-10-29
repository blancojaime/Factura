''' <summary>Acceso abreviado a los servicios del contexto (empresa/gestión) activo.</summary>
Public Module Svc
    Public ReadOnly Property Cuentas As CuentaService
        Get
            Return New CuentaService(Sesion.Ctx)
        End Get
    End Property
    Public ReadOnly Property TipoCambio As TipoCambioService
        Get
            Return New TipoCambioService(Sesion.Ctx)
        End Get
    End Property
    Public ReadOnly Property Vouchers As VoucherService
        Get
            Return New VoucherService(Sesion.Ctx)
        End Get
    End Property
    Public ReadOnly Property Facturas As FacturaService
        Get
            Return New FacturaService(Sesion.Ctx)
        End Get
    End Property
    Public ReadOnly Property Terceros As TerceroService
        Get
            Return New TerceroService(Sesion.Ctx)
        End Get
    End Property
    Public ReadOnly Property Inventario As InventarioService
        Get
            Return New InventarioService(Sesion.Ctx)
        End Get
    End Property
    Public ReadOnly Property Ventas As VentaService
        Get
            Return New VentaService(Sesion.Ctx)
        End Get
    End Property
    Public ReadOnly Property Compras As CompraService
        Get
            Return New CompraService(Sesion.Ctx)
        End Get
    End Property
    Public ReadOnly Property CobrosPagos As CobroPagoService
        Get
            Return New CobroPagoService(Sesion.Ctx)
        End Get
    End Property
    Public ReadOnly Property ActivosFijos As ActivoFijoService
        Get
            Return New ActivoFijoService(Sesion.Ctx)
        End Get
    End Property
    Public ReadOnly Property Planillas As PlanillaService
        Get
            Return New PlanillaService(Sesion.Ctx)
        End Get
    End Property
    Public ReadOnly Property Produccion As ProduccionService
        Get
            Return New ProduccionService(Sesion.Ctx)
        End Get
    End Property
    Public ReadOnly Property Presupuesto As PresupuestoService
        Get
            Return New PresupuestoService(Sesion.Ctx)
        End Get
    End Property
    Public ReadOnly Property Bancos As BancoService
        Get
            Return New BancoService(Sesion.Ctx)
        End Get
    End Property
    Public ReadOnly Property Gestion As GestionService
        Get
            Return New GestionService(Sesion.Ctx)
        End Get
    End Property
    Public ReadOnly Property Ledger As LedgerService
        Get
            Return New LedgerService(Sesion.Ctx)
        End Get
    End Property
    Public ReadOnly Property Centros As CentroCostoService
        Get
            Return New CentroCostoService(Sesion.Ctx)
        End Get
    End Property
End Module
