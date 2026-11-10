from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Usuario
from ..security import (ROLES, SOLO_ADMIN, crear_token, hash_password, usuario_actual, verify_password)
from .deps import log

router = APIRouter(prefix="/api", tags=["auth"])
_fallos: dict[str, list[float]] = {}


class Login(BaseModel):
    username: str
    password: str


class Setup(BaseModel):
    username: str = Field(min_length=3, max_length=60)
    password: str = Field(min_length=8, max_length=128)
    nombre: str = ""


class UsuarioIn(BaseModel):
    username: str = Field(min_length=3, max_length=60)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    nombre: str = ""
    rol: str = "RRHH"
    activo: bool = True


@router.get("/auth/estado")
def estado(db: Session = Depends(get_db)):
    return {"inicializado": db.scalar(select(func.count(Usuario.id))) > 0}


@router.post("/auth/setup")
def setup(d: Setup, db: Session = Depends(get_db)):
    if db.scalar(select(func.count(Usuario.id))) > 0:
        raise HTTPException(409, "El sistema ya fue inicializado")
    u = Usuario(username=d.username, nombre=d.nombre, password_hash=hash_password(d.password), rol="ADMIN")
    db.add(u)
    db.flush()
    log(db, u, "SETUP_ADMIN", "usuario", u.id)
    db.commit()
    return {"token": crear_token(u), "usuario": {"username": u.username, "rol": u.rol, "nombre": u.nombre}}


@router.post("/auth/login")
def login(d: Login, db: Session = Depends(get_db)):
    ahora = time.time()
    f = [t for t in _fallos.get(d.username, []) if ahora - t < 300]
    if len(f) >= 5:
        raise HTTPException(429, "Demasiados intentos fallidos; espere 5 minutos")
    u = db.execute(select(Usuario).where(Usuario.username == d.username, Usuario.activo == True)).scalars().first()  # noqa: E712
    if not u or not verify_password(d.password, u.password_hash):
        f.append(ahora)
        _fallos[d.username] = f
        raise HTTPException(401, "Usuario o contraseña incorrectos")
    _fallos.pop(d.username, None)
    log(db, u, "LOGIN", "usuario", u.id)
    db.commit()
    return {"token": crear_token(u), "usuario": {"username": u.username, "rol": u.rol, "nombre": u.nombre}}


@router.get("/auth/yo")
def yo(u: Usuario = Depends(usuario_actual)):
    return {"username": u.username, "rol": u.rol, "nombre": u.nombre}


@router.get("/usuarios")
def listar(u: Usuario = Depends(SOLO_ADMIN), db: Session = Depends(get_db)):
    return [{"id": x.id, "username": x.username, "nombre": x.nombre, "rol": x.rol, "activo": x.activo}
            for x in db.execute(select(Usuario).order_by(Usuario.username)).scalars()]


@router.post("/usuarios")
def crear(d: UsuarioIn, u: Usuario = Depends(SOLO_ADMIN), db: Session = Depends(get_db)):
    if d.rol not in ROLES or not d.password:
        raise HTTPException(422, "Rol inválido o contraseña faltante")
    if db.execute(select(Usuario).where(Usuario.username == d.username)).scalars().first():
        raise HTTPException(409, "El usuario ya existe")
    n = Usuario(username=d.username, nombre=d.nombre, rol=d.rol, password_hash=hash_password(d.password), activo=d.activo)
    db.add(n)
    db.flush()
    log(db, u, "CREAR_USUARIO", "usuario", n.id, {"username": n.username, "rol": n.rol})
    db.commit()
    return {"id": n.id}


@router.put("/usuarios/{uid}")
def editar(uid: int, d: UsuarioIn, u: Usuario = Depends(SOLO_ADMIN), db: Session = Depends(get_db)):
    n = db.get(Usuario, uid)
    if not n or d.rol not in ROLES:
        raise HTTPException(404, "Usuario no encontrado o rol inválido")
    if n.id == u.id and (not d.activo or d.rol != "ADMIN"):
        raise HTTPException(422, "No puede quitarse a sí mismo el rol ADMIN ni desactivarse")
    n.nombre, n.rol, n.activo = d.nombre, d.rol, d.activo
    if d.password:
        n.password_hash = hash_password(d.password)
    log(db, u, "EDITAR_USUARIO", "usuario", n.id, {"rol": n.rol, "activo": n.activo, "cambio_password": bool(d.password)})
    db.commit()
    return {"ok": True}
