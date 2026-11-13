"""Importaciones desde Excel (presupuesto, catalogo CHB, objetivos POA) y gestion de objetivos del POA."""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import ip_cliente, requiere_roles, usuario_actual
from ..enums import Rol
from ..models import ObjetivoPOA, Usuario
from ..schemas import ObjetivoPoaIn, ObjetivoPoaOut
from ..services import auditoria, importacion, parametros, poa

router = APIRouter(tags=["importaciones"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


async def _leer(archivo: UploadFile) -> bytes:
    datos = await archivo.read(importacion.MAX_BYTES + 1)
    return datos


def _gestion(db: Session, gestion: int | None) -> int:
    return gestion or int(parametros.obtener_todos(db)["gestion"])


def _auditar(db: Session, u: Usuario, request: Request, accion: str, tabla: str, res: dict, nombre: str) -> None:
    auditoria.registrar(db, u.id, accion, tabla, None, None,
                        {"archivo": nombre, "nuevas": res["nuevas"], "actualizadas": res["actualizadas"]}, ip_cliente(request))


@router.get("/plantillas/{tipo}")
def descargar_plantilla(tipo: str, _: Usuario = Depends(usuario_actual)):
    nombres = {"presupuesto": "plantilla_presupuesto.xlsx", "chb": "plantilla_catalogo_chb.xlsx", "poa": "plantilla_objetivos_poa.xlsx"}
    if tipo not in nombres:
        raise HTTPException(404, "Plantilla no encontrada")
    return Response(importacion.plantilla(tipo), media_type=XLSX,
                    headers={"Content-Disposition": f'attachment; filename="{nombres[tipo]}"'})


@router.post("/partidas/importar")
async def importar_presupuesto(request: Request, archivo: UploadFile = File(...), gestion: int | None = Query(None),
                               confirmar: bool = Query(False), db: Session = Depends(get_db),
                               u: Usuario = Depends(requiere_roles(Rol.PRESUPUESTO, Rol.ADMIN))):
    res = importacion.importar_presupuesto(db, await _leer(archivo), archivo.filename or "", _gestion(db, gestion), confirmar)
    if confirmar:
        _auditar(db, u, request, "PRESUPUESTO_IMPORTADO", "partidas_presupuestarias", res, archivo.filename or "")
        db.commit()
    return res


@router.post("/catalogo-chb/importar")
async def importar_catalogo(request: Request, archivo: UploadFile = File(...), confirmar: bool = Query(False),
                            db: Session = Depends(get_db), u: Usuario = Depends(requiere_roles(Rol.CONTRATACIONES, Rol.ADMIN))):
    res = importacion.importar_catalogo_chb(db, await _leer(archivo), archivo.filename or "", confirmar)
    if confirmar:
        _auditar(db, u, request, "CATALOGO_CHB_IMPORTADO", "catalogo_chb", res, archivo.filename or "")
        db.commit()
    return res


# ---------------- objetivos del POA
@router.get("/poa/objetivos", response_model=list[ObjetivoPoaOut])
def listar_objetivos(gestion: int | None = None, db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    g = _gestion(db, gestion)
    return list(db.scalars(select(ObjetivoPOA).where(ObjetivoPOA.gestion == g).order_by(ObjetivoPOA.programa)))


@router.put("/poa/objetivos", response_model=ObjetivoPoaOut)
def guardar_objetivo(datos: ObjetivoPoaIn, request: Request, db: Session = Depends(get_db),
                     u: Usuario = Depends(requiere_roles(Rol.PRESUPUESTO, Rol.ADMIN))):
    clave = poa.normalizar_programa(datos.programa)
    o = next((x for x in db.scalars(select(ObjetivoPOA).where(ObjetivoPOA.gestion == datos.gestion))
              if poa.normalizar_programa(x.programa) == clave), None)
    antes = None
    if o is None:
        o = ObjetivoPOA(gestion=datos.gestion, programa=datos.programa)
        db.add(o)
    else:
        antes = {"objetivo": o.codigo_objetivo}
    o.denominacion_programa, o.codigo_objetivo, o.descripcion_objetivo = (
        datos.denominacion_programa, datos.codigo_objetivo, datos.descripcion_objetivo)
    db.flush()
    auditoria.registrar(db, u.id, "OBJETIVO_POA_GUARDADO", "objetivos_poa", o.id, antes,
                        {"programa": o.programa, "objetivo": o.codigo_objetivo}, ip_cliente(request))
    db.commit()
    return o


@router.delete("/poa/objetivos/{oid}", status_code=204)
def eliminar_objetivo(oid: uuid.UUID, request: Request, db: Session = Depends(get_db),
                      u: Usuario = Depends(requiere_roles(Rol.PRESUPUESTO, Rol.ADMIN))):
    o = db.get(ObjetivoPOA, oid)
    if o is None:
        raise HTTPException(404, "No encontrado")
    auditoria.registrar(db, u.id, "OBJETIVO_POA_ELIMINADO", "objetivos_poa", o.id, {"programa": o.programa}, None, ip_cliente(request))
    db.delete(o)
    db.commit()
    return Response(status_code=204)


@router.post("/poa/objetivos/importar")
async def importar_objetivos(request: Request, archivo: UploadFile = File(...), gestion: int | None = Query(None),
                             confirmar: bool = Query(False), db: Session = Depends(get_db),
                             u: Usuario = Depends(requiere_roles(Rol.PRESUPUESTO, Rol.ADMIN))):
    res = importacion.importar_objetivos_poa(db, await _leer(archivo), archivo.filename or "", _gestion(db, gestion), confirmar)
    if confirmar:
        _auditar(db, u, request, "OBJETIVOS_POA_IMPORTADOS", "objetivos_poa", res, archivo.filename or "")
        db.commit()
    return res
