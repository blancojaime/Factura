"""Orquestación contra la base de datos: importación, procesamiento mensual, permisos, correlativos."""
from __future__ import annotations

import calendar
import hashlib
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .. import audit
from ..models import (Ajuste, AsistenciaDia, Contrato, Correlativo, Empleado, Entidad, EscalaSancion, Feriado, Horario,
                      ImportBiometrico, Liquidacion, Marca, Periodo, Permiso, PermisoTipo)
from . import motor
from .biometrico import _ident, parsear_biometrico


class ReglaNegocio(Exception):
    """Violación de una regla de negocio (se traduce a HTTP 422/409)."""


# ----------------------------------------------------------------------------- correlativos
def siguiente_correlativo(db: Session, tipo: str, gestion: int) -> int:
    """Incremento atómico: UPDATE ... SET ultimo = ultimo + 1 dentro de la transacción.
    Se hace flush ANTES para no perder cambios pendientes de la sesión (no se usa expire_all)."""
    from sqlalchemy import update
    db.flush()
    fila = db.get(Correlativo, (tipo, gestion))
    if fila is None:
        db.add(Correlativo(tipo=tipo, gestion=gestion, ultimo=0))
        db.flush()
    db.execute(update(Correlativo).where(Correlativo.tipo == tipo, Correlativo.gestion == gestion)
               .values(ultimo=Correlativo.ultimo + 1))
    n = db.execute(select(Correlativo.ultimo).where(Correlativo.tipo == tipo, Correlativo.gestion == gestion)
                   .execution_options(populate_existing=True)).scalar_one()
    return n


def formato_cite(prefijo: str, sigla_tipo: str, n: int, gestion: int) -> str:
    return f"{prefijo}-{sigla_tipo}-{n:03d}/{gestion}"


# ----------------------------------------------------------------------------- periodo / calendario
def rango_mes(anio: int, mes: int) -> tuple[date, date]:
    return date(anio, mes, 1), date(anio, mes, calendar.monthrange(anio, mes)[1])


def get_periodo(db: Session, anio: int, mes: int) -> Periodo:
    p = db.get(Periodo, (anio, mes))
    if not p:
        p = Periodo(anio=anio, mes=mes)
        db.add(p)
        db.flush()
    return p


def exigir_abierto(db: Session, d: date) -> None:
    p = db.get(Periodo, (d.year, d.month))
    if p and p.estado == "CERRADO":
        raise ReglaNegocio(f"El periodo {d.month:02d}/{d.year} está CERRADO; reábralo (ADMIN) para modificar")


class Calendario:
    def __init__(self, db: Session, ini: date, fin: date):
        self.feriados = {f.fecha: f.descripcion for f in
                         db.execute(select(Feriado).where(Feriado.fecha.between(ini - timedelta(days=15),
                                                                                 fin + timedelta(days=15)))).scalars()}

    def laborable(self, d: date, dias_lab: str = "01234") -> bool:
        return str(d.weekday()) in dias_lab and d not in self.feriados

    def laborable_std(self, d: date) -> bool:
        return self.laborable(d)


# ----------------------------------------------------------------------------- importación biométrica
def importar_biometrico(db: Session, nombre: str, data: bytes, usuario: str, orden_fecha: str = "dmy",
                        perfil: dict | None = None, perfil_nombre: str = "") -> ImportBiometrico:
    formato, regs, rechazos = parsear_biometrico(nombre, data, orden_fecha, perfil)
    sha = hashlib.sha256(data).hexdigest()
    previo = db.execute(select(ImportBiometrico).where(ImportBiometrico.sha256 == sha)).scalars().first()
    if previo:
        raise ReglaNegocio(f"Este archivo ya fue importado (lote {previo.id}, {previo.fecha:%d/%m/%Y %H:%M})")
    for r in regs:
        exigir_abierto(db, r.fecha_hora.date())
    lote = ImportBiometrico(archivo=nombre[:250], sha256=sha, formato=formato, usuario=usuario, leidas=len(regs),
                            rechazadas=len(rechazos), detalle_rechazo="\n".join(rechazos[:200]))
    db.add(lote)
    db.flush()
    if regs:
        ini = min(r.fecha_hora for r in regs)
        fin = max(r.fecha_hora for r in regs)
        existentes = {(m.identificador, m.fecha_hora, m.dispositivo) for m in db.execute(
            select(Marca.identificador, Marca.fecha_hora, Marca.dispositivo)
            .where(Marca.fecha_hora.between(ini, fin))).all()}
    else:
        existentes = set()
    nuevas = dup = 0
    for r in regs:
        k = (r.identificador, r.fecha_hora, r.dispositivo[:60])
        if k in existentes:
            dup += 1
            continue
        existentes.add(k)
        db.add(Marca(lote_id=lote.id, identificador=r.identificador, fecha_hora=r.fecha_hora, tipo_evento=r.tipo_evento[:40],
                     metodo=r.metodo[:40], dispositivo=r.dispositivo[:60]))
        nuevas += 1
    lote.nuevas, lote.duplicadas = nuevas, dup
    audit.registrar(db, usuario, "IMPORTAR_BIOMETRICO", "import_biometrico", lote.id,
                    {"archivo": nombre, "sha256": sha, "formato": formato, "perfil": perfil_nombre or "automático", "leidas": len(regs), "nuevas": nuevas,
                     "duplicadas": dup, "rechazadas": len(rechazos)})
    return lote


# ----------------------------------------------------------------------------- justificaciones
def justificaciones_por_dia(db: Session, ini: date, fin: date, entidad_ids=None):
    """{(empleado_id, fecha): [Justif]} solo con permisos APROBADOS (y válidos para consultores)."""
    q = select(Permiso).where(Permiso.estado == "APROBADO", Permiso.fecha_desde <= fin, Permiso.fecha_hasta >= ini)
    out: dict = defaultdict(list)
    for p in db.execute(q).scalars():
        cons = any(c.modalidad == "CONSULTOR_LINEA" for c in p.empleado.contratos)
        if cons and not p.autorizado_por.strip():
            continue      # regla del consultor: requiere autorización del fiscal de servicio / contraparte
        d = max(p.fecha_desde, ini)
        while d <= min(p.fecha_hasta, fin):
            desde = motor.minutos(p.hora_desde) if p.hora_desde else 0
            hasta = motor.minutos(p.hora_hasta) if p.hora_hasta else 1440
            out[(p.empleado_id, d)].append(motor.Justif(desde, hasta, p.tipo.categoria, p.tipo.con_goce, p.id))
            d += timedelta(days=1)
    return out


def validar_permiso(db: Session, p: Permiso, emp: Empleado, tipo: PermisoTipo) -> None:
    if p.fecha_hasta < p.fecha_desde:
        raise ReglaNegocio("La fecha final es anterior a la inicial")
    if (p.hora_desde is None) != (p.hora_hasta is None):
        raise ReglaNegocio("Indique hora desde y hora hasta, o ninguna (jornada completa)")
    if p.hora_desde and p.hora_hasta and p.hora_hasta <= p.hora_desde:
        raise ReglaNegocio("La hora final debe ser posterior a la inicial")
    if p.hora_desde and p.fecha_desde != p.fecha_hasta:
        raise ReglaNegocio("Un permiso por horas debe ser de un solo día")
    if p.estado == "APROBADO":
        if any(c.modalidad == "CONSULTOR_LINEA" for c in emp.contratos) and not p.autorizado_por.strip():
            raise ReglaNegocio("Consultor en línea: el permiso/ausencia justificada debe ser autorizado por el "
                               "fiscal de servicio o contraparte municipal (campo 'autorizado_por')")
    if tipo.max_dias is not None:
        dias = (p.fecha_hasta - p.fecha_desde).days + 1
        if p.hora_desde is None and Decimal(dias) > tipo.max_dias:
            raise ReglaNegocio(f"{tipo.nombre}: máximo {tipo.max_dias} día(s) ({tipo.base_legal})")


# ----------------------------------------------------------------------------- procesamiento mensual
def _reglas(h: Horario, ent: Entidad) -> motor.Reglas:
    return motor.Reglas(tuple(motor.TurnoDef(t.nombre, motor.minutos(t.hora_entrada), motor.minutos(t.hora_salida))
                              for t in sorted(h.turnos, key=lambda t: t.orden)),
                        h.tolerancia_min, h.umbral_grave_min, ent.tolerancia_cuenta_total, ent.contar_salida_anticipada)


def contrato_del_mes(emp: Empleado, ini: date, fin: date) -> Contrato | None:
    cand = []
    for c in emp.contratos:
        f_fin = c.fecha_baja or c.fecha_fin
        if c.fecha_inicio <= fin and (f_fin is None or f_fin >= ini):
            cand.append(c)
    return max(cand, key=lambda c: c.fecha_inicio) if cand else None


def ventana(c: Contrato, ini: date, fin: date) -> tuple[date, date]:
    f_fin = c.fecha_baja or c.fecha_fin
    return max(c.fecha_inicio, ini), min(f_fin, fin) if f_fin else fin


def params_calculo(db: Session, ent: Entidad) -> motor.ParamsCalculo:
    esc = db.execute(select(EscalaSancion).where(EscalaSancion.modo == ent.escala_modo)
                     .order_by(EscalaSancion.desde)).scalars().all()
    return motor.ParamsCalculo(
        ent.escala_modo, tuple(motor.FilaEscala(e.desde, e.hasta, e.dias_descuento, e.sancion) for e in esc),
        ent.factor_falta_planta, ent.factor_falta_consultor, ent.max_justificados_consultor,
        ent.contar_salida_anticipada, ent.tasa_afp, ent.tasa_patronal, ent.dias_mes_comercial)


def procesar_periodo(db: Session, anio: int, mes: int, usuario: str, auditar: bool = True) -> dict:
    per = get_periodo(db, anio, mes)
    if per.estado == "CERRADO":
        raise ReglaNegocio("Periodo CERRADO: no se puede reprocesar")
    ini, fin = rango_mes(anio, mes)
    ent = db.get(Entidad, 1)
    cal = Calendario(db, ini, fin)
    horario_def = db.execute(select(Horario).where(Horario.es_defecto == True)).scalars().first()  # noqa: E712
    if not horario_def:
        raise ReglaNegocio("Configure un horario por defecto")
    params = params_calculo(db, ent)
    just = justificaciones_por_dia(db, ini, fin)

    # marcas del mes por identificador normalizado
    por_id: dict[str, dict[date, list[int]]] = defaultdict(lambda: defaultdict(list))
    q = select(Marca.identificador, Marca.fecha_hora).where(Marca.fecha_hora >= datetime.combine(ini, time.min),
                                                            Marca.fecha_hora < datetime.combine(fin + timedelta(days=1), time.min))
    for ident, fh in db.execute(q).all():
        por_id[_ident(ident)][fh.date()].append(fh.hour * 60 + fh.minute)

    multas: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for a in db.execute(select(Ajuste).where(Ajuste.anio == anio, Ajuste.mes == mes, Ajuste.estado == "ACTIVO")).scalars().unique():
        multas[a.empleado_id] += a.monto
    db.execute(delete(AsistenciaDia).where(AsistenciaDia.fecha.between(ini, fin)))
    db.execute(delete(Liquidacion).where(Liquidacion.anio == anio, Liquidacion.mes == mes))
    db.flush()
    n_emp = 0
    # todos los empleados con contrato en el mes (incluye bajas del mes); 'activo' es solo informativo
    for emp in db.execute(select(Empleado).order_by(Empleado.apellidos, Empleado.nombres)).scalars().unique():
        c = contrato_del_mes(emp, ini, fin)
        if not c:
            continue
        h = db.get(Horario, emp.horario_id) if emp.horario_id else horario_def
        reglas = _reglas(h, ent)
        v_ini, v_fin = ventana(c, ini, fin)
        marcas = por_id.get(_ident(emp.codigo), {})
        resultados: list[motor.ResDia] = []
        d = v_ini
        while d <= v_fin:
            lab = cal.laborable(d, h.dias_laborables)
            r = motor.evaluar_dia(reglas, marcas.get(d, []), just.get((emp.id, d), []), lab, feriado=d in cal.feriados)
            resultados.append(r)
            db.add(AsistenciaDia(
                empleado_id=emp.id, fecha=d, estado=r.estado, marcas=r.marcas_txt, min_retraso=r.min_retraso,
                nro_retrasos=r.nro_retrasos, min_salida_anticipada=r.min_salida_anticipada, falta=r.falta,
                justificado=r.justificado, justificado_sin_goce=r.justificado_sin_goce, parcial=r.parcial,
                parcial_sin_goce=r.parcial_sin_goce, categoria_just=r.categoria,
                permiso_id=r.permiso_id, observacion="; ".join(r.observaciones)[:250]))
            d += timedelta(days=1)
        cc = motor.ContratoCalc(c.modalidad, c.haber_basico, c.bono_antiguedad, c.rc_iva, c.aplica_aporte,
                                c.tasa_afp, c.tasa_patronal)
        dias_trab = motor.dias_comerciales(v_ini, v_fin, ini, fin, ent.dias_mes_comercial)
        m = motor.liquidar_mes(cc, resultados, params, dias_trab, multas.get(emp.id, Decimal('0')))
        db.add(Liquidacion(
            anio=anio, mes=mes, empleado_id=emp.id, contrato_id=c.id, modalidad=c.modalidad, haber_basico=c.haber_basico,
            dias_trabajados=m.dias_trabajados, bono_antiguedad=m.bono, total_ganado=m.total_ganado,
            aporte_laboral=m.aporte_laboral, aporte_patronal=m.aporte_patronal, rc_iva=m.rc_iva,
            dias_laborables=m.dias_laborables, dias_asistidos=m.dias_asistidos, faltas=m.faltas,
            min_retraso=m.min_retraso, nro_retrasos=m.nro_retrasos, dias_justificados=m.dias_justificados,
            dias_desc_faltas=m.dias_desc_faltas, dias_desc_atrasos=m.dias_desc_atrasos,
            dias_desc_sin_goce=m.dias_desc_sin_goce, dias_desc_exceso_consultor=m.dias_desc_exceso,
            desc_faltas=m.desc_faltas, desc_atrasos=m.desc_atrasos, desc_otros=m.desc_otros, desc_multas=m.multas,
            horas_permiso=m.horas_permiso,
            dias_descuento=m.dias_descuento, desc_asistencia=m.desc_asistencia, total_descuentos=m.total_descuentos,
            liquido_pagable=m.liquido, sancion=m.sancion, observacion="; ".join(m.observaciones)[:400]))
        n_emp += 1
    per.procesado_en = datetime.now()
    if auditar:
        audit.registrar(db, usuario, "PROCESAR_PERIODO", "periodo", f"{anio}-{mes:02d}", {"empleados": n_emp})
    db.flush()
    return {"anio": anio, "mes": mes, "empleados": n_emp}


def asegurar_actualizado(db: Session, anio: int, mes: int, usuario: str = "sistema") -> None:
    """Pantallas y reportes de un periodo ABIERTO se recalculan antes de mostrarse (una sola fuente de verdad)."""
    per = db.get(Periodo, (anio, mes))
    if not per or per.estado != "CERRADO":
        procesar_periodo(db, anio, mes, usuario, auditar=False)
        db.commit()


def cerrar_periodo(db: Session, anio: int, mes: int, usuario: str) -> Periodo:
    per = get_periodo(db, anio, mes)
    if not per.procesado_en:
        raise ReglaNegocio("Procese el periodo antes de cerrarlo")
    per.estado, per.cerrado_por, per.cerrado_en = "CERRADO", usuario, datetime.now()
    audit.registrar(db, usuario, "CERRAR_PERIODO", "periodo", f"{anio}-{mes:02d}")
    return per


def reabrir_periodo(db: Session, anio: int, mes: int, usuario: str, motivo: str) -> Periodo:
    if len(motivo.strip()) < 10:
        raise ReglaNegocio("Indique el motivo de la reapertura (mínimo 10 caracteres)")
    per = get_periodo(db, anio, mes)
    per.estado = "ABIERTO"
    audit.registrar(db, usuario, "REABRIR_PERIODO", "periodo", f"{anio}-{mes:02d}", {"motivo": motivo})
    return per
