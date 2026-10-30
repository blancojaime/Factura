import os
import tempfile

from contabol.reports import catalogo, excel, pdf
from tests.conftest import BANCO, CAJA, CAPITAL
from tests.test_estados import _escenario


def _poblar(env):
    _escenario(env)
    ctx = env.ctx
    ctx.tc.guardar("2025-01-01", 6.96, 2.5)
    ctx.tc.guardar("2025-12-31", 6.96, 2.6)
    g = [x for x in ctx.activos.grupos() if x["nombre"] == "Equipo de Computación"][0]
    ctx.activos.guardar({"codigo": "PC1", "nombre": "Computadora", "grupo_id": g["id"], "fecha_alta": "2025-01-10", "valor_original": 12000, "contra_cuenta_id": env.cta(CAPITAL)})
    ctx.activos.depreciar(2025, 1, True)
    eid = ctx.rrhh.guardar_empleado({"nombre": "Ana Mamani", "ci": "111", "fecha_ingreso": "2020-01-01", "haber_basico": 6000, "cargo": "Contadora"})
    pid = ctx.rrhh.generar(2025, 1)
    ctx.rrhh.cerrar(pid)
    alm = ctx.db.scalar("SELECT id FROM almacen LIMIT 1")
    mp = ctx.inventario.guardar_item({"codigo": "MP1", "nombre": "Harina"})
    ctx.inventario.registrar({"tipo": "INI", "fecha": "2025-01-01", "almacen_id": alm, "items": [{"item_id": mp, "cantidad": 50, "costo_unit": 3.0}], "generar_asiento": True})
    pt = ctx.inventario.guardar_item({"codigo": "PT1", "nombre": "Pan"})
    oid = ctx.produccion.abrir("2025-02-01", pt, 10, alm, alm)
    ctx.produccion.consumir_mp(oid, "2025-02-02", [{"item_id": mp, "cantidad": 5}])
    ctx.produccion.agregar_mod(oid, eid, 8)
    ctx.produccion.agregar_cif(oid, "Energía", 40)
    ctx.produccion.cerrar(oid, "2025-02-20", 10)
    return {"cuenta": env.cta(CAJA), "banco": env.cta(BANCO), "tercero": ctx.db.scalar("SELECT id FROM tercero WHERE clase='C'"), "item": mp,
            "orden": oid, "empleado": eid, "comp": ctx.db.scalar("SELECT MIN(id) FROM comprobante"), "venta": ctx.db.scalar("SELECT MIN(id) FROM venta"),
            "compra": ctx.db.scalar("SELECT MIN(id) FROM compra")}


def test_todos_los_reportes_generan_pdf_y_excel(env):
    ids = _poblar(env)
    d = tempfile.mkdtemp()
    fallos, n = [], 0
    for r in catalogo.todos():
        vals = {}
        for pd in r.params:
            if pd.tipo == "cuenta":
                vals[pd.clave] = ids["banco"] if "banco" in r.id or r.id == "conciliacion" else ids["cuenta"]
            elif pd.tipo in ("tercero", "tercero_c", "tercero_p"):
                vals[pd.clave] = ids["tercero"]
            elif pd.tipo == "item":
                vals[pd.clave] = ids["item"]
            elif pd.tipo == "orden":
                vals[pd.clave] = ids["orden"]
            elif pd.tipo == "empleado":
                vals[pd.clave] = ids["empleado"]
            elif pd.tipo == "comprobante":
                vals[pd.clave] = ids["comp"]
        if r.id == "nota_venta":
            vals["id"] = ids["venta"]
        if r.id == "nota_compra":
            vals["id"] = ids["compra"]
        try:
            rep = catalogo.ejecutar(env.ctx, r.id, vals)
            raw = pdf.generar_bytes(rep)
            assert raw[:4] == b"%PDF" and len(raw) > 1500, "PDF vacío"
            excel.exportar(rep, os.path.join(d, r.id + ".xlsx"))
            n += 1
        except Exception as ex:  # noqa: BLE001
            fallos.append(f"{r.id}: {type(ex).__name__}: {ex}")
    assert not fallos, "\n".join(fallos)
    assert n >= 55, n


def test_paquete_estados_financieros(env):
    _poblar(env)
    rep = catalogo.ejecutar(env.ctx, "estados_financieros", {})
    assert len(rep.tablas) >= 11
    raw = pdf.generar_bytes(rep)
    assert len(raw) > 8000
