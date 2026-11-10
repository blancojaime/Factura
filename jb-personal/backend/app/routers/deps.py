from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from ..models import Usuario
from ..services.proceso import procesar_periodo, get_periodo
from .. import audit


def log(db: Session, u: Usuario, accion: str, entidad: str, eid="", detalle=None):
    audit.registrar(db, u.username, accion, entidad, eid, detalle)


def reprocesar(db: Session, u: Usuario, fechas: list[date]):
    """Mantiene sincronizado el motor: si el periodo ya fue procesado y sigue abierto, se recalcula."""
    visto = set()
    for f in fechas:
        k = (f.year, f.month)
        if k in visto:
            continue
        visto.add(k)
        p = get_periodo(db, *k)
        if p.procesado_en and p.estado == "ABIERTO":
            procesar_periodo(db, k[0], k[1], u.username)
