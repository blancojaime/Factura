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
from .models import CatalogoCHB, ObjetivoPOA, ParametroInstitucional, PartidaPresupuestaria, Usuario
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
MAE_DEMO = {"mae_nombre": "Lic. Carlos Alberto Rojas Mamani", "mae_cargo": "Alcalde Municipal"}

# Programas del POA y su objetivo de gestion (relacion programa presupuestario - objetivo; objetivos de EJEMPLO)
PROGRAMAS_POA = [
    ("0", "FUNCIONAMIENTO ÓRGANO EJECUTIVO"), ("1", "FUNCIONAMIENTO ÓRGANO DELIBERATIVO"), ("002", "ADMINISTRACIÓN CENTRAL"),
    ("100", "PROMOCIÓN Y FOMENTO A LA PRODUCCIÓN AGROPECUARIA"), ("110", "SANEAMIENTO BÁSICO"),
    ("120", "CONSTRUCCIÓN Y MANTENIMIENTO DE RIEGO Y/O MICRORIEGO"), ("130", "DESARROLLO Y PRESERVACIÓN DEL MEDIO AMBIENTE"),
    ("140", "ASEO URBANO, MANEJO Y TRATAMIENTO DE RESIDUOS SÓLIDOS"), ("150", "FUENTES DE ENERGÍA Y APOYO A LA ELECTRIFICACIÓN"),
    ("160", "SERVICIO DE ALUMBRADO PÚBLICO"), ("170", "INFRAESTRUCTURA URBANA Y RURAL"), ("180", "GESTIÓN DE CAMINOS VECINALES"),
    ("190", "SERVICIO DE CATASTRO URBANO Y RURAL"), ("200", "GESTIÓN DE SALUD"), ("210", "GESTIÓN DE EDUCACIÓN"),
    ("220", "DESARROLLO Y PROMOCIÓN DEL DEPORTE"), ("230", "PROMOCIÓN Y CONSERVACIÓN DE CULTURA Y PATRIMONIO"),
    ("240", "DESARROLLO Y FOMENTO DEL TURISMO"), ("250", "PROMOCIÓN Y POLÍTICAS PARA GRUPOS VULNERABLES Y DE LA MUJER"),
    ("251", "PREVENCIÓN CONTRA LA VIOLENCIA HACIA LA MUJER"), ("260", "DEFENSA Y PROTECCIÓN DE LA NIÑEZ Y ADOLESCENCIA"),
    ("270", "VIALIDAD Y TRANSPORTE PÚBLICO"), ("280", "DEFENSA DEL CONSUMIDOR"), ("290", "SERVICIO DE FAENADO DE GANADO"),
    ("300", "SERVICIO DE INHUMACIÓN, EXHUMACIÓN, CREMACIÓN Y TRASLADO DE RESTOS"), ("310", "GESTIÓN DE RIESGOS"),
    ("320", "RECURSOS HÍDRICOS"), ("330", "SERVICIOS DE SEGURIDAD CIUDADANA"), ("340", "FORTALECIMIENTO INSTITUCIONAL"),
    ("350", "FOMENTO AL DESARROLLO ECONOMICO LOCAL Y PROMOCION DEL EMPLEO"), ("360", "OTROS PROGRAMAS ESPECÍFICOS"),
    ("97", "PARTIDAS NO ASIGNABLES A PROGRAMAS – ACTIVOS FINANCIEROS (Grupo 50000 y otras previsiones)"),
    ("98", "PARTIDAS NO ASIGNABLES A PROGRAMAS – TRANSFERENCIAS (Grupo 70000)"),
    ("99", "PARTIDAS NO ASIGNABLES A PROGRAMAS – DEUDAS (Grupo 60000)"),
]
ESTRUCTURA = {"descripcion_apertura": "FUNCIONAMIENTO ÓRGANO DELIBERATIVO - Gestión administrativa", "programa": "01", "proyecto": "0000", "actividad": "001", "fuente": "20", "organismo": "230"}

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
            v = str(gestion) if clave == "gestion" else MAE_DEMO.get(clave, valor)
            db.add(ParametroInstitucional(clave=clave, valor=v, descripcion=desc))
    for n, (prog, denominacion) in enumerate(PROGRAMAS_POA, start=1):
        if db.scalar(select(ObjetivoPOA).where(ObjetivoPOA.gestion == gestion, ObjetivoPOA.programa == prog)) is None:
            db.add(ObjetivoPOA(id=_id(f"poa:{gestion}:{prog}"), gestion=gestion, programa=prog, denominacion_programa=denominacion,
                               codigo_objetivo=f"OBJ{n}", descripcion_objetivo=f"OBJETIVO {n}"))
    for codigo, desc, saldo in PARTIDAS:
        existe = db.scalar(select(PartidaPresupuestaria).where(
            PartidaPresupuestaria.codigo_partida == codigo, PartidaPresupuestaria.gestion == gestion))
        if existe is not None and not existe.descripcion_apertura:
            existe.descripcion_apertura = ESTRUCTURA["descripcion_apertura"]  # bases creadas antes de la importacion
        if existe is None:
            db.add(PartidaPresupuestaria(id=_id(f"partida:{codigo}:{gestion}"), codigo_partida=codigo, descripcion=desc,
                                         saldo_disponible=saldo, monto_aprobado=saldo, gestion=gestion, **ESTRUCTURA))
    for codigo, desc, unidad, precio in CATALOGO:
        if db.scalar(select(CatalogoCHB).where(CatalogoCHB.codigo_unspsc == codigo)) is None:
            db.add(CatalogoCHB(id=_id(f"chb:{codigo}"), codigo_unspsc=codigo, descripcion_bien=desc, unidad_medida=unidad,
                               precio_referencial_nacional=precio, activo=True))
    db.flush()


if __name__ == "__main__":  # python -m app.seeds  (idempotente)
    from app.database import SessionLocal, preparar_sqlite

    preparar_sqlite()
    with SessionLocal() as _db:
        cargar(_db)
        _db.commit()
    print("Datos demo cargados (usuarios, partidas, catalogo CHB, parametros).")
