from __future__ import annotations
import pytest

from contabol.permisos import permisos_de_rol
from contabol.sistema import ErrorNegocio
from tests.conftest import BANCO, CAJA, CAPITAL, VENTAS, GASTO_LUZ


def _datos(env):
    env.asiento("2025-01-02", CAJA, CAPITAL, 100000, "aporte")
    env.asiento("2025-03-05", CAJA, VENTAS, 40000, "venta")
    env.asiento("2025-03-10", GASTO_LUZ, CAJA, 6000, "luz")


def test_planificacion_y_riesgo(env):
    _datos(env)
    a = env.ctx.auditoria
    e = a.crear_encargo("F", "Auditoría 2025")
    m = a.memorando(e)
    # RD = RA / (RI × RC) con factores B=0,4 M=0,7 A=1,0 (por defecto RI=M, RC=M, RA=5 %)
    assert m["riesgo_deteccion"] == pytest.approx(0.05 / (0.7 * 0.7), abs=1e-4)
    m2 = a.memorando_guardar(e, {"riesgo_inherente": "A", "riesgo_control": "A", "riesgo_auditoria_aceptable": 0.05})
    assert m2["riesgo_deteccion"] == pytest.approx(0.05, abs=1e-4)
    with pytest.raises(ErrorNegocio):
        a.memorando_guardar(e, {"riesgo_auditoria_aceptable": 1.5})
    assert len(a.programas(e)) >= 8 and len(a.riesgos(e)) > 0
    mat = a.materialidad_calcular(e, "INGRESOS", 1.0)
    assert mat["materialidad_global"] == pytest.approx(400.0)
    assert mat["materialidad_desempeno"] == pytest.approx(300.0)
    assert mat["umbral_trivial"] == pytest.approx(20.0)


def test_sumarias_conectadas_al_balance_y_ajustes(env):
    _datos(env)
    a = env.ctx.auditoria
    e = a.crear_encargo("F", "x")
    a.sumarias_generar(e)
    s = {x["indice"]: x for x in a.sumarias(e)}
    assert s["A"]["saldo_sistema"] == pytest.approx(env.saldo(CAJA, "2025-12-31"))
    assert s["II"]["saldo_sistema"] == pytest.approx(40000)
    ana = a.analiticas(s["A"]["id"])[0]
    with pytest.raises(ErrorNegocio):
        a.analitica_guardar(ana["id"], 1.0, "Z9")        # marca inexistente
    a.analitica_guardar(ana["id"], ana["saldo_libros"] - 10, "V,S", "diferencia en arqueo")
    assert a.analiticas(s["A"]["id"])[0]["diferencia"] == pytest.approx(-10)
    with pytest.raises(ErrorNegocio):                    # el asiento propuesto debe cuadrar
        a.ajuste_guardar(e, "AJU", "x", [{"cuenta_id": env.cta(CAJA), "debe": 5}, {"cuenta_id": env.cta(VENTAS), "haber": 4}])
    aid = a.ajuste_guardar(e, "AJU", "Ventas no registradas", [{"cuenta_id": env.cta(CAJA), "debe": 500}, {"cuenta_id": env.cta(VENTAS), "haber": 500}])
    assert a.resumen_desvios(e)["efecto_aceptados"] == 0
    a.ajuste_estado(aid, "ACEPTADO")
    s = {x["indice"]: x for x in a.sumarias(e)}
    assert s["A"]["ajustes"] == pytest.approx(500) and s["A"]["saldo_auditado"] == pytest.approx(s["A"]["saldo_sistema"] + 500)
    assert a.resumen_desvios(e)["efecto_aceptados"] == pytest.approx(500)
    # no corregido por encima de la materialidad => sugiere salvedad
    a.materialidad_calcular(e, "INGRESOS", 1.0)          # 400
    a.ajuste_estado(aid, "NO_CORREGIDO")
    assert a.sugerir_opinion(e)[0] == "SALVEDAD"


def test_hallazgo_requiere_cuatro_elementos(env):
    a = env.ctx.auditoria
    e = a.crear_encargo("F", "x")
    with pytest.raises(ErrorNegocio):
        a.hallazgo_guardar(e, {"condicion": "c", "criterio": "k", "causa": "", "efecto": "f"})
    h = a.hallazgo_guardar(e, {"condicion": "c", "criterio": "k", "causa": "u", "efecto": "f", "recomendacion": "r", "nivel": "A", "impacto_monto": 1000})
    assert a.hallazgos(e)[0]["codigo"] == "H-01" and h


def test_cierre_inmutable_y_hash(env):
    _datos(env)
    a, inf = env.ctx.auditoria, env.ctx.aud_informes
    e = a.crear_encargo("F", "x")
    a.sumarias_generar(e)
    with pytest.raises(ErrorNegocio):
        a.cerrar_encargo(e, "admin")                     # sin dictamen
    inf.emitir(e, inf.borrador_nia700(e))
    with pytest.raises(ErrorNegocio):
        a.cerrar_encargo(e, "incorrecta")
    h = a.cerrar_encargo(e, "admin")
    assert len(h) == 64 and a.verificar_integridad(e)["integro"]
    with pytest.raises(ErrorNegocio):                    # el servicio rechaza cambios
        a.hallazgo_guardar(e, {"condicion": "c", "criterio": "k", "causa": "u", "efecto": "f"})
    with pytest.raises(Exception, match="solo lectura"):  # y la base de datos también (disparadores)
        env.ctx.db.execute("UPDATE cedula_sumaria SET titulo='alterado' WHERE encargo_id=?", (e,))
    with pytest.raises(Exception):
        env.ctx.db.execute("DELETE FROM auditoria_trail")
    # alteración deliberada saltando el disparador => la huella lo detecta
    db = env.ctx.db
    trig = db.one("SELECT sql FROM sqlite_master WHERE type='trigger' AND name LIKE '%cedula_sumaria%' AND sql LIKE '%UPDATE%' LIMIT 1")
    nombre = db.scalar("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE '%cedula_sumaria%' AND sql LIKE '%UPDATE%' LIMIT 1")
    db.execute(f"DROP TRIGGER {nombre}")
    db.execute("UPDATE cedula_sumaria SET titulo='alterado' WHERE encargo_id=?", (e,))
    assert not a.verificar_integridad(e)["integro"] and trig


def test_trail_encadenado(env):
    a = env.ctx.auditoria
    e = a.crear_encargo("F", "x")
    assert a.verificar_trail()
    env.ctx.db.execute("DROP TRIGGER IF EXISTS trg_trail_upd")
    n = env.ctx.db.scalar("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE '%trail%' AND sql LIKE '%UPDATE%'")
    if n:
        env.ctx.db.execute(f"DROP TRIGGER {n}")
    env.ctx.db.execute("UPDATE auditoria_trail SET detalle='manipulado' WHERE id=1")
    assert not a.verificar_trail() and e


def test_contingencia(env):
    t = env.ctx.aud_trib
    env.ctx.tc.guardar("2025-03-20", 6.96, 2.5)
    env.ctx.tc.guardar("2025-12-31", 6.96, 2.6)
    r = t.contingencia(1000, "2025-03-20", "2025-12-31", tasa_anual_pct=10, sancion_pct=0)
    assert r["factor_actualizacion"] == pytest.approx(1.04) and r["tributo_actualizado"] == pytest.approx(1040)
    assert r["intereses"] == pytest.approx(1040 * 0.10 * 286 / 360, abs=0.01)
    assert r["deuda_tributaria"] == pytest.approx(r["tributo_actualizado"] + r["intereses"], abs=0.01)
    with pytest.raises(ErrorNegocio):
        t.contingencia(100, "2025-12-31", "2025-01-01")


def test_bancarizacion_e_iue(env):
    ctx = env.ctx
    ctx.iva.registrar({"libro": "C", "fecha": "2025-04-10", "nit": "123", "razon_social": "Proveedor SA", "nro_factura": "77", "nro_autorizacion": "9", "importe_total": 60000, "generar_asiento": False})
    ctx.iva.registrar({"libro": "C", "fecha": "2025-04-11", "nit": "123", "razon_social": "Proveedor SA", "nro_factura": "78", "nro_autorizacion": "9", "importe_total": 1000, "generar_asiento": False})
    a, t = ctx.auditoria, ctx.aud_trib
    e = a.crear_encargo("T", "MAI")
    r = t.bancarizacion(e)
    assert r["resumen"]["operaciones"] == 1 and r["resumen"]["umbral"] == 50000 and not r["conforme"]
    c = t.depuracion_iue(e)
    assert c["resumen"]["sugerencias_pendientes"] >= 60000 and not c["conforme"]
    g = ctx.db.one("SELECT id FROM gasto_no_deducible_iue WHERE encargo_id=? AND monto>=60000", (e,))
    t.gasto_estado(g["id"], "CONFIRMADO")
    t.gasto_manual(e, "Donación sin comprobante", 500, "Sin respaldo", "D.S. 24051")
    c = t.cedula_iue(e)
    assert c["resumen"]["no_deducibles_confirmados"] >= 60500
    assert len(t.generar_anexos(e)) == 15 and len(t.anexos(e)) == 15


def test_conciliacion_iva_detecta_diferencias(env):
    ctx = env.ctx
    ctx.iva.registrar({"libro": "V", "fecha": "2025-02-10", "nit": "1", "razon_social": "Cli", "nro_factura": "1", "nro_autorizacion": "1", "importe_total": 1000, "generar_asiento": False})
    e = ctx.auditoria.crear_encargo("T", "x")
    r = ctx.aud_trib.conciliacion_iva_it(e)
    feb = [f for f in r["filas"] if f["periodo"].startswith("Febrero")][0]
    assert feb["df_libro"] == pytest.approx(130.0) and feb["df_contabilidad"] == 0 and not feb["conforme"] and not r["conforme"]


def test_pruebas_financieras_y_permisos(env):
    _datos(env)
    p = env.ctx.aud_pruebas
    e = env.ctx.auditoria.crear_encargo("F", "x")
    for k in p.CATALOGO:
        r = p.ejecutar(e, k)
        assert r["titulo"] and "conclusion" in r
    assert len(env.ctx.auditoria.pruebas(e)) == len(p.CATALOGO)
    assert "AUD.FINANCIERA" in permisos_de_rol("AUDITOR") and "AUD.FINANCIERA" in permisos_de_rol("ADMIN")
    assert "AUD.FINANCIERA" not in permisos_de_rol("OPERADOR") and "AUD.TRIBUTARIA" not in permisos_de_rol("CONSULTA")


def test_api_local_solo_lectura(env):
    from contabol import api
    ctx = env.ctx
    e = ctx.auditoria.crear_encargo("F", "API")
    cod, raiz = api.despachar(ctx, "/")
    assert cod == 200 and "/tributario/conciliacion-iva-it" in raiz["rutas"] and raiz["solo_lectura"]
    cod, r = api.despachar(ctx, "/inventarios/corte-documental", {"encargo": [str(e)], "dias": ["3"]})
    assert cod == 200 and "filas" in r
    assert api.despachar(ctx, "/tributario/bancarizacion")[0] == 400        # falta el parámetro encargo
    assert api.despachar(ctx, "/no-existe")[0] == 404
    cod, r = api.despachar(ctx, "/auditoria/integridad", {"encargo": [str(e)]})
    assert cod == 200 and r["cerrado"] is False
    with pytest.raises(ErrorNegocio):
        api.servir(ctx, "corto")


def test_demo_incluye_auditoria():
    import shutil
    import tempfile
    from contabol.demo import crear_empresa_demo
    from contabol.sistema import Sistema
    d = tempfile.mkdtemp()
    try:
        s = Sistema(d)
        u = s.autenticar("admin", "admin")
        eid, gid = crear_empresa_demo(s, u, 2025)
        c = s.abrir_contexto(u, eid, gid)
        enc = c.auditoria.listar()
        assert {x["tipo"] for x in enc} == {"F", "T"}
        f = [x for x in enc if x["tipo"] == "F"][0]
        assert c.auditoria.hallazgos(f["id"]) and c.auditoria.resumen_desvios(f["id"])["efecto_no_corregidos"] != 0
        assert c.auditoria.verificar_trail()
        # cifras citadas en el Manual de Pruebas (Parte I)
        mt = c.auditoria.materialidad(f["id"])
        assert (mt["valor_base"], mt["materialidad_global"], mt["materialidad_desempeno"], mt["umbral_trivial"]) == (2048383.01, 20483.83, 15362.87, 1024.19)
        sm = {x["indice"]: x["saldo_sistema"] for x in c.auditoria.sumarias(f["id"])}
        assert sm["A"] == 1376082.87 and sm["C"] == 458254.9 and sm["II"] == 3651628.17
        assert c.auditoria.resumen_desvios(f["id"])["efecto_no_corregidos"] == -32100.0
        assert c.auditoria.sugerir_opinion(f["id"])[0] == "SALVEDAD" and len(c.auditoria.riesgos(f["id"])) == 29
        tid = [x for x in enc if x["tipo"] == "T"][0]["id"]
        ban = c.aud_trib.bancarizacion(tid)["resumen"]
        assert (ban["operaciones"], ban["sin_respaldo"], ban["importe_sin_respaldo"]) == (35, 17, 1144950.86)
        iue = c.aud_trib.cedula_iue(tid)["resumen"]
        assert iue["utilidad_contable"] == 504111.43
        g = c.db.one("SELECT id FROM gasto_no_deducible_iue WHERE encargo_id=? AND monto>1000", (tid,))
        c.aud_trib.gasto_estado(g["id"], "CONFIRMADO")
        iue = c.aud_trib.cedula_iue(tid)["resumen"]
        assert (iue["utilidad_imponible"], iue["iue"]) == (1649062.29, 412265.57)
        assert len(c.db.query("SELECT id FROM auditoria_prueba WHERE encargo_id=?", (f["id"],))) == 7
        cont = c.aud_trib.contingencia(10000, "2025-03-20", "2025-12-31", tasa_anual_pct=10)
        assert (cont["tributo_actualizado"], cont["intereses"], cont["deuda_tributaria"]) == (10480.77, 832.64, 11313.41)
        c.cerrar()
        s.close()
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_restablecer_admin(env):
    s = env.sis
    s.cambiar_clave(env.usuario["id"], "NuevaClave9")
    for _ in range(5):
        with pytest.raises(ErrorNegocio):
            s.autenticar("admin", "mala")
    with pytest.raises(ErrorNegocio, match="bloqueado"):
        s.autenticar("admin", "NuevaClave9")
    s.restablecer_admin()
    u = s.autenticar("admin", "admin")
    assert u["cambiar_clave"] == 1
