"""Pre-compromiso presupuestario (preventivo): descuento, liberacion y devengado de saldos."""
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..enums import EstadoPreventivo
from ..errors import ReglaNegocioError
from ..models import ContratacionItem, ContratacionMenor, PartidaPresupuestaria, PreventivoC31

CENT = Decimal("0.01")


def importes_por_partida(items: list[ContratacionItem]) -> dict:
    acum: dict = defaultdict(lambda: Decimal("0"))
    for it in items:
        acum[it.partida_id] += Decimal(it.subtotal)
    return acum


def validar_partidas_items(db: Session, items: list[ContratacionItem], gestion: int) -> list[str]:
    errores = []
    for it in items:
        if it.partida_id is None:
            errores.append(f"Ítem {it.numero}: falta seleccionar la partida presupuestaria")
            continue
        p = db.get(PartidaPresupuestaria, it.partida_id)
        if p is None:
            errores.append(f"Ítem {it.numero}: la partida no existe")
        elif p.gestion != gestion:
            errores.append(f"Ítem {it.numero}: la partida {p.codigo_partida} no pertenece a la gestión {gestion}")
        elif p.codigo_partida != it.partida_gasto:
            errores.append(f"Ítem {it.numero}: la partida elegida no coincide con el código {it.partida_gasto}")
    return errores


def certificar(db: Session, c: ContratacionMenor) -> list[PreventivoC31]:
    """Descuenta preventivamente el saldo de cada partida. Todo o nada."""
    requerido = importes_por_partida(c.items)
    partidas = {pid: db.scalar(select(PartidaPresupuestaria).where(PartidaPresupuestaria.id == pid).with_for_update())
                for pid in requerido}
    faltantes = []
    for pid, imp in requerido.items():
        p = partidas[pid]
        if imp > Decimal(p.saldo_disponible):
            faltantes.append(
                f"Partida {p.codigo_partida} ({p.descripcion}): saldo Bs {Decimal(p.saldo_disponible):,.2f}, "
                f"requerido Bs {imp:,.2f}")
    if faltantes:
        raise ReglaNegocioError("Saldo presupuestario insuficiente: devuelva la solicitud o gestione una "
                                "modificación presupuestaria", codigo="SALDO_INSUFICIENTE", errores=faltantes)
    creados = []
    for pid, imp in requerido.items():
        p = partidas[pid]
        p.saldo_disponible = Decimal(p.saldo_disponible) - imp
        prev = PreventivoC31(contratacion_id=c.id, partida_id=pid, importe=imp)
        db.add(prev)
        creados.append(prev)
    db.flush()
    return creados


def liberar(db: Session, c: ContratacionMenor) -> Decimal:
    """Devuelve a las partidas el saldo de los preventivos activos (anulacion / desierto)."""
    total = Decimal("0")
    for prev in c.preventivos:
        if prev.estado == EstadoPreventivo.ACTIVO.value:
            p = db.scalar(select(PartidaPresupuestaria).where(PartidaPresupuestaria.id == prev.partida_id).with_for_update())
            p.saldo_disponible = Decimal(p.saldo_disponible) + Decimal(prev.importe)
            prev.estado = EstadoPreventivo.LIBERADO.value
            total += Decimal(prev.importe)
    db.flush()
    return total


def devengar(db: Session, c: ContratacionMenor, monto_adjudicado: Decimal) -> Decimal:
    """Registra el devengado por el monto adjudicado y libera la diferencia con lo reservado.

    La diferencia (reservado - adjudicado) se reparte proporcionalmente entre las partidas;
    la ultima absorbe el redondeo. Devuelve el monto liberado.
    """
    activos = [p for p in c.preventivos if p.estado == EstadoPreventivo.ACTIVO.value]
    total_reservado = sum((Decimal(p.importe) for p in activos), Decimal("0"))
    monto = Decimal(monto_adjudicado)
    if monto > total_reservado:
        raise ReglaNegocioError("El monto adjudicado excede lo reservado en el preventivo",
                                codigo="DEVENGADO_EXCEDE_RESERVA")
    diferencia = total_reservado - monto
    liberado = Decimal("0")
    for i, prev in enumerate(activos):
        if i == len(activos) - 1:
            parte = diferencia - liberado
        else:
            parte = (diferencia * Decimal(prev.importe) / total_reservado).quantize(CENT, rounding=ROUND_HALF_UP)
        parte = max(Decimal("0"), min(parte, Decimal(prev.importe) - CENT))
        if parte > 0:
            p = db.scalar(select(PartidaPresupuestaria).where(PartidaPresupuestaria.id == prev.partida_id).with_for_update())
            p.saldo_disponible = Decimal(p.saldo_disponible) + parte
            prev.importe = Decimal(prev.importe) - parte
            liberado += parte
        prev.estado = EstadoPreventivo.DEVENGADO.value
    db.flush()
    return liberado
