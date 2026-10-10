"""Endpoints del tramite de Contratacion Menor. El control de acceso por rol se aplica en cada accion."""
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import ip_cliente, requiere_roles, usuario_actual
from ..enums import Rol
from ..models import ContratacionMenor, Usuario
from ..schemas import (
    AdjudicarIn, BloqueSigepOut, C31NroIn, CertificarIn, ContratacionCreate, ContratacionOut, ContratacionResumen,
    ContratacionUpdate, CotizacionCalificacion, CotizacionIn, CotizacionOut, DashboardOut, DocumentoOut, FichasIn,
    FormalizarIn, Formulario110In, ItemIn, ItemOut, MotivoIn, PreventivoOut, RecepcionIn, RecepcionOut, ReglaOut,
)
from ..services import calculador_modalidad as calc, tramite
from ..services.storage import get_storage

router = APIRouter(prefix="/contrataciones", tags=["contrataciones"])

R = Rol


def serializar(db: Session, c: ContratacionMenor, u: Usuario) -> ContratacionOut:
    excluir = {"items", "cotizaciones", "documentos", "recepciones", "preventivos", "acciones", "mensaje_cuantia"}
    base = {k: getattr(c, k) for k in ContratacionOut.model_fields if k not in excluir}
    cots = []
    for q in c.cotizaciones:
        o = CotizacionOut.model_validate(q)
        o.sellada = not c.ofertas_abiertas
        cots.append(o)
    mensaje = ""
    if c.items:
        mensaje = calc.calcular_modalidad(c.monto_referencial_total).mensaje
    return ContratacionOut(
        **base,
        items=[ItemOut.model_validate(i) for i in c.items],
        cotizaciones=cots,
        documentos=[DocumentoOut.model_validate(d) for d in c.documentos],
        recepciones=[RecepcionOut.model_validate(r) for r in c.recepciones],
        preventivos=[PreventivoOut(partida_id=p.partida_id, codigo_partida=p.partida.codigo_partida,
                                   descripcion=p.partida.descripcion, importe=p.importe, estado=p.estado)
                     for p in c.preventivos],
        acciones=tramite.acciones(c, u), mensaje_cuantia=mensaje)


def _cargar(db: Session, cid: uuid.UUID, u: Usuario, bloquear: bool = True) -> ContratacionMenor:
    return tramite.obtener(db, cid, u, bloquear=bloquear)


# ---------------- consultas
@router.get("", response_model=list[ContratacionResumen])
def listar(estado: str | None = None, q: str | None = Query(None, max_length=100), db: Session = Depends(get_db),
           u: Usuario = Depends(usuario_actual)):
    return tramite.listar(db, u, estado, q)


@router.get("/tablero", response_model=DashboardOut)
def tablero(db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    t = tramite.tablero(db, u)
    return DashboardOut(por_estado=t["por_estado"], total=t["total"],
                        pendientes=[ContratacionResumen.model_validate(c) for c in t["pendientes"]])


@router.get("/reglas/simular", response_model=ReglaOut)
def simular_reglas(monto: Decimal = Query(ge=0), plazo: int = Query(ge=1), tipo_objeto: str = "BIEN",
                   db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    """Vista previa en vivo para el formulador: modalidad por cuantia y metodo de formalizacion."""
    try:
        r, metodo = tramite.evaluar_cuantia(db, monto, plazo, tipo_objeto)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return ReglaOut(modalidad=r.modalidad.value if r.modalidad else None, requiere_formulario_110=r.requiere_formulario_110,
                    bloqueado=r.bloqueado, mensaje=r.mensaje, metodo_formalizacion=metodo.value)


@router.get("/{cid}", response_model=ContratacionOut)
def detalle(cid: uuid.UUID, db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    return serializar(db, _cargar(db, cid, u, False), u)


# ---------------- borrador
@router.post("", response_model=ContratacionOut, status_code=status.HTTP_201_CREATED)
def crear(datos: ContratacionCreate, request: Request, db: Session = Depends(get_db),
          u: Usuario = Depends(requiere_roles(R.SOLICITANTE))):
    c = tramite.crear(db, u, datos.model_dump(), ip_cliente(request))
    db.commit()
    return serializar(db, c, u)


@router.patch("/{cid}", response_model=ContratacionOut)
def actualizar(cid: uuid.UUID, datos: ContratacionUpdate, request: Request, db: Session = Depends(get_db),
               u: Usuario = Depends(requiere_roles(R.SOLICITANTE))):
    c = tramite.actualizar(db, u, _cargar(db, cid, u), datos.model_dump(exclude_unset=True), ip_cliente(request))
    db.commit()
    return serializar(db, c, u)


@router.post("/{cid}/items", response_model=ContratacionOut, status_code=status.HTTP_201_CREATED)
def agregar_item(cid: uuid.UUID, datos: ItemIn, request: Request, db: Session = Depends(get_db),
                 u: Usuario = Depends(requiere_roles(R.SOLICITANTE))):
    c = _cargar(db, cid, u)
    tramite.agregar_item(db, u, c, datos.model_dump(), ip_cliente(request))
    db.commit()
    return serializar(db, c, u)


@router.put("/{cid}/items/{item_id}", response_model=ContratacionOut)
def actualizar_item(cid: uuid.UUID, item_id: uuid.UUID, datos: ItemIn, request: Request, db: Session = Depends(get_db),
                    u: Usuario = Depends(requiere_roles(R.SOLICITANTE))):
    c = _cargar(db, cid, u)
    tramite.actualizar_item(db, u, c, item_id, datos.model_dump(), ip_cliente(request))
    db.commit()
    return serializar(db, c, u)


@router.delete("/{cid}/items/{item_id}", response_model=ContratacionOut)
def eliminar_item(cid: uuid.UUID, item_id: uuid.UUID, request: Request, db: Session = Depends(get_db),
                  u: Usuario = Depends(requiere_roles(R.SOLICITANTE))):
    c = _cargar(db, cid, u)
    tramite.eliminar_item(db, u, c, item_id, ip_cliente(request))
    db.commit()
    return serializar(db, c, u)


# ---------------- solicitud y presupuesto
@router.post("/{cid}/solicitar", response_model=ContratacionOut)
def solicitar(cid: uuid.UUID, request: Request, db: Session = Depends(get_db),
              u: Usuario = Depends(requiere_roles(R.SOLICITANTE))):
    c = tramite.solicitar(db, u, _cargar(db, cid, u), ip_cliente(request))
    db.commit()
    return serializar(db, c, u)


@router.post("/{cid}/devolver", response_model=ContratacionOut)
def devolver(cid: uuid.UUID, datos: MotivoIn, request: Request, db: Session = Depends(get_db),
             u: Usuario = Depends(requiere_roles(R.PRESUPUESTO))):
    c = tramite.devolver(db, u, _cargar(db, cid, u), datos.motivo, ip_cliente(request))
    db.commit()
    return serializar(db, c, u)


@router.post("/{cid}/certificar", response_model=ContratacionOut)
def certificar(cid: uuid.UUID, datos: CertificarIn, request: Request, db: Session = Depends(get_db),
               u: Usuario = Depends(requiere_roles(R.PRESUPUESTO))):
    c = tramite.certificar(db, u, _cargar(db, cid, u), datos.preventivo_c31_nro, ip_cliente(request))
    db.commit()
    return serializar(db, c, u)


@router.put("/{cid}/c31", response_model=ContratacionOut)
def registrar_c31(cid: uuid.UUID, datos: C31NroIn, request: Request, db: Session = Depends(get_db),
                  u: Usuario = Depends(requiere_roles(R.PRESUPUESTO))):
    c = tramite.registrar_c31(db, u, _cargar(db, cid, u), datos.preventivo_c31_nro, ip_cliente(request))
    db.commit()
    return serializar(db, c, u)


@router.get("/{cid}/bloque-sigep", response_model=BloqueSigepOut)
def bloque_sigep(cid: uuid.UUID, db: Session = Depends(get_db),
                 u: Usuario = Depends(requiere_roles(R.PRESUPUESTO, R.RPA, R.ADMIN, R.CONTRATACIONES))):
    return tramite.bloque_sigep_de(db, _cargar(db, cid, u, False))


@router.post("/{cid}/aprobar-inicio", response_model=ContratacionOut)
def aprobar_inicio(cid: uuid.UUID, request: Request, db: Session = Depends(get_db),
                   u: Usuario = Depends(requiere_roles(R.RPA))):
    c = tramite.aprobar_inicio(db, u, _cargar(db, cid, u), ip_cliente(request))
    db.commit()
    return serializar(db, c, u)


# ---------------- cotizacion
@router.put("/{cid}/formulario-110", response_model=ContratacionOut)
def formulario_110(cid: uuid.UUID, datos: Formulario110In, request: Request, db: Session = Depends(get_db),
                   u: Usuario = Depends(requiere_roles(R.CONTRATACIONES))):
    c = tramite.registrar_formulario_110(db, u, _cargar(db, cid, u), datos.model_dump(), ip_cliente(request))
    db.commit()
    return serializar(db, c, u)


@router.post("/{cid}/fichas-cotizacion")
def fichas(cid: uuid.UUID, datos: FichasIn, request: Request, db: Session = Depends(get_db),
           u: Usuario = Depends(requiere_roles(R.CONTRATACIONES))):
    r = tramite.enviar_fichas(db, u, _cargar(db, cid, u), [d.model_dump() for d in datos.destinatarios],
                              datos.canales, ip_cliente(request))
    db.commit()
    return r


@router.post("/{cid}/cotizaciones", response_model=CotizacionOut, status_code=status.HTTP_201_CREATED)
def registrar_cotizacion(cid: uuid.UUID, datos: CotizacionIn, request: Request, db: Session = Depends(get_db),
                         u: Usuario = Depends(requiere_roles(R.CONTRATACIONES))):
    c = _cargar(db, cid, u)
    q = tramite.registrar_cotizacion(db, u, c, datos.model_dump(), ip_cliente(request))
    db.commit()
    out = CotizacionOut.model_validate(q)
    out.sellada = True
    return out


@router.post("/{cid}/abrir-ofertas", response_model=ContratacionOut)
def abrir_ofertas(cid: uuid.UUID, request: Request, db: Session = Depends(get_db),
                  u: Usuario = Depends(requiere_roles(R.CONTRATACIONES))):
    c = tramite.abrir_ofertas(db, u, _cargar(db, cid, u), ip_cliente(request))
    db.commit()
    return serializar(db, c, u)


@router.patch("/{cid}/cotizaciones/{cot_id}", response_model=CotizacionOut)
def calificar(cid: uuid.UUID, cot_id: uuid.UUID, datos: CotizacionCalificacion, request: Request,
              db: Session = Depends(get_db), u: Usuario = Depends(requiere_roles(R.CONTRATACIONES))):
    c = _cargar(db, cid, u)
    q = tramite.calificar_cotizacion(db, u, c, cot_id, datos.model_dump(), ip_cliente(request))
    db.commit()
    return CotizacionOut.model_validate(q)


@router.get("/{cid}/evaluacion")
def evaluacion(cid: uuid.UUID, db: Session = Depends(get_db),
               u: Usuario = Depends(requiere_roles(R.CONTRATACIONES, R.RPA, R.ADMIN))):
    """Matriz comparativa en vivo (menor a mayor precio evaluado)."""
    c = _cargar(db, cid, u, False)
    try:
        ev = tramite.matriz(c)
    except Exception as exc:  # ReglaNegocioError -> 422 via handler
        raise exc
    return {
        "hay_desempate": ev.hay_desempate,
        "recomendada": str(ev.recomendada.id) if ev.recomendada else None,
        "ofertas": [{"id": str(e.id), "razon_social": e.razon_social, "monto": str(e.monto), "plazo_dias": e.plazo_dias,
                     "margen_aplicado_pct": str(e.margen_aplicado_pct), "precio_evaluado": str(e.precio_evaluado),
                     "elegible": e.elegible, "motivo": e.motivo, "ranking": e.ranking, "recomendada": e.recomendada,
                     "recibida": e.fecha_recepcion.isoformat()} for e in ev.ofertas],
    }


@router.post("/{cid}/evaluar", response_model=ContratacionOut)
def evaluar(cid: uuid.UUID, request: Request, db: Session = Depends(get_db),
            u: Usuario = Depends(requiere_roles(R.CONTRATACIONES))):
    c = tramite.evaluar(db, u, _cargar(db, cid, u), ip_cliente(request))
    db.commit()
    return serializar(db, c, u)


# ---------------- adjudicacion / formalizacion
@router.post("/{cid}/adjudicar", response_model=ContratacionOut)
def adjudicar(cid: uuid.UUID, datos: AdjudicarIn, request: Request, db: Session = Depends(get_db),
              u: Usuario = Depends(requiere_roles(R.RPA))):
    c = tramite.adjudicar(db, u, _cargar(db, cid, u), datos.cotizacion_id, datos.motivo, ip_cliente(request))
    db.commit()
    return serializar(db, c, u)


@router.post("/{cid}/declarar-desierta", response_model=ContratacionOut)
def desierta(cid: uuid.UUID, datos: MotivoIn, request: Request, db: Session = Depends(get_db),
             u: Usuario = Depends(requiere_roles(R.RPA))):
    c = tramite.declarar_desierta(db, u, _cargar(db, cid, u), datos.motivo, ip_cliente(request))
    db.commit()
    return serializar(db, c, u)


@router.post("/{cid}/formalizar", response_model=ContratacionOut)
def formalizar(cid: uuid.UUID, datos: FormalizarIn, request: Request, db: Session = Depends(get_db),
               u: Usuario = Depends(requiere_roles(R.RPA))):
    c = tramite.formalizar(db, u, _cargar(db, cid, u), datos.cuce, datos.metodo_formalizacion, ip_cliente(request))
    db.commit()
    return serializar(db, c, u)


# ---------------- recepcion, devengado, anulacion
@router.post("/{cid}/recepcion", response_model=ContratacionOut)
def recepcion(cid: uuid.UUID, datos: RecepcionIn, request: Request, db: Session = Depends(get_db),
              u: Usuario = Depends(requiere_roles(R.RECEPCION))):
    c, _ = tramite.recepcionar(db, u, _cargar(db, cid, u), datos.model_dump(), ip_cliente(request))
    db.commit()
    return serializar(db, c, u)


@router.post("/{cid}/devengar", response_model=ContratacionOut)
def devengar(cid: uuid.UUID, request: Request, db: Session = Depends(get_db),
             u: Usuario = Depends(requiere_roles(R.PRESUPUESTO))):
    c = tramite.devengar(db, u, _cargar(db, cid, u), ip_cliente(request))
    db.commit()
    return serializar(db, c, u)


@router.post("/{cid}/anular", response_model=ContratacionOut)
def anular(cid: uuid.UUID, datos: MotivoIn, request: Request, db: Session = Depends(get_db),
           u: Usuario = Depends(requiere_roles(R.RPA, R.SOLICITANTE))):
    c = tramite.anular(db, u, _cargar(db, cid, u), datos.motivo, ip_cliente(request))
    db.commit()
    return serializar(db, c, u)


# ---------------- documentos
@router.get("/{cid}/documentos", response_model=list[DocumentoOut])
def documentos(cid: uuid.UUID, db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    return [DocumentoOut.model_validate(d) for d in _cargar(db, cid, u, False).documentos]


@router.get("/{cid}/documentos/{doc_id}/descargar")
def descargar(cid: uuid.UUID, doc_id: uuid.UUID, db: Session = Depends(get_db), u: Usuario = Depends(usuario_actual)):
    c = _cargar(db, cid, u, False)
    d = next((x for x in c.documentos if x.id == doc_id), None)
    if d is None:
        raise HTTPException(404, "Documento no encontrado")
    contenido = get_storage().get(d.ruta_archivo)
    ext = d.ruta_archivo.rsplit(".", 1)[-1].lower()
    mime = "text/html; charset=utf-8" if ext == "html" else "application/pdf"
    return Response(contenido, media_type=mime,
                    headers={"Content-Disposition": f'inline; filename="{c.correlativo_interno}_{d.tipo_doc}_v{d.version}.{ext}"'})
