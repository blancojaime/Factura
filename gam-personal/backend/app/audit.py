"""Bitácora de auditoría encadenada por SHA-256 (cada fila incluye el hash de la anterior)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AuditLog

GENESIS = "0" * 64


def _h(prev: str, ts: str, usuario: str, accion: str, entidad: str, eid: str, detalle: str) -> str:
    return hashlib.sha256("|".join([prev, ts, usuario, accion, entidad, eid, detalle]).encode("utf-8")).hexdigest()


def registrar(db: Session, usuario: str, accion: str, entidad: str, entidad_id="", detalle=None) -> AuditLog:
    last = db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(1)).scalar_one_or_none()
    prev = last.hash if last else GENESIS
    ts = datetime.now().replace(microsecond=0)
    det = detalle if isinstance(detalle, str) else json.dumps(detalle or {}, ensure_ascii=False, default=str, sort_keys=True)
    row = AuditLog(ts=ts, usuario=usuario, accion=accion, entidad=entidad, entidad_id=str(entidad_id), detalle=det,
                   hash_prev=prev, hash=_h(prev, ts.isoformat(), usuario, accion, entidad, str(entidad_id), det))
    db.add(row)
    db.flush()
    return row


def verificar_cadena(db: Session) -> dict:
    prev, n = GENESIS, 0
    for r in db.execute(select(AuditLog).order_by(AuditLog.id)).scalars():
        n += 1
        esperado = _h(prev, r.ts.isoformat(), r.usuario, r.accion, r.entidad, r.entidad_id, r.detalle)
        if r.hash_prev != prev or r.hash != esperado:
            return {"ok": False, "registros": n, "primer_error_id": r.id}
        prev = r.hash
    return {"ok": True, "registros": n, "primer_error_id": None}
