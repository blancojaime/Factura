"""Carga de datos de un periodo ya procesado para alimentar los 6 reportes."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (AsistenciaDia, Contrato, Empleado, Entidad, Horario, Liquidacion, Periodo, Permiso)
from .proceso import Calendario, ReglaNegocio, procesar_periodo, rango_mes

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]
ORDEN_MOD = {"PERMANENTE": 0, "EVENTUAL": 1, "CONSULTOR_LINEA": 2}
NOMBRE_MOD = {"PERMANENTE": "Personal Permanente", "EVENTUAL": "Personal Eventual",
              "CONSULTOR_LINEA": "Consultores Individuales de Línea"}
CAUSALES = {"RENUNCIA": "Renuncia", "CONCLUSION_CONTRATO": "Conclusión de contrato", "DESTITUCION": "Destitución",
            "JUBILACION": "Jubilación", "FALLECIMIENTO": "Fallecimiento", "RESCISION": "Rescisión de contrato",
            "OTRO": "Otro"}


@dataclass
class DatosPeriodo:
    anio: int
    mes: int
    ini: date
    fin: date
    entidad: Entidad
    periodo: Periodo | None
    horario: Horario
    cal: Calendario
    liquidaciones: list[Liquidacion]
    asistencia: dict[int, list[AsistenciaDia]] = field(default_factory=dict)
    permisos: list[Permiso] = field(default_factory=list)

    @property
    def titulo_periodo(self) -> str:
        return f"{MESES[self.mes - 1].capitalize()} {self.anio}"

    def dias_habiles(self) -> int:
        d, n = self.ini, 0
        while d <= self.fin:
            n += self.cal.laborable(d, self.horario.dias_laborables)
            d += timedelta(days=1)
        return n


def cargar(db: Session, anio: int, mes: int, usuario: str = "sistema") -> DatosPeriodo:
    """Datos del periodo para los reportes.

    Un periodo ABIERTO se recalcula SIEMPRE antes de generar el reporte (así nunca salen planillas vacías o desactualizadas
    por haber importado personal, marcas o permisos después de 'Procesar'). Un periodo CERRADO usa lo congelado."""
    ini, fin = rango_mes(anio, mes)
    per = db.get(Periodo, (anio, mes))
    if not per or per.estado != "CERRADO":
        procesar_periodo(db, anio, mes, usuario, auditar=False)
        db.commit()
        per = db.get(Periodo, (anio, mes))
    n = db.scalar(select(func.count(Liquidacion.id)).where(Liquidacion.anio == anio, Liquidacion.mes == mes))
    if not n:
        raise ReglaNegocio(f"No hay personal con contrato vigente en {mes:02d}/{anio}. Verifique en «Personal» que los contratos "
                           f"tengan fecha de ingreso anterior o dentro del mes y que no estén dados de baja antes del mes.")
    ent = db.get(Entidad, 1)
    h = db.execute(select(Horario).where(Horario.es_defecto == True)).scalars().first()  # noqa: E712
    liqs = db.execute(select(Liquidacion).where(Liquidacion.anio == anio, Liquidacion.mes == mes)).scalars().unique().all()
    liqs.sort(key=lambda l: (ORDEN_MOD[l.modalidad], l.empleado.apellidos.lower(), l.empleado.nombres.lower()))
    asis: dict[int, list[AsistenciaDia]] = {}
    for a in db.execute(select(AsistenciaDia).where(AsistenciaDia.fecha.between(ini, fin))
                        .order_by(AsistenciaDia.fecha)).scalars().unique():
        asis.setdefault(a.empleado_id, []).append(a)
    perms = db.execute(select(Permiso).where(Permiso.estado == "APROBADO", Permiso.fecha_desde <= fin,
                                             Permiso.fecha_hasta >= ini)
                       .order_by(Permiso.fecha_desde)).scalars().unique().all()
    return DatosPeriodo(anio, mes, ini, fin, ent, per, h, Calendario(db, ini, fin), liqs, asis, perms)


def baja_info(c: Contrato, ini: date, fin: date):
    """(fecha_efectiva, causal) si el contrato termina dentro del periodo, si no None."""
    if c.fecha_baja and ini <= c.fecha_baja <= fin:
        return c.fecha_baja, CAUSALES.get(c.causal_baja, c.causal_baja or "Otro")
    if not c.fecha_baja and c.fecha_fin and ini <= c.fecha_fin <= fin:
        return c.fecha_fin, CAUSALES["CONCLUSION_CONTRATO"]
    return None


def es_alta(c: Contrato, ini: date, fin: date) -> bool:
    return ini <= c.fecha_inicio <= fin


def filtrar_liq(datos: DatosPeriodo, tipo: str) -> list[Liquidacion]:
    out = []
    for l in datos.liquidaciones:
        c = l.contrato
        if tipo == "ALTAS" and es_alta(c, datos.ini, datos.fin):
            out.append(l)
        elif tipo == "BAJAS" and baja_info(c, datos.ini, datos.fin):
            out.append(l)
    return out
