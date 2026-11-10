"""Autenticación: scrypt para contraseñas, JWT (HS256) para sesiones, roles ADMIN/RRHH/CONSULTA."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import config
from .db import get_db
from .models import Usuario

_bearer = HTTPBearer(auto_error=False)
ROLES = ("ADMIN", "RRHH", "CONSULTA")


def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, s, d = stored.split("$")
        dk = hashlib.scrypt(pw.encode(), salt=base64.b64decode(s), n=2 ** 14, r=8, p=1, dklen=32)
        return hmac.compare_digest(dk, base64.b64decode(d))
    except Exception:
        return False


def crear_token(u: Usuario) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=config.TOKEN_HORAS)
    return jwt.encode({"sub": u.username, "rol": u.rol, "exp": exp}, config.SECRET_KEY, algorithm="HS256")


def usuario_actual(cred: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)) -> Usuario:
    if not cred:
        raise HTTPException(401, "No autenticado")
    try:
        data = jwt.decode(cred.credentials, config.SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Sesión inválida o vencida")
    u = db.query(Usuario).filter_by(username=data["sub"], activo=True).one_or_none()
    if not u:
        raise HTTPException(401, "Usuario inactivo")
    return u


def requiere(*roles: str):
    def dep(u: Usuario = Depends(usuario_actual)) -> Usuario:
        if u.rol not in roles:
            raise HTTPException(403, "Permiso insuficiente para esta operación")
        return u
    return dep


SOLO_ADMIN = requiere("ADMIN")
ESCRIBE = requiere("ADMIN", "RRHH")
LEE = requiere("ADMIN", "RRHH", "CONSULTA")
