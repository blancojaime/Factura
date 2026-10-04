Attribute VB_Name = "modProcurement"
'==============================================================================
' SIC-MUNI - modProcurement  (Modulo 1: Gestor Express de Solicitud y Cotizacion)
' Umbrales parametrizables en CONFIG (no hardcodeados):
'   TopeContratacionMenor = 50000   TopeSinCuadroComparativo = 20000
'   MinCotizaciones = 3
' Estados de SOLICITUDES.Estado:
'   BORRADOR > EN_COTIZACION > EVALUADA > PRESUPUESTADA > ADJUDICADA > ORDEN_EMITIDA | ANULADA
'==============================================================================
Option Explicit

Public Function ModalidadPorMonto(ByVal monto As Double) As String
    Dim tope As Double, sinCuadro As Double
    tope = CfgNum("TopeContratacionMenor", 50000)
    sinCuadro = CfgNum("TopeSinCuadroComparativo", 20000)
    If monto <= 0 Then
        ModalidadPorMonto = "SIN MONTO"
    ElseIf monto <= sinCuadro Then
        ModalidadPorMonto = "CONTRATACION MENOR"
    ElseIf monto <= tope Then
        ModalidadPorMonto = "CONTRATACION MENOR CON INVITACION Y CUADRO COMPARATIVO"
    Else
        ModalidadPorMonto = "FUERA DE ALCANCE (ANPE/LICITACION)"
    End If
End Function

Public Function CotizacionesRequeridas(ByVal monto As Double) As Long
    If monto > CfgNum("TopeSinCuadroComparativo", 20000) Then
        CotizacionesRequeridas = CLng(CfgNum("MinCotizaciones", 3))
    Else
        CotizacionesRequeridas = 1
    End If
End Function

'------------------------------------------------------------------------------
' SOLICITUD
'------------------------------------------------------------------------------
Public Function CrearSolicitud(ByVal codDA As String, ByVal codUE As String, _
                               ByVal justificacion As String) As String
    Dim sh As Worksheet, r As Long, n As Long
    RequirePermiso P_SOLICITUD
    If Len(Trim$(justificacion)) < 20 Then Fail "Justificacion insuficiente."
    If g_Rol = ROL_US And codDA <> g_DA Then Fail "Solo puede crear solicitudes de su propia Direccion Administrativa."
    Set sh = WS(SH_SOL)
    n = NextSeq("SOL")
    r = NewRow(sh)
    SetV sh, r, "ID_Solicitud", FormatCorrelativo("SOL", n)
    SetV sh, r, "Correlativo", n
    SetV sh, r, "Fecha", Date
    SetV sh, r, "Cod_DA", codDA
    SetV sh, r, "Cod_UE", codUE
    SetV sh, r, "Solicitante", g_Nombre
    SetV sh, r, "Justificacion", justificacion
    SetV sh, r, "Estado", "BORRADOR"
    SetV sh, r, "MontoReferencial", 0
    SetV sh, r, "Modalidad", "SIN MONTO"
    CrearSolicitud = CStr(GetV(sh, r, "ID_Solicitud"))
    LogAudit "SOLICITUD_CREADA", CrearSolicitud
End Function

Public Function FilaSolicitud(ByVal idSol As String) As Long
    FilaSolicitud = FindRow(WS(SH_SOL), "ID_Solicitud", idSol)
    If FilaSolicitud = 0 Then Fail "Solicitud " & idSol & " no existe."
    If Not PuedeVerSolicitud(CStr(GetV(WS(SH_SOL), FilaSolicitud, "Cod_DA"))) Then Fail "Sin acceso a solicitudes de otra Direccion Administrativa."
End Function

Public Sub CambiarEstadoSolicitud(ByVal idSol As String, ByVal nuevo As String)
    Dim r As Long
    r = FilaSolicitud(idSol)
    LogAudit "SOLICITUD_ESTADO", idSol & ": " & GetV(WS(SH_SOL), r, "Estado") & " -> " & nuevo
    SetV WS(SH_SOL), r, "Estado", nuevo
End Sub

' Agrega un item, verifica CHB (alerta) y recalcula monto/modalidad.
' Devuelve el mensaje de alerta CHB ("" si no aplica).
Public Function AgregarItem(ByVal idSol As String, ByVal codUNSPSC As String, ByVal descripcion As String, _
                            ByVal cantidad As Double, ByVal unidad As String, ByVal precioUnit As Double) As String
    Dim shD As Worksheet, rS As Long, r As Long, item As Long, res As CHBResultado, total As Double
    RequirePermiso P_SOLICITUD
    rS = FilaSolicitud(idSol)
    If CStr(GetV(WS(SH_SOL), rS, "Estado")) <> "BORRADOR" Then Fail "Solo se editan solicitudes en BORRADOR."
    If cantidad <= 0 Or precioUnit <= 0 Then Fail "Cantidad y precio referencial deben ser mayores a cero."
    If Len(Trim$(descripcion)) = 0 Then Fail "Falta la descripcion / especificacion tecnica."
    Set shD = WS(SH_DET)
    item = ContarItems(idSol) + 1
    r = NewRow(shD)
    res = ConsultarCHB(codUNSPSC)
    SetV shD, r, "ID_Solicitud", idSol
    SetV shD, r, "Item", item
    SetV shD, r, "CodigoUNSPSC", codUNSPSC
    SetV shD, r, "Descripcion", descripcion
    SetV shD, r, "Cantidad", cantidad
    SetV shD, r, "Unidad", unidad
    SetV shD, r, "PrecioRefUnitario", precioUnit
    SetV shD, r, "PrecioRefTotal", RoundM(cantidad * precioUnit)
    SetV shD, r, "CumpleCHB", IIf(res.EnCatalogo, "NO", "N/A")  ' en catalogo: queda pendiente hasta que RC evalue
    RecalcularSolicitud idSol
    AgregarItem = res.Mensaje
    If Not res.EnCatalogo Then AgregarItem = ""
End Function

Public Function ContarItems(ByVal idSol As String) As Long
    Dim sh As Worksheet, r As Long
    Set sh = WS(SH_DET)
    For r = 2 To LastRow(sh)
        If CStr(GetV(sh, r, "ID_Solicitud")) = idSol Then ContarItems = ContarItems + 1
    Next r
End Function

Public Sub RecalcularSolicitud(ByVal idSol As String)
    Dim sh As Worksheet, r As Long, total As Double, rS As Long
    Set sh = WS(SH_DET)
    For r = 2 To LastRow(sh)
        If CStr(GetV(sh, r, "ID_Solicitud")) = idSol Then total = total + CDbl(GetV(sh, r, "PrecioRefTotal"))
    Next r
    rS = FindRow(WS(SH_SOL), "ID_Solicitud", idSol)
    SetV WS(SH_SOL), rS, "MontoReferencial", RoundM(total)
    SetV WS(SH_SOL), rS, "Modalidad", ModalidadPorMonto(total)
End Sub

' US/RC envia la solicitud al proceso de cotizacion. Bloquea si excede el tope.
Public Sub EnviarACotizacion(ByVal idSol As String)
    Dim rS As Long, monto As Double
    RequirePermiso P_SOLICITUD
    rS = FilaSolicitud(idSol)
    monto = CDbl(GetV(WS(SH_SOL), rS, "MontoReferencial"))
    If ContarItems(idSol) = 0 Then Fail "La solicitud no tiene items."
    If monto > CfgNum("TopeContratacionMenor", 50000) Then
        Fail "Monto referencial Bs " & Format$(monto, "#,##0.00") & " excede el tope de Contratacion Menor. " & _
             "Debe tramitarse como ANPE/Licitacion (fuera de este sistema)."
    End If
    CambiarEstadoSolicitud idSol, "EN_COTIZACION"
End Sub

'------------------------------------------------------------------------------
' COTIZACIONES
'------------------------------------------------------------------------------
Public Function RegistrarCotizacion(ByVal idSol As String, ByVal nit As String, ByVal razon As String, _
        ByVal validez As Date, ByVal monto As Double, ByVal cumpleTec As Boolean) As String
    Dim sh As Worksheet, r As Long, n As Long, rS As Long
    RequirePermiso P_COTIZACION
    rS = FilaSolicitud(idSol)
    If CStr(GetV(WS(SH_SOL), rS, "Estado")) <> "EN_COTIZACION" Then Fail "La solicitud no esta en cotizacion."
    If Not (Len(Trim$(nit)) >= 6 And IsNumeric(nit)) Then Fail "NIT invalido."
    If monto <= 0 Then Fail "Monto cotizado invalido."
    If validez < Date Then Fail "La oferta ya vencio (validez anterior a hoy)."
    If monto > CDbl(GetV(WS(SH_SOL), rS, "MontoReferencial")) * (1 + CfgNum("TolerCotizacionPct", 20) / 100) Then
        Aviso "Aviso: la cotizacion supera el referencial en mas de " & CfgNum("TolerCotizacionPct", 20) & "%.", vbExclamation
    End If
    Set sh = WS(SH_COT)
    n = NextSeq("COT")
    r = NewRow(sh)
    SetV sh, r, "ID_Cotizacion", FormatCorrelativo("COT", n)
    SetV sh, r, "ID_Solicitud", idSol
    SetV sh, r, "Proveedor_NIT", Trim$(nit)
    SetV sh, r, "RazonSocial", razon
    SetV sh, r, "FechaCotizacion", Date
    SetV sh, r, "ValidezOferta", validez
    SetV sh, r, "MontoTotalCotizado", RoundM(monto)
    SetV sh, r, "CumplimientoTecnico", IIf(cumpleTec, "SI", "NO")
    SetV sh, r, "Recomendado", "NO"
    SetV sh, r, "Adjudicada", "NO"
    RegistrarCotizacion = CStr(GetV(sh, r, "ID_Cotizacion"))
    LogAudit "COTIZACION_REGISTRADA", RegistrarCotizacion & " " & razon
End Function

Public Function ContarCotizaciones(ByVal idSol As String) As Long
    Dim sh As Worksheet, r As Long
    Set sh = WS(SH_COT)
    For r = 2 To LastRow(sh)
        If CStr(GetV(sh, r, "ID_Solicitud")) = idSol Then ContarCotizaciones = ContarCotizaciones + 1
    Next r
End Function

' Cuadro comparativo: criterio Cumple/No cumple + Precio Evaluado Mas Bajo.
' Marca Recomendado="SI" a la oferta habil de menor monto. Devuelve resumen/alerta.
Public Function EvaluarCuadro(ByVal idSol As String) As String
    Dim sh As Worksheet, r As Long, rS As Long, req As Long, best As Long, bestM As Double, empate As Boolean, m As Double
    RequirePermiso P_COTIZACION
    rS = FilaSolicitud(idSol)
    req = CotizacionesRequeridas(CDbl(GetV(WS(SH_SOL), rS, "MontoReferencial")))
    If ContarCotizaciones(idSol) < req Then
        EvaluarCuadro = "Se requieren " & req & " cotizaciones; hay " & ContarCotizaciones(idSol) & "."
        Exit Function
    End If
    Set sh = WS(SH_COT)
    For r = 2 To LastRow(sh)
        If CStr(GetV(sh, r, "ID_Solicitud")) = idSol Then
            SetV sh, r, "Recomendado", "NO"
            If UCase$(CStr(GetV(sh, r, "CumplimientoTecnico"))) = "SI" And CDate(GetV(sh, r, "ValidezOferta")) >= Date Then
                m = CDbl(GetV(sh, r, "MontoTotalCotizado"))
                If best = 0 Or m < bestM Then
                    best = r: bestM = m: empate = False
                ElseIf m = bestM Then
                    empate = True
                End If
            End If
        End If
    Next r
    If best = 0 Then EvaluarCuadro = "Ninguna oferta cumple tecnicamente / vigente.": Exit Function
    If empate Then EvaluarCuadro = "EMPATE en precio mas bajo: el RC debe resolver y registrar el criterio de desempate.": Exit Function
    SetV sh, best, "Recomendado", "SI"
    CambiarEstadoSolicitud idSol, "EVALUADA"
    EvaluarCuadro = "Recomendada: " & GetV(sh, best, "RazonSocial") & " por Bs " & Format$(bestM, "#,##0.00")
End Function

' Adjudica. Exige: oferta recomendada, C-31 vigente que cubra el monto (Art. 22
' contabilidad integrada: saldo verificado ANTES de adjudicar) y CHB habilitado.
Public Sub Adjudicar(ByVal idSol As String, ByVal idCot As String)
    Dim shC As Worksheet, rC As Long, obs As String, nro As String
    RequirePermiso P_ADJUDICAR
    FilaSolicitud idSol
    Set shC = WS(SH_COT)
    rC = FindRow(shC, "ID_Cotizacion", idCot)
    If rC = 0 Or CStr(GetV(shC, rC, "ID_Solicitud")) <> idSol Then Fail "Cotizacion no corresponde a la solicitud."
    If CStr(GetV(shC, rC, "Recomendado")) <> "SI" Then Fail "Solo puede adjudicarse la oferta recomendada por el cuadro comparativo."
    obs = ValidarSolicitudParaOrden(idSol)
    If Len(obs) > 0 Then Fail "Bloqueado por CHB:" & vbLf & obs
    nro = C31VigentePorSolicitud(idSol)
    If Len(nro) = 0 Then Fail "No existe C-31 Preventivo vigente para la solicitud. Solicite a Presupuesto la reserva."
    If C31ImporteVigente(nro) + 0.001 < CDbl(GetV(shC, rC, "MontoTotalCotizado")) Then _
        Fail "El preventivo " & nro & " no cubre el monto cotizado. Solicite ampliacion/nuevo preventivo."
    SetV shC, rC, "Adjudicada", "SI"
    CambiarEstadoSolicitud idSol, "ADJUDICADA"
End Sub

'------------------------------------------------------------------------------
' Monto en literal (Bolivianos) para Ordenes y C-31:  "Son: ... 00/100 Bolivianos"
'------------------------------------------------------------------------------
Public Function MontoLiteral(ByVal monto As Double) As String
    Dim ent As Long, cent As Long
    monto = RoundM(monto)
    ent = Int(monto)
    cent = CLng((monto - ent) * 100 + 0.0001)
    MontoLiteral = "Son: " & UCase$(Trim$(NumLetras(ent))) & " " & Format$(cent, "00") & "/100 BOLIVIANOS"
End Function

Private Function NumLetras(ByVal n As Long) As String
    Dim u As Variant, d As Variant, c As Variant, millones As Long, miles As Long, resto As Long, s As String
    If n = 0 Then NumLetras = "cero": Exit Function
    millones = n \ 1000000
    miles = (n Mod 1000000) \ 1000
    resto = n Mod 1000
    If millones > 0 Then s = IIf(millones = 1, "un millon ", Centenas(millones, True) & " millones ")
    If miles > 0 Then s = s & IIf(miles = 1, "mil ", Centenas(miles, True) & " mil ")
    If resto > 0 Then s = s & Centenas(resto)
    NumLetras = Trim$(s)
End Function

Private Function Centenas(ByVal n As Long, Optional ByVal apocope As Boolean = False) As String
    Dim u As Variant, e As Variant, d As Variant, c As Variant, s As String, cc As Long, dd As Long, uu As Long
    u = Array("", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce", _
              "trece", "catorce", "quince", "dieciseis", "diecisiete", "dieciocho", "diecinueve", "veinte", _
              "veintiuno", "veintidos", "veintitres", "veinticuatro", "veinticinco", "veintiseis", "veintisiete", _
              "veintiocho", "veintinueve")
    d = Array("", "", "", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa")
    c = Array("", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos", _
              "setecientos", "ochocientos", "novecientos")
    cc = n \ 100: dd = n Mod 100
    If n = 100 Then Centenas = "cien": Exit Function
    s = c(cc)
    If dd > 0 Then
        If dd < 30 Then
            s = s & " " & u(dd)
        Else
            uu = dd Mod 10
            s = s & " " & d(dd \ 10) & IIf(uu > 0, " y " & u(uu), "")
        End If
    End If
    s = Trim$(s)
    If apocope Then   ' "veintiun mil", "treinta y un mil"
        If Right$(s, 3) = "uno" Then s = Left$(s, Len(s) - 1)
    End If
    Centenas = s
End Function
