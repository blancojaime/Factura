"""Casos de uso del tramite de Contratacion Menor (logica de negocio, independiente de FastAPI).

Cada funcion valida permisos/estado, aplica las reglas normativas, genera los documentos del expediente
y deja el registro de auditoria en la misma transaccion.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..enums import Estado, EstadoCHB, MetodoFormalizacion, ModalidadCuantia, Rol, TipoDoc, TipoObjeto
from ..errors import EstadoInvalidoError, NoEncontradoError, ReglaNegocioError
from ..models import (
    ContratacionItem, ContratacionMenor, CotizacionProveedor, PartidaPresupuestaria, Recepcion, Usuario,
)
from . import auditoria, bloque_sigep, calculador_modalidad as calc, cifrado, notificaciones, parametros, presupuesto
from . import validador_chb, workflow
from .evaluador_ofertas import OfertaIn, evaluar as evaluar_ofertas
from .generador_pdf import generar_documento
from .secuencias import correlativo
from .storage import get_storage

CENT = Decimal("0.01")


def _aware(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


# ------------------------------------------------------------------ acceso
def obtener(db: Session, contratacion_id: uuid.UUID, usuario: Usuario, bloquear: bool = False) -> ContratacionMenor:
    consulta = select(ContratacionMenor).where(ContratacionMenor.id == contratacion_id)
    if bloquear:
        consulta = consulta.with_for_update()
    c = db.scalar(consulta)
    if c is None:
        raise NoEncontradoError("Contratación no encontrada")
    if usuario.rol == Rol.SOLICITANTE.value and c.created_by_id != usuario.id:
        raise NoEncontradoError("Contratación no encontrada")  # no se revela la existencia
    return c


def _solo_creador(c: ContratacionMenor, u: Usuario) -> None:
    if c.created_by_id != u.id:
        raise EstadoInvalidoError("Solo quien creó la solicitud puede realizar esta acción", "ROL_NO_AUTORIZADO")


def acciones(c: ContratacionMenor, u: Usuario) -> list[str]:
    acc = workflow.acciones_disponibles(c.estado, u.rol)
    if u.rol == Rol.SOLICITANTE.value and c.created_by_id != u.id:
        return []
    return acc


def _snap(c: ContratacionMenor) -> dict:
    return {"estado": c.estado, "monto": str(c.monto_referencial_total), "metodo": c.metodo_formalizacion}


def _audit(db, u, accion, c, antes=None, despues=None, ip=""):
    auditoria.registrar(db, u.id, accion, "contrataciones_menores", c.id, antes, despues, ip)


# ------------------------------------------------------------------ cuantia
def _params(db: Session) -> dict[str, str]:
    return parametros.obtener_todos(db)


def evaluar_cuantia(db: Session, monto: Decimal, plazo: int, tipo_objeto: str):
    p = _params(db)
    r = calc.calcular_modalidad(monto, parametros.get_decimal(p, "tope_contratacion_menor"),
                                parametros.get_decimal(p, "tope_compra_directa"))
    metodo = calc.determinar_formalizacion(plazo, tipo_objeto, parametros.get_int(p, "plazo_orden_max_dias"))
    return r, metodo


def _recalcular(db: Session, c: ContratacionMenor) -> None:
    total = sum((Decimal(i.subtotal) for i in c.items), Decimal("0"))
    c.monto_referencial_total = total
    p = _params(db)
    if total >= 1:
        r = calc.calcular_modalidad(total, parametros.get_decimal(p, "tope_contratacion_menor"),
                                    parametros.get_decimal(p, "tope_compra_directa"))
        c.modalidad_cuantia = r.modalidad.value if r.modalidad else None
    else:
        c.modalidad_cuantia = None
    c.metodo_formalizacion = calc.determinar_formalizacion(
        c.plazo_dias_calendario, c.tipo_objeto, parametros.get_int(p, "plazo_orden_max_dias")).value


# ------------------------------------------------------------------ borrador
def crear(db: Session, u: Usuario, datos: dict, ip: str = "") -> ContratacionMenor:
    p = _params(db)
    c = ContratacionMenor(
        correlativo_interno=correlativo(db, "CM", p["gestion"]), created_by_id=u.id,
        estado=Estado.BORRADOR.value, **datos)
    c.tipo_objeto = TipoObjeto(datos["tipo_objeto"]).value
    c.monto_referencial_total = Decimal("0")
    c.metodo_formalizacion = calc.determinar_formalizacion(
        c.plazo_dias_calendario, c.tipo_objeto, parametros.get_int(p, "plazo_orden_max_dias")).value
    db.add(c)
    db.flush()
    _audit(db, u, "CONTRATACION_CREADA", c, None, _snap(c), ip)
    return c


def _requiere_borrador(c: ContratacionMenor) -> None:
    if c.estado != Estado.BORRADOR.value:
        raise EstadoInvalidoError("Solo se puede editar una solicitud en BORRADOR", "NO_EDITABLE")


def actualizar(db: Session, u: Usuario, c: ContratacionMenor, datos: dict, ip: str = "") -> ContratacionMenor:
    _solo_creador(c, u)
    _requiere_borrador(c)
    antes = {k: str(getattr(c, k)) for k in datos}
    for k, v in datos.items():
        if k == "tipo_objeto" and v is not None:
            v = TipoObjeto(v).value
        if v is not None or k in ("justificacion_excepcion_chb", "codigo_autorizacion_chb"):
            setattr(c, k, v)
    if "tipo_objeto" in datos and datos["tipo_objeto"] is not None:
        # al cambiar de tipo se reevalua el CHB de los items
        for it in c.items:
            res = validador_chb.evaluar_item(db, c.tipo_objeto, it.codigo_unspsc, it.fuera_catalogo_chb) \
                if (c.tipo_objeto != TipoObjeto.BIEN.value or it.codigo_unspsc) else None
            it.estado_chb = res.estado.value if res else EstadoCHB.NO_APLICA.value
    _recalcular(db, c)
    c.requiere_excepcion_chb = validador_chb.requiere_excepcion(c.items)
    db.flush()
    _audit(db, u, "CONTRATACION_ACTUALIZADA", c, antes, {k: str(getattr(c, k)) for k in datos}, ip)
    return c


def agregar_item(db: Session, u: Usuario, c: ContratacionMenor, datos: dict, ip: str = "") -> ContratacionItem:
    _solo_creador(c, u)
    _requiere_borrador(c)
    p = _params(db)
    partida = db.get(PartidaPresupuestaria, datos["partida_id"])
    if partida is None:
        raise ReglaNegocioError("La partida presupuestaria no existe", "PARTIDA_INEXISTENTE")
    if partida.gestion != int(p["gestion"]):
        raise ReglaNegocioError(f"La partida no pertenece a la gestión vigente ({p['gestion']})", "PARTIDA_GESTION")
    chb = validador_chb.evaluar_item(db, c.tipo_objeto, datos.get("codigo_unspsc", ""),
                                     bool(datos.get("fuera_catalogo_chb")))
    subtotal = (Decimal(datos["cantidad"]) * Decimal(datos["precio_unitario_ref"])).quantize(CENT, ROUND_HALF_UP)
    nuevo_total = sum((Decimal(i.subtotal) for i in c.items), Decimal("0")) + subtotal
    tope = parametros.get_decimal(p, "tope_contratacion_menor")
    if nuevo_total > tope:
        raise ReglaNegocioError(calc.calcular_modalidad(nuevo_total, tope).mensaje, "SUPERA_CONTRATACION_MENOR")
    numero = (max((i.numero for i in c.items), default=0)) + 1
    item = ContratacionItem(
        contratacion_id=c.id, numero=numero, codigo_unspsc=datos.get("codigo_unspsc", ""),
        partida_id=partida.id, partida_gasto=partida.codigo_partida,
        descripcion_especifica=datos["descripcion_especifica"], unidad_medida=datos["unidad_medida"],
        cantidad=datos["cantidad"], precio_unitario_ref=datos["precio_unitario_ref"], subtotal=subtotal,
        fuera_catalogo_chb=bool(datos.get("fuera_catalogo_chb")), estado_chb=chb.estado.value)
    c.items.append(item)
    db.flush()
    _recalcular(db, c)
    c.requiere_excepcion_chb = validador_chb.requiere_excepcion(c.items)
    db.flush()
    _audit(db, u, "ITEM_AGREGADO", c, None, {"item": numero, "subtotal": str(subtotal), "chb": chb.estado.value}, ip)
    return item


def actualizar_item(db: Session, u: Usuario, c: ContratacionMenor, item_id: uuid.UUID, datos: dict,
                    ip: str = "") -> ContratacionItem:
    _solo_creador(c, u)
    _requiere_borrador(c)
    item = next((i for i in c.items if i.id == item_id), None)
    if item is None:
        raise NoEncontradoError("Ítem no encontrado")
    p = _params(db)
    partida = db.get(PartidaPresupuestaria, datos["partida_id"])
    if partida is None:
        raise ReglaNegocioError("La partida presupuestaria no existe", "PARTIDA_INEXISTENTE")
    if partida.gestion != int(p["gestion"]):
        raise ReglaNegocioError(f"La partida no pertenece a la gestión vigente ({p['gestion']})", "PARTIDA_GESTION")
    chb = validador_chb.evaluar_item(db, c.tipo_objeto, datos.get("codigo_unspsc", ""),
                                     bool(datos.get("fuera_catalogo_chb")))
    subtotal = (Decimal(datos["cantidad"]) * Decimal(datos["precio_unitario_ref"])).quantize(CENT, ROUND_HALF_UP)
    nuevo_total = sum((Decimal(i.subtotal) for i in c.items if i.id != item.id), Decimal("0")) + subtotal
    tope = parametros.get_decimal(p, "tope_contratacion_menor")
    if nuevo_total > tope:
        raise ReglaNegocioError(calc.calcular_modalidad(nuevo_total, tope).mensaje, "SUPERA_CONTRATACION_MENOR")
    antes = {"item": item.numero, "subtotal": str(item.subtotal), "chb": item.estado_chb}
    item.codigo_unspsc = datos.get("codigo_unspsc", "")
    item.partida_id, item.partida_gasto = partida.id, partida.codigo_partida
    item.descripcion_especifica, item.unidad_medida = datos["descripcion_especifica"], datos["unidad_medida"]
    item.cantidad, item.precio_unitario_ref, item.subtotal = datos["cantidad"], datos["precio_unitario_ref"], subtotal
    item.fuera_catalogo_chb, item.estado_chb = bool(datos.get("fuera_catalogo_chb")), chb.estado.value
    db.flush()
    _recalcular(db, c)
    c.requiere_excepcion_chb = validador_chb.requiere_excepcion(c.items)
    db.flush()
    _audit(db, u, "ITEM_ACTUALIZADO", c, antes, {"item": item.numero, "subtotal": str(subtotal), "chb": chb.estado.value}, ip)
    return item


def eliminar_item(db: Session, u: Usuario, c: ContratacionMenor, item_id: uuid.UUID, ip: str = "") -> None:
    _solo_creador(c, u)
    _requiere_borrador(c)
    item = next((i for i in c.items if i.id == item_id), None)
    if item is None:
        raise NoEncontradoError("Ítem no encontrado")
    c.items.remove(item)
    db.flush()
    _recalcular(db, c)
    c.requiere_excepcion_chb = validador_chb.requiere_excepcion(c.items)
    db.flush()
    _audit(db, u, "ITEM_ELIMINADO", c, {"item": item.numero}, None, ip)


# ------------------------------------------------------------------ solicitud y presupuesto
def solicitar(db: Session, u: Usuario, c: ContratacionMenor, ip: str = "") -> ContratacionMenor:
    _solo_creador(c, u)
    antes = _snap(c)
    p = _params(db)
    errores: list[str] = []
    if not c.items:
        errores.append("La solicitud debe tener al menos un ítem")
    if len((c.especificaciones_tecnicas or "").strip()) < 20:
        errores.append("Redacte las Especificaciones Técnicas / Términos de Referencia (mínimo 20 caracteres)")
    if not (c.unidad_solicitante or "").strip():
        errores.append("Indique la unidad solicitante")
    if len((c.justificacion or "").strip()) < 10:
        errores.append("Indique la justificación de la necesidad")
    if not (c.lugar_entrega or "").strip():
        errores.append("Indique el lugar de entrega o ejecución")
    if c.items:
        r = calc.calcular_modalidad(c.monto_referencial_total, parametros.get_decimal(p, "tope_contratacion_menor"),
                                    parametros.get_decimal(p, "tope_compra_directa"))
        if r.bloqueado:
            errores.append(r.mensaje)
        errores += validador_chb.validar_contratacion_chb(
            c.items, c.justificacion_excepcion_chb, parametros.get_int(p, "chb_min_justificacion"))
        errores += presupuesto.validar_partidas_items(db, c.items, int(p["gestion"]))
    if errores:
        raise ReglaNegocioError("La solicitud no puede enviarse", "SOLICITUD_INCOMPLETA", errores)
    _recalcular(db, c)
    c.requiere_excepcion_chb = validador_chb.requiere_excepcion(c.items)
    workflow.aplicar(c, "solicitar", u.rol)
    db.flush()
    generar_documento(db, c, TipoDoc.C1_SOLICITUD, u)
    if c.requiere_excepcion_chb:
        generar_documento(db, c, TipoDoc.INFORME_EXCEPCION_CHB, u)
    _audit(db, u, "SOLICITUD_ENVIADA", c, antes, _snap(c), ip)
    return c


def devolver(db: Session, u: Usuario, c: ContratacionMenor, motivo: str, ip: str = "") -> ContratacionMenor:
    antes = _snap(c)
    workflow.aplicar(c, "devolver", u.rol)
    c.ultima_observacion = f"Devuelta por Presupuesto: {motivo}"
    db.flush()
    _audit(db, u, "SOLICITUD_DEVUELTA", c, antes, {**_snap(c), "motivo": motivo}, ip)
    return c


def certificar(db: Session, u: Usuario, c: ContratacionMenor, nro_c31: str | None, ip: str = "") -> ContratacionMenor:
    antes = _snap(c)
    if c.estado != Estado.SOLICITADO.value:  # validacion previa para no tocar saldos en un estado invalido
        raise EstadoInvalidoError(f"La acción 'certificar' no es válida con la contratación en estado {c.estado}")
    presupuesto.certificar(db, c)
    workflow.aplicar(c, "certificar", u.rol)
    if nro_c31:
        c.preventivo_c31_nro = nro_c31.strip()
    c.ultima_observacion = None
    db.flush()
    generar_documento(db, c, TipoDoc.CERTIFICACION_C31, u)
    _audit(db, u, "PRESUPUESTO_CERTIFICADO", c, antes, {**_snap(c), "c31": c.preventivo_c31_nro}, ip)
    return c


def registrar_c31(db: Session, u: Usuario, c: ContratacionMenor, nro: str, ip: str = "") -> ContratacionMenor:
    if c.estado not in (Estado.CERTIFICADO_PRESUPUESTO.value, Estado.EN_COTIZACION.value, Estado.EVALUADO.value,
                        Estado.ADJUDICADO.value, Estado.FORMALIZADO.value):
        raise EstadoInvalidoError("El N° de C-31 solo se registra con presupuesto certificado y trámite vigente")
    antes = c.preventivo_c31_nro
    c.preventivo_c31_nro = nro.strip()
    db.flush()
    generar_documento(db, c, TipoDoc.CERTIFICACION_C31, u)
    _audit(db, u, "C31_NRO_REGISTRADO", c, {"c31": antes}, {"c31": c.preventivo_c31_nro}, ip)
    return c


def bloque_sigep_de(db: Session, c: ContratacionMenor) -> dict:
    p = _params(db)
    if c.preventivos:
        lineas = [(pv.partida, pv.importe) for pv in c.preventivos if pv.estado != "LIBERADO"]
        origen = "PREVENTIVO"
    else:
        lineas = [(db.get(PartidaPresupuestaria, pid), imp) for pid, imp in presupuesto.importes_por_partida(c.items).items()
                  if pid is not None]
        origen = "PREVISTO"
    b = bloque_sigep.construir(p, lineas)
    b["origen"] = origen
    return b


def aprobar_inicio(db: Session, u: Usuario, c: ContratacionMenor, ip: str = "") -> ContratacionMenor:
    antes = _snap(c)
    workflow.aplicar(c, "aprobar_inicio", u.rol)
    c.rpa_id = u.id
    db.flush()
    _audit(db, u, "INICIO_PROCESO_APROBADO", c, antes, _snap(c), ip)
    return c


# ------------------------------------------------------------------ cotizacion
def registrar_formulario_110(db: Session, u: Usuario, c: ContratacionMenor, datos: dict, ip: str = "") -> ContratacionMenor:
    if c.estado != Estado.EN_COTIZACION.value:
        raise EstadoInvalidoError("El Formulario 110 se registra con la contratación EN_COTIZACION")
    if c.ofertas_abiertas:
        raise EstadoInvalidoError("Las ofertas ya fueron abiertas")
    antes = {"f110": c.nro_formulario_110, "limite": str(c.fecha_limite_ofertas)}
    c.nro_formulario_110 = datos["nro_formulario_110"].strip()
    c.fecha_limite_ofertas = _aware(datos["fecha_limite_ofertas"])
    if datos.get("cuce"):
        c.cuce = datos["cuce"].strip()
    db.flush()
    _audit(db, u, "FORMULARIO_110_REGISTRADO", c, antes,
           {"f110": c.nro_formulario_110, "limite": str(c.fecha_limite_ofertas), "cuce": c.cuce}, ip)
    return c


def _exigir_f110(c: ContratacionMenor) -> None:
    if c.modalidad_cuantia == ModalidadCuantia.CONSULTA_PRECIOS.value and not c.nro_formulario_110:
        raise ReglaNegocioError(
            "Para montos de Bs 20.001 a Bs 50.000 debe publicarse la Consulta de Precios en SICOES y registrarse "
            "el número de Formulario 110 antes de continuar", "FORMULARIO_110_REQUERIDO")


def enviar_fichas(db: Session, u: Usuario, c: ContratacionMenor, destinatarios: list[dict], canales: list[str],
                  ip: str = "") -> dict:
    if c.estado != Estado.EN_COTIZACION.value:
        raise EstadoInvalidoError("Las fichas se emiten con la contratación EN_COTIZACION")
    _exigir_f110(c)
    doc = generar_documento(db, c, TipoDoc.FICHA_COTIZACION, u, {"destinatarios": destinatarios})
    pdf = get_storage().get(doc.ruta_archivo)
    resultados = []
    for d in destinatarios:
        fila = {"razon_social": d["razon_social"], "canales": {}}
        texto = (f"{c.correlativo_interno}: solicitud de cotización para «{c.objeto_contratacion}». "
                 f"Plazo de presentación: {c.fecha_limite_ofertas or 'según ficha'}.")
        if "EMAIL" in canales:
            fila["canales"]["EMAIL"] = notificaciones.enviar_correo(
                d.get("correo", ""), f"Solicitud de cotización {c.correlativo_interno}", texto, pdf,
                f"ficha_{c.correlativo_interno}.pdf")
        if "WHATSAPP" in canales:
            fila["canales"]["WHATSAPP"] = notificaciones.enlace_whatsapp(d.get("telefono", ""), texto) or "SIN_TELEFONO"
        if "IMPRESO" in canales:
            fila["canales"]["IMPRESO"] = str(doc.id)
        resultados.append(fila)
    _audit(db, u, "FICHAS_COTIZACION_EMITIDAS", c, None,
           {"documento": str(doc.id), "canales": canales, "destinatarios": [d["razon_social"] for d in destinatarios]}, ip)
    return {"documento_id": str(doc.id), "resultados": resultados}


def registrar_cotizacion(db: Session, u: Usuario, c: ContratacionMenor, datos: dict, ip: str = "") -> CotizacionProveedor:
    if c.estado != Estado.EN_COTIZACION.value:
        raise EstadoInvalidoError("Solo se cargan cotizaciones con la contratación EN_COTIZACION")
    if c.ofertas_abiertas:
        raise EstadoInvalidoError("Las ofertas ya fueron abiertas: no se admiten más cotizaciones")
    _exigir_f110(c)
    if any(q.nit_ci.upper() == datos["nit_ci"].upper() for q in c.cotizaciones):
        raise ReglaNegocioError("Ya existe una cotización de ese NIT/CI para esta contratación", "COTIZACION_DUPLICADA")
    ahora = _ahora()
    recibida = _aware(datos.get("fecha_recepcion")) or ahora
    if recibida > ahora + timedelta(minutes=1):
        raise ReglaNegocioError("La fecha y hora de recepción no puede ser futura", "RECEPCION_FUTURA")
    lim = _aware(c.fecha_limite_ofertas)
    if lim and recibida > lim:
        raise ReglaNegocioError("La oferta fue recibida después del plazo de presentación", "OFERTA_EXTEMPORANEA")
    q = CotizacionProveedor(
        contratacion_id=c.id, nit_ci=datos["nit_ci"].strip(), razon_social=datos["razon_social"].strip(),
        correo=datos.get("correo", ""), telefono=datos.get("telefono", ""), monto_total_ofertado=None,
        monto_cifrado=cifrado.cifrar_monto(datos["monto_total_ofertado"]),
        plazo_ofertado_dias=datos["plazo_ofertado_dias"], fecha_recepcion=recibida)
    c.cotizaciones.append(q)
    db.flush()
    _audit(db, u, "COTIZACION_REGISTRADA_SELLADA", c, None,
           {"cotizacion": str(q.id), "proveedor": q.razon_social, "recibida": recibida.isoformat()}, ip)
    return q


def abrir_ofertas(db: Session, u: Usuario, c: ContratacionMenor, ip: str = "") -> ContratacionMenor:
    if c.estado != Estado.EN_COTIZACION.value:
        raise EstadoInvalidoError("Solo se abren ofertas con la contratación EN_COTIZACION")
    if c.ofertas_abiertas:
        return c
    if not c.cotizaciones:
        raise ReglaNegocioError("No hay ofertas para abrir", "SIN_OFERTAS")
    lim = _aware(c.fecha_limite_ofertas)
    if lim and _ahora() < lim:
        raise ReglaNegocioError("Aún no vence el plazo de presentación de ofertas", "PLAZO_VIGENTE")
    for q in c.cotizaciones:
        q.monto_total_ofertado = cifrado.descifrar_monto(q.monto_cifrado)
    c.ofertas_abiertas = True
    db.flush()
    _audit(db, u, "OFERTAS_ABIERTAS", c, None, {"ofertas": len(c.cotizaciones)}, ip)
    return c


def calificar_cotizacion(db: Session, u: Usuario, c: ContratacionMenor, cot_id: uuid.UUID, datos: dict,
                         ip: str = "") -> CotizacionProveedor:
    if c.estado != Estado.EN_COTIZACION.value or not c.ofertas_abiertas:
        raise EstadoInvalidoError("La calificación se registra con las ofertas abiertas y la contratación EN_COTIZACION")
    q = next((x for x in c.cotizaciones if x.id == cot_id), None)
    if q is None:
        raise NoEncontradoError("Cotización no encontrada")
    if datos["registro_preferencia"] == "NINGUNO" and datos["registro_preferencia_valido"]:
        raise ReglaNegocioError("Indique el tipo de registro de preferencia (PRO_BOLIVIA o MYPE)", "PREFERENCIA_TIPO")
    antes = {"cumple": q.cumple_especificaciones, "margen": str(q.margen_preferencia_pct)}
    q.cumple_especificaciones = datos["cumple_especificaciones"]
    q.observaciones = datos.get("observaciones", "")
    q.registro_preferencia = datos["registro_preferencia"]
    q.registro_preferencia_valido = datos["registro_preferencia_valido"]
    q.margen_preferencia_pct = datos["margen_preferencia_pct"]
    db.flush()
    _audit(db, u, "COTIZACION_CALIFICADA", c, antes,
           {"cotizacion": str(q.id), "cumple": q.cumple_especificaciones, "margen": str(q.margen_preferencia_pct),
            "registro_valido": q.registro_preferencia_valido}, ip)
    return q


def _ofertas_in(c: ContratacionMenor) -> list[OfertaIn]:
    return [OfertaIn(id=q.id, razon_social=q.razon_social, monto=q.monto_total_ofertado or Decimal("0"),
                     plazo_dias=q.plazo_ofertado_dias, cumple=q.cumple_especificaciones,
                     fecha_recepcion=_aware(q.fecha_recepcion), margen_pct=q.margen_preferencia_pct,
                     registro_valido=q.registro_preferencia_valido) for q in c.cotizaciones]


def matriz(c: ContratacionMenor):
    """Vista previa de la evaluacion (no persiste). Solo con ofertas abiertas."""
    if not c.ofertas_abiertas:
        raise ReglaNegocioError("Las ofertas están selladas: ábralas al vencer el plazo", "OFERTAS_SELLADAS")
    return evaluar_ofertas(_ofertas_in(c), c.monto_referencial_total, c.plazo_dias_calendario)


def evaluar(db: Session, u: Usuario, c: ContratacionMenor, ip: str = "") -> ContratacionMenor:
    antes = _snap(c)
    if c.estado != Estado.EN_COTIZACION.value:
        raise EstadoInvalidoError(f"La acción 'evaluar' no es válida con la contratación en estado {c.estado}")
    if not c.ofertas_abiertas:
        raise ReglaNegocioError("Abra las ofertas antes de evaluar", "OFERTAS_SELLADAS")
    p = _params(db)
    minimo = parametros.get_int(p, "min_cotizaciones_consulta" if c.modalidad_cuantia ==
                                ModalidadCuantia.CONSULTA_PRECIOS.value else "min_cotizaciones_directa")
    if len(c.cotizaciones) < minimo:
        raise ReglaNegocioError(f"Se requieren al menos {minimo} cotización(es); hay {len(c.cotizaciones)}",
                                "COTIZACIONES_INSUFICIENTES")
    ev = evaluar_ofertas(_ofertas_in(c), c.monto_referencial_total, c.plazo_dias_calendario)
    if ev.recomendada is None:
        raise ReglaNegocioError("Ninguna oferta es elegible: corresponde declarar desierto el proceso", "SIN_ELEGIBLES")
    por_id = {str(e.id): e for e in ev.ofertas}
    for q in c.cotizaciones:
        e = por_id[str(q.id)]
        q.precio_evaluado, q.ranking, q.recomendada = e.precio_evaluado, e.ranking, e.recomendada
        q.motivo_descalificacion = e.motivo or None
    workflow.aplicar(c, "evaluar", u.rol)
    db.flush()
    generar_documento(db, c, TipoDoc.CUADRO_COMPARATIVO, u)
    _audit(db, u, "OFERTAS_EVALUADAS", c, antes,
           {**_snap(c), "recomendada": str(ev.recomendada.id), "desempate": ev.hay_desempate}, ip)
    return c


def adjudicar(db: Session, u: Usuario, c: ContratacionMenor, cot_id: uuid.UUID | None, motivo: str,
              ip: str = "") -> ContratacionMenor:
    antes = _snap(c)
    if c.estado != Estado.EVALUADO.value:
        raise EstadoInvalidoError(f"La acción 'adjudicar' no es válida con la contratación en estado {c.estado}")
    recomendada = next((q for q in c.cotizaciones if q.recomendada), None)
    elegida = recomendada if cot_id is None else next((q for q in c.cotizaciones if q.id == cot_id), None)
    if elegida is None:
        raise NoEncontradoError("Cotización no encontrada")
    if elegida.ranking is None:
        raise ReglaNegocioError("La oferta no es elegible: " + (elegida.motivo_descalificacion or ""), "OFERTA_NO_ELEGIBLE")
    if recomendada is not None and elegida.id != recomendada.id and len((motivo or "").strip()) < 10:
        raise ReglaNegocioError("Para adjudicar una oferta distinta de la recomendada debe fundamentarse el motivo",
                                "MOTIVO_REQUERIDO")
    workflow.aplicar(c, "adjudicar", u.rol)
    elegida.adjudicado = True
    c.fecha_adjudicacion = _ahora()
    c.rpa_id = u.id
    db.flush()
    generar_documento(db, c, TipoDoc.NOTA_ADJUDICACION, u, {"motivo": motivo})
    _audit(db, u, "ADJUDICADO", c, antes, {**_snap(c), "cotizacion": str(elegida.id), "motivo": motivo}, ip)
    return c


def declarar_desierta(db: Session, u: Usuario, c: ContratacionMenor, motivo: str, ip: str = "") -> ContratacionMenor:
    antes = _snap(c)
    workflow.aplicar(c, "declarar_desierta", u.rol)
    liberado = presupuesto.liberar(db, c)
    c.motivo_cierre = f"DESIERTO: {motivo}"
    db.flush()
    _audit(db, u, "DECLARADO_DESIERTO", c, antes, {**_snap(c), "motivo": motivo, "saldo_liberado": str(liberado)}, ip)
    return c


# ------------------------------------------------------------------ formalizacion y recepcion
def _adjudicada(c: ContratacionMenor) -> CotizacionProveedor | None:
    return next((q for q in c.cotizaciones if q.adjudicado), None)


def formalizar(db: Session, u: Usuario, c: ContratacionMenor, cuce: str | None, metodo_pedido: str | None,
               ip: str = "") -> ContratacionMenor:
    antes = _snap(c)
    if c.estado != Estado.ADJUDICADO.value:
        raise EstadoInvalidoError(f"La acción 'formalizar' no es válida con la contratación en estado {c.estado}")
    p = _params(db)
    errores = []
    if not c.preventivo_c31_nro:
        errores.append("Presupuesto debe registrar el N° de comprobante C-31 antes de formalizar")
    if c.modalidad_cuantia == ModalidadCuantia.CONSULTA_PRECIOS.value and not (cuce or c.cuce):
        errores.append("Registre el CUCE de la contratación (Consulta de Precios SICOES)")
    if errores:
        raise ReglaNegocioError("No puede formalizarse", "FORMALIZACION_INCOMPLETA", errores)
    adj = _adjudicada(c)
    plazo_max = parametros.get_int(p, "plazo_orden_max_dias")
    metodo = calc.determinar_formalizacion(c.plazo_dias_calendario, c.tipo_objeto, plazo_max)
    if metodo_pedido and metodo_pedido != metodo.value:
        if metodo == MetodoFormalizacion.CONTRATO:
            raise ReglaNegocioError(
                f"El plazo de {c.plazo_dias_calendario} días calendario (> {plazo_max}) obliga a emitir CONTRATO "
                "ADMINISTRATIVO: no se permite una orden simple", "FORMALIZACION_CONTRATO_OBLIGATORIO")
        raise ReglaNegocioError(f"Para este objeto y plazo corresponde {metodo.value}", "FORMALIZACION_INCORRECTA")
    workflow.aplicar(c, "formalizar", u.rol)
    c.metodo_formalizacion = metodo.value
    if cuce:
        c.cuce = cuce.strip()
    c.fecha_formalizacion = date.today()
    db.flush()
    tipo = TipoDoc.CONTRATO_ADMINISTRATIVO if metodo == MetodoFormalizacion.CONTRATO else TipoDoc.ORDEN_COMPRA_SERVICIO
    generar_documento(db, c, tipo, u)
    _audit(db, u, "FORMALIZADO", c, antes, {**_snap(c), "documento": tipo.value, "proveedor": adj.razon_social}, ip)
    return c


def recepcionar(db: Session, u: Usuario, c: ContratacionMenor, datos: dict, ip: str = "") -> tuple[ContratacionMenor, Recepcion]:
    antes = _snap(c)
    if c.estado != Estado.FORMALIZADO.value:
        raise EstadoInvalidoError(f"La acción 'recepcionar' no es válida con la contratación en estado {c.estado}")
    fecha = datos["fecha_recepcion"]
    if fecha > date.today():
        raise ReglaNegocioError("La fecha de recepción no puede ser futura", "RECEPCION_FUTURA")
    if c.fecha_formalizacion and fecha < c.fecha_formalizacion:
        raise ReglaNegocioError("La fecha de recepción no puede ser anterior a la formalización", "RECEPCION_ANTERIOR")
    adj = _adjudicada(c)
    por_numero = {d["numero"]: d for d in datos.get("detalle", [])}
    detalle: dict[str, dict] = {}
    todo_conforme = bool(datos["conforme"])
    for it in c.items:
        d = por_numero.get(it.numero)
        cant = Decimal(d["cantidad_recibida"]) if d else Decimal(it.cantidad)
        conforme_item = bool(d["conforme"]) if d else True
        if cant < Decimal(it.cantidad) or not conforme_item:
            todo_conforme = False
        detalle[str(it.numero)] = {"cantidad_recibida": str(cant), "conforme": conforme_item}
    if not todo_conforme and len((datos.get("observaciones") or "").strip()) < 10:
        raise ReglaNegocioError("Detalle las observaciones de la recepción (mínimo 10 caracteres)", "OBSERVACIONES_REQUERIDAS")
    limite = (c.fecha_formalizacion or fecha) + timedelta(days=adj.plazo_ofertado_dias if adj else c.plazo_dias_calendario)
    retraso = max(0, (fecha - limite).days)
    rec = Recepcion(contratacion_id=c.id, fecha_recepcion=fecha, conforme=todo_conforme,
                    observaciones=datos.get("observaciones", ""), detalle=detalle, dias_retraso=retraso,
                    created_by_id=u.id)
    if todo_conforme:
        prefijo = "NIA" if c.tipo_objeto == TipoObjeto.BIEN.value else "IC"
        rec.nro_nia = correlativo(db, prefijo, _params(db)["gestion"])
    c.recepciones.append(rec)
    db.flush()
    if todo_conforme:
        workflow.aplicar(c, "recepcionar", u.rol)
        db.flush()
        generar_documento(db, c, TipoDoc.ACTA_RECEPCION_FORM500, u, {"recepcion": rec})
    _audit(db, u, "RECEPCION_CONFORME" if todo_conforme else "RECEPCION_OBSERVADA", c, antes,
           {**_snap(c), "nia": rec.nro_nia, "dias_retraso": retraso}, ip)
    return c, rec


def devengar(db: Session, u: Usuario, c: ContratacionMenor, ip: str = "") -> ContratacionMenor:
    antes = _snap(c)
    if c.estado != Estado.RECEPCIONADO.value:
        raise EstadoInvalidoError(f"La acción 'devengar' no es válida con la contratación en estado {c.estado}")
    adj = _adjudicada(c)
    liberado = presupuesto.devengar(db, c, adj.monto_total_ofertado)
    workflow.aplicar(c, "devengar", u.rol)
    db.flush()
    _audit(db, u, "DEVENGADO", c, antes, {**_snap(c), "devengado": str(adj.monto_total_ofertado),
                                          "saldo_liberado": str(liberado)}, ip)
    return c


def anular(db: Session, u: Usuario, c: ContratacionMenor, motivo: str, ip: str = "") -> ContratacionMenor:
    antes = _snap(c)
    if u.rol == Rol.SOLICITANTE.value:
        _solo_creador(c, u)
    workflow.aplicar(c, "anular", u.rol)
    liberado = presupuesto.liberar(db, c)
    c.motivo_cierre = f"ANULADO: {motivo}"
    db.flush()
    _audit(db, u, "ANULADO", c, antes, {**_snap(c), "motivo": motivo, "saldo_liberado": str(liberado)}, ip)
    return c


# ------------------------------------------------------------------ consultas
def listar(db: Session, u: Usuario, estado: str | None = None, q: str | None = None, limite: int = 100):
    consulta = select(ContratacionMenor).order_by(ContratacionMenor.created_at.desc()).limit(limite)
    if u.rol == Rol.SOLICITANTE.value:
        consulta = consulta.where(ContratacionMenor.created_by_id == u.id)
    if estado:
        consulta = consulta.where(ContratacionMenor.estado == estado)
    if q:
        patron = f"%{q.lower()}%"
        consulta = consulta.where(func.lower(ContratacionMenor.objeto_contratacion).like(patron)
                                  | func.lower(ContratacionMenor.correlativo_interno).like(patron))
    return list(db.scalars(consulta))


def tablero(db: Session, u: Usuario) -> dict:
    todas = list(db.scalars(select(ContratacionMenor).where(
        ContratacionMenor.created_by_id == u.id) if u.rol == Rol.SOLICITANTE.value else select(ContratacionMenor)))
    por_estado: dict[str, int] = {e.value: 0 for e in Estado}
    for c in todas:
        por_estado[c.estado] += 1
    pend_estados = {e.value for e in workflow.PENDIENTES[Rol(u.rol)]}
    pendientes = [c for c in todas if c.estado in pend_estados]
    pendientes.sort(key=lambda c: c.updated_at or c.created_at, reverse=True)
    return {"por_estado": por_estado, "pendientes": pendientes[:20], "total": len(todas)}
