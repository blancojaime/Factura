"""Activación de CONTA JB: código de solicitud por equipo + código de activación firmado (Ed25519).

* El programa solo contiene la clave PÚBLICA: puede verificar códigos pero no fabricarlos.
* El proveedor emite el código con su clave PRIVADA (Ayuda > Emitir código de activación, o `emitir()`).
* Sin activar, el programa funciona en modo de prueba durante DIAS_PRUEBA días desde el primer uso.
"""
from __future__ import annotations

import base64
import hashlib
import os
import platform
import sys
import uuid
from datetime import date, timedelta

from . import _ed25519

CLAVE_PUBLICA_HEX = "24a757ecc4a15f6b25877f3e24f504e1f99f7e25301517194d171ff58414c367"
DIAS_PRUEBA = 30
BASE = date(2000, 1, 1)
VERSION = 1


def generar_par() -> tuple:
    """(clave privada PEM, clave pública hex) nuevos. Ver el Manual de Activación, sección «par de claves nuevo»."""
    return _ed25519.generar_par()


# ----------------------------------------------------------------- equipo
def id_equipo() -> str:
    """Identificador estable del equipo (MachineGuid de Windows; en otros sistemas, MAC + nombre)."""
    if sys.platform.startswith("win"):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
                return str(winreg.QueryValueEx(k, "MachineGuid")[0])
        except OSError:
            pass
    return f"{uuid.getnode():x}-{platform.node()}"


def codigo_solicitud(equipo: str | None = None) -> str:
    """Código de solicitud que el usuario envía al proveedor, p. ej. JB-7K3Q-M2XA-9PLD-4HVE-ZT8R."""
    h = hashlib.sha256(("contajb|" + (equipo or id_equipo())).encode()).digest()
    b = base64.b32encode(h).decode()[:20]
    return "JB-" + "-".join(b[i:i + 4] for i in range(0, 20, 4))


def _normalizar(s: str) -> str:
    return "".join((s or "").split()).replace("-", "").upper()


# ---------------------------------------------------------------- códigos
def _mensaje(solicitud: str, payload: bytes) -> bytes:
    return b"CONTAJB1|" + _normalizar(solicitud).encode() + b"|" + payload


def emitir(clave_privada_pem: bytes, solicitud: str, vence: date | None) -> str:
    """Genera el código de activación para una solicitud. vence=None => licencia perpetua."""
    sol = _normalizar(solicitud)
    if not sol.startswith("JB") or len(sol) != 22:
        raise ValueError("El código de solicitud no es válido (formato JB-XXXX-XXXX-XXXX-XXXX-XXXX).")
    dias = 0 if vence is None else (vence - BASE).days
    if vence is not None and dias <= 0:
        raise ValueError("La fecha de vencimiento no es válida.")
    payload = bytes([VERSION]) + dias.to_bytes(4, "big")
    firma = _ed25519.firmar(_ed25519.semilla_desde_pem(clave_privada_pem), _mensaje(sol, payload))
    txt = base64.b32encode(payload + firma).decode().rstrip("=")
    return "-".join(txt[i:i + 8] for i in range(0, len(txt), 8))


def verificar(codigo: str, solicitud: str | None = None, hoy: date | None = None, clave_publica_hex: str | None = None) -> dict:
    """Valida un código de activación. Devuelve {'vence': date|None, 'perpetua': bool}; lanza ValueError si no es válido o venció."""
    raw = _normalizar(codigo)
    if not raw:
        raise ValueError("Ingrese el código de activación.")
    try:
        datos = base64.b32decode(raw + "=" * (-len(raw) % 8))
    except Exception:  # noqa: BLE001
        raise ValueError("El código de activación tiene caracteres no válidos.") from None
    if len(datos) != 5 + 64:
        raise ValueError("El código de activación está incompleto o es incorrecto.")
    payload, firma = datos[:5], datos[5:]
    if payload[0] != VERSION:
        raise ValueError("Versión de código no reconocida.")
    try:
        valida = _ed25519.verificar(bytes.fromhex(clave_publica_hex or CLAVE_PUBLICA_HEX), _mensaje(solicitud or codigo_solicitud(), payload), firma)
    except ValueError:
        valida = False
    if not valida:
        raise ValueError("El código de activación no corresponde a este equipo o no es auténtico.")
    dias = int.from_bytes(payload[1:], "big")
    vence = None if dias == 0 else BASE + timedelta(days=dias)
    if vence is not None and (hoy or date.today()) > vence:
        raise ValueError(f"La licencia venció el {vence:%d/%m/%Y}. Solicite un nuevo código de activación.")
    return {"vence": vence, "perpetua": vence is None}


# ------------------------------------------------------- estado en el sistema
def _cfg(sis, clave, defecto=""):
    r = sis.db.one("SELECT valor FROM config WHERE clave=?", (clave,))
    return r["valor"] if r else defecto


def _set(sis, clave, valor):
    sis.db.execute("INSERT INTO config (clave, valor) VALUES (?,?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor", (clave, valor))


def estado(sis, hoy: date | None = None) -> dict:
    """Estado de la licencia: modo 'activada' | 'prueba' | 'vencida' | 'bloqueada'."""
    hoy = hoy or date.today()
    ult = _cfg(sis, "lic_ultimo_uso")
    if ult and hoy < date.fromisoformat(ult) - timedelta(days=1):
        return {"modo": "bloqueada", "mensaje": "La fecha del equipo es anterior a la del último uso. Corrija la fecha de Windows.", "dias": 0, "solicitud": codigo_solicitud()}
    if not ult or hoy > date.fromisoformat(ult):
        _set(sis, "lic_ultimo_uso", hoy.isoformat())
    cod = _cfg(sis, "lic_codigo")
    if cod:
        try:
            v = verificar(cod, hoy=hoy)
            return {"modo": "activada", "vence": v["vence"], "perpetua": v["perpetua"], "dias": None, "solicitud": codigo_solicitud(),
                    "mensaje": "Licencia perpetua" if v["perpetua"] else f"Licencia vigente hasta el {v['vence']:%d/%m/%Y}"}
        except ValueError as ex:
            msg = str(ex)
    else:
        msg = ""
    ini = _cfg(sis, "lic_inicio")
    if not ini:
        ini = hoy.isoformat()
        _set(sis, "lic_inicio", ini)
    restan = DIAS_PRUEBA - (hoy - date.fromisoformat(ini)).days
    if restan > 0:
        return {"modo": "prueba", "dias": restan, "solicitud": codigo_solicitud(), "mensaje": f"Modo de prueba: quedan {restan} días." + (f" ({msg})" if msg else "")}
    return {"modo": "vencida", "dias": 0, "solicitud": codigo_solicitud(), "mensaje": msg or "El período de prueba terminó. Active CONTA JB con su código de activación."}


def activar(sis, codigo: str) -> dict:
    v = verificar(codigo)
    _set(sis, "lic_codigo", "".join(codigo.split()))
    return v


def puede_usarse(est: dict) -> bool:
    return est["modo"] in ("activada", "prueba")
