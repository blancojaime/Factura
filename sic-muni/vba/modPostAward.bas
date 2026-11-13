Attribute VB_Name = "modPostAward"
'==============================================================================
' SIC-MUNI - modPostAward
' Despues de la adjudicacion: anulacion de Orden y de Solicitud, recepcion con
' calculo de multa por retraso (parametros CONFIG: PenalidadPorMil, PenalidadMaxPct).
' Estados ORDENES_GASTO.EstadoOrden: EMITIDA > RECIBIDA | ANULADA
'==============================================================================
Option Explicit

Public Function OrdenVigenteDeSolicitud(ByVal idSol As String) As String
    Dim sh As Worksheet, r As Long
    Set sh = WS(SH_ORD)
    For r = 2 To LastRow(sh)
        If CStr(GetV(sh, r, "ID_Solicitud")) = idSol And CStr(GetV(sh, r, "EstadoOrden")) <> "ANULADA" Then
            OrdenVigenteDeSolicitud = CStr(GetV(sh, r, "NroOrden")): Exit Function
        End If
    Next r
End Function

Private Function FilaOrden(ByVal nroOrden As String) As Long
    FilaOrden = FindRow(WS(SH_ORD), "NroOrden", nroOrden)
    If FilaOrden = 0 Then Fail "Orden " & nroOrden & " inexistente."
    modProcurement.FilaSolicitud CStr(GetV(WS(SH_ORD), FilaOrden, "ID_Solicitud"))   ' control de acceso por DA
End Function

Public Function TieneRecepcionConforme(ByVal nroOrden As String) As Boolean
    Dim sh As Worksheet, r As Long
    Set sh = WS(SH_REC)
    For r = 2 To LastRow(sh)
        If CStr(GetV(sh, r, "NroOrden")) = nroOrden And CStr(GetV(sh, r, "Resultado")) = "CONFORME" Then TieneRecepcionConforme = True: Exit Function
    Next r
End Function

' Anula la Orden. La solicitud vuelve a ADJUDICADA (se puede emitir otra Orden)
' y el C-31 sigue vigente: si corresponde liberarlo, PF lo revierte aparte.
Public Sub AnularOrden(ByVal nroOrden As String, ByVal motivo As String)
    Dim sh As Worksheet, r As Long, idSol As String
    RequirePermiso P_ORDEN
    If Len(Trim$(motivo)) < 10 Then Fail "Indique el motivo de la anulacion (min. 10 caracteres)."
    r = FilaOrden(nroOrden)
    Set sh = WS(SH_ORD)
    If CStr(GetV(sh, r, "EstadoOrden")) = "ANULADA" Then Fail "La Orden ya esta anulada."
    If TieneRecepcionConforme(nroOrden) Then Fail "No se anula una Orden con recepcion conforme."
    idSol = CStr(GetV(sh, r, "ID_Solicitud"))
    SetV sh, r, "EstadoOrden", "ANULADA"
    SetV sh, r, "MotivoAnulacion", motivo
    CambiarEstadoSolicitud idSol, "ADJUDICADA"
    LogAudit "ORDEN_ANULADA", nroOrden & " - " & motivo
End Sub

' Cancela una solicitud completa (desierta, desistida, error). Exige que no haya
' Orden vigente ni C-31 vigente (revertir antes).
Public Sub AnularSolicitud(ByVal idSol As String, ByVal motivo As String)
    Dim rS As Long
    RequirePermiso P_SOLICITUD
    If Len(Trim$(motivo)) < 10 Then Fail "Indique el motivo de la anulacion (min. 10 caracteres)."
    rS = modProcurement.FilaSolicitud(idSol)
    If CStr(GetV(WS(SH_SOL), rS, "Estado")) = "ANULADA" Then Fail "La solicitud ya esta anulada."
    If Len(OrdenVigenteDeSolicitud(idSol)) > 0 Then Fail "Hay una Orden vigente; anulela primero."
    If Len(C31VigentePorSolicitud(idSol)) > 0 Then Fail "Hay un C-31 vigente; solicite a Presupuesto su reversion total."
    CambiarEstadoSolicitud idSol, "ANULADA"
    LogAudit "SOLICITUD_ANULADA", idSol & " - " & motivo
End Sub

' Registra una recepcion. Calcula dias de retraso y multa:
'   multa = monto * PenalidadPorMil/1000 * dias, con tope PenalidadMaxPct del monto.
' Si es CONFORME la Orden pasa a RECIBIDA; si es OBSERVADA queda EMITIDA para
' una nueva recepcion tras la subsanacion. Devuelve el N de recepcion.
Public Function RegistrarRecepcion(ByVal nroOrden As String, ByVal fechaRec As Date, _
                                   ByVal conforme As Boolean, ByVal obs As String) As String
    Dim shO As Worksheet, shR As Worksheet, rO As Long, r As Long, n As Long
    Dim emision As Date, limite As Date, dias As Long, monto As Double, multa As Double, tope As Double
    RequirePermiso P_ORDEN
    rO = FilaOrden(nroOrden)
    Set shO = WS(SH_ORD): Set shR = WS(SH_REC)
    If CStr(GetV(shO, rO, "EstadoOrden")) <> "EMITIDA" Then Fail "La Orden esta en estado " & GetV(shO, rO, "EstadoOrden") & "; solo se recepciona una Orden EMITIDA."
    emision = CDate(GetV(shO, rO, "FechaEmision"))
    If fechaRec < emision Then Fail "La fecha de recepcion no puede ser anterior a la emision de la Orden."
    If fechaRec > Date Then Fail "La fecha de recepcion no puede ser futura."
    If Not conforme And Len(Trim$(obs)) < 10 Then Fail "Detalle las observaciones (min. 10 caracteres)."
    monto = CDbl(GetV(shO, rO, "MontoTotal"))
    limite = emision + CLng(GetV(shO, rO, "PlazoDias"))
    dias = CLng(fechaRec - limite): If dias < 0 Then dias = 0
    multa = RoundM(monto * CfgNum("PenalidadPorMil", 3) / 1000 * dias)
    tope = RoundM(monto * CfgNum("PenalidadMaxPct", 10) / 100)
    If multa > tope Then multa = tope
    n = NextSeq("REC")
    r = NewRow(shR)
    SetV shR, r, "NroRecepcion", FormatCorrelativo("REC", n)
    SetV shR, r, "NroOrden", nroOrden
    SetV shR, r, "FechaRecepcion", fechaRec
    SetV shR, r, "FechaLimite", limite
    SetV shR, r, "DiasRetraso", dias
    SetV shR, r, "MontoMulta", multa
    SetV shR, r, "Resultado", IIf(conforme, "CONFORME", "OBSERVADA")
    SetV shR, r, "Observaciones", obs
    SetV shR, r, "Usuario", g_Usuario
    If conforme Then SetV shO, rO, "EstadoOrden", "RECIBIDA"
    RegistrarRecepcion = CStr(GetV(shR, r, "NroRecepcion"))
    LogAudit "RECEPCION", RegistrarRecepcion & " orden " & nroOrden & " dias retraso " & dias & " multa Bs " & Format$(multa, "#,##0.00")
End Function
