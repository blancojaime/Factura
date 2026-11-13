"""Nucleo de licencias de SICOM-MUNI (sin dependencias del servidor web).

Lo usan el servidor (verificar) y el Emisor de Licencias externo (firmar). Esquema:
  * El emisor conserva una llave PRIVADA Ed25519 (nunca se distribuye).
  * El servidor lleva solo la llave PUBLICA (app/licencia_publica.pem) y verifica la firma.
  * Cada licencia se liga al ID del equipo (o "*" para cualquier equipo) y puede vencer y limitar usuarios.
Formatos: archivo .sicomlic (JSON) o "clave de activacion" de una linea: SICOM1-<base64url(JSON)>.
"""
import base64
import hashlib
import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

PREFIJO = "SICOM1-"
FORMATO = 1


# ------------------------------------------------------------------ ID del equipo
def _id_crudo() -> str:
    if sys.platform.startswith("win"):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography",
                                0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
                return str(winreg.QueryValueEx(k, "MachineGuid")[0])
        except OSError:
            pass
    for ruta in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            texto = Path(ruta).read_text().strip()
            if texto:
                return texto
        except OSError:
            continue
    return f"MAC-{uuid.getnode():012x}"


def id_equipo() -> str:
    """ID estable del equipo con formato XXXX-XXXX-XXXX-XXXX (derivado del identificador del sistema operativo)."""
    h = hashlib.sha256(("SICOM-MUNI|" + _id_crudo().lower()).encode()).hexdigest().upper()[:16]
    return "-".join(h[i:i + 4] for i in range(0, 16, 4))


def normalizar_id(texto: str) -> str:
    limpio = "".join(c for c in texto.upper() if c.isalnum())
    return "-".join(limpio[i:i + 4] for i in range(0, len(limpio), 4)) if len(limpio) == 16 else texto.strip().upper()


# ------------------------------------------------------------------ llaves
def generar_par_llaves() -> tuple[bytes, bytes]:
    privada = Ed25519PrivateKey.generate()
    pem_priv = privada.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    pem_pub = privada.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    return pem_priv, pem_pub


def cargar_privada(pem: bytes | str) -> Ed25519PrivateKey:
    clave = serialization.load_pem_private_key(pem.encode() if isinstance(pem, str) else pem, password=None)
    if not isinstance(clave, Ed25519PrivateKey):
        raise ValueError("La llave privada no es Ed25519")
    return clave


def cargar_publica(pem: bytes | str) -> Ed25519PublicKey:
    clave = serialization.load_pem_public_key(pem.encode() if isinstance(pem, str) else pem)
    if not isinstance(clave, Ed25519PublicKey):
        raise ValueError("La llave publica no es Ed25519")
    return clave


def publica_de(pem_privada: bytes | str) -> bytes:
    return cargar_privada(pem_privada).public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)


# ------------------------------------------------------------------ emitir / verificar
def _canonico(datos: dict) -> bytes:
    return json.dumps(datos, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def emitir(pem_privada: bytes | str, *, entidad: str, equipo: str = "*", vence: date | None = None,
           max_usuarios: int | None = None, observaciones: str = "", hoy: date | None = None) -> dict:
    if not entidad.strip():
        raise ValueError("Indique el nombre de la entidad")
    equipo = "*" if equipo.strip() in ("", "*") else normalizar_id(equipo)
    if equipo != "*" and len(equipo) != 19:
        raise ValueError("El ID del equipo debe tener el formato XXXX-XXXX-XXXX-XXXX")
    datos = {
        "licencia_id": uuid.uuid4().hex[:12].upper(), "entidad": entidad.strip(), "equipo": equipo,
        "emitida": (hoy or date.today()).isoformat(), "vence": vence.isoformat() if vence else None,
        "max_usuarios": int(max_usuarios) if max_usuarios else None, "observaciones": observaciones.strip(),
    }
    firma = cargar_privada(pem_privada).sign(_canonico(datos))
    return {"formato": FORMATO, "datos": datos, "firma": base64.b64encode(firma).decode()}


def a_clave(licencia: dict) -> str:
    """Clave de activacion de una sola linea (para pegar en la pantalla de activacion)."""
    return PREFIJO + base64.urlsafe_b64encode(json.dumps(licencia, separators=(",", ":"), ensure_ascii=False).encode()).decode().rstrip("=")


def leer(texto: str) -> dict:
    """Acepta el contenido de un archivo .sicomlic (JSON) o una clave SICOM1-..."""
    t = texto.strip().lstrip("﻿")
    if t.startswith(PREFIJO):
        b = t[len(PREFIJO):].strip()
        t = base64.urlsafe_b64decode(b + "=" * (-len(b) % 4)).decode("utf-8")
    lic = json.loads(t)
    if not isinstance(lic, dict) or "datos" not in lic or "firma" not in lic:
        raise ValueError("El contenido no es una licencia de SICOM-MUNI")
    return lic


@dataclass
class Resultado:
    valida: bool
    codigo: str  # OK, FORMATO, FIRMA, EQUIPO, VENCIDA
    mensaje: str
    datos: dict = field(default_factory=dict)

    @property
    def dias_restantes(self) -> int | None:
        v = self.datos.get("vence")
        return (date.fromisoformat(v) - date.today()).days if v else None


def verificar(licencia: dict | str, pem_publica: bytes | str, equipo_local: str, hoy: date | None = None) -> Resultado:
    hoy = hoy or date.today()
    try:
        lic = leer(licencia) if isinstance(licencia, str) else licencia
        datos, firma = lic["datos"], base64.b64decode(lic["firma"])
    except Exception:  # noqa: BLE001
        return Resultado(False, "FORMATO", "El archivo o la clave no es una licencia válida de SICOM-MUNI")
    try:
        cargar_publica(pem_publica).verify(firma, _canonico(datos))
    except (InvalidSignature, ValueError):
        return Resultado(False, "FIRMA", "La licencia no es auténtica (firma inválida)", datos)
    if datos.get("equipo", "*") != "*" and normalizar_id(datos["equipo"]) != normalizar_id(equipo_local):
        return Resultado(False, "EQUIPO", f"La licencia fue emitida para otro equipo ({datos['equipo']})", datos)
    if datos.get("vence") and date.fromisoformat(datos["vence"]) < hoy:
        return Resultado(False, "VENCIDA", f"La licencia venció el {datos['vence']}", datos)
    return Resultado(True, "OK", "Licencia válida", datos)


def ahora() -> datetime:
    return datetime.now()
