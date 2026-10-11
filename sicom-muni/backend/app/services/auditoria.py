"""Audit Trail inalterable: solo INSERT (trigger en PostgreSQL) y cadena de hashes SHA-256.

Cada registro incluye el hash del anterior; alterar o borrar una fila rompe la cadena y
`verificar_cadena` lo detecta aun si alguien desactivara el trigger.
"""
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AuditLog, Secuencia
from .secuencias import siguiente

GENESIS = "0" * 64


def _json_seguro(obj: Any) -> Any:
    if obj is None:
        return None
    return json.loads(json.dumps(obj, default=str, ensure_ascii=False))


def _hash(secuencia: int, previo: str, usuario_id: str, accion: str, tabla: str, registro_id: str,
          antes: Any, despues: Any, ip: str, ts_iso: str) -> str:
    carga = json.dumps(
        [secuencia, previo, usuario_id, accion, tabla, registro_id, antes, despues, ip, ts_iso],
        sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(carga.encode("utf-8")).hexdigest()


def registrar(db: Session, usuario_id: uuid.UUID | None, accion: str, tabla: str = "", registro_id: Any = "",
              antes: Any = None, despues: Any = None, ip: str = "") -> AuditLog:
    secuencia = siguiente(db, "audit")  # bloquea la fila del contador: serializa la cadena
    previo = db.scalar(select(AuditLog.hash_registro).where(AuditLog.secuencia == secuencia - 1)) or GENESIS
    ahora = datetime.now(timezone.utc)
    antes_j, despues_j = _json_seguro(antes), _json_seguro(despues)
    h = _hash(secuencia, previo, str(usuario_id or ""), accion, tabla, str(registro_id), antes_j, despues_j, ip,
              ahora.isoformat())
    fila = AuditLog(usuario_id=usuario_id, accion=accion, tabla_afectada=tabla, registro_id=str(registro_id),
                    datos_previos_json=antes_j, datos_nuevos_json=despues_j, ip_address=ip, timestamp=ahora,
                    secuencia=secuencia, hash_previo=previo, hash_registro=h)
    db.add(fila)
    db.flush()
    return fila


def verificar_cadena(db: Session) -> dict:
    """Recorre toda la cadena. Devuelve {ok, total, primera_ruptura}."""
    previo = GENESIS
    total = 0
    for fila in db.scalars(select(AuditLog).order_by(AuditLog.secuencia)):
        total += 1
        ts = fila.timestamp
        if ts.tzinfo is None:  # SQLite devuelve fechas ingenuas
            ts = ts.replace(tzinfo=timezone.utc)
        esperado = _hash(fila.secuencia, previo, str(fila.usuario_id or ""), fila.accion, fila.tabla_afectada,
                         fila.registro_id, fila.datos_previos_json, fila.datos_nuevos_json, fila.ip_address,
                         ts.isoformat())
        if fila.hash_previo != previo or fila.hash_registro != esperado:
            return {"ok": False, "total": total, "primera_ruptura": fila.secuencia}
        previo = fila.hash_registro
    return {"ok": True, "total": total, "primera_ruptura": None}
