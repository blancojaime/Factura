"""Motor de control de asistencia (funciones PURAS, sin base de datos => verificables por auditoría).

Conceptos
---------
* Las marcas del día se asignan a los "slots" del horario (entrada/salida de cada turno) por proximidad:
  los límites entre slots son los puntos medios entre horas oficiales consecutivas. Así no se depende de
  la etiqueta Entrada/Salida del reloj (que suele ser poco fiable).
* Se trabaja en minutos (los segundos se descartan: 08:10:50 cuenta como 08:10).
* Una justificación (permiso/licencia/comisión/vacación aprobada) cubre un intervalo del día; el minuto
  cubierto no es retraso, y un turno sin marcas totalmente cubierto es falta JUSTIFICADA.
* Un turno sin marcas y no cubierto por completo es falta INJUSTIFICADA (fracción = duración del turno /
  duración total de la jornada, p.ej. 0,5 con dos turnos iguales).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from decimal import ROUND_HALF_UP, Decimal

D0 = Decimal("0")
D1 = Decimal("1")

# estados diarios
NORMAL = "NORMAL"
RETRASO_LEVE = "RETRASO_LEVE"
RETRASO_GRAVE = "RETRASO_GRAVE"
FALTA_INJUSTIFICADA = "FALTA_INJUSTIFICADA"
FALTA_JUSTIFICADA = "FALTA_JUSTIFICADA"
OMISION = "OMISION_MARCACION"
NO_LABORABLE = "NO_LABORABLE"
FERIADO = "FERIADO"


def minutos(t: time) -> int:
    return t.hour * 60 + t.minute


def hhmm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


@dataclass(frozen=True)
class TurnoDef:
    nombre: str
    entrada: int   # minuto del día
    salida: int


@dataclass(frozen=True)
class Reglas:
    turnos: tuple[TurnoDef, ...]
    tolerancia: int = 10
    umbral_grave: int = 30
    tolerancia_cuenta_total: bool = True   # True: superada la tolerancia se cuenta TODO el retraso desde la hora oficial
    contar_salida_anticipada: bool = False


@dataclass(frozen=True)
class Justif:
    desde: int            # minuto del día (0 = inicio)
    hasta: int            # 1440 = fin de día
    categoria: str
    con_goce: bool
    permiso_id: int | None = None


@dataclass
class ResDia:
    estado: str
    marcas: list[int] = field(default_factory=list)
    min_retraso: int = 0
    nro_retrasos: int = 0
    min_salida_anticipada: int = 0
    falta: Decimal = D0
    justificado: Decimal = D0
    justificado_sin_goce: Decimal = D0
    parcial: Decimal = D0                 # fracción de día cubierta por permisos POR HORAS (turnos con asistencia)
    parcial_sin_goce: Decimal = D0        # idem, solo permisos sin goce de haberes (descuentan)
    categoria: str = ""
    permiso_id: int | None = None
    observaciones: list[str] = field(default_factory=list)

    @property
    def marcas_txt(self) -> str:
        return " ".join(hhmm(m) for m in self.marcas)


def _q(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def pesos_turnos(turnos) -> list[Decimal]:
    total = sum(t.salida - t.entrada for t in turnos)
    pesos, acum = [], D0
    for i, t in enumerate(turnos):
        w = D1 - acum if i == len(turnos) - 1 else _q(Decimal(t.salida - t.entrada) / Decimal(total))
        pesos.append(w)
        acum += w
    return pesos


def _union(ints: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for a, b in sorted(i for i in ints if i[1] > i[0]):
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def _cubierto(a: int, b: int, justifs) -> int:
    """Minutos de [a,b) cubiertos por la unión de las justificaciones."""
    if b <= a:
        return 0
    tot = 0
    for x, y in _union([(j.desde, j.hasta) for j in justifs]):
        tot += max(0, min(b, y) - max(a, x))
    return tot


MIN_ENTRE_MARCAS = 5   # marcas a menos de 5 min de la anterior se consideran doble pulsación


def depurar_marcas(marcas: list[int]) -> list[int]:
    out: list[int] = []
    for m in sorted(set(marcas)):
        if not out or m - out[-1] >= MIN_ENTRE_MARCAS:
            out.append(m)
    return out


def _cubierto_sg(a: int, b: int, justifs) -> int:
    return _cubierto(a, b, [j for j in justifs if not j.con_goce])


def asignar_marcas(turnos, marcas: list[int], justifs=(), tolerancia: int = 0):
    """Asigna las marcas a (entrada, salida) de cada turno.

    Región de un turno = desde el punto medio entre la salida del turno anterior y su entrada, hasta el punto medio
    entre su salida y la entrada del siguiente. En la región: 2 o más marcas => primera = entrada, última = salida;
    una sola marca => es ENTRADA si cae antes de la mitad del turno o si el lapso desde la hora oficial hasta la
    marca está cubierto por un permiso (llegada tardía autorizada); en otro caso es SALIDA (falta la entrada)."""
    res = []
    n = len(turnos)
    for i, t in enumerate(turnos):
        lo = (turnos[i - 1].salida + t.entrada) / 2 if i > 0 else -1
        hi = (t.salida + turnos[i + 1].entrada) / 2 if i < n - 1 else 10 ** 6
        reg = [m for m in marcas if lo <= m < hi]
        if len(reg) >= 2:
            res.append((reg[0], reg[-1]))
        elif len(reg) == 1:
            m = reg[0]
            medio = (t.entrada + t.salida) / 2
            cubierta = m > t.entrada and _cubierto(t.entrada, m, justifs) >= (m - t.entrada) - tolerancia
            res.append((m, None) if (m <= medio or cubierta) else (None, m))
        else:
            res.append((None, None))
    return res


def evaluar_dia(reglas: Reglas, marcas: list[int], justifs: list[Justif], laborable: bool,
                feriado: bool = False) -> ResDia:
    marcas = depurar_marcas(marcas)
    if not laborable:
        r = ResDia(FERIADO if feriado else NO_LABORABLE, marcas)
        if marcas:
            r.observaciones.append("Marcas en día no laborable (no computan)")
        return r

    turnos = reglas.turnos
    pesos = pesos_turnos(turnos)
    total_min = sum(x.salida - x.entrada for x in turnos)
    asign = asignar_marcas(turnos, marcas, justifs, reglas.tolerancia)
    r = ResDia(NORMAL, marcas)
    grave = False
    cubiertos: list[tuple[Justif, Decimal]] = []
    for t, w, (ent, sal) in zip(turnos, pesos, asign):
        if ent is None and sal is None:
            if _cubierto(t.entrada, t.salida, justifs) >= t.salida - t.entrada:
                j = max(justifs, key=lambda j: max(0, min(t.salida, j.hasta) - max(t.entrada, j.desde)))
                cubiertos.append((j, w))
                r.justificado += w
                if not j.con_goce:
                    r.justificado_sin_goce += w
            else:
                r.falta += w
                r.observaciones.append(f"Sin marcas en turno {t.nombre}")
            continue
        if ent is not None:
            late = max(0, ent - t.entrada) - _cubierto(t.entrada, max(ent, t.entrada), justifs)
            late = max(0, late)
            if late > reglas.tolerancia:
                contado = late if reglas.tolerancia_cuenta_total else late - reglas.tolerancia
                r.min_retraso += contado
                r.nro_retrasos += 1
                grave = grave or contado > reglas.umbral_grave
        else:
            r.observaciones.append(f"Omisión de marca de entrada ({t.nombre})")
        if sal is not None:
            early = max(0, t.salida - sal) - _cubierto(min(sal, t.salida), t.salida, justifs)
            r.min_salida_anticipada += max(0, early)
            if early > reglas.tolerancia:
                r.observaciones.append(f"Salida anticipada {early} min ({t.nombre})")
        else:
            r.observaciones.append(f"Omisión de marca de salida ({t.nombre})")
        # permiso POR HORAS dentro de un turno con asistencia: las horas cubiertas no se trabajaron
        # (si el permiso cubre el turno completo y la persona asistió, prevalece la asistencia)
        dur = t.salida - t.entrada
        cub, cub_sg = _cubierto(t.entrada, t.salida, justifs), _cubierto_sg(t.entrada, t.salida, justifs)
        if 0 < cub < dur:
            r.parcial += Decimal(cub) / Decimal(total_min)
            r.parcial_sin_goce += Decimal(cub_sg) / Decimal(total_min)

    if cubiertos:
        j = max(cubiertos, key=lambda c: c[1])[0]
        r.categoria, r.permiso_id = j.categoria, j.permiso_id
    r.parcial, r.parcial_sin_goce = _q(r.parcial), _q(r.parcial_sin_goce)
    omision = any(o.startswith("Omisión") for o in r.observaciones)
    if r.falta > 0:
        r.estado = FALTA_INJUSTIFICADA
    elif r.justificado > 0:
        r.estado = FALTA_JUSTIFICADA
    elif r.min_retraso > 0:
        r.estado = RETRASO_GRAVE if grave else RETRASO_LEVE
    elif omision:
        r.estado = OMISION
    return r


# ----------------------------------------------------------------------------- mensual
@dataclass
class FilaEscala:
    desde: int
    hasta: int | None
    dias: Decimal
    sancion: str


@dataclass
class ParamsCalculo:
    escala_modo: str = "MINUTOS"
    escala: tuple = ()
    factor_falta_planta: Decimal = Decimal("2")
    factor_falta_consultor: Decimal = D1
    max_justificados_consultor: Decimal = D1
    contar_salida_anticipada: bool = False
    tasa_afp: Decimal = Decimal("0.1271")
    tasa_patronal: Decimal = Decimal("0.1721")
    dias_mes: int = 30


@dataclass
class ContratoCalc:
    modalidad: str
    haber: Decimal
    bono: Decimal = D0
    rc_iva: Decimal = D0
    aplica_aporte: bool = True
    tasa_afp: Decimal | None = None
    tasa_patronal: Decimal | None = None


@dataclass
class ResMes:
    dias_laborables: Decimal
    dias_asistidos: Decimal
    faltas: Decimal
    min_retraso: int
    nro_retrasos: int
    dias_justificados: Decimal
    dias_trabajados: Decimal
    bono: Decimal
    total_ganado: Decimal
    aporte_laboral: Decimal
    aporte_patronal: Decimal
    rc_iva: Decimal
    dias_desc_faltas: Decimal
    dias_desc_atrasos: Decimal
    dias_desc_sin_goce: Decimal
    dias_desc_exceso: Decimal
    desc_faltas: Decimal
    desc_atrasos: Decimal
    desc_otros: Decimal
    dias_descuento: Decimal
    desc_asistencia: Decimal
    total_descuentos: Decimal
    liquido: Decimal
    sancion: str
    observaciones: list[str]
    multas: Decimal = D0                  # multas / descuentos adicionales aplicados (manuales)
    horas_permiso: Decimal = D0           # días-equivalentes por permisos por horas


def buscar_escala(escala, valor: int) -> FilaEscala | None:
    for f in escala:
        if f.desde <= valor and (f.hasta is None or valor <= f.hasta):
            return f
    return None


def dias_comerciales(inicio, fin, mes_ini, mes_fin, dias_mes: int = 30) -> Decimal:
    """Días trabajados en base comercial de 30 días (como en la planilla: haber/30*días)."""
    a = 1 if inicio <= mes_ini else min(inicio.day, dias_mes)
    b = dias_mes if fin >= mes_fin else min(fin.day, dias_mes)
    return Decimal(max(0, b - a + 1))


def liquidar_mes(c: ContratoCalc, dias: list[ResDia], p: ParamsCalculo, dias_trab: Decimal, multas: Decimal = D0) -> ResMes:
    es_cons = c.modalidad == "CONSULTOR_LINEA"
    lab = [d for d in dias if d.estado not in (NO_LABORABLE, FERIADO)]
    faltas = sum((d.falta for d in lab), D0)
    justif = sum((d.justificado for d in lab), D0)
    sin_goce = sum((d.justificado_sin_goce for d in lab), D0)
    parc = sum((d.parcial for d in lab), D0)
    parc_sg = sum((d.parcial_sin_goce for d in lab), D0)
    minutos_ = sum(d.min_retraso for d in lab)
    if p.contar_salida_anticipada:
        minutos_ += sum(d.min_salida_anticipada for d in lab)
    nro = sum(d.nro_retrasos for d in lab)
    obs: list[str] = []

    valor = minutos_ if p.escala_modo == "MINUTOS" else nro
    fila = buscar_escala(p.escala, valor) if valor > 0 else None
    d_atr = fila.dias if fila else D0
    sancion = fila.sancion if fila and (fila.dias > 0 or "monest" in fila.sancion or "llamada" in fila.sancion) else ""

    factor = p.factor_falta_consultor if es_cons else p.factor_falta_planta
    d_falt = faltas * factor
    d_sg, d_exc = D0, D0
    if es_cons:
        d_exc = max(D0, justif + parc - p.max_justificados_consultor)
        if d_exc > 0:
            obs.append(f"Consultor: {justif + parc} día(s) justificado(s); excede el máximo contractual de "
                       f"{p.max_justificados_consultor} día(s)/mes")
    else:
        d_sg = sin_goce + parc_sg
    dias_desc = d_falt + d_atr + d_sg + d_exc

    dia_valor = c.haber / Decimal(p.dias_mes)
    desc_f, desc_a = _q(dia_valor * d_falt), _q(dia_valor * d_atr)
    desc_o = _q(dia_valor * (d_sg + d_exc))

    bono = _q(c.bono / Decimal(p.dias_mes) * dias_trab) if c.bono else D0
    ganado = _q(c.haber / Decimal(p.dias_mes) * dias_trab) + bono
    desc_asis = desc_f + desc_a + desc_o
    if desc_asis > ganado:
        desc_asis = ganado
        obs.append("Descuento por asistencia limitado al total ganado")
    tasa = c.tasa_afp if c.tasa_afp is not None else p.tasa_afp
    tasa_p = c.tasa_patronal if c.tasa_patronal is not None else p.tasa_patronal
    aporte = _q(ganado * tasa) if c.aplica_aporte else D0
    patronal = _q(ganado * tasa_p) if c.aplica_aporte else D0
    # multas / descuentos adicionales: no pueden dejar el líquido en negativo
    tope = max(D0, ganado - desc_asis - aporte - c.rc_iva)
    multas_ap = min(_q(multas), tope)
    if multas_ap < _q(multas):
        obs.append(f"Multas/descuentos limitados a {multas_ap} para no dejar líquido negativo (solicitado {_q(multas)})")
    total_desc = aporte + c.rc_iva + desc_asis + multas_ap
    asist = max(D0, Decimal(len(lab)) - faltas - justif)
    return ResMes(Decimal(len(lab)), asist, faltas, minutos_, nro, justif, dias_trab, bono, ganado, aporte, patronal,
                  c.rc_iva, d_falt, d_atr, d_sg, d_exc, desc_f, desc_a, desc_o, dias_desc, desc_asis, total_desc,
                  ganado - total_desc, sancion, obs, multas_ap, parc)


def detectar_abandono(fechas_falta: list, es_laborable) -> str:
    """Abandono de funciones: 3 días hábiles continuos o 6 discontinuos en el mes (RIP / informe tipo)."""
    from datetime import timedelta
    fs = sorted(set(fechas_falta))
    if len(fs) >= 6:
        return "DISCONTINUO"
    S = set(fs)
    for f in fs:
        run, cur = 1, f
        while True:
            nxt = cur + timedelta(days=1)
            while not es_laborable(nxt):
                nxt += timedelta(days=1)
            if nxt in S:
                run += 1
                cur = nxt
                if run >= 3:
                    return "CONTINUO"
            else:
                break
    return ""
