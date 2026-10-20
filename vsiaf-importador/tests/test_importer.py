import datetime as dt
import os

import pytest

from vsiaf_importer import service
from vsiaf_importer.dbf import DbfTable
from vsiaf_importer.demo import make_demo_install
from vsiaf_importer.excelio import build_template, read_workbook
from vsiaf_importer.importer import ImportAbort, Importer, Options
from vsiaf_importer.ufv import load_from_csv, bundled_csv
from vsiaf_importer.vsiafdb import VsiafDb

TODAY = dt.date(2026, 10, 20)
UFV = load_from_csv(bundled_csv())


def fecha(n):
    return (TODAY - dt.timedelta(days=n)).strftime("%d/%m/%Y")


@pytest.fixture()
def inst(tmp_path):
    root = str(tmp_path / "vsiaf")
    make_demo_install(root)
    return root


def write_book(tmp_path, rows, name="libro.xlsx"):
    db = VsiafDb(str(tmp_path / "vsiaf"))
    p = str(tmp_path / name)
    build_template(p, db.grupos(), db.estados(), db.motivos_baja(), db.organismos(), db.departamentos(), rows)
    return p


def importer(inst, **kw):
    opt = Options(default_unit="1", today=TODAY, calc_date=TODAY, **kw)
    return Importer(VsiafDb(inst), UFV, opt)


BASE = {
    "OFICINAS": [dict(oficina="ADMINISTRACION"), dict(oficina="ALMACEN")],
    "RESPONSABLES": [dict(oficina="ADMINISTRACION", responsable="ANA PEREZ", cargo="JEFE", ci="1", expedido="LPZ"),
                     dict(oficina="ALMACEN", responsable="CARLOS QUISPE", cargo="ENCARGADO")],
    "AUXILIARES": [dict(grupo_contable=15, auxiliar="LAPTOP"), dict(grupo_contable=2, auxiliar="ESCRITORIO")],
}


def activo(**kw):
    d = dict(codigo="A-1", descripcion="LAPTOP", grupo_contable=15, auxiliar="LAPTOP", oficina="ADMINISTRACION",
             responsable="ANA PEREZ", estado_bien="Bueno", fecha_incorporacion=fecha(30), costo_inicial=1000,
             organismo_financiador="111", estado_registro="APROBADO")
    d.update(kw)
    return d


def run(inst, tmp_path, rows, apply=True, **kw):
    full = dict(BASE)
    full.update(rows)
    p = write_book(tmp_path, full)
    imp = importer(inst, **kw)
    res = imp.plan(read_workbook(p))
    if apply:
        imp.apply(p)
    return imp, res


def issues(res, level="ERROR"):
    return [i.message for i in res.issues if i.level == level and i.sheet != "(UFV)"]


# ----------------------------------------------------------------------------- camino feliz
def test_flujo_completo_demo(tmp_path):
    root = str(tmp_path / "v")
    make_demo_install(root)
    x = str(tmp_path / "demo.xlsx")
    service.create_template(x, root, ejemplos=True)
    res, rep = service.run(root, x, Options(default_unit="901"), apply=True)
    assert res.errors == 0 and res.applied and os.path.exists(rep) and os.path.exists(res.backup_path)
    db = VsiafDb(root)
    act = {r["CODIGO"]: r for r in db.table("ACTUAL").records(include_deleted=True)}
    assert act["EJ-0001"]["CODOFIC"] == 2 and act["EJ-0001"]["API_ESTADO"] == 3      # transferido a ALMACEN
    assert act["EJ-0002"].deleted and act["EJ-0002"]["B_REV"] is True                  # revaluado y luego dado de baja
    assert act["EJ-0003"]["API_ESTADO"] == 1                                           # elaborado
    assert len(list(db.table("BAJAS").records())) == 1 and len(list(db.table("REVAL").records())) == 1
    assert len(list(db.table("TRASFE").records())) == 1


def test_campos_del_alta(inst, tmp_path):
    imp, res = run(inst, tmp_path, {"ACTIVOS": [activo(codigo="ab-1", codigo_adicional="x9", cod_rube="R1",
                                                         nro_convenio="C-5", observaciones="Obs ñ")]})
    assert res.errors == 0
    r = list(VsiafDb(inst).table("ACTUAL").records())[0]
    assert r["CODIGO"] == "AB-1" and r["CODIGOSEC"] == "X9" and r["ENTIDAD"] == "9999" and r["UNIDAD"] == "1"
    assert r["CODCONT"] == 15 and r["VIDAUTIL"] == 4.0 and r["COSTO"] == 1000 and r["DEPACU"] == 0
    assert r["B_REV"] is False and r["BAND_UFV"] is False and r["BANDERAS"] == "0"
    assert r["CODESTADO"] == 1 and r["ORG_FIN"] == "111" and r["OBSERV"] == "Obs ñ" and r["USUAR"] == "admin"
    inc = TODAY - dt.timedelta(days=30)
    assert (r["DIA"], r["MES"], r["ANO"]) == (inc.day, inc.month, inc.year)


def test_estado_por_defecto_elaborado(inst, tmp_path):
    imp, res = run(inst, tmp_path, {"ACTIVOS": [activo(estado_registro=None)]})
    assert list(VsiafDb(inst).table("ACTUAL").records())[0]["API_ESTADO"] == 1


# ----------------------------------------------------------------------------- validaciones
@pytest.mark.parametrize("cambios,texto", [
    (dict(vida_util=9), "difiere de la del grupo"),
    (dict(dep_acumulada_inicial=50), "incorporaciones especiales"),
    (dict(fecha_incorporacion="01/01/2099"), "futura"),
    (dict(fecha_incorporacion="01/01/1980"), "No hay UFV"),
    (dict(costo_inicial=0), "mayor a cero"),
    (dict(organismo_financiador="999"), "no existe en el clasificador"),
    (dict(estado_bien="Pésimo"), "no válido"),
    (dict(oficina="NO EXISTE"), "no existe en la unidad"),
    (dict(responsable="OTRO"), "no existe en esa oficina"),
    (dict(auxiliar="NO EXISTE"), "no existe en el grupo"),
    (dict(grupo_contable="XYZ"), "no reconocido"),
    (dict(codigo="X" * 16), "largo máximo"),
    (dict(descripcion=None), "obligatorio"),
    (dict(costo_inicial="abc"), "no es un número"),
    (dict(incorporacion_especial="SI", vida_util=6), "Incorporaciones"),
])
def test_validaciones_de_activo(inst, tmp_path, cambios, texto):
    imp, res = run(inst, tmp_path, {"ACTIVOS": [activo(**cambios)]}, apply=False)
    assert any(texto in m for m in issues(res)), issues(res)
    with pytest.raises(ImportAbort):
        imp.apply()


def test_incorporacion_especial_habilitada(inst, tmp_path):
    imp, res = run(inst, tmp_path, {"ACTIVOS": [activo(incorporacion_especial="SI", vida_util=6,
                                                         dep_acumulada_inicial=100)]}, allow_incesp=True)
    r = list(VsiafDb(inst).table("ACTUAL").records())[0]
    assert r["BANDERAS"] == "1" and r["VIDAUTIL"] == 6.0 and r["DEPACU"] == 100


def test_codigo_duplicado_en_libro_y_en_bd(inst, tmp_path):
    imp, res = run(inst, tmp_path, {"ACTIVOS": [activo(), activo()]}, apply=False)
    assert any("ya existe en la fila" in m for m in issues(res))
    run(inst, tmp_path, {"ACTIVOS": [activo()]})
    imp2, res2 = run(inst, tmp_path, {"ACTIVOS": [activo()]}, apply=False)
    assert any("ya existe en el VSIAF" in m for m in issues(res2))


def test_maestros_existentes_se_omiten(inst, tmp_path):
    run(inst, tmp_path, {})
    n_of = len(list(VsiafDb(inst).table("OFICINA").records()))
    imp, res = run(inst, tmp_path, {}, apply=False)
    assert res.counts == {} and any("ya existe" in m for m in issues(res, "AVISO"))
    assert n_of == 2


def test_codigos_correlativos(inst, tmp_path):
    run(inst, tmp_path, {})
    db = VsiafDb(inst)
    assert [r["CODOFIC"] for r in db.table("OFICINA").records()] == [1, 2]
    assert [(r["CODOFIC"], r["CODRESP"]) for r in db.table("RESP").records()] == [(1, 1), (2, 1)]
    assert [(r["CODCONT"], r["CODAUX"]) for r in db.table("AUXILIAR").records()] == [(15, 1), (2, 1)]
    assert [r["COD_EXP"] for r in db.table("RESP").records()] == [2, 0]


# ----------------------------------------------------------------------------- revalúo / transferencia / baja
def test_reval_igual_que_vsiaf(inst, tmp_path):
    imp, res = run(inst, tmp_path, {
        "ACTIVOS": [activo(codigo="R-1", fecha_incorporacion=fecha(100), costo_inicial=2000)],
        "REVALUOS": [dict(codigo="R-1", fecha_revaluo=fecha(10), nuevo_costo=3500, nueva_vida_util=5,
                          disposicion_respaldo="RES-1", motivo="TECNICO")]})
    assert res.errors == 0
    db = VsiafDb(inst)
    a = list(db.table("ACTUAL").records())[0]
    rv = list(db.table("REVAL").records())[0]
    base = TODAY - dt.timedelta(days=9)           # fecha del revalúo + 1
    assert (a["DIA"], a["MES"], a["ANO"]) == (base.day, base.month, base.year)
    assert a["B_REV"] is True and a["COSTO"] == 3500 and a["VIDAUTIL"] == 5 and a["DEPACU"] == 0
    old = TODAY - dt.timedelta(days=100)
    assert rv["COSTO"] == 2000 and rv["VIDAUTIL"] == 4 and (rv["DIA"], rv["MES"], rv["ANO"]) == (old.day, old.month, old.year)
    assert rv["RESOLUCION"] == "RES-1" and rv["OBSERV"] == "TECNICO" and rv["DEPGESTION"] > 0
    assert rv["ACTUA"] == pytest.approx(2000 - rv["DEPACU"], abs=0.01)


def test_reval_requiere_aprobado_y_resolucion_unica(inst, tmp_path):
    imp, res = run(inst, tmp_path, {
        "ACTIVOS": [activo(codigo="E-1", estado_registro="ELABORADO"), activo(codigo="P-1")],
        "REVALUOS": [dict(codigo="E-1", fecha_revaluo=fecha(5), nuevo_costo=1, nueva_vida_util=4, disposicion_respaldo="R1"),
                     dict(codigo="P-1", fecha_revaluo=fecha(5), nuevo_costo=5, nueva_vida_util=4, disposicion_respaldo="R2"),
                     dict(codigo="P-1", fecha_revaluo=fecha(4), nuevo_costo=6, nueva_vida_util=4, disposicion_respaldo="R2")]},
        apply=False)
    msgs = issues(res)
    assert any("ELABORADO" in m for m in msgs) and any("Ya existe un revalúo" in m for m in msgs)


def test_transferencia_misma_y_distinta_unidad(inst, tmp_path):
    rows = {"UNIDADES": [dict(unidad="2", descripcion="OTRA")],
            "OFICINAS": BASE["OFICINAS"] + [dict(unidad="2", oficina="DIRECCION")],
            "RESPONSABLES": BASE["RESPONSABLES"] + [dict(unidad="2", oficina="DIRECCION", responsable="MARIA", cargo="DIR")],
            "AUXILIARES": BASE["AUXILIARES"] + [dict(unidad="2", grupo_contable=15, auxiliar="LAP2")],
            "ACTIVOS": [activo(codigo="T-1"), activo(codigo="T-2")],
            "TRANSFERENCIAS": [dict(codigo="T-1", oficina_destino="ALMACEN", responsable_destino="CARLOS QUISPE"),
                               dict(codigo="T-2", unidad_destino="2", oficina_destino="DIRECCION",
                                    responsable_destino="MARIA", auxiliar_destino="LAP2")]}
    imp, res = run(inst, tmp_path, rows)
    assert res.errors == 0
    db = VsiafDb(inst)
    act = {r["CODIGO"]: r for r in db.table("ACTUAL").records()}
    assert (act["T-1"]["UNIDAD"], act["T-1"]["CODOFIC"], act["T-1"]["CODRESP"]) == ("1", 2, 1)
    assert (act["T-2"]["UNIDAD"], act["T-2"]["CODOFIC"], act["T-2"]["CODAUX"]) == ("2", 1, 1)
    tr = list(db.table("TRASFE").records())
    assert [(t["CODIGO"], t["UNIDADINI"], t["UNIDAD"]) for t in tr] == [("T-1", "1", "1"), ("T-2", "1", "2")]


def test_transferencia_entre_unidades_exige_auxiliar(inst, tmp_path):
    rows = {"UNIDADES": [dict(unidad="2", descripcion="OTRA")], "OFICINAS": BASE["OFICINAS"] + [dict(unidad="2", oficina="D")],
            "RESPONSABLES": BASE["RESPONSABLES"] + [dict(unidad="2", oficina="D", responsable="M", cargo="X")],
            "ACTIVOS": [activo()], "TRANSFERENCIAS": [dict(codigo="A-1", unidad_destino="2", oficina_destino="D", responsable_destino="M")]}
    imp, res = run(inst, tmp_path, rows, apply=False)
    assert any("auxiliar de destino" in m for m in issues(res))


def test_baja_igual_que_vsiaf(inst, tmp_path):
    imp, res = run(inst, tmp_path, {
        "ACTIVOS": [activo(codigo="B-1", fecha_incorporacion=fecha(40), costo_inicial=1200)],
        "BAJAS": [dict(codigo="B-1", fecha_baja=fecha(3), motivo_baja="Hurto", disposicion_respaldo="RB-1",
                       observaciones="ROBADO")]})
    assert res.errors == 0
    db = VsiafDb(inst)
    all_a = list(db.table("ACTUAL").records(include_deleted=True))
    assert all_a[0].deleted and all_a[0]["OBSERV"] == "DADO DE BAJA" and list(db.table("ACTUAL").records()) == []
    b = list(db.table("BAJAS").records())[0]
    assert b["CODBAJA"] == 2 and b["RESOLUCION"] == "RB-1" and b["MOTIVO"] == "ROBADO" and b["OBSERV"] == "DADO DE BAJA"
    assert b["COSTO"] == 1200 and b["COSBAJINI"] == 1200 and b["COSACTBAJ"] == 1200 and b["DEPGESTION"] > 0
    assert (b["D_BAJA"], b["A_BAJA"]) == ((TODAY - dt.timedelta(days=3)).day, 2026)


def test_baja_error_transcripcion_solo_gestion_vigente(inst, tmp_path):
    rows = {"ACTIVOS": [activo(codigo="V-1", fecha_incorporacion="15/03/2025")],
            "BAJAS": [dict(codigo="V-1", fecha_baja=fecha(1), motivo_baja=9, disposicion_respaldo="X")]}
    imp, res = run(inst, tmp_path, rows, apply=False)
    assert any("gestión vigente" in m for m in issues(res))


def test_baja_fecha_anterior_o_activo_inexistente(inst, tmp_path):
    rows = {"ACTIVOS": [activo(codigo="V-1", fecha_incorporacion=fecha(10))],
            "BAJAS": [dict(codigo="V-1", fecha_baja=fecha(20), motivo_baja=1, disposicion_respaldo="X"),
                      dict(codigo="NOHAY", fecha_baja=fecha(1), motivo_baja=1, disposicion_respaldo="X"),
                      dict(codigo="V-1", fecha_baja=fecha(1), motivo_baja=77, disposicion_respaldo="X")]}
    imp, res = run(inst, tmp_path, rows, apply=False)
    msgs = " | ".join(issues(res))
    assert "anterior a la fecha base" in msgs and "No existe el activo" in msgs and "no reconocido" in msgs


# ----------------------------------------------------------------------------- políticas
def test_un_error_cancela_todo_y_solo_validas_importa_el_resto(inst, tmp_path):
    rows = {"ACTIVOS": [activo(codigo="OK-1"), activo(codigo="MAL-1", costo_inicial=0)]}
    imp, res = run(inst, tmp_path, rows, apply=False)
    before = [open(os.path.join(inst, "dbfs", "ACTUAL.DBF"), "rb").read()]
    with pytest.raises(ImportAbort):
        imp.apply()
    assert before == [open(os.path.join(inst, "dbfs", "ACTUAL.DBF"), "rb").read()]
    imp2, res2 = run(inst, tmp_path, rows, only_valid=True)
    assert res2.applied and [r["CODIGO"] for r in VsiafDb(inst).table("ACTUAL").records()] == ["OK-1"]


def test_validar_no_escribe(inst, tmp_path):
    h = {f: open(os.path.join(inst, "dbfs", f), "rb").read() for f in os.listdir(os.path.join(inst, "dbfs"))}
    run(inst, tmp_path, {"ACTIVOS": [activo()]}, apply=False)
    assert h == {f: open(os.path.join(inst, "dbfs", f), "rb").read() for f in os.listdir(os.path.join(inst, "dbfs"))}


def test_respaldo_compatible_y_restaurable(inst, tmp_path):
    import zipfile
    imp, res = run(inst, tmp_path, {"ACTIVOS": [activo()]})
    z = zipfile.ZipFile(res.backup_path)
    names = {n.upper() for n in z.namelist()}
    assert {"ACTUAL.DBF", "ACTUAL.FPT", "CODCONT.DBF"} <= names and all("/" not in n for n in names)
    assert os.path.exists(res.backup_path[:-4] + ".gtz")
    # el respaldo contiene la BD ANTES de importar
    z.extractall(str(tmp_path / "ex"))
    assert DbfTable(str(tmp_path / "ex" / "ACTUAL.DBF")).nrec == 0


def test_rollback_si_falla_la_escritura(inst, tmp_path, monkeypatch):
    p = write_book(tmp_path, dict(BASE, ACTIVOS=[activo()]))
    imp = importer(inst)
    imp.plan(read_workbook(p))
    before = {f: open(os.path.join(inst, "dbfs", f), "rb").read() for f in os.listdir(os.path.join(inst, "dbfs"))}
    orig = DbfTable.save
    calls = {"n": 0}

    def boom(self):
        calls["n"] += 1
        if calls["n"] == 3:
            raise OSError("disco lleno")
        return orig(self)

    monkeypatch.setattr(DbfTable, "save", boom)
    with pytest.raises(OSError):
        imp.apply(p)
    assert before == {f: open(os.path.join(inst, "dbfs", f), "rb").read() for f in os.listdir(os.path.join(inst, "dbfs"))
                      if not f.endswith(".vsiaf_imp_tmp")}


def test_gestion_cerrada_bloquea(inst, tmp_path):
    from vsiaf_importer.dbf import create_table
    os.makedirs(os.path.join(inst, "closeges"), exist_ok=True)
    cp = os.path.join(inst, "closeges", "closeges.DBF")
    create_table(cp, [("NOM_ARCH", "C", 6, 0)], version=0x03)
    t = DbfTable(cp)
    t.append(dict(NOM_ARCH="ACTUAL"))
    t.save()
    imp, res = run(inst, tmp_path, {"ACTIVOS": [activo()]}, apply=False)
    assert any("CERRADA" in m for m in issues(res))
    with pytest.raises(ImportAbort):
        imp.apply()


def test_libro_sin_hojas_reconocidas(inst, tmp_path):
    from openpyxl import Workbook
    p = str(tmp_path / "x.xlsx")
    wb = Workbook()
    wb.active.title = "OTRA"
    wb.save(p)
    imp = importer(inst)
    res = imp.plan(read_workbook(p))
    assert res.errors == 1
    with pytest.raises(ImportAbort):
        imp.apply()


def test_fechas_y_numeros_en_formatos_distintos(inst, tmp_path):
    imp, res = run(inst, tmp_path, {"ACTIVOS": [
        activo(codigo="F-1", fecha_incorporacion=TODAY - dt.timedelta(days=5), costo_inicial="1.234,56"),
        activo(codigo="F-2", fecha_incorporacion=(TODAY - dt.timedelta(days=5)).isoformat(), costo_inicial="1,234.56"),
        activo(codigo="F-3", fecha_incorporacion=(TODAY - dt.timedelta(days=5)).strftime("%d-%m-%Y"), costo_inicial=1234.56)]})
    assert res.errors == 0
    assert {r["COSTO"] for r in VsiafDb(inst).table("ACTUAL").records()} == {1234.56}
