"""Pruebas unitarias del motor (funciones puras)."""
from decimal import Decimal as D

from app.services import motor as m
from app.services.motor import (ContratoCalc, FilaEscala, Justif, ParamsCalculo, Reglas, TurnoDef, evaluar_dia,
                                liquidar_mes, detectar_abandono)
from datetime import date, timedelta

R = Reglas((TurnoDef("Mañana", 480, 720), TurnoDef("Tarde", 870, 1110)), tolerancia=10, umbral_grave=30)


def t(s):
    h, mi = s.split(":")
    return int(h) * 60 + int(mi)


def dia(marcas, justifs=(), reglas=R):
    return evaluar_dia(reglas, [t(x) for x in marcas], list(justifs), True)


def test_dia_normal():
    r = dia(["07:55", "12:02", "14:28", "18:35"])
    assert r.estado == m.NORMAL and r.min_retraso == 0 and r.falta == 0


def test_tolerancia_y_retraso_completo():
    assert dia(["08:10", "12:00", "14:30", "18:30"]).min_retraso == 0          # justo en la tolerancia
    r = dia(["08:11", "12:00", "14:30", "18:30"])
    assert r.min_retraso == 11 and r.estado == m.RETRASO_LEVE and r.nro_retrasos == 1


def test_tolerancia_solo_exceso():
    reglas = Reglas(R.turnos, 10, 30, tolerancia_cuenta_total=False)
    assert dia(["08:25", "12:00", "14:30", "18:30"], reglas=reglas).min_retraso == 15


def test_retraso_grave():
    assert dia(["08:31", "12:00", "14:30", "18:30"]).estado == m.RETRASO_GRAVE
    assert dia(["08:30", "12:00", "14:30", "18:30"]).estado == m.RETRASO_LEVE      # 30 no supera el umbral


def test_retraso_en_tarde():
    r = dia(["08:00", "12:00", "14:52", "18:30"])
    assert r.min_retraso == 22


def test_falta_dia_completo_y_media():
    assert dia([]).falta == D(1) and dia([]).estado == m.FALTA_INJUSTIFICADA
    r = dia(["07:55", "12:06"])
    assert r.falta == D("0.5") and r.estado == m.FALTA_INJUSTIFICADA


def test_falta_justificada_dia_completo():
    r = dia([], [Justif(0, 1440, "LICENCIA", True, 7)])
    assert r.estado == m.FALTA_JUSTIFICADA and r.falta == 0 and r.justificado == 1 and r.permiso_id == 7


def test_justificada_sin_goce():
    r = dia([], [Justif(0, 1440, "PERMISO", False)])
    assert r.justificado_sin_goce == 1


def test_permiso_horas_cubre_llegada_tardia():
    r = dia(["10:05", "12:03", "14:25", "18:35"], [Justif(480, 600, "PERMISO", True)])
    assert r.min_retraso == 0 and r.estado == m.NORMAL


def test_permiso_horas_parcial_no_cubre_todo():
    r = dia(["10:35", "12:03", "14:25", "18:35"], [Justif(480, 600, "PERMISO", True)])
    assert r.min_retraso == 35 and r.estado == m.RETRASO_GRAVE


def test_permiso_parcial_no_justifica_turno_ausente():
    # permiso de 2 h en un turno de 4 h sin marcas: el resto es falta injustificada
    r = dia(["14:28", "18:35"], [Justif(480, 600, "PERMISO", True)])
    assert r.falta == D("0.5") and r.justificado == 0


def test_omision_marcacion():
    r = dia(["08:00", "14:28", "18:35"])
    assert r.estado == m.OMISION and r.falta == 0
    r = dia(["07:59", "12:05", "18:35"])
    assert r.estado == m.OMISION


def test_doble_pulsacion_se_ignora():
    r = dia(["08:00", "08:02", "12:00", "14:30", "14:31", "18:30"])
    assert r.estado == m.NORMAL and r.marcas == [480, 720, 870, 1110]


def test_dia_no_laborable():
    r = evaluar_dia(R, [480], [], laborable=False)
    assert r.estado == m.NO_LABORABLE and r.falta == 0
    assert evaluar_dia(R, [], [], laborable=False, feriado=True).estado == m.FERIADO


def test_jornada_continua_un_turno():
    R1 = Reglas((TurnoDef("Continua", 480, 960),), 5, 30)
    assert evaluar_dia(R1, [t("08:06"), t("16:00")], [], True).min_retraso == 6
    assert evaluar_dia(R1, [], [], True).falta == D(1)


def test_pesos_tres_turnos_suman_uno():
    p = m.pesos_turnos((TurnoDef("a", 0, 100), TurnoDef("b", 100, 200), TurnoDef("c", 200, 300)))
    assert sum(p) == 1


ESC = (FilaEscala(0, 30, D(0), "Sin sanción"), FilaEscala(31, 60, D(0), "Amonestación escrita"),
       FilaEscala(61, 90, D("0.5"), "Descuento 0.5"), FilaEscala(91, 120, D(1), "Descuento 1.0"),
       FilaEscala(121, None, D(2), "Descuento 2.0 + llamada severa"))
P = ParamsCalculo(escala=ESC)


def _dias(n_norm=22, retrasos=(), faltas=0, justif=0, sin_goce=0):
    out = [m.ResDia(m.NORMAL) for _ in range(n_norm)]
    for mins in retrasos:
        out.append(m.ResDia(m.RETRASO_LEVE, min_retraso=mins, nro_retrasos=1))
    for _ in range(faltas):
        out.append(m.ResDia(m.FALTA_INJUSTIFICADA, falta=D(1)))
    for i in range(justif):
        out.append(m.ResDia(m.FALTA_JUSTIFICADA, justificado=D(1), justificado_sin_goce=D(1) if i < sin_goce else D(0)))
    return out


def test_liquidacion_planta_sin_incidencias():
    r = liquidar_mes(ContratoCalc("PERMANENTE", D(6000)), _dias(), P, D(30))
    assert (r.total_ganado, r.aporte_laboral, r.aporte_patronal, r.liquido) == (D("6000.00"), D("762.60"), D("1032.60"), D("5237.40"))


def test_escala_bordes():
    assert liquidar_mes(ContratoCalc("PERMANENTE", D(3000)), _dias(retrasos=[30]), P, D(30)).dias_desc_atrasos == 0
    r = liquidar_mes(ContratoCalc("PERMANENTE", D(3000)), _dias(retrasos=[31]), P, D(30))
    assert r.dias_desc_atrasos == 0 and r.sancion == "Amonestación escrita"
    assert liquidar_mes(ContratoCalc("PERMANENTE", D(3000)), _dias(retrasos=[61]), P, D(30)).dias_desc_atrasos == D("0.5")
    assert liquidar_mes(ContratoCalc("PERMANENTE", D(3000)), _dias(retrasos=[60, 31]), P, D(30)).dias_desc_atrasos == D(1)
    assert liquidar_mes(ContratoCalc("PERMANENTE", D(3000)), _dias(retrasos=[100, 31]), P, D(30)).dias_desc_atrasos == D(2)


def test_falta_doble_haber():
    r = liquidar_mes(ContratoCalc("EVENTUAL", D(3000)), _dias(faltas=1), P, D(30))
    assert r.dias_desc_faltas == 2 and r.desc_faltas == D("200.00")


def test_consultor_un_dia_gratis_y_exceso():
    c = ContratoCalc("CONSULTOR_LINEA", D(6000), aplica_aporte=False)
    r1 = liquidar_mes(c, _dias(justif=1), P, D(30))
    assert r1.dias_desc_exceso == 0 and r1.desc_asistencia == 0 and r1.liquido == D("6000.00")
    r2 = liquidar_mes(c, _dias(justif=2), P, D(30))
    assert r2.dias_desc_exceso == 1 and r2.desc_otros == D("200.00") and r2.liquido == D("5800.00")
    assert r2.aporte_laboral == 0


def test_consultor_falta_no_se_duplica():
    r = liquidar_mes(ContratoCalc("CONSULTOR_LINEA", D(6000), aplica_aporte=False), _dias(faltas=1), P, D(30))
    assert r.dias_desc_faltas == 1 and r.desc_faltas == D("200.00")


def test_planta_permiso_sin_goce_descuenta_dia():
    r = liquidar_mes(ContratoCalc("EVENTUAL", D(3000)), _dias(justif=2, sin_goce=1), P, D(30))
    assert r.dias_desc_sin_goce == 1 and r.desc_otros == D("100.00")


def test_dias_parciales_y_bono_y_rciva():
    c = ContratoCalc("PERMANENTE", D(3000), bono=D(300), rc_iva=D("6.64"))
    r = liquidar_mes(c, _dias(), P, D(15))
    assert r.total_ganado == D("1650.00") and r.rc_iva == D("6.64")
    assert r.aporte_laboral == D("209.72") and r.liquido == D("1650.00") - D("209.72") - D("6.64")


def test_tope_descuento():
    r = liquidar_mes(ContratoCalc("PERMANENTE", D(300)), _dias(faltas=20), P, D(30))
    assert r.desc_asistencia == r.total_ganado


def test_dias_comerciales():
    from datetime import date
    a, b = date(2026, 2, 1), date(2026, 2, 28)
    assert m.dias_comerciales(a, b, a, b) == 30
    assert m.dias_comerciales(date(2026, 10, 16), date(2026, 10, 31), date(2026, 10, 1), date(2026, 10, 31)) == 15
    assert m.dias_comerciales(date(2026, 10, 1), date(2026, 10, 10), date(2026, 10, 1), date(2026, 10, 31)) == 10
    assert m.dias_comerciales(date(2026, 10, 31), date(2026, 10, 31), date(2026, 10, 1), date(2026, 10, 31)) == 1


def test_abandono():
    lab = lambda d: d.weekday() < 5
    assert detectar_abandono([date(2026, 10, 21), date(2026, 10, 22), date(2026, 10, 23)], lab) == "CONTINUO"
    assert detectar_abandono([date(2026, 10, 22), date(2026, 10, 23), date(2026, 10, 26)], lab) == "CONTINUO"   # cruza fin de semana
    assert detectar_abandono([date(2026, 10, 1), date(2026, 10, 8)], lab) == ""
    seis = [date(2026, 10, 1), date(2026, 10, 5), date(2026, 10, 7), date(2026, 10, 12), date(2026, 10, 14), date(2026, 10, 19)]
    assert detectar_abandono(seis, lab) == "DISCONTINUO"
