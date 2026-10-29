Namespace Data

    ''' <summary>
    ''' Esquemas de las bases de datos de ContaBol.
    '''  - Sistema (maestra): empresas, gestiones, usuarios, permisos, auditoría.
    '''  - Gestión: una base de datos por empresa y gestión (año), con toda la contabilidad y módulos comerciales.
    ''' Separar por empresa y gestión mantiene cada archivo Access muy por debajo del límite de 2 GB.
    ''' </summary>
    Public Module Schemas

        Public Const VersionEsquema As Integer = 1

        Public Function Maestra() As SchemaDef
            Dim s As New SchemaDef()

            s.Table("ConfigGlobal").Txt("Clave", 60, True).Txt("Valor", 255).Uniq("Clave")

            s.Table("Empresa").
                Txt("Codigo", 12, True).Txt("RazonSocial", 150, True).Txt("NombreComercial", 100).
                Txt("Nit", 20).Txt("Direccion", 200).Txt("Ciudad", 60).Txt("Telefono", 40).Txt("Email", 100).
                Txt("Actividad", 150).Txt("RepLegal", 100).Txt("Matricula", 30).Txt("Carpeta", 60, True).
                Dt("FechaCreacion", True).Flag("Activa").Flag("EsDefecto").Txt("Observacion", 255).
                Uniq("Codigo")

            s.Table("Gestion").
                Ref("EmpresaId", "Empresa").Int("Anio", True).Dt("FechaInicio", True).Dt("FechaFin", True).
                Txt("Archivo", 200, True).Txt("Estado", 1, True).Flag("CorrelativoMensual").Int("MesInicio", True).
                Flag("EsDefecto").Dt("FechaCreacion", True).Dt("FechaCierre").
                Uniq("EmpresaId", "Anio")

            s.Table("Usuario").
                Txt("Login", 30, True).Txt("Nombre", 100, True).Txt("Hash", 200, True).Txt("Salt", 100, True).
                Flag("Activo").Flag("EsAdmin").Flag("CambiarClave").Txt("Email", 100).Dt("UltimoAcceso").
                Int("Intentos", True).Uniq("Login")

            s.Table("UsuarioEmpresa").
                Ref("UsuarioId", "Usuario").Ref("EmpresaId", "Empresa").Txt("Rol", 20, True).
                Uniq("UsuarioId", "EmpresaId")

            s.Table("Permiso").
                Ref("UsuarioId", "Usuario").Ref("EmpresaId", "Empresa").Txt("Opcion", 50, True).
                Uniq("UsuarioId", "EmpresaId", "Opcion")

            s.Table("Auditoria").
                Dt("Fecha", True).Int("UsuarioId", True).Txt("Login", 30).Int("EmpresaId", True).Int("GestionId", True).
                Txt("Modulo", 40).Txt("Accion", 40).Txt("Detalle", 255).Txt("Equipo", 60).Idx("Fecha")

            s.Table("RegistroBackup").
                Dt("Fecha", True).Txt("Tipo", 20).Txt("Archivo", 255).Int("EmpresaId", True).
                Txt("Resultado", 255).Dbl("TamanoMb")

            Return s
        End Function

        Public Function Gestion() As SchemaDef
            Dim s As New SchemaDef()

            s.Table("Parametro").Txt("Clave", 60, True).Txt("Valor", 255).Uniq("Clave")
            s.Table("Secuencia").Txt("Clave", 40, True).Int("Valor", True).Uniq("Clave")

            s.Table("TipoCambio").Dt("Fecha", True).Dbl("Usd").Dbl("Ufv").Uniq("Fecha")

            s.Table("TipoComprobante").
                Txt("Codigo", 3, True).Txt("Nombre", 40, True).Flag("Sistema").Flag("Activo").Uniq("Codigo")

            s.Table("CentroCosto").
                Txt("Codigo", 15, True).Txt("Nombre", 80, True).Txt("Tipo", 1, True).Flag("Activo").Uniq("Codigo")

            s.Table("Cuenta").
                Txt("Codigo", 20, True).Txt("Nombre", 120, True).Int("Nivel", True).Int("PadreId").
                Int("Rubro", True).Txt("Naturaleza", 1, True).Flag("EsMovimiento").Txt("Moneda", 3, True).
                Flag("Ajustable").Flag("Presupuestable").Txt("CostoTipo", 1).Flag("EsBanco").Flag("Activa").
                Uniq("Codigo").Idx("PadreId")

            s.Table("Comprobante").
                Ref("TipoId", "TipoComprobante").Int("Numero", True).Int("Mes", True).Dt("Fecha", True).
                Dbl("TC").Txt("Moneda", 3, True).Txt("Glosa", 255).Txt("Referencia", 80).Txt("Cheque", 30).
                Txt("Banco", 60).Txt("Estado", 1, True).Txt("Origen", 10).Int("OrigenId", True).
                Int("UsuarioId", True).Dt("Creado", True).Dt("Modificado").
                Mon("DebeBs").Mon("HaberBs").Mon("DebeUsd").Mon("HaberUsd").Txt("Observacion", 255).
                Uniq("TipoId", "Mes", "Numero").Idx("Fecha").Idx("Origen", "OrigenId")

            s.Table("ComprobanteDet").
                Ref("ComprobanteId", "Comprobante").Int("Linea", True).Ref("CuentaId", "Cuenta").Dt("Fecha", True).
                Txt("Glosa", 255).Mon("DebeBs").Mon("HaberBs").Mon("DebeUsd").Mon("HaberUsd").
                Int("CentroCostoId").Int("TerceroId").Txt("Cheque", 30).Flag("Conciliado").Dt("FechaConcil").
                Flag("Vigente").Idx("ComprobanteId").Idx("CuentaId", "Fecha")

            s.Table("Tercero").
                Txt("Codigo", 20, True).Txt("Nombre", 150, True).Txt("Nit", 20).Txt("Direccion", 200).
                Txt("Ciudad", 60).Txt("Telefono", 40).Txt("Email", 100).Txt("Actividad", 100).Txt("Contacto", 80).
                Flag("EsCliente").Flag("EsProveedor").Mon("LimiteCredito").Int("DiasCredito", True).Txt("NivelPrecio", 1).
                Int("CuentaCxcId").Int("CuentaCxpId").Int("CuentaAnticipoId").Flag("Activo").Dt("Creado", True).
                Uniq("Codigo").Idx("Nombre")

            s.Table("MovTercero").
                Ref("TerceroId", "Tercero").Txt("Clase", 3, True).Dt("Fecha", True).Txt("Tipo", 4, True).
                Txt("DocTipo", 10).Int("DocId", True).Txt("Referencia", 40).Txt("Detalle", 150).
                Mon("Debe").Mon("Haber").Dbl("TC").Int("ComprobanteId", True).Flag("Vigente").
                Idx("TerceroId", "Clase", "Fecha").Idx("DocTipo", "DocId")

            s.Table("Vendedor").Txt("Nombre", 80, True).Txt("Ci", 20).Txt("Telefono", 40).Dbl("ComisionPct").Flag("Activo")
            s.Table("Sucursal").Txt("Codigo", 10, True).Txt("Nombre", 80, True).Txt("Direccion", 150).Flag("Activa").Uniq("Codigo")

            ' ---------- Inventarios ----------
            s.Table("UnidadMedida").Txt("Codigo", 10, True).Txt("Nombre", 40, True).Uniq("Codigo")
            s.Table("Almacen").Txt("Codigo", 10, True).Txt("Nombre", 60, True).Txt("Direccion", 120).Flag("Activo").Uniq("Codigo")
            s.Table("GrupoItem").Txt("Codigo", 10, True).Txt("Nombre", 60, True).Uniq("Codigo")

            s.Table("Item").
                Txt("Codigo", 25, True).Txt("Descripcion", 150, True).Txt("Abrev", 30).Ref("GrupoId", "GrupoItem", False).
                Ref("UnidadId", "UnidadMedida", False).Flag("EsServicio").Flag("ManejaVenc").Txt("Moneda", 3, True).
                Dbl("UtilidadPct").Dbl("StockMin").Int("CuentaInvId").Int("CuentaIngId").Int("CuentaCostoId").
                Dbl("PrecioA").Dbl("PrecioB").Dbl("PrecioC").Dbl("PrecioD").Dbl("PrecioE").Dbl("PrecioF").Dbl("PrecioG").
                Txt("CodBarra", 40).Txt("Marca", 40).Flag("Activo").Dbl("Stock").Dbl("CostoProm").Dbl("UltimoCosto").
                Txt("Observacion", 255).Uniq("Codigo").Idx("Descripcion")

            s.Table("MovInv").
                Txt("Tipo", 4, True).Int("Numero", True).Dt("Fecha", True).Ref("AlmacenId", "Almacen").
                Int("AlmacenDestId").Int("TerceroId").Txt("Moneda", 3, True).Dbl("TC").Txt("Detalle", 200).
                Txt("Estado", 1, True).Txt("DocTipo", 10).Int("DocId", True).Int("ComprobanteId", True).
                Int("UsuarioId", True).Dt("Creado", True).Mon("TotalBs").
                Uniq("Tipo", "Numero").Idx("Fecha").Idx("DocTipo", "DocId")

            s.Table("MovInvDet").
                Ref("MovId", "MovInv").Int("Linea", True).Ref("ItemId", "Item").Ref("AlmacenId", "Almacen").
                Dt("Fecha", True).Int("Signo", True).Dbl("Cantidad").Dbl("PrecioUnit").Dbl("CostoUnitBs").Mon("ImporteBs").
                Dt("FechaVenc").Txt("Lote", 30).Flag("Vigente").
                Idx("MovId").Idx("ItemId", "Fecha").Idx("AlmacenId")

            ' ---------- Comercial ----------
            s.Table("FacturaIva").
                Txt("Libro", 1, True).Dt("Fecha", True).Int("Mes", True).Txt("NroFactura", 20, True).Txt("Autorizacion", 60).
                Txt("CodControl", 20).Txt("Nit", 20).Txt("RazonSocial", 150).Int("TerceroId").
                Mon("ImporteTotal").Mon("NoSujeto").Mon("Exento").Mon("TasaCero").Mon("Subtotal").Mon("Descuento").
                Mon("GiftCard").Mon("BaseCf").Mon("Impuesto").Txt("Estado", 1, True).Txt("TipoOp", 2).Txt("Dui", 25).
                Txt("Sucursal", 10).Int("ComprobanteId", True).Txt("Origen", 10).Int("OrigenId", True).
                Int("UsuarioId", True).Dt("Creado", True).Idx("Libro", "Fecha").Idx("Libro", "NroFactura")

            s.Table("Venta").
                Txt("Tipo", 3, True).Int("Numero", True).Dt("Fecha", True).Ref("ClienteId", "Tercero").
                Ref("AlmacenId", "Almacen").Int("VendedorId").Txt("Moneda", 3, True).Dbl("TC").Txt("Detalle", 200).
                Mon("SubtotalBs").Mon("DescuentoBs").Mon("RecargoBs").Mon("TotalBs").Mon("AnticipoBs").Mon("ACuentaBs").
                Mon("SaldoBs").Mon("CostoBs").Flag("ConFactura").Txt("NroFactura", 20).Int("CuentaCobroId").
                Txt("Estado", 1, True).Int("MovInvId", True).Int("ComprobanteId", True).Int("ComprobanteCostoId", True).
                Int("ComprobanteItId", True).Dt("Vencimiento").Int("UsuarioId", True).Dt("Creado", True).
                Uniq("Tipo", "Numero").Idx("Fecha").Idx("ClienteId")

            s.Table("Aplicacion").
                Int("ComprobanteId", True).Txt("Clase", 3, True).Int("DocId", True).Dt("Fecha", True).Mon("Monto").
                Flag("Vigente").Idx("ComprobanteId").Idx("Clase", "DocId")

            s.Table("VentaDet").
                Ref("VentaId", "Venta").Int("Linea", True).Ref("ItemId", "Item").Txt("Descripcion", 150).
                Dbl("Cantidad").Dbl("PrecioUnit").Mon("ImporteBs").Dbl("CostoUnitBs").Idx("VentaId")

            s.Table("Compra").
                Txt("Tipo", 3, True).Int("Numero", True).Dt("Fecha", True).Ref("ProveedorId", "Tercero").
                Ref("AlmacenId", "Almacen").Txt("Moneda", 3, True).Dbl("TC").Txt("Detalle", 200).
                Mon("SubtotalBs").Mon("DescuentoBs").Mon("RecargoBs").Mon("TotalBs").Mon("AnticipoBs").Mon("ACuentaBs").
                Mon("SaldoBs").Mon("CreditoFiscalBs").Flag("ConFactura").Txt("NroFactura", 20).Txt("Autorizacion", 60).
                Int("CuentaPagoId").Txt("Estado", 1, True).Int("MovInvId", True).Int("ComprobanteId", True).
                Dt("Vencimiento").Int("UsuarioId", True).Dt("Creado", True).
                Uniq("Tipo", "Numero").Idx("Fecha").Idx("ProveedorId")

            s.Table("CompraDet").
                Ref("CompraId", "Compra").Int("Linea", True).Ref("ItemId", "Item").Txt("Descripcion", 150).
                Dbl("Cantidad").Dbl("PrecioUnit").Mon("ImporteBs").Dt("FechaVenc").Idx("CompraId")

            ' ---------- Activos fijos ----------
            s.Table("GrupoActivo").
                Txt("Nombre", 60, True).Int("VidaUtilAnios", True).Dbl("PorcDep").
                Int("CuentaActivoId").Int("CuentaDepAcumId").Int("CuentaGastoId")

            s.Table("ActivoFijo").
                Txt("Codigo", 20, True).Txt("Nombre", 150, True).Ref("GrupoId", "GrupoActivo", False).
                Int("CuentaActivoId", True).Int("CuentaDepAcumId", True).Int("CuentaGastoId", True).
                Dt("FechaAlta", True).Mon("ValorOriginal").Dbl("UfvAlta").Dbl("TcAlta").Dbl("Cantidad").
                Dbl("PorcDep").Mon("DepAcumInicial").Mon("ValorResidual").Txt("Ubicacion", 80).Txt("Responsable", 80).
                Txt("Serie", 40).Txt("Marca", 40).Dt("FechaBaja").Txt("MotivoBaja", 100).Txt("Estado", 1, True).
                Int("TerceroId").Txt("Factura", 30).Int("CentroCostoId").Txt("Observacion", 255).
                Uniq("Codigo")

            s.Table("DepreciacionAF").
                Ref("ActivoId", "ActivoFijo").Dt("Fecha", True).Txt("Periodo", 7, True).Dbl("UfvIni").Dbl("UfvFin").
                Mon("ValorAct").Mon("ActualizaValor").Mon("DepPeriodo").Mon("ActualizaDep").Mon("DepAcum").Mon("ValorNeto").
                Int("ComprobanteId", True).Idx("ActivoId", "Periodo")

            ' ---------- Planillas ----------
            s.Table("Empleado").
                Txt("Item", 10).Txt("Nombre", 120, True).Txt("Ci", 20).Dt("FechaIngreso", True).Dt("FechaNac").
                Txt("Cargo", 60).Mon("Haber").Txt("Nua", 20).Txt("Afp", 20).Txt("Banco", 40).Txt("CuentaBanco", 30).
                Txt("Estado", 1, True).Int("CentroCostoId").Txt("Email", 100).Txt("Telefono", 40).Txt("Direccion", 150).
                Flag("Eventual").Dt("FechaRetiro").Idx("Nombre")

            s.Table("PlanillaPeriodo").
                Int("Anio", True).Int("Mes", True).Txt("Tipo", 1, True).Dbl("TC").Txt("Estado", 1, True).
                Int("ComprobanteId", True).Mon("Smn").Dt("FechaCierre").Txt("Observacion", 255).
                Uniq("Anio", "Mes", "Tipo")

            s.Table("PlanillaDet").
                Ref("PeriodoId", "PlanillaPeriodo").Ref("EmpleadoId", "Empleado").Int("Dias", True).
                Mon("Haber").Mon("BonoAntig").Dbl("HorasExtras").Mon("MontoHorasExtras").Mon("BonoProd").Mon("BonoDom").
                Mon("OtrosIngresos").Mon("TotalGanado").
                Mon("AfpVejez").Mon("AfpRiesgo").Mon("AfpComision").Mon("AfpSolidario").Mon("Ans").Mon("TotalAfp").
                Mon("IngresoNeto").Mon("MinimoNoImp").Mon("BaseImponible").Mon("RcIvaBruto").Mon("Cred2Smn").
                Mon("Facturas").Mon("CredFacturas").Mon("SaldoAnterior").Mon("SaldoAnteriorAct").Mon("RcIvaRet").
                Mon("SaldoSiguiente").Mon("Anticipo").Mon("Prestamo").Mon("OtrosDesc").Mon("TotalDesc").Mon("Liquido").
                Mon("PatCns").Mon("PatRiesgoProf").Mon("PatVivienda").Mon("PatSolidario").Mon("TotalPatronal").
                Mon("ProvAguinaldo").Mon("ProvIndem").Idx("PeriodoId")

            s.Table("AnticipoSueldo").
                Ref("EmpleadoId", "Empleado").Int("Anio", True).Int("Mes", True).Dt("Fecha", True).
                Mon("Monto").Mon("Confirmado").Txt("Detalle", 100).Idx("Anio", "Mes")

            ' ---------- Costos y producción ----------
            s.Table("OrdenProd").
                Int("Numero", True).Dt("Fecha", True).Ref("ItemId", "Item").Dbl("Cantidad").Txt("Estado", 1, True).
                Int("AlmacenMpId", True).Int("AlmacenPtId", True).Txt("Detalle", 200).Mon("CostoMp").Mon("CostoMod").
                Mon("CostoCif").Mon("CostoTotal").Dbl("CostoUnit").Dt("FechaCierre").Int("ComprobanteId", True).
                Uniq("Numero")

            s.Table("OrdenProdMod").
                Ref("OrdenId", "OrdenProd").Ref("EmpleadoId", "Empleado").Dbl("Horas").Mon("CostoHora").Mon("Monto").
                Idx("OrdenId")

            s.Table("OrdenProdCif").
                Ref("OrdenId", "OrdenProd").Txt("Detalle", 100, True).Mon("Monto").Int("CuentaId").Idx("OrdenId")

            ' ---------- Presupuesto ----------
            s.Table("Presupuesto").Ref("CuentaId", "Cuenta").Int("Mes", True).Mon("MontoBs").Uniq("CuentaId", "Mes")

            Return s
        End Function

    End Module

End Namespace
