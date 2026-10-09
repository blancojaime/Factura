"""Datos de prueba (usuarios, catalogo UNSPSC/CHB de ejemplo y presupuesto inicial).

Fuente unica: la usan las pruebas (via ORM) y `scripts/make_seeds.py` (que genera db/seeds.sql).
TODOS los datos son FICTICIOS / ilustrativos: reemplacelos con los reales antes de operar.
"""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import security
from .enums import Rol
from .models import CatalogoCHB, ParametroInstitucional, PartidaPresupuestaria, Usuario
from .services import parametros

PASSWORD_DEMO = "Sicom#2026Demo"
NS = uuid.UUID("6f1c2b0e-0000-4000-8000-5a1c0b00d3e0")


def _id(nombre: str) -> uuid.UUID:
    return uuid.uuid5(NS, nombre)


USUARIOS = [
    ("solicitante", "María Lidia Quispe Mamani", "Jefa de Unidad de Obras", Rol.SOLICITANTE, "solicitante@gam.local"),
    ("presupuesto", "Juan Carlos Mendoza Rojas", "Responsable de Presupuesto", Rol.PRESUPUESTO, "presupuesto@gam.local"),
    ("contrataciones", "Rosario Elena Vargas Choque", "Encargada de Compras Menores", Rol.CONTRATACIONES, "compras@gam.local"),
    ("rpa", "Ing. Fernando Luis Condori Apaza", "Responsable del Proceso de Contratación", Rol.RPA, "rpa@gam.local"),
    ("recepcion", "Pedro Pablo Mamani Flores", "Responsable de Recepción y Almacenes", Rol.RECEPCION, "almacen@gam.local"),
    ("admin", "Administrador del Sistema", "Administrador", Rol.ADMIN, "admin@gam.local"),
]

# (codigo, descripcion, saldo, programa, proyecto, actividad, fuente, organismo) - codigos ilustrativos
PARTIDAS = [
    ("39500", "Útiles de escritorio y oficina", Decimal("30000.00")),
    ("34200", "Productos minerales y no metálicos (materiales de construcción)", Decimal("80000.00")),
    ("25800", "Mantenimiento y reparación de inmuebles y equipos", Decimal("45000.00")),
    ("43100", "Equipo de oficina y muebles", Decimal("60000.00")),
]
ESTRUCTURA = {"programa": "01", "proyecto": "0000", "actividad": "001", "fuente": "20", "organismo": "230"}

# (codigo_unspsc, descripcion, unidad, precio_referencial) - catalogo CHB de EJEMPLO
CATALOGO = [
    ("30111505", "Cemento portland IP-30 (bolsa de 50 kg)", "Bolsa", Decimal("58.00")),
    ("30131501", "Ladrillo cerámico de 6 huecos", "Unidad", Decimal("1.20")),
    ("14111507", "Papel bond tamaño carta 75 g", "Resma", Decimal("32.00")),
    ("43211500", "Computadora de escritorio", "Unidad", Decimal("5200.00")),
    ("56101500", "Escritorio metálico de oficina", "Unidad", Decimal("850.00")),
]


def cargar(db: Session, gestion: int | None = None, password: str = PASSWORD_DEMO, hash_cache: str | None = None) -> None:
    """Inserta (idempotente) los datos de prueba."""
    gestion = gestion or date.today().year
    h = hash_cache or security.hash_password(password)
    for username, nombre, cargo, rol, email in USUARIOS:
        if db.scalar(select(Usuario).where(Usuario.username == username)) is None:
            db.add(Usuario(id=_id(f"usuario:{username}"), username=username, password_hash=h, nombre_completo=nombre,
                           cargo=cargo, rol=rol.value, email=email))
    for clave, (valor, desc) in parametros.DEFAULTS.items():
        if db.get(ParametroInstitucional, clave) is None:
            v = str(gestion) if clave == "gestion" else valor
            db.add(ParametroInstitucional(clave=clave, valor=v, descripcion=desc))
    for codigo, desc, saldo in PARTIDAS:
        existe = db.scalar(select(PartidaPresupuestaria).where(
            PartidaPresupuestaria.codigo_partida == codigo, PartidaPresupuestaria.gestion == gestion))
        if existe is None:
            db.add(PartidaPresupuestaria(id=_id(f"partida:{codigo}:{gestion}"), codigo_partida=codigo, descripcion=desc,
                                         saldo_disponible=saldo, monto_aprobado=saldo, gestion=gestion, **ESTRUCTURA))
    for codigo, desc, unidad, precio in CATALOGO:
        if db.scalar(select(CatalogoCHB).where(CatalogoCHB.codigo_unspsc == codigo)) is None:
            db.add(CatalogoCHB(id=_id(f"chb:{codigo}"), codigo_unspsc=codigo, descripcion_bien=desc, unidad_medida=unidad,
                               precio_referencial_nacional=precio, activo=True))
    db.flush()
