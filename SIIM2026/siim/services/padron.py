"""Empadronamiento (PMC): F-019 altas, F-027 modificaciones, F-035 bajas, licencias, inspecciones y estadísticas."""
from datetime import date, timedelta

from .base import Ctx, ServiceError, ahora, hoy, numero, row_dict

PMC_INICIAL = 10000000
TABLAS_OBJ = {"inmuebles": "INMUEBLE", "vehiculos": "VEHÍCULO", "actividades": "ACTIVIDAD ECONÓMICA", "publicidad": "PUBLICIDAD"}

CAMPOS_CONTRIB = ["persona", "tipo_doc", "nro_doc", "expedido", "paterno", "materno", "nombre", "nit", "razon_social", "zona", "barrio", "tipo_via",
                  "calle", "numero", "bloque", "piso", "dpto", "telefono", "celular", "email", "medidor", "casilla", "observaciones", "benemerito",
                  "fecha_nacimiento"]
CAMPOS_OBJ = {
    "inmuebles": ["tipo", "zona", "barrio", "tipo_via", "calle", "numero", "cod_catastral", "cod_censal", "material_via", "superficie", "inclinacion",
                  "luz", "agua", "telefono", "alcantarillado", "calidad", "sup_construida", "anio_construccion", "otras_construcciones", "valor_declarado",
                  "exento", "nro_ddrr"],
    "vehiculos": ["placa", "pta", "tipo", "marca", "modelo", "procedencia", "pais", "anio_fab", "anio_imp", "uso", "exento", "cilindrada", "toneladas",
                  "doble_traccion", "turbo", "puertas", "chasis", "carroceria", "plazas", "revalorizacion", "nro_motor", "nro_chasis", "color"],
    "actividades": ["act", "cat", "nombre_comercial", "nit", "matricula_comercio", "ciiu", "fecha_inicio", "fecha_cese", "superficie", "consumo_elect",
                    "zona", "barrio", "tipo_via", "calle", "numero", "telefono", "exento", "habitualidad"],
    "publicidad": ["tipo", "descripcion", "ubicacion", "ancho", "alto", "fecha_instalacion", "exento"],
}


def faltantes_contribuyente(d: dict):
    f = []
    p = d.get("persona", "N")
    if not d.get("nro_doc") and not d.get("nit"):
        f.append("número de documento o NIT")
    if p == "J":
        if not d.get("razon_social"):
            f.append("razón social")
    else:
        if not d.get("paterno") and not d.get("materno"):
            f.append("apellido paterno o materno")
        if not d.get("nombre"):
            f.append("nombre")
    if not d.get("calle"):
        f.append("dirección (calle)")
    return f


def nombre_completo(c) -> str:
    if c["persona"] == "J":
        return (c["razon_social"] or "").strip()
    return " ".join(x for x in (c["paterno"], c["materno"], c["nombre"]) if x).strip()


def nuevo_contribuyente(ctx: Ctx, data: dict, nro_orden="", fecha=None) -> int:
    ctx.require("padron.editar")
    fecha = fecha or hoy()
    with ctx.db.tx():
        ult = ctx.db.scalar("SELECT MAX(pmc) FROM contribuyentes", default=PMC_INICIAL)
        pmc = max(ult, PMC_INICIAL) + 1
        row = {k: data.get(k) for k in CAMPOS_CONTRIB if k in data}
        row.setdefault("persona", "N")
        row.update(pmc=pmc, estado="ACTIVO" if not faltantes_contribuyente(row) else "INCOMPLETO", fecha_registro=fecha, usuario=ctx.user)
        ctx.db.insert("contribuyentes", row)
        ctx.db.insert("emp_formularios", dict(tipo="F-019", nro_orden=nro_orden, fecha=fecha, pmc=pmc, usuario=ctx.user, creado=hoy() + " " + ahora()))
        ctx.log("F019_ALTA", "contribuyentes", pmc, {"orden": nro_orden})
    return pmc


def modificar_contribuyente(ctx: Ctx, pmc: int, data: dict, form="F-027", nro_orden="", fecha=None):
    ctx.require("padron.editar")
    ant = ctx.db.one("SELECT * FROM contribuyentes WHERE pmc=?", (pmc,))
    if not ant:
        raise ServiceError(f"PMC {pmc} no existe.")
    cambios = {k: data[k] for k in CAMPOS_CONTRIB if k in data and (ant[k] or "") != (data[k] or "")}
    with ctx.db.tx():
        merged = {**row_dict(ant), **cambios}
        cambios["estado"] = "ACTIVO" if not faltantes_contribuyente(merged) else "INCOMPLETO"
        ctx.db.update("contribuyentes", cambios, "pmc=?", (pmc,))
        ctx.db.insert("emp_formularios", dict(tipo=form, nro_orden=nro_orden, fecha=fecha or hoy(), pmc=pmc, usuario=ctx.user, creado=hoy() + " " + ahora()))
        ctx.log(form.replace("-", "") + "_MODIF", "contribuyentes", pmc, {k: [ant[k] if k in ant.keys() else None, v] for k, v in cambios.items()})


def guardar_objeto(ctx: Ctx, tabla: str, pmc: int, data: dict, id_=None, form="F-019") -> int:
    ctx.require("padron.editar")
    if tabla not in CAMPOS_OBJ:
        raise ValueError(tabla)
    c = ctx.db.one("SELECT estado FROM contribuyentes WHERE pmc=?", (pmc,))
    if not c or c["estado"] != "ACTIVO":
        raise ServiceError("El contribuyente debe estar ACTIVO (datos completos) antes de registrar bienes o actividades.")
    row = {k: data.get(k) for k in CAMPOS_OBJ[tabla] if k in data}
    _validar_objeto(ctx, tabla, row, id_)
    with ctx.db.tx():
        if id_:
            ant = ctx.db.one(f"SELECT * FROM {tabla} WHERE id=?", (id_,))
            ctx.db.update(tabla, {**row, "usuario": ctx.user}, "id=? AND pmc=?", (id_, pmc))
            ctx.log(f"{form.replace('-', '')}_MODIF_{tabla}", tabla, id_, {k: [ant[k], v] for k, v in row.items() if ant[k] != v})
        else:
            id_ = ctx.db.insert(tabla, {**row, "pmc": pmc, "estado": "ACTIVO", "usuario": ctx.user})
            ctx.log(f"{form.replace('-', '')}_ALTA_{tabla}", tabla, id_)
    return id_


def _validar_objeto(ctx, tabla, row, id_):
    db = ctx.db
    if tabla == "vehiculos":
        pl = (row.get("placa") or "").strip().upper()
        if not pl:
            raise ServiceError("La placa es obligatoria.")
        row["placa"] = pl
        dup = db.one("SELECT id FROM vehiculos WHERE placa=? AND estado='ACTIVO' AND id<>?", (pl, id_ or 0))
        if dup:
            raise ServiceError(f"La placa {pl} ya está registrada en el padrón (use IMT para transferir).")
        if not row.get("anio_fab") or not (1900 <= int(row["anio_fab"]) <= date.today().year + 1):
            raise ServiceError("Año de fabricación inválido.")
    elif tabla == "inmuebles":
        if row.get("tipo") == "RURAL":
            if float(row.get("valor_declarado") or 0) <= 0:
                raise ServiceError("Para inmueble rural declare el valor del inmueble.")
        elif float(row.get("superficie") or 0) <= 0 and row.get("tipo") != "DEPARTAMENTO":
            raise ServiceError("La superficie del terreno debe ser mayor a cero.")
        if row.get("tipo") in ("CASA", "DEPARTAMENTO") and float(row.get("sup_construida") or 0) > 0 and not row.get("calidad"):
            raise ServiceError("Indique la calidad de construcción.")
        if row.get("anio_construccion") and not (1800 <= int(row["anio_construccion"]) <= date.today().year):
            raise ServiceError("Año de construcción inválido.")
    elif tabla == "actividades":
        if not row.get("act") or not row.get("cat"):
            raise ServiceError("Seleccione la actividad económica y su categoría.")
        if not row.get("fecha_inicio"):
            raise ServiceError("La fecha de inicio de actividades es obligatoria (se usa para calcular duodécimas).")
    elif tabla == "publicidad":
        if float(row.get("ancho") or 0) <= 0 or float(row.get("alto") or 0) <= 0:
            raise ServiceError("Indique ancho y alto del anuncio.")


def baja_objeto(ctx: Ctx, tabla: str, id_: int, fecha=None, motivo="", nro_orden=""):
    """F-035: desincorporación (baja). Los registros no se borran: pasan a INACTIVO y quedan en bitácora."""
    ctx.require("padron.baja")
    ant = ctx.db.one(f"SELECT * FROM {tabla} WHERE id=?", (id_,))
    if not ant or ant["estado"] != "ACTIVO":
        raise ServiceError("El registro no existe o ya está dado de baja.")
    fecha = fecha or hoy()
    with ctx.db.tx():
        upd = dict(estado="INACTIVO")
        if tabla == "actividades":
            upd["fecha_cese"] = fecha
            upd["estado_licencia"] = "CANCELADA"
        elif "fecha_baja" in ant.keys():
            upd["fecha_baja"] = fecha
        ctx.db.update(tabla, upd, "id=?", (id_,))
        ctx.db.insert("emp_formularios", dict(tipo="F-035", nro_orden=nro_orden, fecha=fecha, pmc=ant["pmc"], usuario=ctx.user, creado=hoy() + " " + ahora()))
        ctx.log("F035_BAJA", tabla, id_, {"motivo": motivo, "fecha": fecha})


def objetos(db, tabla, pmc, solo_activos=True):
    q = f"SELECT * FROM {tabla} WHERE pmc=?" + (" AND estado='ACTIVO'" if solo_activos else "") + " ORDER BY id"
    return db.all(q, (pmc,))


def buscar(db, texto="", por="nombre", limite=500, solo_con=None):
    """Búsqueda 'multiacceso' (equivalente a F6): apellido/nombre/razón social/documento/NIT/PMC/placa."""
    t = (texto or "").strip()
    like = f"{t}%"
    where, p = [], []
    if por == "pmc" and t.isdigit():
        where.append("c.pmc=?"); p.append(int(t))
    elif por == "documento":
        where.append("(c.nro_doc LIKE ? OR c.nit LIKE ?)"); p += [like, like]
    elif por == "placa":
        where.append("c.pmc IN (SELECT pmc FROM vehiculos WHERE placa LIKE ?)"); p.append(like.upper())
    elif por == "razon":
        where.append("c.razon_social LIKE ?"); p.append(f"%{t}%")
    elif t:
        where.append("(c.paterno LIKE ? OR c.materno LIKE ? OR c.nombre LIKE ? OR c.razon_social LIKE ?)"); p += [like, like, like, f"%{t}%"]
    if solo_con in TABLAS_OBJ:
        where.append(f"c.pmc IN (SELECT pmc FROM {solo_con} WHERE estado='ACTIVO')")
    w = ("WHERE " + " AND ".join(where)) if where else ""
    return db.all(f"SELECT c.* FROM contribuyentes c {w} ORDER BY c.paterno, c.materno, c.nombre, c.razon_social LIMIT {int(limite)}", p)


def estadisticas(db):
    q = lambda s, p=(): db.scalar(s, p, 0)
    return {
        "contribuyentes": q("SELECT COUNT(*) FROM contribuyentes WHERE estado='ACTIVO'"),
        "incompletos": q("SELECT COUNT(*) FROM contribuyentes WHERE estado='INCOMPLETO'"),
        "naturales": q("SELECT COUNT(*) FROM contribuyentes WHERE estado='ACTIVO' AND persona='N'"),
        "juridicas": q("SELECT COUNT(*) FROM contribuyentes WHERE estado='ACTIVO' AND persona='J'"),
        "inmuebles": q("SELECT COUNT(*) FROM inmuebles WHERE estado='ACTIVO'"),
        "vehiculos": q("SELECT COUNT(*) FROM vehiculos WHERE estado='ACTIVO'"),
        "actividades": q("SELECT COUNT(*) FROM actividades WHERE estado='ACTIVO'"),
        "publicidad": q("SELECT COUNT(*) FROM publicidad WHERE estado='ACTIVO'"),
    }


# ----------------------- Licencias de funcionamiento (mejora) -----------------------
def emitir_licencia(ctx: Ctx, act_id: int, fecha=None, permitir_con_deuda=False):
    ctx.require("padron.editar")
    a = ctx.db.one("SELECT * FROM actividades WHERE id=? AND estado='ACTIVO'", (act_id,))
    if not a:
        raise ServiceError("Actividad no encontrada o inactiva.")
    fecha = fecha or hoy()
    if not permitir_con_deuda:
        deuda = ctx.db.scalar("SELECT COUNT(*) FROM liquidaciones WHERE rubro='PAF' AND objeto_id=? AND estado='PENDIENTE' AND fecha_venc<?", (act_id, fecha), 0)
        if deuda:
            raise ServiceError(f"La actividad tiene {deuda} patente(s) vencida(s) sin pagar. Regularice antes de emitir/renovar la licencia.")
    meses = int(ctx.db.param("licencia_vigencia_meses", "12"))
    d = date.fromisoformat(fecha)
    y, m = divmod(d.month - 1 + meses, 12)
    vence = date(d.year + y, m + 1, min(d.day, 28)).isoformat()
    nro = a["nro_licencia"] or numero(ctx.db, "LF", fecha)
    ctx.db.update("actividades", dict(nro_licencia=nro, licencia_emision=fecha, licencia_vence=vence, estado_licencia="VIGENTE"), "id=?", (act_id,))
    ctx.log("LICENCIA_EMITIDA", "actividades", act_id, {"nro": nro, "vence": vence})
    return nro, vence


def refrescar_licencias(db, hoy_=None):
    h = hoy_ or hoy()
    db.execute("UPDATE actividades SET estado_licencia='VENCIDA' WHERE estado='ACTIVO' AND licencia_vence IS NOT NULL AND licencia_vence<? AND estado_licencia='VIGENTE'", (h,))


def licencias_por_vencer(db, dias=None, hoy_=None):
    dias = dias if dias is not None else int(db.param("alerta_licencia_dias", "30"))
    h = hoy_ or hoy()
    lim = (date.fromisoformat(h) + timedelta(days=dias)).isoformat()
    return db.all("""SELECT a.*, c.paterno,c.materno,c.nombre,c.razon_social,c.persona FROM actividades a JOIN contribuyentes c ON c.pmc=a.pmc
                     WHERE a.estado='ACTIVO' AND a.licencia_vence BETWEEN ? AND ? ORDER BY a.licencia_vence""", (h, lim))


def registrar_inspeccion(ctx: Ctx, act_id: int, resultado: str, observaciones="", inspector="", plazo=None, fecha=None):
    ctx.require("fiscal")
    a = ctx.db.one("SELECT pmc FROM actividades WHERE id=?", (act_id,))
    if not a:
        raise ServiceError("Actividad no encontrada.")
    i = ctx.db.insert("inspecciones", dict(actividad_id=act_id, pmc=a["pmc"], fecha=fecha or hoy(), inspector=inspector or ctx.user, resultado=resultado,
                                           observaciones=observaciones, plazo_subsanar=plazo, usuario=ctx.user))
    if resultado == "CLAUSURA":
        ctx.db.update("actividades", dict(estado_licencia="SUSPENDIDA"), "id=?", (act_id,))
    ctx.log("INSPECCION", "actividades", act_id, {"resultado": resultado})
    return i
