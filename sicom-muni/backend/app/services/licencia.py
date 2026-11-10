"""Licenciamiento: modo de prueba (dias), licencia firmada ligada al equipo y limite de usuarios."""
import time
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import SessionLocal
from ..models import ParametroInstitucional, Usuario
from . import licencia_core as core
from . import parametros

PARAM_LICENCIA = "licencia_texto"
PARAM_PRUEBA = "prueba_inicio"
_TTL = 45.0
_cache: dict = {"t": 0.0, "estado": None}


def llave_publica() -> bytes:
    ruta = get_settings().licencia_llave_publica
    return Path(ruta or Path(__file__).resolve().parent.parent / "licencia_publica.pem").read_bytes()


def _valor(db: Session, clave: str) -> str:
    p = db.get(ParametroInstitucional, clave)
    return p.valor if p is not None else ""


def estado(db: Session, forzar: bool = False) -> dict:
    s = get_settings()
    ahora = time.monotonic()
    if not forzar and _cache["estado"] is not None and ahora - _cache["t"] < _TTL:
        return _cache["estado"]
    equipo = core.id_equipo()
    base = {"obligatoria": s.licencia_obligatoria, "id_equipo": equipo, "entidad": "", "vence": None,
            "dias_restantes": None, "max_usuarios": None, "licencia_id": None}
    texto = _valor(db, PARAM_LICENCIA)
    res = core.verificar(texto, llave_publica(), equipo) if texto else None
    if res is not None and res.valida:
        d = res.datos
        e = {**base, "modo": "LICENCIADA", "operativo": True, "entidad": d.get("entidad", ""), "vence": d.get("vence"),
             "dias_restantes": res.dias_restantes, "max_usuarios": d.get("max_usuarios"), "licencia_id": d.get("licencia_id"),
             "mensaje": "Licencia activa"}
    elif not s.licencia_obligatoria:
        e = {**base, "modo": "NO_REQUERIDA", "operativo": True, "mensaje": "Este despliegue no exige licencia"}
    else:
        inicio = _valor(db, PARAM_PRUEBA)
        if not inicio:  # primer arranque: comienza el periodo de prueba
            inicio = date.today().isoformat()
            parametros.guardar(db, PARAM_PRUEBA, inicio)
            db.commit()
        restantes = s.licencia_dias_prueba - (date.today() - date.fromisoformat(inicio)).days
        previa = f" ({res.mensaje})" if res is not None else ""
        if restantes > 0:
            e = {**base, "modo": "PRUEBA", "operativo": True, "dias_restantes": restantes,
                 "mensaje": f"Modo de prueba: quedan {restantes} día(s). Active la licencia para continuar{previa}."}
        else:
            vencida = res is not None and res.codigo == "VENCIDA"
            e = {**base, "modo": "VENCIDA" if vencida else "PRUEBA_VENCIDA", "operativo": False,
                 "mensaje": ("La licencia venció." if vencida else "El periodo de prueba terminó.") + " Active una licencia para usar el sistema."}
    _cache.update(t=ahora, estado=e)
    return e


def invalidar_cache() -> None:
    _cache.update(t=0.0, estado=None)


def operativo() -> bool:
    """Para el middleware: consulta con su propia sesion (usa cache)."""
    with SessionLocal() as db:
        return bool(estado(db)["operativo"])


def activar(db: Session, texto: str) -> dict:
    res = core.verificar(texto, llave_publica(), core.id_equipo())
    if not res.valida:
        raise HTTPException(422, res.mensaje)
    activos = db.scalar(select(func.count()).select_from(Usuario).where(Usuario.activo.is_(True))) or 0
    tope = res.datos.get("max_usuarios")
    if tope and activos > tope:
        raise HTTPException(422, f"La licencia permite {tope} usuario(s) y hay {activos} activos: desactive usuarios antes de activarla")
    parametros.guardar(db, PARAM_LICENCIA, texto.strip())
    parametros.guardar(db, "licencia_activada_en", datetime.now(timezone.utc).isoformat())
    db.commit()
    invalidar_cache()
    return estado(db, forzar=True)


def exigir_cupo_usuarios(db: Session) -> None:
    """Antes de crear o reactivar un usuario: respeta el maximo de usuarios de la licencia."""
    tope = estado(db).get("max_usuarios")
    if not tope:
        return
    activos = db.scalar(select(func.count()).select_from(Usuario).where(Usuario.activo.is_(True))) or 0
    if activos >= tope:
        raise HTTPException(422, f"La licencia permite {tope} usuario(s) activos: no se pueden agregar más")
