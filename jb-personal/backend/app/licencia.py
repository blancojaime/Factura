"""Activación de JB-Personal.

* Código de equipo: huella estable de la PC/servidor (MachineGuid de Windows o /etc/machine-id) -> «JBP-XXXXX-XXXXX-XXXXX».
* Código de activación: «JBP1.<datos>.<firma>» firmado con Ed25519 por la herramienta externa JB-Activador (el emisor).
  La aplicación solo contiene la clave PÚBLICA: puede verificar licencias pero NO emitirlas.
* Sin activar: periodo de prueba de 30 días; luego el sistema queda en SOLO LECTURA (se puede consultar, respaldar y activar,
  pero no registrar, importar, procesar ni generar reportes) hasta ingresar un código válido.
Aviso: toda protección de software escrita en un lenguaje interpretado es una medida DISUASIVA, no infranqueable.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from sqlalchemy.orm import Session

from . import audit, config
from .licencia_publica import CLAVE_PUBLICA_B64
from .models import Licencia

PRODUCTO = "JB-Personal"
DIAS_PRUEBA = 30
PREFIJO = "JBP1"


class LicenciaError(Exception):
    pass


def _guid_equipo() -> str:
    if sys.platform.startswith("win"):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0,
                                winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
                return str(winreg.QueryValueEx(k, "MachineGuid")[0])
        except OSError:
            pass
    for f in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            return Path(f).read_text().strip()
        except OSError:
            continue
    import uuid
    return str(uuid.getnode())


def id_equipo() -> str:
    h = hashlib.sha256(f"{PRODUCTO}|{_guid_equipo()}".encode()).hexdigest().upper()[:15]
    return f"JBP-{h[:5]}-{h[5:10]}-{h[10:15]}"


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def verificar_codigo(codigo: str, equipo: str | None = None, hoy: date | None = None) -> dict:
    """Devuelve el contenido firmado o lanza LicenciaError con un mensaje claro."""
    codigo = "".join((codigo or "").split())
    try:
        pref, datos, firma = codigo.split(".")
    except ValueError:
        raise LicenciaError("El código de activación tiene un formato inválido")
    if pref != PREFIJO:
        raise LicenciaError("El código de activación no corresponde a esta versión de JB-Personal")
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(CLAVE_PUBLICA_B64)).verify(_b64d(firma), _b64d(datos))
        d = json.loads(_b64d(datos))
    except (InvalidSignature, ValueError, json.JSONDecodeError):
        raise LicenciaError("Código de activación inválido o alterado")
    if d.get("p") != PRODUCTO:
        raise LicenciaError("El código no es para JB-Personal")
    if d.get("m") not in ((equipo or id_equipo()), "*"):
        raise LicenciaError("Este código fue emitido para OTRO equipo (código de equipo distinto)")
    if d.get("v") and date.fromisoformat(d["v"]) < (hoy or date.today()):
        raise LicenciaError(f"La licencia venció el {d['v']}")
    return d


# ---------------------------------------------------------------- estado
def _marca_archivo() -> Path:
    return config.DATA_DIR / ".jbp_inicio"


def _fila(db: Session) -> Licencia:
    lic = db.get(Licencia, 1)
    if not lic:
        previo = None
        try:
            previo = date.fromisoformat(_marca_archivo().read_text().strip())     # evita reiniciar la prueba borrando la BD
        except (OSError, ValueError):
            pass
        lic = Licencia(id=1, primer_uso=min(previo, date.today()) if previo else date.today())
        db.add(lic)
        db.flush()
    try:
        if not _marca_archivo().exists():
            _marca_archivo().write_text(lic.primer_uso.isoformat())
    except OSError:
        pass
    return lic


def estado(db: Session, hoy: date | None = None) -> dict:
    hoy = hoy or date.today()
    lic = _fila(db)
    base = {"id_equipo": id_equipo(), "producto": PRODUCTO}
    if lic.codigo:
        try:
            d = verificar_codigo(lic.codigo, hoy=hoy)
            return {**base, "estado": "ACTIVADA", "entidad": d.get("e", ""), "vence": d.get("v"), "bloqueado": False,
                    "dias_restantes": (date.fromisoformat(d["v"]) - hoy).days if d.get("v") else None,
                    "mensaje": "Licencia activa" + (f" hasta {d['v']}" if d.get("v") else " (sin vencimiento)")}
        except LicenciaError as e:
            return {**base, "estado": "VENCIDA", "bloqueado": True, "dias_restantes": 0, "vence": None, "entidad": lic.entidad,
                    "mensaje": f"{e}. El sistema está en modo solo lectura: solicite un nuevo código de activación."}
    resto = DIAS_PRUEBA - (hoy - lic.primer_uso).days
    if resto > 0:
        return {**base, "estado": "PRUEBA", "bloqueado": False, "dias_restantes": resto, "vence": None, "entidad": "",
                "mensaje": f"Periodo de prueba: {resto} día(s) restantes. Active el sistema con su código de activación."}
    return {**base, "estado": "PRUEBA_VENCIDA", "bloqueado": True, "dias_restantes": 0, "vence": None, "entidad": "",
            "mensaje": "El periodo de prueba terminó: el sistema está en modo solo lectura. Ingrese su código de activación."}


def activar(db: Session, codigo: str, usuario: str) -> dict:
    d = verificar_codigo(codigo)
    lic = _fila(db)
    lic.codigo = "".join(codigo.split())
    lic.entidad = d.get("e", "")
    lic.vence = date.fromisoformat(d["v"]) if d.get("v") else None
    lic.activada = datetime.now()
    audit.registrar(db, usuario, "ACTIVAR_LICENCIA", "licencia", 1, {"entidad": lic.entidad, "vence": d.get("v"), "equipo": id_equipo()})
    _cache.clear()
    return estado(db)


def cargar_archivo(db: Session) -> None:
    """Si existe <datos>/licencia.jbp (instalación asistida por TI) y aún no hay licencia válida, la activa."""
    f = config.DATA_DIR / "licencia.jbp"
    if f.exists() and not _fila(db).codigo:
        try:
            activar(db, f.read_text(), "archivo")
        except LicenciaError:
            pass


# ---------------------------------------------------------------- bloqueo (modo solo lectura)
_cache: dict = {}
EXENTAS = ("/api/auth/", "/api/licencia", "/api/salud", "/api/backup", "/api/docs", "/api/openapi")


def bloqueado(db_factory) -> tuple[bool, str]:
    ahora = time.time()
    c = _cache.get("v")
    if c and ahora - c[0] < 30:
        return c[1], c[2]
    with db_factory() as s:
        e = estado(s)
        s.commit()
    _cache["v"] = (ahora, e["bloqueado"], e["mensaje"])
    return e["bloqueado"], e["mensaje"]


def requiere_bloqueo(metodo: str, ruta: str) -> bool:
    """En modo bloqueado se permiten consultas (GET) y todo lo exento; se impiden escrituras y la generación de reportes."""
    if any(ruta.startswith(x) for x in EXENTAS) or not ruta.startswith("/api/"):
        return False
    return metodo != "GET" or ruta.startswith("/api/reportes/")
