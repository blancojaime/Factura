"""Catálogo de reportes (equivalentes a los del SIIM 98 + mejoras). Cada reporte se exporta a PDF y Excel."""
from datetime import date

from ..calc.util import D
from ..services import liquidacion as L, otros, padron
from ..services import recaudacion as R
from ..services.base import Ctx, hoy
from .engine import Col, Report

CATALOGO = {}
NOMBRE = "COALESCE(NULLIF(TRIM(c.razon_social),''), TRIM(IFNULL(c.paterno,'')||' '||IFNULL(c.materno,'')||' '||IFNULL(c.nombre,'')))"
P_DESDE = dict(name="desde", label="Desde", kind="date", default="ini_anio")
P_HASTA = dict(name="hasta", label="Hasta", kind="date", default="hoy")
P_GESTION = dict(name="gestion", label="Gestión", kind="gestion")
P_RUBRO = dict(name="rubro", label="Rubro", kind="choice", choices=["", "IPBI", "IPVA", "PAF", "PUB", "IMT"])
P_FECHA = dict(name="fecha", label="Fecha", kind="date", default="hoy")


def reporte(id_, grupo, titulo, params=()):
    def deco(fn):
        CATALOGO[id_] = dict(id=id_, grupo=grupo, titulo=titulo, params=list(params), fn=fn)
        return fn
    return deco


def ejecutar(ctx: Ctx, id_, **p) -> Report:
    r = CATALOGO[id_]["fn"](ctx, **p)
    r.code = r.code or id_.upper()
    return r


def _rep(titulo, cols, rows, sub="", **k):
    return Report(titulo, cols, [dict(r) if not isinstance(r, dict) else r for r in rows], sub, **k)


def _rng(p):
    return p.get("desde") or f"{date.today().year}-01-01", p.get("hasta") or hoy()


C = Col
# ----------------------------------------------------------------------------------------------- EMPADRONAMIENTO
@reporte("emp_contribuyentes", "Empadronamiento", "Listado de contribuyentes empadronados",
         [dict(name="persona", label="Tipo de persona", kind="choice", choices=["", "N", "J", "S"]), dict(name="zona", label="Zona", kind="text"),
          dict(name="estado", label="Estado", kind="choice", choices=["ACTIVO", "INCOMPLETO", "INACTIVO", ""])])
def _(ctx, persona="", zona="", estado="ACTIVO"):
    q, a = f"SELECT c.pmc, {NOMBRE} AS nombre, c.persona, c.tipo_doc, c.nro_doc, c.nit, c.zona, TRIM(IFNULL(c.tipo_via,'')||' '||IFNULL(c.calle,'')||' '||IFNULL(c.numero,'')) AS dir, c.telefono, c.estado, c.fecha_registro FROM contribuyentes c WHERE 1=1", []
    for col, v in (("c.persona", persona), ("c.zona", zona), ("c.estado", estado)):
        if v:
            q += f" AND {col}=?"; a.append(v)
    return _rep("Listado de contribuyentes empadronados", [C("pmc", "PMC", "text", .8), C("nombre", "Nombre / Razón social", "text", 3), C("persona", "Tipo", "text", .4), C("nro_doc", "Documento", "text", 1),
                C("nit", "NIT", "text", 1), C("zona", "Zona", "text", .5), C("dir", "Dirección", "text", 2.5), C("telefono", "Teléfono", "text", .9), C("estado", "Estado", "text", .8),
                C("fecha_registro", "Registro", "date", .8)], ctx.db.all(q + " ORDER BY nombre", a))


@reporte("emp_inmuebles", "Empadronamiento", "Listado de inmuebles empadronados", [dict(name="zona", label="Zona", kind="text"), dict(name="tipo", label="Tipo", kind="choice", choices=["", "CASA", "TERRENO", "DEPARTAMENTO", "RURAL"])])
def _(ctx, zona="", tipo=""):
    q, a = f"SELECT i.id, i.pmc, {NOMBRE} AS nombre, i.tipo, i.zona, TRIM(IFNULL(i.calle,'')||' '||IFNULL(i.numero,'')) AS dir, i.cod_catastral, i.material_via, i.superficie, i.sup_construida, i.anio_construccion, i.exento FROM inmuebles i JOIN contribuyentes c ON c.pmc=i.pmc WHERE i.estado='ACTIVO'", []
    for col, v in (("i.zona", zona), ("i.tipo", tipo)):
        if v:
            q += f" AND {col}=?"; a.append(v)
    return _rep("Listado de inmuebles empadronados", [C("pmc", "PMC", "text", .8), C("nombre", "Propietario", "text", 2.5), C("tipo", "Tipo", "text", 1), C("zona", "Zona", "text", .5), C("dir", "Dirección", "text", 2),
                C("cod_catastral", "Cód. catastral", "text", 1.1), C("material_via", "Vía", "text", .8), C("superficie", "Sup. m²", "money", .8, True), C("sup_construida", "Constr. m²", "money", .8, True),
                C("anio_construccion", "Año", "text", .5), C("exento", "Exención", "text", .9)], ctx.db.all(q + " ORDER BY i.zona, nombre", a))


@reporte("emp_vehiculos", "Empadronamiento", "Listado de vehículos empadronados", [dict(name="tipo", label="Tipo", kind="text")])
def _(ctx, tipo=""):
    q, a = f"SELECT v.pmc, {NOMBRE} AS nombre, v.placa, v.tipo, v.marca, v.modelo, v.procedencia, v.anio_fab, v.cilindrada, v.toneladas, v.uso, v.exento FROM vehiculos v JOIN contribuyentes c ON c.pmc=v.pmc WHERE v.estado='ACTIVO'", []
    if tipo:
        q += " AND v.tipo=?"; a.append(tipo.upper())
    return _rep("Listado de vehículos automotores empadronados", [C("pmc", "PMC", "text", .8), C("nombre", "Propietario", "text", 2.5), C("placa", "Placa", "text", .9), C("tipo", "Tipo", "text", 1),
                C("marca", "Marca", "text", 1), C("modelo", "Modelo", "text", 1), C("procedencia", "Procedencia", "text", 1.1), C("anio_fab", "Año", "text", .5), C("cilindrada", "cc", "int", .6),
                C("toneladas", "Ton.", "money", .5), C("uso", "Uso", "text", .8), C("exento", "Exención", "text", .8)], ctx.db.all(q + " ORDER BY v.placa", a))


@reporte("emp_actividades", "Empadronamiento", "Listado de actividades económicas empadronadas",
         [dict(name="act", label="Tipo de actividad", kind="act"), dict(name="zona", label="Zona", kind="text"), dict(name="estado_licencia", label="Estado licencia", kind="choice", choices=["", "VIGENTE", "VENCIDA", "SIN LICENCIA", "SUSPENDIDA"])])
def _(ctx, act="", zona="", estado_licencia=""):
    q, a = f"""SELECT a.pmc, {NOMBRE} AS nombre, a.nombre_comercial, a.act||'-'||a.cat AS cod, t.descripcion AS tipo, a.zona, a.superficie, a.fecha_inicio, a.nro_licencia,
               a.licencia_vence, a.estado_licencia FROM actividades a JOIN contribuyentes c ON c.pmc=a.pmc JOIN act_tipos t ON t.codigo=a.act WHERE a.estado='ACTIVO'""", []
    for col, v in (("a.act", act), ("a.zona", zona), ("a.estado_licencia", estado_licencia)):
        if v:
            q += f" AND {col}=?"; a.append(v)
    return _rep("Listado de actividades económicas empadronadas", [C("pmc", "PMC", "text", .8), C("nombre", "Contribuyente", "text", 2.2), C("nombre_comercial", "Nombre comercial", "text", 2), C("cod", "Act-Cat", "text", .6),
                C("tipo", "Actividad", "text", 2), C("zona", "Zona", "text", .5), C("superficie", "m²", "money", .6, True), C("fecha_inicio", "Inicio", "date", .8), C("nro_licencia", "N° licencia", "text", 1),
                C("licencia_vence", "Vence", "date", .8), C("estado_licencia", "Licencia", "text", 1)], ctx.db.all(q + " ORDER BY a.act,a.cat,nombre", a))


@reporte("emp_publicidad", "Empadronamiento", "Listado de publicidad y propaganda")
def _(ctx):
    rows = ctx.db.all(f"SELECT p.pmc, {NOMBRE} AS nombre, p.tipo, p.descripcion, p.ubicacion, p.ancho, p.alto, p.ancho*p.alto AS area, p.exento FROM publicidad p JOIN contribuyentes c ON c.pmc=p.pmc WHERE p.estado='ACTIVO' ORDER BY nombre")
    return _rep("Listado de publicidad y propaganda", [C("pmc", "PMC", "text", .8), C("nombre", "Contribuyente", "text", 2.5), C("tipo", "Tipo", "text", 1.2), C("descripcion", "Descripción", "text", 2.5),
                C("ubicacion", "Ubicación", "text", 2), C("area", "Área m²", "money", .8, True), C("exento", "Exención", "text", .9)], rows)


@reporte("emp_control", "Empadronamiento", "Control de empadronamiento (F-019 / F-027 / F-035)",
         [P_DESDE, P_HASTA, dict(name="usuario", label="Usuario", kind="text"), dict(name="pmc", label="PMC", kind="text")])
def _(ctx, desde=None, hasta=None, usuario="", pmc=""):
    d, h = _rng(dict(desde=desde, hasta=hasta))
    q, a = f"SELECT f.fecha, f.tipo, f.nro_orden, f.pmc, {NOMBRE} AS nombre, f.usuario FROM emp_formularios f LEFT JOIN contribuyentes c ON c.pmc=f.pmc WHERE f.fecha BETWEEN ? AND ?", [d, h]
    if usuario:
        q += " AND f.usuario=?"; a.append(usuario)
    if pmc:
        q += " AND f.pmc=?"; a.append(int(pmc))
    return _rep("Control de empadronamiento", [C("fecha", "Fecha", "date", 1), C("tipo", "Formulario", "text", 1), C("nro_orden", "N° orden", "text", 1), C("pmc", "PMC", "text", 1), C("nombre", "Contribuyente", "text", 3),
                C("usuario", "Usuario", "text", 1)], ctx.db.all(q + " ORDER BY f.fecha, f.id", a), f"Del {d} al {h}")


@reporte("emp_estadisticas", "Empadronamiento", "Estadísticas de empadronamiento por zona")
def _(ctx):
    rows = ctx.db.all("""SELECT z.codigo AS zona, z.descripcion,
        (SELECT COUNT(*) FROM contribuyentes WHERE zona=z.codigo AND estado='ACTIVO') AS contrib,
        (SELECT COUNT(*) FROM inmuebles WHERE zona=z.codigo AND estado='ACTIVO') AS inm,
        (SELECT COUNT(*) FROM actividades WHERE zona=z.codigo AND estado='ACTIVO') AS act,
        (SELECT COUNT(*) FROM vehiculos v JOIN contribuyentes c ON c.pmc=v.pmc WHERE c.zona=z.codigo AND v.estado='ACTIVO') AS veh FROM zonas z ORDER BY z.codigo""")
    return _rep("Estadísticas de empadronamiento por zona", [C("zona", "Zona", "text", .6), C("descripcion", "Descripción", "text", 2.5), C("contrib", "Contribuyentes", "int", 1, True), C("inm", "Inmuebles", "int", 1, True),
                C("veh", "Vehículos (zona del propietario)", "int", 1.3, True), C("act", "Actividades", "int", 1, True)], rows)


@reporte("emp_incompletos", "Empadronamiento", "Registros incompletos (pendientes de depuración)")
def _(ctx):
    rows = ctx.db.all(f"SELECT c.pmc, {NOMBRE} AS nombre, c.nro_doc, c.fecha_registro, c.usuario FROM contribuyentes c WHERE c.estado='INCOMPLETO' ORDER BY c.pmc")
    return _rep("Registros incompletos", [C("pmc", "PMC", "text", 1), C("nombre", "Nombre", "text", 3), C("nro_doc", "Documento", "text", 1.3), C("fecha_registro", "Registro", "date", 1), C("usuario", "Usuario", "text", 1)], rows)


@reporte("emp_bajas", "Empadronamiento", "Bajas registradas (F-035)", [P_DESDE, P_HASTA])
def _(ctx, desde=None, hasta=None):
    d, h = _rng(dict(desde=desde, hasta=hasta))
    rows = ctx.db.all("SELECT fecha, pmc, nro_orden, usuario FROM emp_formularios WHERE tipo='F-035' AND fecha BETWEEN ? AND ? ORDER BY fecha", (d, h))
    return _rep("Bajas registradas (F-035)", [C("fecha", "Fecha", "date"), C("pmc", "PMC", "text"), C("nro_orden", "N° orden", "text"), C("usuario", "Usuario", "text")], rows, f"Del {d} al {h}")


@reporte("emp_material_vias", "Empadronamiento", "Inmuebles por material de vías y zona")
def _(ctx):
    rows = ctx.db.all("SELECT zona, material_via, COUNT(*) AS n, SUM(superficie) AS sup FROM inmuebles WHERE estado='ACTIVO' AND tipo<>'RURAL' GROUP BY zona, material_via ORDER BY zona, material_via")
    return _rep("Inmuebles por material de vías y zona", [C("zona", "Zona", "text"), C("material_via", "Material de vía", "text", 1.5), C("n", "Inmuebles", "int", 1, True), C("sup", "Superficie m²", "money", 1.2, True)], rows)


@reporte("emp_servicios", "Empadronamiento", "Inmuebles por servicios básicos y zona")
def _(ctx):
    rows = ctx.db.all("SELECT zona, COUNT(*) AS n, SUM(luz) AS luz, SUM(agua) AS agua, SUM(alcantarillado) AS alc, SUM(telefono) AS tel FROM inmuebles WHERE estado='ACTIVO' AND tipo<>'RURAL' GROUP BY zona ORDER BY zona")
    return _rep("Inmuebles por servicios básicos y zona", [C("zona", "Zona"), C("n", "Inmuebles", "int", 1, True), C("luz", "Luz", "int", 1, True), C("agua", "Agua", "int", 1, True),
                C("alc", "Alcantarillado", "int", 1.2, True), C("tel", "Teléfono", "int", 1, True)], rows)


# ----------------------------------------------------------------------------------------------- LIQUIDACIÓN
@reporte("liq_listado", "Liquidación", "Liquidaciones emitidas", [P_DESDE, P_HASTA, P_RUBRO, dict(name="estado", label="Estado", kind="choice", choices=["", "PENDIENTE", "PAGADA", "PARCIAL", "EN_PLAN", "ANULADA", "RECTIFICADA"])])
def _(ctx, desde=None, hasta=None, rubro="", estado=""):
    d, h = _rng(dict(desde=desde, hasta=hasta))
    q, a = f"SELECT l.nro, l.fecha, l.rubro, l.gestion, l.tipo_liq, l.pmc, {NOMBRE} AS nombre, l.objeto_desc, l.impuesto, l.neto, l.estado, l.usuario FROM liquidaciones l JOIN contribuyentes c ON c.pmc=l.pmc WHERE l.fecha BETWEEN ? AND ?", [d, h]
    for col, v in (("l.rubro", rubro), ("l.estado", estado)):
        if v:
            q += f" AND {col}=?"; a.append(v)
    return _rep("Liquidaciones emitidas", [C("nro", "N°", "text", 1.3), C("fecha", "Fecha", "date", .9), C("rubro", "Rubro", "text", .6), C("gestion", "Gest.", "text", .5), C("tipo_liq", "Tipo", "text", 1), C("pmc", "PMC", "text", .9),
                C("nombre", "Contribuyente", "text", 2.2), C("objeto_desc", "Bien / actividad", "text", 3), C("neto", "Importe Bs", "money", 1, True), C("estado", "Estado", "text", .9)],
                ctx.db.all(q + " ORDER BY l.id", a), f"Del {d} al {h}")


@reporte("liq_evasores", "Liquidación", "Contribuyentes en mora (preliquidación masiva, sin emitir)", [P_RUBRO, P_GESTION, dict(name="zona", label="Zona", kind="text")])
def _(ctx, rubro="IPBI", gestion=None, zona=""):
    rubro = rubro or "IPBI"
    gestion = int(gestion or ctx.db.param("gestion_hasta"))
    rows, errs = L.liquidar_masiva(Ctx(ctx.db, None) if False else ctx, rubro, gestion, zona=zona or None, guardar=False)
    out = [dict(r, nombre=_nombre(ctx.db, r["pmc"])) for r in rows]
    notas = [f"Observación PMC {e[0]}: {e[1]}" for e in errs[:30]]
    return _rep(f"Contribuyentes en mora – {rubro} gestión {gestion}", [C("pmc", "PMC", "text", 1), C("nombre", "Contribuyente", "text", 3), C("descripcion", "Bien / actividad", "text", 3.5), C("neto", "Impuesto Bs", "money", 1, True),
                C("mora", "Días mora", "int", .8), C("total_hoy", "Deuda hoy Bs", "money", 1.1, True)], out, notes=notas)


def _nombre(db, pmc):
    return db.scalar(f"SELECT {NOMBRE} FROM contribuyentes c WHERE pmc=?", (pmc,), "")


# ----------------------------------------------------------------------------------------------- RECAUDACIÓN
@reporte("rec_diario", "Recaudación", "Recaudación diaria (cajas / entidades bancarias)",
         [P_FECHA, dict(name="modalidad", label="Modalidad", kind="choice", choices=["", "CAJA", "BANCO"]), dict(name="cajero", label="Cajero / entidad", kind="text"), dict(name="detalle", label="Detalle", kind="choice", choices=["DETALLE", "RESUMEN"])])
def _(ctx, fecha=None, modalidad="", cajero="", detalle="DETALLE"):
    f = fecha or hoy()
    q, a = f"SELECT p.nro_recibo, p.hora, p.rubro, p.gestion, p.pmc, {NOMBRE} AS nombre, p.modalidad, COALESCE(NULLIF(p.entidad,''),p.cajero) AS cajero, p.monto_neto, p.descuento, p.mant_valor, p.interes, p.multa_df+p.sancion AS multas, p.total FROM pagos p JOIN contribuyentes c ON c.pmc=p.pmc WHERE p.fecha=? AND p.estado='VIGENTE'", [f]
    if modalidad:
        q += " AND p.modalidad=?"; a.append(modalidad)
    if cajero:
        q += " AND (p.cajero=? OR p.entidad=?)"; a += [cajero, cajero]
    rows = ctx.db.all(q + " ORDER BY p.id", a)
    if detalle == "RESUMEN":
        agg = {}
        for r in rows:
            k = (r["rubro"], r["modalidad"], r["cajero"])
            x = agg.setdefault(k, dict(rubro=r["rubro"], modalidad=r["modalidad"], cajero=r["cajero"], n=0, total=0.0))
            x["n"] += 1; x["total"] += r["total"]
        return _rep("Resumen de recaudación diaria", [C("rubro", "Rubro"), C("modalidad", "Modalidad"), C("cajero", "Cajero / entidad", "text", 2), C("n", "Pagos", "int", .8, True), C("total", "Total Bs", "money", 1.2, True)], list(agg.values()), f"Fecha: {f}")
    return _rep("Recaudación diaria", [C("nro_recibo", "Recibo", "text", 1.3), C("hora", "Hora", "text", .7), C("rubro", "Rubro", "text", .6), C("gestion", "Gest.", "text", .5), C("pmc", "PMC", "text", .9),
                C("nombre", "Contribuyente", "text", 2.2), C("cajero", "Cajero/entidad", "text", 1), C("monto_neto", "Impuesto", "money", .9, True), C("descuento", "Desc.", "money", .7, True),
                C("mant_valor", "M.V.", "money", .7, True), C("interes", "Interés", "money", .7, True), C("multas", "Multas", "money", .7, True), C("total", "Total Bs", "money", .9, True)], rows, f"Fecha: {f}")


@reporte("rec_mensual", "Recaudación", "Recaudación mensual / anual por rubro", [P_RUBRO, dict(name="anio", label="Año", kind="gestion"), dict(name="mes", label="Mes (1-12, vacío = anual)", kind="text")])
def _(ctx, rubro="", anio=None, mes=""):
    anio = int(anio or date.today().year)
    q, a = "SELECT substr(fecha,6,2) AS mes, rubro, COUNT(*) AS n, SUM(total) AS total, SUM(monto_neto-descuento+mant_valor) AS tributo, SUM(interes) AS interes, SUM(multa_df+sancion) AS multas FROM pagos WHERE estado='VIGENTE' AND substr(fecha,1,4)=?", [str(anio)]
    if rubro:
        q += " AND rubro=?"; a.append(rubro)
    if mes:
        q += " AND substr(fecha,6,2)=?"; a.append(f"{int(mes):02d}")
    return _rep(f"Recaudación {'mensual' if mes else 'anual'} {anio}", [C("mes", "Mes"), C("rubro", "Rubro"), C("n", "Pagos", "int", .8, True), C("tributo", "Tributo", "money", 1.2, True), C("interes", "Intereses", "money", 1, True),
                C("multas", "Multas", "money", 1, True), C("total", "Total Bs", "money", 1.2, True)], ctx.db.all(q + " GROUP BY mes, rubro ORDER BY mes, rubro", a))


@reporte("rec_periodo_fiscal", "Recaudación", "Recaudación por periodo fiscal y zona (con nivel de evasión)", [P_RUBRO, P_GESTION])
def _(ctx, rubro="IPBI", gestion=None):
    rubro = rubro or "IPBI"
    g = int(gestion or ctx.db.param("gestion_hasta"))
    tabla = L.TABLA[rubro]
    rows = []
    for z in ctx.db.all("SELECT DISTINCT COALESCE(zona,'-') AS zona FROM " + tabla + " WHERE estado='ACTIVO' ORDER BY 1"):
        total = ctx.db.scalar(f"SELECT COUNT(*) FROM {tabla} WHERE estado='ACTIVO' AND COALESCE(zona,'-')=?", (z["zona"],), 0)
        pag = ctx.db.scalar(f"SELECT COUNT(DISTINCT l.objeto_id) FROM liquidaciones l JOIN {tabla} o ON o.id=l.objeto_id WHERE l.rubro=? AND l.gestion=? AND l.estado='PAGADA' AND COALESCE(o.zona,'-')=?", (rubro, g, z["zona"]), 0)
        monto = ctx.db.scalar(f"SELECT COALESCE(SUM(p.total),0) FROM pagos p JOIN liquidaciones l ON l.id=p.liq_id JOIN {tabla} o ON o.id=l.objeto_id WHERE l.rubro=? AND l.gestion=? AND p.estado='VIGENTE' AND COALESCE(o.zona,'-')=?", (rubro, g, z["zona"]), 0)
        rows.append(dict(zona=z["zona"], total=total, pagados=pag, monto=monto, evasion=(100 * (total - pag) / total) if total else 0))
    return _rep(f"Recaudación por periodo fiscal {g} – {rubro}", [C("zona", "Zona"), C("total", "Bienes/actividades", "int", 1.2, True), C("pagados", "Con pago", "int", 1, True), C("monto", "Recaudado Bs", "money", 1.3, True),
                C("evasion", "Evasión", "pct", 1)], rows)


@reporte("rec_sincom", "Recaudación", "Reporte SINCOM – mayorizado por rubros de recaudación", [P_DESDE, P_HASTA])
def _(ctx, desde=None, hasta=None):
    d, h = _rng(dict(desde=desde, hasta=hasta))
    db = ctx.db
    acum = {}
    def add(cod, v):
        acum[cod] = acum.get(cod, 0) + float(v or 0)
    from ..core.seed import RUBROS_LIQ
    for p in db.all("SELECT rubro, SUM(monto_neto-descuento+mant_valor) tr, SUM(interes) i, SUM(multa_df+sancion) m FROM pagos WHERE estado='VIGENTE' AND fecha BETWEEN ? AND ? GROUP BY rubro", (d, h)):
        add(RUBROS_LIQ[p["rubro"]], p["tr"]); add("16130", p["i"]); add("15910", p["m"])
    for r in db.all("SELECT fd.rubro, SUM(fd.total) t FROM fuc_det fd JOIN fuc f ON f.id=fd.fuc_id WHERE f.estado='RECAUDADO' AND f.fecha_pago BETWEEN ? AND ? GROUP BY fd.rubro", (d, h)):
        add(r["rubro"], r["t"])
    rub = {r["codigo"]: r for r in db.all("SELECT * FROM rubros")}
    rows = []
    for cod in sorted(rub):
        if rub[cod]["tipo"] == "S":
            if acum.get(cod):
                rows.append(dict(codigo=cod, descripcion=rub[cod]["descripcion"], monto=acum[cod], nivel=2))
    # agregados: sumar por prefijos de rubros maestros de nivel superior
    for cod in sorted(rub):
        if rub[cod]["tipo"] == "N":
            s = sum(v for c, v in acum.items() if c.startswith(cod[:3] if len(cod) == 5 and cod.endswith("00") and cod[3:] == "00" else cod[:2]) and rub.get(c, {"tipo": "S"})["tipo"] == "S" and c != cod) if cod.endswith("000") else sum(v for c, v in acum.items() if c.startswith(cod[:3]))
            if s:
                rows.append(dict(codigo=cod, descripcion=rub[cod]["descripcion"].upper(), monto=s, nivel=1))
    rows.sort(key=lambda r: r["codigo"])
    total = sum(v for v in acum.values())
    rows.append(dict(codigo="", descripcion="TOTAL RECAUDADO", monto=total))
    return _rep("Reporte SINCOM – Listado mayorizado por rubros", [C("codigo", "Rubro", "text", 1), C("descripcion", "Descripción", "text", 5), C("monto", "Monto Bs", "money", 1.5)], rows, f"Del {d} al {h}")


@reporte("rec_cuenta_corriente", "Recaudación", "Cuenta corriente del contribuyente", [dict(name="pmc", label="PMC", kind="pmc"), P_FECHA])
def _(ctx, pmc=None, fecha=None):
    pmc = int(pmc)
    filas = R.cuenta_corriente(ctx, pmc, True, fecha or hoy())
    nom = _nombre(ctx.db, pmc)
    return _rep(f"Cuenta corriente – PMC {pmc}", [C("gestion", "Gestión", "text", .7), C("rubro", "Rubro", "text", .6), C("nro", "Liquidación", "text", 1.3), C("objeto", "Bien / actividad", "text", 3.5), C("estado", "Estado", "text", 1),
                C("impuesto", "Impuesto", "money", 1, True), C("pagado", "Pagado", "money", 1, True), C("a_pagar", "A pagar hoy", "money", 1.1, True)], filas, f"{nom} – al {fecha or hoy()}",
                notes=["Las filas 'NO LIQUIDADA' son estimaciones de gestiones vencidas que aún no se liquidaron (posible evasión)."])


@reporte("rec_anulados", "Recaudación", "Pagos anulados", [P_DESDE, P_HASTA])
def _(ctx, desde=None, hasta=None):
    d, h = _rng(dict(desde=desde, hasta=hasta))
    rows = ctx.db.all("SELECT nro_recibo, fecha, rubro, pmc, total, anulado_por, anulado_motivo FROM pagos WHERE estado='ANULADO' AND fecha BETWEEN ? AND ? ORDER BY id", (d, h))
    return _rep("Pagos anulados", [C("nro_recibo", "Recibo", "text", 1.3), C("fecha", "Fecha", "date"), C("rubro", "Rubro", "text", .6), C("pmc", "PMC"), C("total", "Total", "money", 1, True), C("anulado_por", "Anulado por"), C("anulado_motivo", "Motivo", "text", 3)], rows, f"Del {d} al {h}")


@reporte("rec_comparativo", "Recaudación", "Comparativo anual de recaudación por rubro")
def _(ctx):
    rows = ctx.db.all("SELECT substr(fecha,1,4) AS anio, rubro, COUNT(*) AS n, SUM(total) AS total FROM pagos WHERE estado='VIGENTE' GROUP BY anio, rubro ORDER BY anio DESC, rubro")
    return _rep("Comparativo anual de recaudación", [C("anio", "Año"), C("rubro", "Rubro"), C("n", "Pagos", "int", 1, True), C("total", "Total Bs", "money", 1.5, True)], rows)


# ----------------------------------------------------------------------------------------------- ACTIVIDADES ECONÓMICAS (módulo especial)
@reporte("act_licencias_vencer", "Actividades Económicas", "Licencias de funcionamiento por vencer", [dict(name="dias", label="Próximos N días", kind="int", default=30)])
def _(ctx, dias=30):
    rows = padron.licencias_por_vencer(ctx.db, int(dias or 30))
    out = [dict(nro_licencia=r["nro_licencia"], nombre=r["razon_social"] or f"{r['paterno'] or ''} {r['materno'] or ''} {r['nombre'] or ''}".strip(), nombre_comercial=r["nombre_comercial"], act=f"{r['act']}-{r['cat']}", vence=r["licencia_vence"]) for r in rows]
    return _rep(f"Licencias de funcionamiento que vencen en {dias} días", [C("nro_licencia", "N° licencia", "text", 1.2), C("nombre", "Contribuyente", "text", 3), C("nombre_comercial", "Establecimiento", "text", 2.5), C("act", "Act-Cat"), C("vence", "Vence", "date")], out)


@reporte("act_sin_licencia", "Actividades Económicas", "Actividades sin licencia o con licencia vencida (fiscalización)")
def _(ctx):
    padron.refrescar_licencias(ctx.db)
    rows = ctx.db.all(f"SELECT a.pmc, {NOMBRE} AS nombre, a.nombre_comercial, a.act||'-'||a.cat AS cod, a.zona, a.estado_licencia, a.licencia_vence FROM actividades a JOIN contribuyentes c ON c.pmc=a.pmc WHERE a.estado='ACTIVO' AND a.estado_licencia IN ('SIN LICENCIA','VENCIDA','SUSPENDIDA') ORDER BY a.estado_licencia, nombre")
    return _rep("Actividades sin licencia / con licencia vencida", [C("pmc", "PMC"), C("nombre", "Contribuyente", "text", 2.5), C("nombre_comercial", "Establecimiento", "text", 2.5), C("cod", "Act-Cat"), C("zona", "Zona"), C("estado_licencia", "Estado", "text", 1.2), C("licencia_vence", "Venció", "date")], rows)


@reporte("act_proyeccion", "Actividades Económicas", "Proyección de ingresos por Patente de Funcionamiento (simulación)", [P_GESTION, dict(name="modalidad", label="Modalidad", kind="choice", choices=["TOPE_ZONA_SUP", "PUA", "CATEGORIA"])])
def _(ctx, gestion=None, modalidad=None):
    g = int(gestion or ctx.db.param("gestion_hasta"))
    from ..calc.patentes import calcular_paf
    from ..calc.ipbi import CalcError
    rows, err = [], []
    for a in ctx.db.all(f"SELECT a.*, {NOMBRE} AS nombre FROM actividades a JOIN contribuyentes c ON c.pmc=a.pmc WHERE a.estado='ACTIVO'"):
        try:
            d = calcular_paf(ctx.db, a, g, modalidad or None)
            rows.append(dict(pmc=a["pmc"], nombre=a["nombre"], comercial=a["nombre_comercial"], cod=f"{a['act']}-{a['cat']}", zona=a["zona"], sup=a["superficie"], pf=d["impuesto"], nota=d.get("duodecimas", "") or d.get("nota", "")))
        except CalcError as e:
            err.append(f"PMC {a['pmc']}: {e}")
    return _rep(f"Proyección Patente de Funcionamiento {g} ({modalidad or ctx.db.param('patente_modalidad')})", [C("pmc", "PMC"), C("nombre", "Contribuyente", "text", 2.5), C("comercial", "Establecimiento", "text", 2.2), C("cod", "Act-Cat"), C("zona", "Zona"),
                C("sup", "m²", "money", .7), C("pf", "Patente Bs", "money", 1, True), C("nota", "Observación", "text", 1.5)], rows, notes=err[:20])


@reporte("act_resumen_tipo", "Actividades Económicas", "Resumen de actividades por tipo y categoría")
def _(ctx):
    rows = ctx.db.all("SELECT a.act, t.descripcion AS tipo, COUNT(*) AS n, SUM(a.superficie) AS sup, SUM(CASE WHEN a.estado_licencia='VIGENTE' THEN 1 ELSE 0 END) AS conlic FROM actividades a JOIN act_tipos t ON t.codigo=a.act WHERE a.estado='ACTIVO' GROUP BY a.act ORDER BY a.act")
    return _rep("Resumen de actividades económicas por tipo", [C("act", "Cód."), C("tipo", "Tipo de actividad", "text", 4), C("n", "Establecimientos", "int", 1.2, True), C("conlic", "Con licencia vigente", "int", 1.3, True), C("sup", "Superficie m²", "money", 1.2, True)], rows)


@reporte("act_inspecciones", "Actividades Económicas", "Inspecciones realizadas", [P_DESDE, P_HASTA])
def _(ctx, desde=None, hasta=None):
    d, h = _rng(dict(desde=desde, hasta=hasta))
    rows = ctx.db.all("SELECT i.fecha, a.nombre_comercial, i.pmc, i.inspector, i.resultado, i.observaciones, i.plazo_subsanar FROM inspecciones i LEFT JOIN actividades a ON a.id=i.actividad_id WHERE i.fecha BETWEEN ? AND ? ORDER BY i.fecha", (d, h))
    return _rep("Inspecciones realizadas", [C("fecha", "Fecha", "date"), C("nombre_comercial", "Establecimiento", "text", 2.5), C("pmc", "PMC"), C("inspector", "Inspector", "text", 1.3), C("resultado", "Resultado", "text", 1.2), C("observaciones", "Observaciones", "text", 3), C("plazo_subsanar", "Plazo", "date")], rows, f"Del {d} al {h}")


@reporte("act_ciiu", "Actividades Económicas", "Actividades por clasificador CIIU")
def _(ctx):
    rows = ctx.db.all("SELECT a.ciiu, COALESCE(c.descripcion,'(sin clasificar)') AS d, COUNT(*) n FROM actividades a LEFT JOIN ciiu c ON c.codigo=a.ciiu WHERE a.estado='ACTIVO' GROUP BY a.ciiu ORDER BY n DESC")
    return _rep("Actividades por clasificador CIIU", [C("ciiu", "CIIU"), C("d", "Descripción", "text", 4), C("n", "Establecimientos", "int", 1, True)], rows)


# ----------------------------------------------------------------------------------------------- OTROS INGRESOS
@reporte("otros_formularios", "Otros ingresos", "Listado de formularios únicos de caja (FUC)", [P_DESDE, P_HASTA, dict(name="estado", label="Estado", kind="choice", choices=["", "BORRADOR", "RECAUDADO", "ANULADO"])])
def _(ctx, desde=None, hasta=None, estado=""):
    d, h = _rng(dict(desde=desde, hasta=hasta))
    q, a = "SELECT nro, fecha, hora, nombre, detalle, estado, total, cajero FROM fuc WHERE fecha BETWEEN ? AND ?", [d, h]
    if estado:
        q += " AND estado=?"; a.append(estado)
    return _rep("Listado de formularios únicos de caja", [C("nro", "FUC", "text", 1.3), C("fecha", "Fecha", "date"), C("hora", "Hora", "text", .7), C("nombre", "Nombre", "text", 2.5), C("detalle", "Detalle", "text", 3), C("estado", "Estado", "text", 1), C("total", "Total Bs", "money", 1, True), C("cajero", "Usuario")], ctx.db.all(q + " ORDER BY id", a), f"Del {d} al {h}")


@reporte("otros_percibidos", "Otros ingresos", "Ingresos percibidos por rubro y subnivel", [P_DESDE, P_HASTA, dict(name="nivel", label="Nivel", kind="choice", choices=["RUBRO", "SUBNIVEL", "SIMPLE"])])
def _(ctx, desde=None, hasta=None, nivel="SUBNIVEL"):
    d, h = _rng(dict(desde=desde, hasta=hasta))
    if nivel == "RUBRO":
        rows = ctx.db.all("SELECT r.codigo AS cod, r.descripcion AS d, SUM(fd.total) AS total, SUM(fd.cantidad) AS cant FROM fuc_det fd JOIN fuc f ON f.id=fd.fuc_id JOIN rubros r ON r.codigo=fd.rubro WHERE f.estado='RECAUDADO' AND f.fecha_pago BETWEEN ? AND ? GROUP BY r.codigo ORDER BY r.codigo", (d, h))
    elif nivel == "SIMPLE":
        rows = ctx.db.all("SELECT fd.subnivel AS cod, fd.descripcion AS d, SUM(fd.total) AS total, SUM(fd.cantidad) AS cant FROM fuc_det fd JOIN fuc f ON f.id=fd.fuc_id WHERE f.estado='RECAUDADO' AND f.fecha_pago BETWEEN ? AND ? GROUP BY fd.subnivel ORDER BY fd.subnivel", (d, h))
    else:
        rows = ctx.db.all("SELECT COALESCE(s.padre, fd.subnivel) AS cod, COALESCE(p.descripcion, fd.descripcion) AS d, SUM(fd.total) AS total, SUM(fd.cantidad) AS cant FROM fuc_det fd JOIN fuc f ON f.id=fd.fuc_id JOIN subniveles s ON s.codigo=fd.subnivel LEFT JOIN subniveles p ON p.codigo=s.padre WHERE f.estado='RECAUDADO' AND f.fecha_pago BETWEEN ? AND ? GROUP BY cod ORDER BY cod", (d, h))
    return _rep(f"Ingresos percibidos – nivel {nivel.lower()}", [C("cod", "Código", "text", 1.2), C("d", "Descripción", "text", 4), C("cant", "Cantidad", "num", 1), C("total", "Total Bs", "money", 1.3, True)], rows, f"Del {d} al {h}")


@reporte("otros_devengados", "Otros ingresos", "Ingresos devengados (contratos y alquileres)", [P_FECHA])
def _(ctx, fecha=None):
    return _rep("Ingresos devengados", [C("nro", "Contrato", "text", 1.2), C("fecha", "Fecha", "date"), C("subnivel", "Subnivel", "text", 1.2), C("beneficiario", "Beneficiario", "text", 2.5), C("periodos", "Periodos", "int", .8),
                C("devengado", "Devengado", "money", 1.1, True), C("percibido", "Percibido", "money", 1.1, True), C("saldo", "Saldo", "money", 1.1, True)], otros.devengados(ctx.db, fecha or hoy()), f"Al {fecha or hoy()}")


# ----------------------------------------------------------------------------------------------- PLANES / FISCALIZACIÓN
@reporte("plan_listado", "Fiscalización y planes", "Planes de pago", [dict(name="estado", label="Estado", kind="choice", choices=["", "VIGENTE", "CUMPLIDO", "INCUMPLIDO"])])
def _(ctx, estado=""):
    q = f"SELECT p.nro, p.fecha, p.pmc, {NOMBRE} AS nombre, p.deuda_total, p.cuota_inicial, p.n_cuotas, p.estado, (SELECT COUNT(*) FROM plan_cuotas q WHERE q.plan_id=p.id AND q.estado='PENDIENTE' AND q.vence<?) AS vencidas FROM planes_pago p JOIN contribuyentes c ON c.pmc=p.pmc"
    a = [hoy()]
    if estado:
        q += " WHERE p.estado=?"; a.append(estado)
    return _rep("Planes de pago", [C("nro", "Plan", "text", 1.3), C("fecha", "Fecha", "date"), C("pmc", "PMC"), C("nombre", "Contribuyente", "text", 3), C("deuda_total", "Deuda Bs", "money", 1.1, True), C("cuota_inicial", "Cuota inicial", "money", 1, True),
                C("n_cuotas", "Cuotas", "int", .7), C("vencidas", "Vencidas impagas", "int", 1), C("estado", "Estado")], ctx.db.all(q + " ORDER BY p.id", a))


@reporte("fis_intimaciones", "Fiscalización y planes", "Intimaciones emitidas", [P_DESDE, P_HASTA])
def _(ctx, desde=None, hasta=None):
    d, h = _rng(dict(desde=desde, hasta=hasta))
    rows = ctx.db.all(f"SELECT i.nro, i.fecha, i.pmc, {NOMBRE} AS nombre, i.deuda, i.plazo_dias, i.estado FROM intimaciones i JOIN contribuyentes c ON c.pmc=i.pmc WHERE i.fecha BETWEEN ? AND ? ORDER BY i.id", (d, h))
    return _rep("Intimaciones emitidas (F-345)", [C("nro", "N°", "text", 1.3), C("fecha", "Fecha", "date"), C("pmc", "PMC"), C("nombre", "Contribuyente", "text", 3), C("deuda", "Deuda Bs", "money", 1.1, True), C("plazo_dias", "Plazo días", "int"), C("estado", "Estado")], rows, f"Del {d} al {h}")


# ----------------------------------------------------------------------------------------------- MANTENIMIENTO / SEGURIDAD
@reporte("mant_cotizaciones", "Mantenimiento", "Cotizaciones del dólar y UFV", [P_DESDE, P_HASTA])
def _(ctx, desde=None, hasta=None):
    d, h = _rng(dict(desde=desde, hasta=hasta))
    return _rep("Cotizaciones del dólar y UFV", [C("fecha", "Fecha", "date"), C("tipo_dia", "Tipo de día"), C("dolar", "Dólar (Bs)", "num", 1), C("ufv", "UFV (Bs)", "num", 1)], ctx.db.all("SELECT * FROM cotizaciones WHERE fecha BETWEEN ? AND ? ORDER BY fecha", (d, h)), f"Del {d} al {h}")


@reporte("mant_parametros", "Mantenimiento", "Parámetros globales del sistema")
def _(ctx):
    rows = [r for r in ctx.db.all("SELECT clave, valor FROM parametros WHERE clave NOT LIKE '%_sig' AND clave NOT IN ('licencia','backup_clave') ORDER BY clave")]
    return _rep("Parámetros globales", [C("clave", "Parámetro", "text", 2), C("valor", "Valor", "text", 4)], rows)


@reporte("mant_usuarios", "Mantenimiento", "Usuarios del sistema")
def _(ctx):
    return _rep("Usuarios del sistema", [C("usuario", "Usuario"), C("nombre", "Nombre", "text", 2.5), C("rol", "Rol", "text", 1.5), C("activo", "Activo", "int", .6), C("ultimo_acceso", "Último acceso", "text", 1.5)],
                ctx.db.all("SELECT usuario,nombre,rol,activo,ultimo_acceso FROM usuarios ORDER BY usuario"))


@reporte("mant_zonas_barrios", "Mantenimiento", "Zonas y barrios")
def _(ctx):
    rows = ctx.db.all("SELECT 'ZONA' AS tipo, codigo, descripcion, '' AS zona FROM zonas UNION ALL SELECT 'BARRIO', codigo, descripcion, COALESCE(zona,'') FROM barrios ORDER BY 1,2")
    return _rep("Zonas y barrios", [C("tipo", "Tipo"), C("codigo", "Código"), C("descripcion", "Descripción", "text", 4), C("zona", "Zona")], rows)


@reporte("mant_actividades", "Mantenimiento", "Estructura de actividades económicas y categorías")
def _(ctx):
    rows = ctx.db.all("SELECT t.codigo AS act, t.descripcion AS tipo, c.cat, c.descripcion AS categoria FROM act_tipos t LEFT JOIN act_categorias c ON c.act=t.codigo ORDER BY t.codigo, c.cat")
    return _rep("Estructura de actividades económicas", [C("act", "Act."), C("tipo", "Tipo de actividad", "text", 3), C("cat", "Cat."), C("categoria", "Categoría", "text", 4)], rows)


@reporte("mant_rubros", "Mantenimiento", "Catálogo de rubros y subniveles de recaudación")
def _(ctx):
    rows = ctx.db.all("SELECT r.codigo, r.descripcion, r.tipo, '' AS frec, NULL AS monto, NULL AS pct FROM rubros r UNION ALL SELECT s.codigo, '   '||s.descripcion, s.tipo, s.frecuencia, s.monto, s.porcentaje FROM subniveles s ORDER BY 1")
    return _rep("Catálogo de rubros y subniveles", [C("codigo", "Código", "text", 1.3), C("descripcion", "Descripción", "text", 5), C("tipo", "Tipo", "text", 1), C("frec", "Frecuencia", "text", 1), C("monto", "Monto Bs", "money", 1), C("pct", "%", "money", .6)], rows)


@reporte("mant_fechas_venc", "Mantenimiento", "Fechas de vencimiento por rubro y gestión")
def _(ctx):
    return _rep("Fechas de vencimiento", [C("rubro", "Rubro"), C("gestion", "Gestión"), C("contado", "Contado / 1.ª cuota", "date"), C("cuota2", "2.ª cuota", "date"), C("sin_accesorios", "Sin descuento ni accesorios hasta", "date", 1.6)],
                ctx.db.all("SELECT * FROM fechas_venc ORDER BY gestion DESC, rubro"))


@reporte("mant_bitacora", "Mantenimiento", "Bitácora de operaciones (auditoría)", [P_DESDE, P_HASTA, dict(name="usuario", label="Usuario", kind="text")])
def _(ctx, desde=None, hasta=None, usuario=""):
    d, h = _rng(dict(desde=desde, hasta=hasta))
    q, a = "SELECT id, fecha, usuario, accion, tabla, registro, substr(detalle,1,120) AS detalle FROM bitacora WHERE substr(fecha,1,10) BETWEEN ? AND ?", [d, h]
    if usuario:
        q += " AND usuario=?"; a.append(usuario)
    return _rep("Bitácora de operaciones", [C("id", "N°", "int", .6), C("fecha", "Fecha/hora", "text", 1.4), C("usuario", "Usuario", "text", 1), C("accion", "Acción", "text", 1.6), C("tabla", "Tabla", "text", 1), C("registro", "Reg.", "text", .8), C("detalle", "Detalle", "text", 4)], ctx.db.all(q + " ORDER BY id", a), f"Del {d} al {h}")
