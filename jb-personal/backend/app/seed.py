"""Datos iniciales: parámetros, horario oficial, escalas, tipos de permiso y feriados nacionales."""
from __future__ import annotations

from datetime import date, time, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Entidad, EscalaSancion, Feriado, Horario, PermisoTipo, Turno


def pascua(y: int) -> date:
    """Domingo de Pascua (algoritmo gregoriano anónimo)."""
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return date(y, mes, dia)


def feriados_nacionales(y: int) -> list[tuple[date, str]]:
    p = pascua(y)
    return sorted([
        (date(y, 1, 1), "Año Nuevo"),
        (date(y, 1, 22), "Día del Estado Plurinacional"),
        (p - timedelta(days=48), "Lunes de Carnaval (asueto por decreto)"),
        (p - timedelta(days=47), "Martes de Carnaval (asueto por decreto)"),
        (p - timedelta(days=2), "Viernes Santo"),
        (date(y, 5, 1), "Día del Trabajo"),
        (p + timedelta(days=60), "Corpus Christi"),
        (date(y, 6, 21), "Año Nuevo Andino Amazónico"),
        (date(y, 8, 6), "Día de la Patria"),
        (date(y, 11, 2), "Día de Todos los Santos / Difuntos"),
        (date(y, 12, 25), "Navidad"),
    ])


TIPOS = [  # codigo, nombre, categoria, con_goce, max_dias, base_legal
    ("PARTICULAR_CGH", "Permiso particular con goce de haberes", "PERMISO", True, None, "RIP"),
    ("PARTICULAR_SGH", "Permiso particular sin goce de haberes", "PERMISO", False, None, "RIP"),
    ("COMISION_OFICIAL", "Comisión oficial", "COMISION", True, None, "RIP"),
    ("LIC_MEDICA", "Licencia médica / baja médica (CNS)", "LICENCIA", True, None, "Certificado de incapacidad CNS"),
    ("DUELO", "Licencia por duelo (luto)", "LICENCIA", True, None, "RIP"),
    ("MATRIMONIO", "Licencia por matrimonio", "LICENCIA", True, None, "RIP"),
    ("CUMPLEANOS", "Permiso por cumpleaños", "LICENCIA", True, None, "RIP"),
    ("LACTANCIA", "Permiso por lactancia materna", "LICENCIA", True, None, "Normativa de lactancia materna"),
    ("PATERNIDAD", "Licencia por paternidad", "LICENCIA", True, Decimal("3"), "D.S. N° 1212"),
    ("EXAMEN_PREVENTIVO", "Examen preventivo (Papanicolaou / mamografía / próstata)", "LICENCIA", True, Decimal("1"),
     "Ley N° 252 / Ley N° 798"),
    ("VACACION", "Vacación", "VACACION", True, None, "Art. 49 Ley N° 2027"),
    ("OLVIDO_MARCACION", "Regularización por omisión de marcación", "PERMISO", True, None, "RIP"),
]

ESCALA_MINUTOS = [  # desde, hasta, dias, sanción  (31-45 y siguientes según el informe tipo del GAM)
    (0, 30, "0", "Sin sanción"),
    (31, 60, "0", "Amonestación escrita"),
    (61, 90, "0.5", "Descuento 0.5 día de haber"),
    (91, 120, "1", "Descuento 1.0 día de haber"),
    (121, None, "2", "Descuento 2.0 días de haber + llamada de atención severa"),
]
ESCALA_CANTIDAD = [  # ejemplo de la especificación: 1 a 3 retrasos = amonestación; 4 o más = descuentos
    (0, 0, "0", "Sin sanción"),
    (1, 3, "0", "Amonestación / tolerancia"),
    (4, 6, "0.5", "Descuento 0.5 día de haber"),
    (7, None, "1", "Descuento 1.0 día de haber"),
]


def seed_defaults(s: Session) -> None:
    if not s.get(Entidad, 1):
        s.add(Entidad(id=1))
    if not s.execute(select(Horario)).first():
        h = Horario(nombre="Jornada discontinua oficial", es_defecto=True, tolerancia_min=10, umbral_grave_min=30)
        h.turnos = [Turno(orden=1, nombre="Mañana", hora_entrada=time(8, 0), hora_salida=time(12, 0)),
                    Turno(orden=2, nombre="Tarde", hora_entrada=time(14, 30), hora_salida=time(18, 30))]
        s.add(h)
    if not s.execute(select(EscalaSancion)).first():
        for modo, filas in (("MINUTOS", ESCALA_MINUTOS), ("CANTIDAD", ESCALA_CANTIDAD)):
            for d, h_, dias, txt in filas:
                s.add(EscalaSancion(modo=modo, desde=d, hasta=h_, dias_descuento=Decimal(dias), sancion=txt))
    existentes = {t.codigo for t in s.execute(select(PermisoTipo)).scalars()}
    for cod, nom, cat, goce, mx, base in TIPOS:
        if cod not in existentes:
            s.add(PermisoTipo(codigo=cod, nombre=nom, categoria=cat, con_goce=goce, max_dias=mx, base_legal=base))
    if not s.execute(select(Feriado)).first():
        for y in range(2026, 2031):
            for f, d in feriados_nacionales(y):
                s.add(Feriado(fecha=f, descripcion=d))
