Attribute VB_Name = "modBudgetEngine"
'==============================================================================
' SIC-MUNI - modBudgetEngine  (Modulo 3: control presupuestario y C-31 Preventivo)
' - Verificacion de saldo por estructura programatica completa.
' - Emision de C-31 Preventivo (cabecera C31 + detalle C31_DET por partida).
' - Asociacion del N de C-31 generado en SIGEP, reversion parcial / total.
' - Generacion de la Orden de Compra / Servicio.
' Estados C31.Estado:  PREVENTIVO > ASOCIADO (N SIGEP) > REVERTIDO_PARCIAL | REVERTIDO_TOTAL
' IMPORTANTE: este C-31 es el registro/boleta INTERNA de reserva. El C-31 oficial
' lo genera y aprueba el SIGEP; aqui se asocia su numero (no se simula su validez).
'==============================================================================
Option Explicit

Public Type LineaC31
    Programa As String
    Proyecto As String
    ActObra As String
    Fuente As String
    Organismo As String
    Partida As String
    Importe As Double
End Type

'------------------------------------------------------------------------------
' SALDOS
'------------------------------------------------------------------------------
Public Function FilaPresupuesto(ByVal da As String, ByVal ue As String, ByRef L As LineaC31) As Long
    Dim sh As Worksheet, r As Long, gest As String
    Set sh = WS(SH_PRE)
    gest = CfgVal("Gestion", CStr(Year(Date)))
    For r = 2 To LastRow(sh)
        If CStr(GetV(sh, r, "Gestion")) = gest _
           And CStr(GetV(sh, r, "DA")) = da And CStr(GetV(sh, r, "UE")) = ue _
           And CStr(GetV(sh, r, "Programa")) = L.Programa And CStr(GetV(sh, r, "Proyecto")) = L.Proyecto _
           And CStr(GetV(sh, r, "ActObra")) = L.ActObra And CStr(GetV(sh, r, "Fuente")) = L.Fuente _
           And CStr(GetV(sh, r, "Organismo")) = L.Organismo And CStr(GetV(sh, r, "Partida_ObjetoGasto")) = L.Partida Then
            FilaPresupuesto = r: Exit Function
        End If
    Next r
End Function

Public Function SaldoDisponible(ByVal da As String, ByVal ue As String, ByRef L As LineaC31) As Double
    Dim r As Long, sh As Worksheet
    r = FilaPresupuesto(da, ue, L)
    If r = 0 Then Fail "La estructura programatica (partida " & L.Partida & ") no existe en el presupuesto de la gestion."
    Set sh = WS(SH_PRE)
    SaldoDisponible = CDbl(GetV(sh, r, "PresupuestoAprobado")) - CDbl(GetV(sh, r, "PreventivoComprometido"))
End Function

'------------------------------------------------------------------------------
' EMISION DE C-31 PREVENTIVO
' Todo-o-nada: primero valida TODAS las lineas, luego aplica.
'------------------------------------------------------------------------------
Public Function EmitirC31(ByVal idSol As String, ByRef lineas() As LineaC31) As String
    Dim rS As Long, da As String, ue As String, i As Long, n As Long, total As Double
    Dim shP As Worksheet, shC As Worksheet, shD As Worksheet, r As Long, nro As String, rP As Long, estSol As String
    RequirePermiso P_C31
    rS = FilaSolicitud(idSol)
    da = CStr(GetV(WS(SH_SOL), rS, "Cod_DA"))
    ue = CStr(GetV(WS(SH_SOL), rS, "Cod_UE"))
    estSol = CStr(GetV(WS(SH_SOL), rS, "Estado"))
    If estSol <> "EVALUADA" Then Fail "La solicitud debe estar EVALUADA (cuadro comparativo cerrado) para reservar presupuesto (estado: " & estSol & ")."
    If Len(C31VigentePorSolicitud(idSol)) > 0 Then Fail "La solicitud ya tiene un C-31 vigente. Reviertalo antes de emitir otro."

    ' 1) Validacion previa (sin modificar nada)
    For i = LBound(lineas) To UBound(lineas)
        If lineas(i).Importe <= 0 Then Fail "Linea " & (i - LBound(lineas) + 1) & ": importe invalido."
        If Len(lineas(i).Partida) = 0 Then Fail "Linea " & (i - LBound(lineas) + 1) & ": falta partida (objeto del gasto)."
        If lineas(i).Importe > SaldoDisponible(da, ue, lineas(i)) + 0.001 Then
            Fail "Saldo insuficiente en partida " & lineas(i).Partida & ": disponible Bs " & _
                 Format$(SaldoDisponible(da, ue, lineas(i)), "#,##0.00") & ", requerido Bs " & Format$(lineas(i).Importe, "#,##0.00")
        End If
        total = total + lineas(i).Importe
    Next i
    ' Mismo rubro presupuestario en varias lineas: validar acumulado
    ValidarAcumulado da, ue, lineas

    ' 2) Aplicacion
    Set shP = WS(SH_PRE): Set shC = WS(SH_C31): Set shD = WS(SH_C31D)
    n = NextSeq("C31")
    nro = FormatCorrelativo("C31P", n)
    r = NewRow(shC)
    SetV shC, r, "NroInterno", nro
    SetV shC, r, "Fecha", Date
    SetV shC, r, "ID_Solicitud", idSol
    SetV shC, r, "DA", da
    SetV shC, r, "UE", ue
    SetV shC, r, "MontoTotal", RoundM(total)
    SetV shC, r, "MontoRevertido", 0
    SetV shC, r, "Estado", "PREVENTIVO"
    SetV shC, r, "NroC31_SIGEP", ""
    SetV shC, r, "Usuario", g_Usuario
    For i = LBound(lineas) To UBound(lineas)
        r = NewRow(shD)
        SetV shD, r, "NroInterno", nro
        SetV shD, r, "Linea", i - LBound(lineas) + 1
        SetV shD, r, "Programa", lineas(i).Programa
        SetV shD, r, "Proyecto", lineas(i).Proyecto
        SetV shD, r, "ActObra", lineas(i).ActObra
        SetV shD, r, "Fuente", lineas(i).Fuente
        SetV shD, r, "Organismo", lineas(i).Organismo
        SetV shD, r, "Partida", lineas(i).Partida
        SetV shD, r, "Importe", RoundM(lineas(i).Importe)
        SetV shD, r, "ImporteRevertido", 0
        rP = FilaPresupuesto(da, ue, lineas(i))
        SetV shP, rP, "PreventivoComprometido", RoundM(CDbl(GetV(shP, rP, "PreventivoComprometido")) + lineas(i).Importe)
    Next i
    CambiarEstadoSolicitud idSol, "PRESUPUESTADA"
    LogAudit "C31_EMITIDO", nro & " Bs " & Format$(total, "#,##0.00") & " sol " & idSol
    EmitirC31 = nro
End Function

Private Sub ValidarAcumulado(ByVal da As String, ByVal ue As String, ByRef lineas() As LineaC31)
    Dim i As Long, j As Long, acum As Double
    For i = LBound(lineas) To UBound(lineas)
        acum = 0
        For j = LBound(lineas) To UBound(lineas)
            If lineas(j).Programa = lineas(i).Programa And lineas(j).Proyecto = lineas(i).Proyecto _
               And lineas(j).ActObra = lineas(i).ActObra And lineas(j).Fuente = lineas(i).Fuente _
               And lineas(j).Organismo = lineas(i).Organismo And lineas(j).Partida = lineas(i).Partida Then acum = acum + lineas(j).Importe
        Next j
        If acum > SaldoDisponible(da, ue, lineas(i)) + 0.001 Then Fail "Saldo insuficiente (acumulado) en partida " & lineas(i).Partida & "."
    Next i
End Sub

'------------------------------------------------------------------------------
' Consultas de C-31 por solicitud
'------------------------------------------------------------------------------
' Devuelve NroInterno del C-31 no revertido totalmente ("" si no hay)
Public Function C31VigentePorSolicitud(ByVal idSol As String) As String
    Dim sh As Worksheet, r As Long
    Set sh = WS(SH_C31)
    For r = 2 To LastRow(sh)
        If CStr(GetV(sh, r, "ID_Solicitud")) = idSol And CStr(GetV(sh, r, "Estado")) <> "REVERTIDO_TOTAL" Then
            C31VigentePorSolicitud = CStr(GetV(sh, r, "NroInterno")): Exit Function
        End If
    Next r
End Function

Public Function C31ImporteVigente(ByVal nro As String) As Double
    Dim sh As Worksheet, r As Long
    Set sh = WS(SH_C31)
    r = FindRow(sh, "NroInterno", nro)
    If r > 0 Then C31ImporteVigente = CDbl(GetV(sh, r, "MontoTotal")) - CDbl(GetV(sh, r, "MontoRevertido"))
End Function

'------------------------------------------------------------------------------
' ASOCIACION del C-31 de SIGEP
'------------------------------------------------------------------------------
Public Sub AsociarC31SIGEP(ByVal nroInterno As String, ByVal nroSigep As String)
    Dim sh As Worksheet, r As Long
    RequirePermiso P_C31
    nroSigep = Trim$(nroSigep)
    If Not (Len(nroSigep) >= 1 And Len(nroSigep) <= 10 And IsNumeric(nroSigep)) Then Fail "N de C-31 SIGEP invalido (numerico, hasta 10 digitos)."
    Set sh = WS(SH_C31)
    r = FindRow(sh, "NroInterno", nroInterno)
    If r = 0 Then Fail "Preventivo interno inexistente."
    If CStr(GetV(sh, r, "Estado")) <> "PREVENTIVO" Then Fail "Solo se asocia un preventivo en estado PREVENTIVO."
    If FindRow(sh, "NroC31_SIGEP", nroSigep) > 0 Then Fail "Ese N de C-31 SIGEP ya esta asociado a otro preventivo."
    SetV sh, r, "NroC31_SIGEP", nroSigep
    SetV sh, r, "Estado", "ASOCIADO"
    LogAudit "C31_ASOCIADO", nroInterno & " -> SIGEP " & nroSigep
End Sub

'------------------------------------------------------------------------------
' REVERSIONES
'------------------------------------------------------------------------------
Public Sub RevertirParcial(ByVal nroInterno As String, ByVal linea As Long, ByVal monto As Double, ByVal motivo As String)
    Dim shC As Worksheet, shD As Worksheet, rC As Long, rD As Long, r As Long, rP As Long
    Dim L As LineaC31, vigente As Double, rev As Double
    RequirePermiso P_REVERSION
    If Len(Trim$(motivo)) < 10 Then Fail "Indique el motivo de la reversion."
    If monto <= 0 Then Fail "Monto de reversion invalido."
    Set shC = WS(SH_C31): Set shD = WS(SH_C31D)
    rC = FindRow(shC, "NroInterno", nroInterno)
    If rC = 0 Then Fail "Preventivo inexistente."
    If CStr(GetV(shC, rC, "Estado")) = "REVERTIDO_TOTAL" Then Fail "El preventivo ya esta revertido totalmente."
    For r = 2 To LastRow(shD)
        If CStr(GetV(shD, r, "NroInterno")) = nroInterno And CLng(GetV(shD, r, "Linea")) = linea Then rD = r: Exit For
    Next r
    If rD = 0 Then Fail "Linea inexistente."
    vigente = CDbl(GetV(shD, rD, "Importe")) - CDbl(GetV(shD, rD, "ImporteRevertido"))
    If monto > vigente + 0.001 Then Fail "La reversion excede el importe vigente de la linea (Bs " & Format$(vigente, "#,##0.00") & ")."
    AplicarReversionLinea shC, rC, shD, rD, monto
    If C31ImporteVigente(nroInterno) < 0.005 Then
        SetV shC, rC, "Estado", "REVERTIDO_TOTAL"
    Else
        SetV shC, rC, "Estado", "REVERTIDO_PARCIAL"
    End If
    LogAudit "C31_REV_PARCIAL", nroInterno & " lin " & linea & " Bs " & Format$(monto, "#,##0.00") & " - " & motivo
End Sub

Public Sub RevertirTotal(ByVal nroInterno As String, ByVal motivo As String)
    Dim shC As Worksheet, shD As Worksheet, rC As Long, r As Long, vig As Double
    RequirePermiso P_REVERSION
    If Len(Trim$(motivo)) < 10 Then Fail "Indique el motivo de la reversion."
    Set shC = WS(SH_C31): Set shD = WS(SH_C31D)
    rC = FindRow(shC, "NroInterno", nroInterno)
    If rC = 0 Then Fail "Preventivo inexistente."
    If CStr(GetV(shC, rC, "Estado")) = "REVERTIDO_TOTAL" Then Fail "Ya esta revertido."
    If OrdenEmitidaParaSolicitud(CStr(GetV(shC, rC, "ID_Solicitud"))) Then Fail "Existe una Orden emitida con cargo a este preventivo; anule la Orden primero."
    For r = 2 To LastRow(shD)
        If CStr(GetV(shD, r, "NroInterno")) = nroInterno Then
            vig = CDbl(GetV(shD, r, "Importe")) - CDbl(GetV(shD, r, "ImporteRevertido"))
            If vig > 0 Then AplicarReversionLinea shC, rC, shD, r, vig
        End If
    Next r
    SetV shC, rC, "Estado", "REVERTIDO_TOTAL"
    ' La solicitud vuelve a EVALUADA para poder re-presupuestarse
    CambiarEstadoSolicitud CStr(GetV(shC, rC, "ID_Solicitud")), "EVALUADA"
    LogAudit "C31_REV_TOTAL", nroInterno & " - " & motivo
End Sub

Private Sub AplicarReversionLinea(shC As Worksheet, rC As Long, shD As Worksheet, rD As Long, ByVal monto As Double)
    Dim L As LineaC31, rP As Long, shP As Worksheet
    Set shP = WS(SH_PRE)
    L.Programa = CStr(GetV(shD, rD, "Programa")): L.Proyecto = CStr(GetV(shD, rD, "Proyecto"))
    L.ActObra = CStr(GetV(shD, rD, "ActObra")): L.Fuente = CStr(GetV(shD, rD, "Fuente"))
    L.Organismo = CStr(GetV(shD, rD, "Organismo")): L.Partida = CStr(GetV(shD, rD, "Partida"))
    rP = FilaPresupuesto(CStr(GetV(shC, rC, "DA")), CStr(GetV(shC, rC, "UE")), L)
    If rP = 0 Then Fail "No se halla la estructura programatica para devolver el saldo."
    SetV shP, rP, "PreventivoComprometido", RoundM(CDbl(GetV(shP, rP, "PreventivoComprometido")) - monto)
    SetV shD, rD, "ImporteRevertido", RoundM(CDbl(GetV(shD, rD, "ImporteRevertido")) + monto)
    SetV shC, rC, "MontoRevertido", RoundM(CDbl(GetV(shC, rC, "MontoRevertido")) + monto)
End Sub

Public Function OrdenEmitidaParaSolicitud(ByVal idSol As String) As Boolean
    Dim sh As Worksheet, r As Long
    Set sh = WS(SH_ORD)
    For r = 2 To LastRow(sh)
        If CStr(GetV(sh, r, "ID_Solicitud")) = idSol And CStr(GetV(sh, r, "EstadoOrden")) <> "ANULADA" Then OrdenEmitidaParaSolicitud = True: Exit Function
    Next r
End Function

'------------------------------------------------------------------------------
' ORDEN DE COMPRA / SERVICIO
' Puertas: rol RC, solicitud ADJUDICADA, CHB habilitado, C-31 vigente que cubre
' el monto adjudicado (si sobra reserva, PF debe revertir la diferencia).
'------------------------------------------------------------------------------
Public Function GenerarOrden(ByVal idSol As String, ByVal tipo As String, ByVal cuce As String, _
                             ByVal plazoDias As Long, ByVal lugarEntrega As String) As String
    Dim shO As Worksheet, shC As Worksheet, rS As Long, rC As Long, r As Long, obs As String
    Dim nroC31 As String, monto As Double, n As Long, rK As Long
    RequirePermiso P_ORDEN
    tipo = UCase$(tipo)
    If tipo <> "COMPRA" And tipo <> "SERVICIO" Then Fail "Tipo debe ser COMPRA o SERVICIO."
    rS = FilaSolicitud(idSol)
    If CStr(GetV(WS(SH_SOL), rS, "Estado")) <> "ADJUDICADA" Then Fail "La solicitud debe estar ADJUDICADA."
    If OrdenEmitidaParaSolicitud(idSol) Then Fail "Ya existe una Orden para esta solicitud."
    If plazoDias <= 0 Then Fail "Plazo de entrega/ejecucion invalido."
    If Len(Trim$(lugarEntrega)) = 0 Then Fail "Falta lugar de entrega/prestacion."
    obs = ValidarSolicitudParaOrden(idSol)
    If Len(obs) > 0 Then Fail "Orden BLOQUEADA por CHB:" & vbLf & obs
    Set shC = WS(SH_COT)
    For r = 2 To LastRow(shC)
        If CStr(GetV(shC, r, "ID_Solicitud")) = idSol And CStr(GetV(shC, r, "Adjudicada")) = "SI" Then rC = r: Exit For
    Next r
    If rC = 0 Then Fail "No hay cotizacion adjudicada."
    monto = CDbl(GetV(shC, rC, "MontoTotalCotizado"))
    nroC31 = C31VigentePorSolicitud(idSol)
    If Len(nroC31) = 0 Then Fail "Sin C-31 Preventivo vigente."
    If C31ImporteVigente(nroC31) + 0.001 < monto Then Fail "El preventivo no cubre el monto adjudicado."
    ' Si se exige asociacion a SIGEP para emitir:
    rK = FindRow(WS(SH_C31), "NroInterno", nroC31)
    If CfgVal("ExigirC31SIGEPParaOrden", "SI") = "SI" And CStr(GetV(WS(SH_C31), rK, "Estado")) = "PREVENTIVO" Then _
        Fail "Asocie primero el N de C-31 aprobado en SIGEP (estado actual: PREVENTIVO sin asociar)."

    Set shO = WS(SH_ORD)
    n = NextSeq("OC_" & Left$(tipo, 1))
    r = NewRow(shO)
    SetV shO, r, "NroOrden", FormatCorrelativo(IIf(tipo = "COMPRA", "OC", "OS"), n)
    SetV shO, r, "Tipo", IIf(tipo = "COMPRA", "Compra", "Servicio")
    SetV shO, r, "CUCE_SICOES", cuce
    SetV shO, r, "ID_Solicitud", idSol
    SetV shO, r, "ID_Cotizacion", GetV(shC, rC, "ID_Cotizacion")
    SetV shO, r, "Proveedor_Adjudicado", GetV(shC, rC, "RazonSocial")
    SetV shO, r, "NIT", CStr(GetV(shC, rC, "Proveedor_NIT"))
    SetV shO, r, "MontoTotal", monto
    SetV shO, r, "NroPreventivo_C31", nroC31
    SetV shO, r, "EstadoC31", GetV(WS(SH_C31), rK, "Estado")
    SetV shO, r, "FechaEmision", Date
    SetV shO, r, "PlazoDias", plazoDias
    SetV shO, r, "LugarEntrega", lugarEntrega
    SetV shO, r, "EstadoOrden", "EMITIDA"
    SetV shO, r, "Usuario", g_Usuario
    CambiarEstadoSolicitud idSol, "ORDEN_EMITIDA"
    GenerarOrden = CStr(GetV(shO, r, "NroOrden"))
    LogAudit "ORDEN_EMITIDA", GenerarOrden & " Bs " & Format$(monto, "#,##0.00")
End Function
