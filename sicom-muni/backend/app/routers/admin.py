"""Administracion: usuarios, parametros institucionales y auditoria (ROL_ADMIN)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import security
from ..database import get_db
from ..deps import ip_cliente, requiere_roles, usuario_actual
from ..enums import Rol
from ..models import AuditLog, ParametroInstitucional, Usuario
from ..schemas import ParametroIn, ParametroOut, UsuarioCreate, UsuarioOut, UsuarioUpdate
from ..services import auditoria, parametros

router = APIRouter(prefix="/admin", tags=["admin"])
solo_admin = requiere_roles(Rol.ADMIN)


# ---------------- usuarios
@router.get("/usuarios", response_model=list[UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db), _: Usuario = Depends(solo_admin)):
    return list(db.scalars(select(Usuario).order_by(Usuario.username)))


@router.post("/usuarios", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def crear_usuario(datos: UsuarioCreate, request: Request, db: Session = Depends(get_db), admin: Usuario = Depends(solo_admin)):
    err = security.password_error(datos.password)
    if err:
        raise HTTPException(422, err)
    if db.scalar(select(Usuario).where(Usuario.username == datos.username)):
        raise HTTPException(409, "El usuario ya existe")
    u = Usuario(username=datos.username, password_hash=security.hash_password(datos.password),
                nombre_completo=datos.nombre_completo, cargo=datos.cargo, rol=datos.rol.value, email=datos.email)
    db.add(u)
    db.flush()
    auditoria.registrar(db, admin.id, "USUARIO_CREADO", "usuarios", u.id, None,
                        {"username": u.username, "rol": u.rol}, ip_cliente(request))
    db.commit()
    return u


@router.patch("/usuarios/{uid}", response_model=UsuarioOut)
def actualizar_usuario(uid: uuid.UUID, datos: UsuarioUpdate, request: Request, db: Session = Depends(get_db),
                       admin: Usuario = Depends(solo_admin)):
    u = db.get(Usuario, uid)
    if u is None:
        raise HTTPException(404, "Usuario no encontrado")
    antes = {"rol": u.rol, "activo": u.activo, "nombre": u.nombre_completo}
    cambios = datos.model_dump(exclude_unset=True)
    if "password" in cambios and cambios["password"]:
        err = security.password_error(cambios["password"])
        if err:
            raise HTTPException(422, err)
        u.password_hash = security.hash_password(cambios.pop("password"))
        u.intentos_fallidos, u.bloqueado_hasta = 0, None
    cambios.pop("password", None)
    if "activo" in cambios and u.id == admin.id and cambios["activo"] is False:
        raise HTTPException(422, "No puede desactivar su propia cuenta")
    if "rol" in cambios and cambios["rol"] is not None:
        if u.id == admin.id and cambios["rol"] != Rol.ADMIN:
            raise HTTPException(422, "No puede quitarse a sí mismo el rol de administrador")
        cambios["rol"] = cambios["rol"].value
    for k, v in cambios.items():
        if v is not None:
            setattr(u, k, v)
    db.flush()
    auditoria.registrar(db, admin.id, "USUARIO_ACTUALIZADO", "usuarios", u.id, antes,
                        {"rol": u.rol, "activo": u.activo, "nombre": u.nombre_completo}, ip_cliente(request))
    db.commit()
    return u


# ---------------- parametros
@router.get("/parametros", response_model=list[ParametroOut])
def listar_parametros(db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    valores = parametros.obtener_todos(db)
    return [ParametroOut(clave=k, valor=valores[k], descripcion=parametros.DEFAULTS[k][1]) for k in parametros.DEFAULTS]


@router.put("/parametros/{clave}", response_model=ParametroOut)
def guardar_parametro(clave: str, datos: ParametroIn, request: Request, db: Session = Depends(get_db),
                      admin: Usuario = Depends(solo_admin)):
    if clave not in parametros.DEFAULTS:
        raise HTTPException(404, "Parámetro desconocido")
    if clave in ("tope_contratacion_menor", "tope_compra_directa", "plazo_orden_max_dias", "min_cotizaciones_consulta",
                 "min_cotizaciones_directa", "chb_min_justificacion", "gestion"):
        if not datos.valor.strip().isdigit() or int(datos.valor) < 1:
            raise HTTPException(422, "El valor debe ser un número entero positivo")
    if clave == "logo_url" and datos.valor and not datos.valor.startswith("data:image/"):
        raise HTTPException(422, "El logotipo debe cargarse como imagen embebida (data:image/...)")
    antes = parametros.obtener_todos(db)[clave]
    parametros.guardar(db, clave, datos.valor)
    db.flush()
    auditoria.registrar(db, admin.id, "PARAMETRO_ACTUALIZADO", "parametros_institucionales", clave,
                        {"valor": antes[:200]}, {"valor": datos.valor[:200]}, ip_cliente(request))
    db.commit()
    return ParametroOut(clave=clave, valor=datos.valor, descripcion=parametros.DEFAULTS[clave][1])


# ---------------- auditoria
@router.get("/auditoria")
def listar_auditoria(accion: str | None = None, limite: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
                     db: Session = Depends(get_db), _: Usuario = Depends(solo_admin)):
    consulta = select(AuditLog).order_by(AuditLog.secuencia.desc()).limit(limite).offset(offset)
    if accion:
        consulta = consulta.where(AuditLog.accion == accion)
    filas = db.scalars(consulta)
    return [{"secuencia": f.secuencia, "usuario_id": str(f.usuario_id) if f.usuario_id else None, "accion": f.accion,
             "tabla_afectada": f.tabla_afectada, "registro_id": f.registro_id, "datos_previos": f.datos_previos_json,
             "datos_nuevos": f.datos_nuevos_json, "ip": f.ip_address, "timestamp": f.timestamp,
             "hash_registro": f.hash_registro} for f in filas]


@router.get("/auditoria/verificar")
def verificar_auditoria(db: Session = Depends(get_db), _: Usuario = Depends(solo_admin)):
    return auditoria.verificar_cadena(db)
