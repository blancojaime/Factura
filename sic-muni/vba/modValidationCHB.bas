Attribute VB_Name = "modValidationCHB"
'==============================================================================
' SIC-MUNI - modValidationCHB
' Validacion contra el catalogo "Compro Hecho en Bolivia" (CAT_CHB) y control
' de excepciones de Ficha Tecnica (segun la especificacion del proyecto:
' D.S. 4505 / R.B.M. 012/2024; verificar el texto vigente antes de implantar).
'
' Resultado por item (SOLICITUDES_DET.CumpleCHB):
'   "N/A"        el codigo no esta en el catalogo CHB
'   "SI"         esta en catalogo, ficha vigente y se compra por catalogo
'   "EXCEPCION"  fuera de catalogo con excepcion completa y valida
'   "NO"         pendiente / incompleto  -> BLOQUEA la Orden de Compra
'==============================================================================
Option Explicit

Public Type CHBResultado
    EnCatalogo As Boolean
    FichaVigente As Boolean
    RequiereMDPyEP As Boolean
    Descripcion As String
    Unidad As String
    Mensaje As String
End Type

' Consulta el catalogo. Nivel de coincidencia configurable (CONFIG: CHB_NivelMatch,
' 8 = codigo UNSPSC exacto; 6 = familia/clase).
Public Function ConsultarCHB(ByVal codigo As String) As CHBResultado
    Dim sh As Worksheet, lr As Long, r As Long, n As Long, cCod As Long, v As Variant
    Dim res As CHBResultado, venc As Variant
    codigo = Trim$(codigo)
    n = CLng(CfgNum("CHB_NivelMatch", 8))
    Set sh = WS(SH_CAT)
    lr = LastRow(sh)
    cCod = ColIdx(sh, "CodigoUNSPSC")
    For r = 2 To lr
        If Left$(Trim$(CStr(sh.Cells(r, cCod).Value)), n) = Left$(codigo, n) And Len(codigo) >= n Then
            res.EnCatalogo = True
            res.Descripcion = CStr(GetV(sh, r, "Descripcion"))
            res.Unidad = CStr(GetV(sh, r, "Unidad"))
            res.RequiereMDPyEP = CBool(GetV(sh, r, "RequiereAutorizacionMDPyEP"))
            venc = GetV(sh, r, "Vigencia")
            res.FichaVigente = CBool(GetV(sh, r, "FichaTecnicaCHB")) And _
                               (IsEmpty(venc) Or Not IsDate(venc) Or CDate(venc) >= Date)
            Exit For
        End If
    Next r
    If Not res.EnCatalogo Then
        res.Mensaje = "Codigo fuera del catalogo CHB: no aplica verificacion."
    ElseIf res.FichaVigente Then
        res.Mensaje = "ALERTA CHB: bien/servicio regulado por produccion nacional. " & _
                      "Corresponde compra por catalogo (Ficha Tecnica vigente)."
    Else
        res.Mensaje = "ALERTA CHB: existe en catalogo pero SIN Ficha Tecnica vigente. " & _
                      "Se requiere Codigo de Excepcion autorizado para continuar."
    End If
    ConsultarCHB = res
End Function

' Devuelve "" si los datos de excepcion estan completos y son validos.
Public Function ValidarExcepcion(ByVal codExc As String, ByVal justif As String, _
                                 ByVal nroAut As String, ByVal fechaAut As Variant) As String
    Dim patron As String, minJust As Long
    patron = CfgVal("PatronCodigoExcepcion", "*")      ' ajustar al formato real del MDPyEP
    minJust = CLng(CfgNum("MinCaracteresJustificacion", 80))
    codExc = Trim$(codExc)
    If Len(codExc) < 6 Or Not (codExc Like patron) Then
        ValidarExcepcion = "Codigo Unico de Excepcion (Solicitud de Excepcion de Ficha Tecnica, Perfil 991/1014) ausente o con formato invalido."
    ElseIf Len(Trim$(justif)) < minJust Then
        ValidarExcepcion = "La Justificacion Tecnica/Legal debe detallar la insuficiencia de calidad, cantidad o plazo (min. " & minJust & " caracteres)."
    ElseIf Len(Trim$(nroAut)) = 0 Then
        ValidarExcepcion = "Falta el N de Autorizacion expresa del MDPyEP."
    ElseIf Not IsDate(fechaAut) Then
        ValidarExcepcion = "Falta la fecha de la Autorizacion del MDPyEP."
    ElseIf CDate(fechaAut) > Date Then
        ValidarExcepcion = "La fecha de autorizacion no puede ser futura."
    End If
End Function

' Evalua y registra el resultado CHB de un item. Devuelve mensaje para la UI
' ("" = sin observaciones). optaFueraCatalogo = la US/RC decide comprar fuera
' del mercado virtual.
Public Function EvaluarItemCHB(ByVal idSol As String, ByVal item As Long, _
        ByVal optaFueraCatalogo As Boolean, ByVal codExc As String, ByVal justif As String, _
        ByVal nroAut As String, ByVal fechaAut As Variant) As String
    Dim sh As Worksheet, r As Long, res As CHBResultado, e As String, estado As String
    RequirePermiso P_CHB
    Set sh = WS(SH_DET)
    r = FilaItem(idSol, item)
    If r = 0 Then Fail "Item inexistente."
    res = ConsultarCHB(CStr(GetV(sh, r, "CodigoUNSPSC")))

    If Not res.EnCatalogo Then
        estado = "N/A"
    ElseIf res.FichaVigente And Not optaFueraCatalogo Then
        estado = "SI"
    Else
        e = ValidarExcepcion(codExc, justif, nroAut, fechaAut)
        If Len(e) = 0 Then
            estado = "EXCEPCION"
            SetV sh, r, "CodigoExcepcionMDPyEP", Trim$(codExc)
            SetV sh, r, "JustificacionExcepcion", Trim$(justif)
            SetV sh, r, "NroAutorizacionMDPyEP", Trim$(nroAut)
            SetV sh, r, "FechaAutorizacion", CDate(fechaAut)
        Else
            estado = "NO"
            EvaluarItemCHB = e
        End If
    End If
    SetV sh, r, "CumpleCHB", estado
    LogAudit "CHB_EVAL", idSol & "/" & item & " -> " & estado
    If Len(EvaluarItemCHB) = 0 Then EvaluarItemCHB = IIf(estado = "N/A", "", res.Mensaje)
End Function

' Puerta de control previa a la Orden de Compra/Servicio. Devuelve "" si todos
' los items estan habilitados; si no, la lista de observaciones (bloqueante).
Public Function ValidarSolicitudParaOrden(ByVal idSol As String) As String
    Dim sh As Worksheet, r As Long, lr As Long, estado As String, res As CHBResultado, out As String
    Set sh = WS(SH_DET)
    lr = LastRow(sh)
    For r = 2 To lr
        If CStr(sh.Cells(r, ColIdx(sh, "ID_Solicitud")).Value) = idSol Then
            estado = UCase$(CStr(GetV(sh, r, "CumpleCHB")))
            ' Reconsulta vigente: si la ficha vencio despues de evaluar, vuelve a bloquear.
            res = ConsultarCHB(CStr(GetV(sh, r, "CodigoUNSPSC")))
            If res.EnCatalogo And estado = "SI" And Not res.FichaVigente Then estado = "NO"
            If estado = "" Or estado = "NO" Then
                out = out & "- Item " & GetV(sh, r, "Item") & ": sin Ficha Tecnica CHB vigente ni Codigo de Excepcion autorizado." & vbLf
            ElseIf estado = "EXCEPCION" Then
                If Len(ValidarExcepcion(CStr(GetV(sh, r, "CodigoExcepcionMDPyEP")), CStr(GetV(sh, r, "JustificacionExcepcion")), _
                       CStr(GetV(sh, r, "NroAutorizacionMDPyEP")), GetV(sh, r, "FechaAutorizacion"))) > 0 Then
                    out = out & "- Item " & GetV(sh, r, "Item") & ": excepcion incompleta." & vbLf
                End If
            ElseIf estado <> "SI" And estado <> "N/A" Then
                out = out & "- Item " & GetV(sh, r, "Item") & ": estado CHB desconocido (" & estado & ")." & vbLf
            End If
        End If
    Next r
    ValidarSolicitudParaOrden = out
End Function

Public Function FilaItem(ByVal idSol As String, ByVal item As Long) As Long
    Dim sh As Worksheet, r As Long, lr As Long
    Set sh = WS(SH_DET)
    lr = LastRow(sh)
    For r = 2 To lr
        If CStr(GetV(sh, r, "ID_Solicitud")) = idSol And CLng(GetV(sh, r, "Item")) = item Then FilaItem = r: Exit Function
    Next r
End Function
