"""Activación offline por código de máquina + licencia firmada Ed25519.

Flujo: el cliente envía su CÓDIGO DE INSTALACIÓN; el proveedor (herramienta externa tools/licencias.py,
con su clave privada) devuelve una LICENCIA firmada. La app sólo contiene la clave pública.
"""
import base64
import hashlib
import json
import os
import platform
import subprocess
import uuid
from datetime import date, datetime, timedelta

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .paths import resource_dir

PREFIX = "SIIM1"
TRIAL_DAYS = 30


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _raw_machine_id() -> str:
    try:
        if os.name == "nt":
            import winreg
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            return winreg.QueryValueEx(k, "MachineGuid")[0]
        for p in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            if os.path.exists(p):
                return open(p).read().strip()
    except Exception:
        pass
    return f"{uuid.getnode():x}-{platform.node()}"


def machine_code() -> str:
    """Código de instalación legible: XXXX-XXXX-XXXX-XXXX (hash de la identidad de la máquina)."""
    h = hashlib.sha256(("SIIM2026|" + _raw_machine_id()).encode()).hexdigest().upper()[:16]
    return "-".join(h[i:i + 4] for i in range(0, 16, 4))


def load_public_key(pem: bytes = None):
    if pem is None:
        p = resource_dir() / "resources" / "license_pub.pem"
        if not p.exists():
            return None
        pem = p.read_bytes()
    return serialization.load_pem_public_key(pem)


class LicenseStatus:
    def __init__(self, estado, mensaje, datos=None, dias=None):
        self.estado = estado          # LICENCIADO | PRUEBA | VENCIDO | INVALIDO | SIN_CONFIG
        self.mensaje = mensaje
        self.datos = datos or {}
        self.dias = dias

    @property
    def ok(self):
        return self.estado in ("LICENCIADO", "PRUEBA")


def verify_license_text(text: str, pubkey=None, machine=None, today=None) -> LicenseStatus:
    pubkey = pubkey or load_public_key()
    if pubkey is None:
        return LicenseStatus("SIN_CONFIG", "Esta compilación no tiene clave pública de licencias.")
    today = today or date.today()
    try:
        pre, body, sig = text.strip().split(".")
        if pre != PREFIX:
            raise ValueError
        payload = _b64d(body)
        pubkey.verify(_b64d(sig), payload)
        d = json.loads(payload)
    except (ValueError, InvalidSignature, Exception):
        return LicenseStatus("INVALIDO", "La licencia no es válida o fue alterada.")
    if d.get("maquina") not in ("*", (machine or machine_code())):
        return LicenseStatus("INVALIDO", "La licencia fue emitida para otro equipo.", d)
    if d.get("vence"):
        dias = (date.fromisoformat(d["vence"]) - today).days
        if dias < 0:
            return LicenseStatus("VENCIDO", f"La licencia venció el {d['vence']}.", d, dias)
        return LicenseStatus("LICENCIADO", f"Licenciado a {d.get('cliente')} (vence {d['vence']}).", d, dias)
    return LicenseStatus("LICENCIADO", f"Licenciado a {d.get('cliente')} (perpetua).", d)


class LicenseManager:
    """Gestiona licencia instalada, periodo de prueba y detección de retroceso de reloj."""

    def __init__(self, db, pubkey=None):
        self.db = db
        self.pubkey = pubkey

    def _stamp(self, what, value):
        key = hashlib.sha256((machine_code() + what).encode()).hexdigest()[:8]
        return hashlib.sha256((key + what + value).encode()).hexdigest()[:16]

    def _get(self, k):
        v = self.db.param(k)
        s = self.db.param(k + "_sig")
        return v if v and s == self._stamp(k, v) else None

    def _put(self, k, v):
        self.db.set_param(k, v)
        self.db.set_param(k + "_sig", self._stamp(k, v))

    def install(self, text: str) -> LicenseStatus:
        st = verify_license_text(text, self.pubkey)
        if st.estado in ("LICENCIADO",):
            self.db.set_param("licencia", text.strip())
        return st

    def status(self, today=None) -> LicenseStatus:
        today = today or date.today()
        last = self._get("ultimo_uso")
        if last and today < date.fromisoformat(last) - timedelta(days=1):
            return LicenseStatus("INVALIDO", "Se detectó que la fecha del sistema fue retrasada. Corrija la fecha de Windows.")
        if not last or today > date.fromisoformat(last):
            self._put("ultimo_uso", today.isoformat())
        lic = self.db.param("licencia")
        if lic:
            st = verify_license_text(lic, self.pubkey, today=today)
            if st.ok or st.estado == "VENCIDO":
                return st
        ini = self._get("inicio_prueba")
        if not ini:
            ini = today.isoformat()
            self._put("inicio_prueba", ini)
        dias = TRIAL_DAYS - (today - date.fromisoformat(ini)).days
        if dias >= 0:
            return LicenseStatus("PRUEBA", f"Versión de prueba: quedan {dias} día(s).", dias=dias)
        return LicenseStatus("VENCIDO", "El periodo de prueba terminó. Active su licencia.", dias=dias)
