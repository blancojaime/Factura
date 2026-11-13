"""Programa Operativo Anual (POA): objetivos por programa presupuestario y Certificacion POA de una contratacion."""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import ReglaNegocioError
from ..models import ContratacionMenor, ObjetivoPOA, PartidaPresupuestaria

MIN_JUSTIFICACION_POA = 20


def normalizar_programa(valor) -> str:
    """'002' y '2' son el mismo programa; los codigos no numericos se comparan en mayusculas."""
    s = str(valor).strip()
    return str(int(s)) if s.isdigit() else s.upper()


def objetivos_por_programa(db: Session, gestion: int) -> dict[str, ObjetivoPOA]:
    return {normalizar_programa(o.programa): o for o in db.scalars(select(ObjetivoPOA).where(ObjetivoPOA.gestion == gestion))}


def programas_de_contratacion(db: Session, c: ContratacionMenor, gestion: int) -> list[dict]:
    """Programas presupuestarios (de las partidas de los items) con su objetivo POA y el monto que les corresponde."""
    objetivos = objetivos_por_programa(db, gestion)
    agrupado: dict[str, dict] = {}
    for item in c.items:
        partida = db.get(PartidaPresupuestaria, item.partida_id) if item.partida_id else None
        if partida is None:
            continue
        clave = normalizar_programa(partida.programa)
        g = agrupado.setdefault(clave, {"programa": partida.programa, "monto": Decimal("0"), "partidas": set(),
                                        "descripcion_apertura": partida.descripcion_apertura})
        g["monto"] += item.subtotal
        g["partidas"].add(partida.codigo_partida)
    resultado = []
    for clave, g in sorted(agrupado.items()):
        o = objetivos.get(clave)
        resultado.append({
            "programa": g["programa"], "monto": g["monto"], "partidas": sorted(g["partidas"]),
            "denominacion_programa": (o.denominacion_programa if o else "") or g["descripcion_apertura"],
            "codigo_objetivo": o.codigo_objetivo if o else None,
            "descripcion_objetivo": o.descripcion_objetivo if o else None,
            "objetivo_registrado": o is not None,
        })
    return resultado


def validar_certificacion(db: Session, c: ContratacionMenor, gestion: int, justificacion: str) -> list[dict]:
    errores: list[str] = []
    if len((justificacion or "").strip()) < MIN_JUSTIFICACION_POA:
        errores.append(f"Justifique cómo la contratación apoya el logro del objetivo del POA (mínimo {MIN_JUSTIFICACION_POA} caracteres)")
    programas = programas_de_contratacion(db, c, gestion)
    if not programas:
        errores.append("La contratación no tiene ítems con programa presupuestario")
    for p in programas:
        if not p["objetivo_registrado"]:
            errores.append(f"El programa {p['programa']} no tiene objetivo del POA registrado: regístrelo o impórtelo en el menú «Objetivos POA»")
    if errores:
        raise ReglaNegocioError("No se puede emitir la Certificación POA", "POA_INCOMPLETO", errores)
    return programas
