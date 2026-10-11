"""Autenticacion: access token (15 min) en el cuerpo y refresh token rotativo en cookie HTTP-only."""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import security
from ..config import get_settings
from ..database import get_db
from ..deps import ip_cliente, usuario_actual
from ..models import RefreshToken, Usuario
from ..schemas import LoginIn, TokenOut, UsuarioOut
from ..services import auditoria

router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE = "refresh_token"
COOKIE_PATH = "/api/v1/auth"


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


def _emitir(db: Session, u: Usuario, response: Response) -> TokenOut:
    s = get_settings()
    access = security.crear_access_token(u.id, u.rol)
    refresh, jti, h, expira = security.crear_refresh_token(u.id)
    db.add(RefreshToken(id=jti, usuario_id=u.id, token_hash=h, expires_at=expira))
    response.set_cookie(COOKIE, refresh, max_age=s.refresh_token_days * 86400, httponly=True, secure=s.cookie_secure,
                        samesite=s.cookie_samesite, path=COOKIE_PATH)
    return TokenOut(access_token=access, expires_in=s.access_token_minutes * 60)


@router.post("/login", response_model=TokenOut)
def login(datos: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    s = get_settings()
    ip = ip_cliente(request)
    u = db.scalar(select(Usuario).where(Usuario.username == datos.username.strip()))
    generico = HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario o contraseña incorrectos")
    if u is None:
        security.verify_password(datos.password, security.hash_password("dummy-timing"))  # iguala tiempos
        auditoria.registrar(db, None, "LOGIN_FALLIDO", "usuarios", datos.username[:60], None, {"motivo": "usuario"}, ip)
        db.commit()
        raise generico
    bloqueo = _aware(u.bloqueado_hasta)
    if bloqueo and bloqueo > _ahora():
        raise HTTPException(status.HTTP_423_LOCKED, "Cuenta bloqueada temporalmente por intentos fallidos")
    if not u.activo or not security.verify_password(datos.password, u.password_hash):
        u.intentos_fallidos += 1
        motivo = "inactivo" if not u.activo else "clave"
        if u.intentos_fallidos >= s.max_failed_logins:
            u.bloqueado_hasta = _ahora() + timedelta(minutes=s.lockout_minutes)
            u.intentos_fallidos = 0
            auditoria.registrar(db, u.id, "LOGIN_BLOQUEO", "usuarios", u.id, None, {"minutos": s.lockout_minutes}, ip)
        else:
            auditoria.registrar(db, u.id, "LOGIN_FALLIDO", "usuarios", u.id, None, {"motivo": motivo}, ip)
        db.commit()
        raise generico
    u.intentos_fallidos = 0
    u.bloqueado_hasta = None
    token = _emitir(db, u, response)
    auditoria.registrar(db, u.id, "LOGIN_OK", "usuarios", u.id, None, None, ip)
    db.commit()
    return token


@router.post("/refresh", response_model=TokenOut)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    no_auth = HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión expirada")
    token = request.cookies.get(COOKIE)
    if not token:
        raise no_auth
    try:
        datos = security.decodificar(token, "refresh")
        jti = uuid.UUID(datos["jti"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise no_auth
    rt = db.get(RefreshToken, jti)
    if rt is None or rt.revoked or rt.token_hash != security.hash_token(token):
        # reutilizacion de un token ya rotado/revocado: se revocan todos los tokens del usuario
        if rt is not None:
            for otro in db.scalars(select(RefreshToken).where(RefreshToken.usuario_id == rt.usuario_id)):
                otro.revoked = True
            auditoria.registrar(db, rt.usuario_id, "REFRESH_REUTILIZADO", "refresh_tokens", rt.id, None, None, ip_cliente(request))
            db.commit()
        raise no_auth
    u = db.get(Usuario, rt.usuario_id)
    if u is None or not u.activo:
        raise no_auth
    rt.revoked = True  # rotacion
    nuevo = _emitir(db, u, response)
    db.commit()
    return nuevo


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE)
    if token:
        try:
            datos = security.decodificar(token, "refresh")
            rt = db.get(RefreshToken, uuid.UUID(datos["jti"]))
            if rt:
                rt.revoked = True
                auditoria.registrar(db, rt.usuario_id, "LOGOUT", "usuarios", rt.usuario_id, None, None, ip_cliente(request))
                db.commit()
        except (jwt.PyJWTError, ValueError, KeyError):
            pass
    response.delete_cookie(COOKIE, path=COOKIE_PATH)


@router.get("/me", response_model=UsuarioOut)
def me(u: Usuario = Depends(usuario_actual)):
    return u
