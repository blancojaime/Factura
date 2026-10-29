Imports ContaBol.Core.Common
Imports ContaBol.Core.Domain
Imports ContaBol.Core.Services
Imports Xunit

Public Class ProvisionTests

    <Fact>
    Public Sub CreaEmpresaConPlanDeCuentasYParametros()
        Using e As New Entorno()
            Dim n As Integer = e.Ctx.Db.ScalarInt("SELECT COUNT(*) FROM Cuenta")
            Assert.True(n > 200, "El plan de cuentas debe tener más de 200 cuentas, tiene " & n)
            Assert.Equal("13", e.Ctx.Param.Valor("IVA_PCT"))
            Assert.Equal(6, e.Ctx.Db.ScalarInt("SELECT COUNT(*) FROM TipoComprobante"))
            ' jerarquía
            Dim caja = e.Ctx.CuentaPorCodigo("1.1.1.01.001")
            Assert.NotNull(caja)
            Assert.Equal(5, caja.GetI("Nivel"))
            Assert.True(caja.GetF("EsMovimiento"))
            Dim grupo = e.Ctx.CuentaPorCodigo("1.1.1")
            Assert.False(grupo.GetF("EsMovimiento"))
            Assert.Equal(e.Ctx.CuentaPorCodigo("1.1").GetI("Id"), grupo.GetI("PadreId"))
            ' naturaleza de cuentas regularizadoras
            Assert.Equal("A", e.Ctx.CuentaPorCodigo("1.2.1.02.003").GetS("Naturaleza"))
            Assert.Equal("D", e.Ctx.CuentaPorCodigo("5.1.1.01.001").GetS("Naturaleza"))
        End Using
    End Sub

    <Fact>
    Public Sub CuentasDeParametrosExistenEnElPlan()
        Using e As New Entorno()
            For Each kv In e.Ctx.Param.Todos()
                If kv.Key.StartsWith("CTA_") Then
                    Assert.True(e.Ctx.CuentaPorCodigo(kv.Value) IsNot Nothing, "Cuenta inexistente para " & kv.Key & " = " & kv.Value)
                End If
            Next
        End Using
    End Sub

    <Fact>
    Public Sub MultiempresaYMultigestionSonBasesIndependientes()
        Using e As New Entorno()
            Dim svc As New EmpresaService(e.Sistema)
            Dim e2 As New EmpresaInfo With {.Codigo = "OTRA", .RazonSocial = "Otra Empresa S.A.", .Nit = "999"}
            Dim r = svc.CrearEmpresa(e2, New NuevaGestionOpciones With {.Anio = 2025, .CorrelativoMensual = False}, e.Usuario.Id)
            Using c2 = e.Sistema.AbrirContexto(e.Usuario, r.Item1, r.Item2)
                Assert.NotEqual(e.Ctx.RutaGestion, c2.RutaGestion)
                Assert.Equal("Otra Empresa S.A.", c2.Param.Valor("EMP_NOMBRE"))
                Assert.Equal("Comercial Prueba S.R.L.", e.Ctx.Param.Valor("EMP_NOMBRE"))
            End Using
            ' nueva gestión para la primera empresa
            Dim g2 = svc.CrearGestion(e.Ctx.Empresa, New NuevaGestionOpciones With {.Anio = 2026})
            Assert.Equal(2, e.Sistema.ListarGestiones(e.Ctx.Empresa.Id).Rows.Count)
            Assert.Equal(2, e.Sistema.ListarEmpresas().Rows.Count)
            Assert.Throws(Of InvalidOperationException)(Sub() svc.CrearGestion(e.Ctx.Empresa, New NuevaGestionOpciones With {.Anio = 2026}))
            Assert.Throws(Of InvalidOperationException)(Sub() svc.CrearEmpresa(New EmpresaInfo With {.Codigo = "test", .RazonSocial = "x"}, New NuevaGestionOpciones()))
        End Using
    End Sub

    <Fact>
    Public Sub UsuariosConClaveHasheadaYPermisosPorEmpresa()
        Using e As New Entorno()
            Dim uid = e.Sistema.CrearUsuario("maria", "María Pérez", "clave123", False)
            Dim hash = e.Sistema.Db.ScalarStr("SELECT Hash FROM Usuario WHERE Id=@i", "i", uid)
            Assert.DoesNotContain("clave123", hash)
            Assert.Throws(Of UnauthorizedAccessException)(Sub() e.Sistema.Autenticar("maria", "mala"))
            Dim u = e.Sistema.Autenticar("maria", "clave123")
            ' sin acceso a ninguna empresa
            Assert.Throws(Of UnauthorizedAccessException)(Sub() e.Sistema.AbrirContexto(u, e.Ctx.Empresa.Id, e.Ctx.Gestion.Id))
            e.Sistema.AsignarEmpresa(uid, e.Ctx.Empresa.Id, Permisos.RolAuxiliar)
            Using c = e.Sistema.AbrirContexto(u, e.Ctx.Empresa.Id, e.Ctx.Gestion.Id)
                Assert.True(c.Usuario.Puede("CONT.COMPROBANTES"))
                Assert.False(c.Usuario.Puede("ADM.USUARIOS"))
                Assert.Throws(Of UnauthorizedAccessException)(Sub() c.Requiere("ADM.USUARIOS"))
            End Using
            ' bloqueo por intentos
            For i = 1 To 5
                Try
                    e.Sistema.Autenticar("maria", "x")
                Catch ex As UnauthorizedAccessException
                End Try
            Next
            Assert.Throws(Of UnauthorizedAccessException)(Sub() e.Sistema.Autenticar("maria", "clave123"))
            e.Sistema.CambiarClave(uid, "nueva456")
            Assert.NotNull(e.Sistema.Autenticar("maria", "nueva456"))
        End Using
    End Sub

    <Fact>
    Public Sub NumeroEnLetras()
        Assert.Equal("MIL QUINIENTOS 50/100 BOLIVIANOS", NumeroLetras.Importe(1500.5D))
        Assert.Equal("CIEN 00/100 BOLIVIANOS", NumeroLetras.Importe(100D))
        Assert.Equal("VEINTIUN MIL TRESCIENTOS CUARENTA Y CINCO 99/100 BOLIVIANOS", NumeroLetras.Importe(21345.99D))
        Assert.Equal("UN MILLON DOSCIENTOS MIL 00/100 BOLIVIANOS", NumeroLetras.Importe(1200000D))
        Assert.Equal("CERO 00/100 BOLIVIANOS", NumeroLetras.Importe(0D))
    End Sub

End Class
