"""Contraseñas (PBKDF2-HMAC-SHA256) y validaciones."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

ITERACIONES = 200_000


def nueva_sal() -> str:
    return base64.b64encode(os.urandom(16)).decode()


def hash_clave(clave: str, sal: str) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), base64.b64decode(sal), ITERACIONES, dklen=32)
    return base64.b64encode(dk).decode()


def verificar(clave: str, sal: str, hash_: str) -> bool:
    return hmac.compare_digest(hash_clave(clave, sal), hash_)


def validar_clave(clave: str) -> None:
    if len(clave or "") < 6:
        raise ValueError("La contraseña debe tener al menos 6 caracteres.")
    if clave.lower() in ("admin", "123456", "password", "contrasena", "contraseña"):
        raise ValueError("La contraseña es demasiado simple; elija otra.")
