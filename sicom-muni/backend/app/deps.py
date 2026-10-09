"""Dependencias FastAPI: usuario autenticado y control de acceso por rol (RBAC)."""
import uuid

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .enums import Rol
from .models import Usuario
from .security import decodificar

_bearer = HTTPBearer(auto_error=False)


def usuario_actual(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)
) -> Usuario:
    no_auth = HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado", headers={"WWW-Authenticate": "Bearer"})
    if cred is None:
        raise no_auth
    try:
        datos = decodificar(cred.credentials, "access")
        uid = uuid.UUID(datos["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise no_auth
    u = db.get(Usuario, uid)
    if u is None or not u.activo:
        raise no_auth
    return u


def requiere_roles(*roles: Rol):
    permitidos = {r.value for r in roles}

    def _dep(u: Usuario = Depends(usuario_actual)) -> Usuario:
        if u.rol not in permitidos:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Su rol no tiene permiso para esta operación")
        return u

    return _dep


def ip_cliente(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else ""
