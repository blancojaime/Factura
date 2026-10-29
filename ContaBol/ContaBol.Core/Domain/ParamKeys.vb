Namespace Domain

    ''' <summary>Claves de la tabla Parametro (por gestión). Las cuentas se guardan por su código.</summary>
    Public Module ParamKeys
        ' Datos de la empresa (copia para reportes y consolidación)
        Public Const EmpNombre As String = "EMP_NOMBRE"
        Public Const EmpNit As String = "EMP_NIT"
        Public Const EmpDireccion As String = "EMP_DIRECCION"
        Public Const EmpCiudad As String = "EMP_CIUDAD"
        Public Const EmpGestion As String = "EMP_GESTION"

        ' Impuestos y reglas
        Public Const IvaPct As String = "IVA_PCT"
        Public Const ItPct As String = "IT_PCT"
        Public Const ItSinFactura As String = "IT_SIN_FACTURA"
        Public Const DescEnBase As String = "DESC_REC_EN_BASE"
        Public Const NivelImpresion As String = "NIVEL_IMPRESION"
        Public Const ControlPresupuesto As String = "CONTROL_PRESUPUESTO"
        Public Const StockNegativo As String = "STOCK_NEGATIVO"
        Public Const TcDefecto As String = "TC_DEFECTO"
        Public Const Redondeo As String = "REDONDEO"

        ' Cuentas del módulo contable / comercial
        Public Const CtaCaja As String = "CTA_CAJA"
        Public Const CtaCreditoFiscal As String = "CTA_CF_IVA"
        Public Const CtaDebitoFiscal As String = "CTA_DF_IVA"
        Public Const CtaItGasto As String = "CTA_IT_GASTO"
        Public Const CtaItPagar As String = "CTA_IT_PAGAR"
        Public Const CtaCxc As String = "CTA_CXC"
        Public Const CtaCxp As String = "CTA_CXP"
        Public Const CtaAnticipoCli As String = "CTA_ANT_CLI"
        Public Const CtaAnticipoProv As String = "CTA_ANT_PROV"
        Public Const CtaInventario As String = "CTA_INVENT"
        Public Const CtaVentas As String = "CTA_VENTAS"
        Public Const CtaCostoVentas As String = "CTA_COSTO_VTA"
        Public Const CtaDescVentas As String = "CTA_DESC_VEN"
        Public Const CtaRecVentas As String = "CTA_REC_VEN"
        Public Const CtaDescCompras As String = "CTA_DESC_COMP"
        Public Const CtaRecCompras As String = "CTA_REC_COMP"
        Public Const CtaMermas As String = "CTA_MERMAS"
        Public Const CtaAjusteInflIng As String = "CTA_AJUSTE_ING"
        Public Const CtaAjusteInflEgr As String = "CTA_AJUSTE_EGR"
        Public Const CtaDifCambioIng As String = "CTA_DIFCAMBIO_ING"
        Public Const CtaDifCambioEgr As String = "CTA_DIFCAMBIO_EGR"
        Public Const CtaResultadoGestion As String = "CTA_RESULTADO"
        Public Const CtaResultadoAcum As String = "CTA_RESULT_ACUM"

        ' Producción
        Public Const CtaMateriaPrima As String = "CTA_MP"
        Public Const CtaProdTerminados As String = "CTA_PT"
        Public Const CtaMano As String = "CTA_MOD"
        Public Const CtaCif As String = "CTA_CIF"

        ' Activos fijos
        Public Const CtaAjusteAf As String = "CTA_AJUSTE_AF"

        ' Planillas
        Public Const Smn As String = "SMN"
        Public Const CtaSueldos As String = "CTA_SUELDOS"
        Public Const CtaBonoAntig As String = "CTA_BONO_ANTIG"
        Public Const CtaHorasExtras As String = "CTA_HEXTRAS"
        Public Const CtaOtrosBonos As String = "CTA_OTROS_BONOS"
        Public Const CtaSueldosPagar As String = "CTA_SUELDOS_PAGAR"
        Public Const CtaAfpLaboralPagar As String = "CTA_AFP_LAB_PAGAR"
        Public Const CtaAfpPatronalPagar As String = "CTA_AFP_PAT_PAGAR"
        Public Const CtaCnsPagar As String = "CTA_CNS_PAGAR"
        Public Const CtaViviendaPagar As String = "CTA_VIVIENDA_PAGAR"
        Public Const CtaSolidarioPagar As String = "CTA_SOLIDARIO_PAGAR"
        Public Const CtaRcIvaPagar As String = "CTA_RCIVA_PAGAR"
        Public Const CtaAnticipoPers As String = "CTA_ANTICIPO_PERS"
        Public Const CtaGastoCns As String = "CTA_GASTO_CNS"
        Public Const CtaGastoRiesgo As String = "CTA_GASTO_RIESGO"
        Public Const CtaGastoVivienda As String = "CTA_GASTO_VIVIENDA"
        Public Const CtaGastoSolidario As String = "CTA_GASTO_SOLIDARIO"
        Public Const CtaGastoAguinaldo As String = "CTA_GASTO_AGUINALDO"
        Public Const CtaProvAguinaldo As String = "CTA_PROV_AGUINALDO"
        Public Const CtaGastoIndem As String = "CTA_GASTO_INDEM"
        Public Const CtaProvIndem As String = "CTA_PROV_INDEM"

        Public Const PlAfpVejez As String = "PL_AFP_VEJEZ"
        Public Const PlAfpRiesgo As String = "PL_AFP_RIESGO"
        Public Const PlAfpComision As String = "PL_AFP_COMISION"
        Public Const PlAfpSolidario As String = "PL_AFP_SOLIDARIO"
        Public Const PlPatCns As String = "PL_PAT_CNS"
        Public Const PlPatRiesgo As String = "PL_PAT_RIESGO"
        Public Const PlPatVivienda As String = "PL_PAT_VIVIENDA"
        Public Const PlPatSolidario As String = "PL_PAT_SOLIDARIO"
        Public Const PlRcIvaPct As String = "PL_RCIVA_PCT"
        Public Const PlRcIvaMinSmn As String = "PL_RCIVA_MIN_SMN"
        Public Const PlRcIvaCredSmn As String = "PL_RCIVA_CRED_SMN"
        Public Const PlAnsTramo1 As String = "PL_ANS_T1"
        Public Const PlAnsTramo2 As String = "PL_ANS_T2"
        Public Const PlAnsTramo3 As String = "PL_ANS_T3"
        Public Const PlDiasMes As String = "PL_DIAS_MES"
    End Module

End Namespace
