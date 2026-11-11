from __future__ import annotations

import io
import json
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from openpyxl import Workbook
from openpyxl.styles import Font
from pydantic import BaseModel, Field
from sqlalchemy import extract, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Empleado, Entidad, MemoConfig, MemoPlantilla, Memorandum, Usuario
from ..reports import memorandum as doc
from ..security import ESCRIBE, LEE, SOLO_ADMIN
from ..services import memos
from ..services.proceso import ReglaNegocio
from .deps import log, reprocesar

router = APIRouter(prefix="/api", tags=["memorandums"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class MemoIn(BaseModel):
    tipo: str
    fecha: date
    fecha_efectiva: date
    empleado_id: int | None = None
    destinatario: str = Field(min_length=3, max_length=200)
    destinatario_ci: str = Field(default="", max_length=40)
    cargo: str = Field(min_length=3, max_length=250)
    referencia: str = Field(default="", max_length=300)
    cuerpo: str = Field(min_length=20)
    datos: dict = {}
    firmante_nombre: str = ""
    firmante_cargo: str = ""


class TextoIn(BaseModel):
    tipo: str
    fecha: date | None = None
    fecha_efectiva: date | None = None
    fecha_renuncia: date | None = None
    destinatario: str = ""
    cargo: str = ""
    datos: dict = {}


def _m(m: Memorandum, detalle=False):
    r = {"id": m.id, "tipo": m.tipo, "tipo_nombre": memos.TIPOS[m.tipo], "estado": m.estado, "cite": m.cite, "gestion": m.gestion,
         "correlativo": m.correlativo, "fecha": m.fecha.isoformat(), "fecha_efectiva": m.fecha_efectiva.isoformat(),
         "empleado_id": m.empleado_id, "destinatario": m.destinatario, "destinatario_ci": m.destinatario_ci, "cargo": m.cargo,
         "efecto": m.efecto_aplicado, "recibido_fecha": m.recibido_fecha.isoformat() if m.recibido_fecha else None, "recibido_por": m.recibido_por}
    if detalle:
        r.update({"referencia": m.referencia, "cuerpo": m.cuerpo, "datos": json.loads(m.datos or "{}"), "firmante_nombre": m.firmante_nombre,
                  "firmante_cargo": m.firmante_cargo, "motivo_anulacion": m.motivo_anulacion, "emitido_por": m.emitido_por,
                  "emitido_en": m.emitido_en.isoformat(sep=" ") if m.emitido_en else None})
    return r


def _get(db: Session, mid: int) -> Memorandum:
    m = db.get(Memorandum, mid)
    if not m:
        raise HTTPException(404, "Memorándum no encontrado")
    return m


def _aplicar(m: Memorandum, d: MemoIn, db: Session):
    if d.tipo not in memos.TIPOS:
        raise HTTPException(422, "Tipo de memorándum inválido")
    if d.empleado_id and not db.get(Empleado, d.empleado_id):
        raise HTTPException(404, "Servidor no encontrado")
    if d.fecha_efectiva < date(2000, 1, 1):
        raise HTTPException(422, "Fecha efectiva inválida")
    m.tipo, m.fecha, m.fecha_efectiva, m.empleado_id = d.tipo, d.fecha, d.fecha_efectiva, d.empleado_id
    m.destinatario, m.destinatario_ci, m.cargo = d.destinatario.strip(), d.destinatario_ci.strip(), d.cargo.strip()
    m.referencia, m.cuerpo, m.datos = d.referencia or memos.PLANTILLAS[d.tipo][0], d.cuerpo, json.dumps(d.datos, ensure_ascii=False)
    m.firmante_nombre, m.firmante_cargo = d.firmante_nombre, d.firmante_cargo


@router.post("/memorandums/texto")
def texto(d: TextoIn, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    """Redacta el cuerpo a partir de la plantilla y los datos (para llenar el formulario)."""
    datos = {**d.datos, "fecha": (d.fecha or date.today()).isoformat(), "fecha_efectiva": d.fecha_efectiva.isoformat() if d.fecha_efectiva else "",
             "fecha_renuncia": d.fecha_renuncia.isoformat() if d.fecha_renuncia else "", "destinatario": d.destinatario, "cargo": d.cargo}
    return memos.redactar(db, d.tipo, datos)


@router.get("/memorandums")
def listar(tipo: str = "", estado: str = "", gestion: int | None = None, q: str = "", u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    st = select(Memorandum).order_by(Memorandum.id.desc()).limit(500)
    if tipo:
        st = st.where(Memorandum.tipo == tipo)
    if estado:
        st = st.where(Memorandum.estado == estado)
    if gestion:
        st = st.where(extract("year", Memorandum.fecha) == gestion)
    if q:
        like = f"%{q}%"
        st = st.where(or_(Memorandum.cite.ilike(like), Memorandum.destinatario.ilike(like), Memorandum.cargo.ilike(like)))
    return [_m(m) for m in db.execute(st).scalars().unique()]


@router.get("/memorandums/{mid}")
def ver(mid: int, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    return _m(_get(db, mid), True)


@router.post("/memorandums")
def crear(d: MemoIn, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    m = Memorandum(creado_por=u.username, estado="BORRADOR")
    _aplicar(m, d, db)
    db.add(m)
    db.flush()
    log(db, u, "CREAR_MEMORANDUM", "memorandum", m.id, {"tipo": m.tipo, "destinatario": m.destinatario})
    db.commit()
    return _m(m, True)


@router.put("/memorandums/{mid}")
def editar(mid: int, d: MemoIn, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    m = _get(db, mid)
    if m.estado != "BORRADOR":
        raise HTTPException(409, "Un memorándum EMITIDO no se edita (inalterabilidad); anúlelo y emita uno nuevo")
    _aplicar(m, d, db)
    log(db, u, "EDITAR_MEMORANDUM", "memorandum", m.id, {"tipo": m.tipo})
    db.commit()
    return _m(m, True)


@router.delete("/memorandums/{mid}")
def borrar(mid: int, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    m = _get(db, mid)
    if m.estado != "BORRADOR":
        raise HTTPException(409, "Solo se eliminan borradores; un memorándum emitido se anula (el número no se reutiliza)")
    log(db, u, "ELIMINAR_MEMORANDUM", "memorandum", m.id, {"tipo": m.tipo, "destinatario": m.destinatario})
    db.delete(m)
    db.commit()
    return {"ok": True}


class EmitirIn(BaseModel):
    registrar_baja: bool | None = None
    causal: str = "CONCLUSION_CONTRATO"


@router.post("/memorandums/{mid}/emitir")
def emitir(mid: int, d: EmitirIn | None = None, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    m = _get(db, mid)
    d = d or EmitirIn()
    datos = json.loads(m.datos or "{}")
    datos["causal"] = d.causal
    m.datos = json.dumps(datos, ensure_ascii=False)
    try:
        memos.emitir(db, m, u.username, d.registrar_baja)
    except ReglaNegocio:
        db.rollback()
        raise
    reprocesar(db, u, [m.fecha_efectiva])
    db.commit()
    return _m(m, True)


class AnularIn(BaseModel):
    motivo: str


@router.post("/memorandums/{mid}/anular")
def anular(mid: int, d: AnularIn, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    m = _get(db, mid)
    try:
        memos.anular(db, m, d.motivo, u.username)
    except ReglaNegocio:
        db.rollback()
        raise
    reprocesar(db, u, [m.fecha_efectiva])
    db.commit()
    return _m(m, True)


class RecepcionIn(BaseModel):
    fecha: date
    recibido_por: str = ""


@router.post("/memorandums/{mid}/recepcion")
def recepcion(mid: int, d: RecepcionIn, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    """Registra el cargo de recepción (fecha y quien recibió). Es lo único que puede completarse tras emitir."""
    m = _get(db, mid)
    if m.estado != "EMITIDO":
        raise HTTPException(409, "Solo un memorándum EMITIDO registra recepción")
    if d.fecha < m.fecha:
        raise HTTPException(422, "La recepción no puede ser anterior a la fecha del memorándum")
    m.recibido_fecha, m.recibido_por = d.fecha, d.recibido_por
    log(db, u, "RECEPCION_MEMORANDUM", "memorandum", m.id, {"cite": m.cite, "fecha": d.fecha.isoformat(), "por": d.recibido_por})
    db.commit()
    return _m(m, True)


def _ctx_doc(db: Session):
    return db.get(Entidad, 1), memos.get_config(db)


@router.get("/memorandums/{mid}/pdf")
def pdf(mid: int, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    m = _get(db, mid)
    ent, cfg = _ctx_doc(db)
    nombre = (m.cite or f"borrador-{m.id}").replace("/", "-").replace("°", "")
    return Response(doc.pdf(m, ent, cfg), media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{nombre}.pdf"'})


@router.get("/memorandums/{mid}/docx")
def word(mid: int, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    m = _get(db, mid)
    ent, cfg = _ctx_doc(db)
    nombre = (m.cite or f"borrador-{m.id}").replace("/", "-").replace("°", "")
    return Response(doc.word(m, ent, cfg), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}.docx"'})


# ------------------------------------------------------------------ plantillas y membrete
class PlantillaIn(BaseModel):
    referencia: str = Field(min_length=3, max_length=200)
    cuerpo: str = Field(min_length=30)


@router.get("/memo-plantillas")
def plantillas(u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    return [{"tipo": p.tipo, "nombre": memos.TIPOS[p.tipo], "referencia": p.referencia, "cuerpo": p.cuerpo}
            for p in db.execute(select(MemoPlantilla).order_by(MemoPlantilla.tipo)).scalars()]


@router.put("/memo-plantillas/{tipo}")
def guardar_plantilla(tipo: str, d: PlantillaIn, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    p = db.get(MemoPlantilla, tipo)
    if not p:
        raise HTTPException(404, "Tipo desconocido")
    p.referencia, p.cuerpo = d.referencia, d.cuerpo
    log(db, u, "EDITAR_PLANTILLA_MEMO", "memo_plantilla", tipo)
    db.commit()
    return {"ok": True}


@router.post("/memo-plantillas/{tipo}/restaurar")
def restaurar_plantilla(tipo: str, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    if tipo not in memos.PLANTILLAS:
        raise HTTPException(404, "Tipo desconocido")
    p = db.get(MemoPlantilla, tipo)
    p.referencia, p.cuerpo = memos.PLANTILLAS[tipo]
    log(db, u, "RESTAURAR_PLANTILLA_MEMO", "memo_plantilla", tipo)
    db.commit()
    return {"ok": True}


class ConfigIn(BaseModel):
    prefijo: str = Field(min_length=2, max_length=60, pattern=r"^[A-Za-z0-9ÁÉÍÓÚÑáéíóúñ/_. -]+$")
    encabezado: str = ""
    lema: str = ""
    pie: str = ""
    decreto_estructura: str = ""
    firmante_nombre: str = ""
    firmante_cargo: str = ""


def _cfg(c: MemoConfig):
    return {"prefijo": c.prefijo, "encabezado": c.encabezado, "lema": c.lema, "pie": c.pie, "decreto_estructura": c.decreto_estructura,
            "firmante_nombre": c.firmante_nombre, "firmante_cargo": c.firmante_cargo, "tiene_logo": bool(c.logo)}


@router.get("/memo-config")
def get_cfg(u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    return _cfg(memos.get_config(db))


@router.put("/memo-config")
def put_cfg(d: ConfigIn, u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    c = memos.get_config(db)
    for k, v in d.model_dump().items():
        setattr(c, k, v)
    log(db, u, "EDITAR_MEMO_CONFIG", "memo_config", 1, d.model_dump())
    db.commit()
    return _cfg(c)


@router.post("/memo-config/logo")
async def subir_logo(archivo: UploadFile = File(...), u: Usuario = Depends(ESCRIBE), db: Session = Depends(get_db)):
    data = await archivo.read()
    if len(data) > 3_000_000:
        raise HTTPException(413, "El logo no debe superar 3 MB")
    mime = {b"\x89PNG": "image/png", b"\xff\xd8\xff": "image/jpeg"}
    tipo = next((v for k, v in mime.items() if data.startswith(k)), None)
    if not tipo:
        raise HTTPException(422, "El logo debe ser PNG o JPG")
    c = memos.get_config(db)
    c.logo, c.logo_mime = data, tipo
    log(db, u, "SUBIR_LOGO_MEMO", "memo_config", 1, {"bytes": len(data)})
    db.commit()
    return {"ok": True}


@router.get("/memo-config/logo")
def logo(u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    c = memos.get_config(db)
    if not c.logo:
        raise HTTPException(404, "Sin logo")
    return Response(c.logo, media_type=c.logo_mime or "image/png")


# ------------------------------------------------------------------ control de cites
@router.get("/cites")
def cites(u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    """Todas las series de cites del sistema con su último número."""
    return memos.series_cites(db)


@router.get("/cites/memorandum/{gestion}")
def cites_memo(gestion: int, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    return memos.resumen_cites(db, gestion)


class FijarIn(BaseModel):
    gestion: int = Field(ge=2000, le=2100)
    numero: int = Field(ge=1, le=99999)
    motivo: str


@router.post("/cites/memorandum/siguiente")
def fijar(d: FijarIn, u: Usuario = Depends(SOLO_ADMIN), db: Session = Depends(get_db)):
    try:
        r = memos.fijar_siguiente(db, d.gestion, d.numero, u.username, d.motivo)
    except ReglaNegocio:
        db.rollback()
        raise
    db.commit()
    return r


@router.get("/memorandums-registro.xlsx")
def registro(gestion: int, u: Usuario = Depends(LEE), db: Session = Depends(get_db)):
    """Libro de registro de cites de la gestión (incluye anulados y números saltados)."""
    resumen = memos.resumen_cites(db, gestion)
    ms = {m.correlativo: m for m in db.execute(select(Memorandum).where(Memorandum.gestion == gestion)).scalars().unique()}
    wb = Workbook()
    ws = wb.active
    ws.title = f"Cites {gestion}"
    ws.append(["N°", "CITE", "Tipo", "Estado", "Fecha", "Fecha efectiva", "Destinatario", "C.I.", "Cargo", "Efecto aplicado", "Recepción", "Recibido por", "Emitido por", "Motivo de anulación"])
    for c in ws[1]:
        c.font = Font(bold=True)
    for d in resumen["detalle"]:
        m = ms.get(d["n"])
        ws.append([d["n"], d["cite"], d["tipo"], d["estado"], m.fecha if m else None, m.fecha_efectiva if m else None, m.destinatario if m else "",
                   m.destinatario_ci if m else "", m.cargo if m else "", m.efecto_aplicado if m else "", m.recibido_fecha if m else None,
                   m.recibido_por if m else "", m.emitido_por if m else "", m.motivo_anulacion if m else ""])
    for col, w in zip("ABCDEFGHIJKLMN", [6, 30, 36, 11, 12, 14, 32, 14, 40, 44, 12, 24, 14, 40]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"
    out = io.BytesIO()
    wb.save(out)
    return Response(out.getvalue(), media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="Registro_Cites_Memorandums_{gestion}.xlsx"'})
