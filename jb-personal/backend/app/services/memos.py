"""Memorándums de RR.HH.: Designación de Cargo, Aceptación de Renuncia y Agradecimiento de Funciones.

* Redacción basada en los modelos del municipio (editable en «Plantillas»). Variables entre llaves: {cargo}, {fecha_efectiva}...
* CITE correlativo ÚNICO por gestión para todos los tipos: «<prefijo>/N°077/2026». El número se asigna al EMITIR
  (atómico, sin reutilización: un memorándum anulado conserva su número). Los borradores no consumen número.
* Al emitir puede aplicar el efecto en el sistema: Designación -> cargo y N° de documento del contrato;
  Aceptación de renuncia / Agradecimiento -> baja del contrato (fecha efectiva y causal), reflejada en las planillas.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import audit
from ..models import Contrato, Correlativo, Empleado, Entidad, MemoConfig, MemoPlantilla, Memorandum
from .proceso import ReglaNegocio, exigir_abierto, siguiente_correlativo

TIPOS = {"DESIGNACION": "Memorándum de Designación de Cargo",
         "ACEPTACION_RENUNCIA": "Memorándum de Aceptación de Renuncia",
         "AGRADECIMIENTO": "Memorándum de Agradecimiento de Funciones"}
SERIE = "MEMORANDUM"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

PLANTILLAS = {
    "DESIGNACION": ("DESIGNACIÓN DE CARGO", """En cumplimiento a la Ley N° 2027 Estatuto del Funcionario Público, el art. 26 N° 10 de la Ley N° 482, normas básicas del sistema de administración de personal, por disposición de este despacho, por medio de la presente se le hace extensivo el presente **MEMORANDUM DE DESIGNACIÓN**, respecto al cargo público de:

## {cargo_mayus}

Cargo que deberá ejercer sus funciones dentro del marco normativo vigente a partir de la presente fecha {fecha_efectiva}, por ello a partir de la presente es responsable de todos los actos y omisiones en el ejercicio de sus funciones, así como la documentación existente y la que genere en el cargo designado, consiguientemente deberá recibir el inventario correspondiente.

Deseándole éxitos en sus funciones y recordarle que las obligaciones de las servidoras y servidores públicos se encuentran suscritas al cumplimiento de la Constitución Política del Estado, Ley N° 482 Ley de Gobiernos Autónomos Municipales, Ley N° 2027 Estatuto del Funcionario Público, reglamento interno y el manual de funciones del {entidad}, bajo los principios de eficacia, economía, calidad, transparencia y licitud en el marco de la Ley N° 1178 Ley de Administración y Control Gubernamentales concordante con el Decreto Supremo N° 23318-A de 3 de noviembre de 1992, Ley N° 004 Ley de lucha contra la corrupción, enriquecimiento ilícito e investigación de fortunas "Marcelo Quiroga Santa Cruz".

Sin otro particular, se dispone su cumplimiento.

Atentamente.-"""),
    "ACEPTACION_RENUNCIA": ("ACEPTACIÓN DE RENUNCIA AL CARGO", """En cumplimiento a la Ley N° 482 de Gobiernos Autónomos Municipales, {decreto_estructura} que aprueba la Estructura Organizacional del {entidad} de la Gestión {gestion}, y en ATENCIÓN A LA HOJA DE RUTA CON REFERENCIA **RENUNCIA IRREVOCABLE AL CARGO DE {cargo_mayus}**, en fecha {fecha_renuncia} se comunica que es **ACEPTADA SU RENUNCIA AL CARGO DE {cargo_mayus}** del {entidad}, por lo cual la **RELACIÓN LABORAL** que vincula quedará extinguida a partir del **{fecha_efectiva}**.

En consecuencia, como corresponde de acuerdo a norma, usted deberá proceder a la entrega de toda la documentación e informe de actividades y toda la documentación generada en medio magnético, en un plazo de {plazo_entrega_texto} días hábiles, activos fijos y/o valores asignados a su persona. Asimismo, recordamos a usted que tiene la obligación de presentar su Declaración Jurada de Bienes y Rentas "Después del ejercicio del cargo" y remitir {copias_dj_texto} copias al Área de Recursos Humanos en un plazo máximo de {plazo_dj_dias} días calendario, objeto de evitar la contravención a la Ley N° 1178 del 20 de julio de 1990, la Responsabilidad por la Función Pública, D.S. 23318-A, Ley 2027 Estatuto del Funcionario Público, Reglamento Interno del {entidad} y demás normativa vigente.

Agradecemos a usted por el trabajo desempeñado en el {entidad}.

Atentamente."""),
    "AGRADECIMIENTO": ("AGRADECIMIENTO DE FUNCIONES", """El Ejecutivo Municipal del {entidad} representado por su máxima autoridad **{mae_nombre} {mae_cargo_mayus}**, y en uso de las atribuciones conferidas por el art. 26 de la Ley N° 482 de Gobiernos Autónomos Municipales, se comunica a usted **SU AGRADECIMIENTO** por la conclusión de sus funciones **{cargo_mayus}**, con efecto a partir de la fecha {fecha_efectiva}.

En aplicación de la Ley N° 1178 (SAFCO) y las Normas Básicas del Sistema de Administración de Bienes y Servicios, se instruye que proceda de forma inmediata y obligatoria a la entrega formal, completa y documentada de:

- Bienes muebles e inmuebles bajo su responsabilidad.
- Archivos físicos y digitales.
- Documentación administrativa y técnica.
- Informes y asuntos pendientes.

La entrega deberá realizarse mediante Acta de Entrega y Recepción, debidamente suscrita con la autoridad o servidor público designado, adjuntando inventarios y respaldos correspondientes.

Se deja expresa constancia que el incumplimiento, retraso u omisión en la entrega generará la determinación de responsabilidades administrativas, civiles y/o penales, conforme a normativa vigente.

Sin otro particular, se dispone su estricto cumplimiento.
Atentamente.-"""),
}
NUM_TXT = {1: "uno (1)", 2: "dos (2)", 3: "tres (3)", 4: "cuatro (4)", 5: "cinco (5)", 10: "diez (10)"}


def fecha_larga(d: date | str | None) -> str:
    if not d:
        return "[COMPLETAR: fecha]"
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def get_config(db: Session) -> MemoConfig:
    c = db.get(MemoConfig, 1)
    if not c:
        c = MemoConfig(id=1)
        db.add(c)
        db.flush()
    return c


def sembrar(db: Session) -> None:
    get_config(db)
    for tipo, (ref, cuerpo) in PLANTILLAS.items():
        if not db.get(MemoPlantilla, tipo):
            db.add(MemoPlantilla(tipo=tipo, referencia=ref, cuerpo=cuerpo))


def contexto(db: Session, tipo: str, d: dict) -> dict:
    ent, cfg = db.get(Entidad, 1), get_config(db)
    cargo = (d.get("cargo") or "").strip()
    n = lambda k, v: int(d.get(k) or v)  # noqa: E731
    mae_n = cfg.firmante_nombre or ent.mae_nombre
    mae_c = cfg.firmante_cargo or ent.mae_cargo
    return {
        "entidad": ent.nombre, "ciudad": ent.ciudad, "gestion": (d.get("fecha") or date.today().isoformat())[:4],
        "destinatario": d.get("destinatario", ""), "cargo": cargo, "cargo_mayus": cargo.upper(),
        "fecha": fecha_larga(d.get("fecha")), "fecha_efectiva": fecha_larga(d.get("fecha_efectiva")),
        "fecha_renuncia": fecha_larga(d.get("fecha_renuncia")) if tipo == "ACEPTACION_RENUNCIA" else "",
        "decreto_estructura": (d.get("decreto_estructura") or cfg.decreto_estructura or "[COMPLETAR: Decreto Municipal de la Estructura Organizacional]"),
        "plazo_entrega_dias": n("plazo_entrega_dias", 3), "plazo_entrega_texto": NUM_TXT.get(n("plazo_entrega_dias", 3), str(n("plazo_entrega_dias", 3))),
        "plazo_dj_dias": n("plazo_dj_dias", 30), "copias_dj": n("copias_dj", 3), "copias_dj_texto": NUM_TXT.get(n("copias_dj", 3), str(n("copias_dj", 3))),
        "mae_nombre": mae_n or "[COMPLETAR: nombre de la MAE]", "mae_cargo": mae_c, "mae_cargo_mayus": mae_c.upper(),
    }


def redactar(db: Session, tipo: str, d: dict) -> dict:
    if tipo not in TIPOS:
        raise ReglaNegocio("Tipo de memorándum inválido")
    p = db.get(MemoPlantilla, tipo)
    ref, cuerpo = (p.referencia, p.cuerpo) if p else PLANTILLAS[tipo]
    ctx = contexto(db, tipo, d)
    # sustitución ESTRICTA de {nombre}: solo identificadores simples (no se evalúan atributos ni índices de la plantilla)
    cuerpo = re.sub(r"\{(\w+)\}", lambda m: str(ctx[m.group(1)]) if m.group(1) in ctx else f"[COMPLETAR: {m.group(1)}]", cuerpo)
    return {"referencia": ref, "cuerpo": cuerpo}


def formato_cite(prefijo: str, n: int, gestion: int) -> str:
    return f"{prefijo.strip('/ ')}/N°{n:03d}/{gestion}"


# ----------------------------------------------------------------------------- ciclo de vida
def _efecto_baja(db: Session, m: Memorandum, datos: dict, usuario: str) -> str:
    emp = m.empleado
    if not emp:
        return ""
    cont = [c for c in emp.contratos if c.fecha_inicio <= m.fecha_efectiva and (c.fecha_baja is None or c.fecha_baja >= m.fecha_efectiva)]
    if not cont:
        raise ReglaNegocio("El servidor no tiene un contrato vigente a la fecha efectiva: no se puede registrar la baja")
    c = max(cont, key=lambda x: x.fecha_inicio)
    exigir_abierto(db, m.fecha_efectiva)
    causal = "RENUNCIA" if m.tipo == "ACEPTACION_RENUNCIA" else datos.get("causal", "CONCLUSION_CONTRATO")
    c.fecha_baja, c.causal_baja = m.fecha_efectiva, causal
    emp.activo = m.fecha_efectiva > date.today()                                 # sigue activo hasta la fecha efectiva
    datos["contrato_baja_id"] = c.id
    return f"Baja registrada: contrato {c.id}, {m.fecha_efectiva:%d/%m/%Y}, causal {causal}"


def emitir(db: Session, m: Memorandum, usuario: str, registrar_baja: bool | None = None) -> Memorandum:
    if m.estado != "BORRADOR":
        raise ReglaNegocio("Solo se puede emitir un memorándum en BORRADOR")
    if "[COMPLETAR" in m.cuerpo or "[COMPLETAR" in m.cargo or "[COMPLETAR" in m.destinatario:
        raise ReglaNegocio("El texto aún tiene campos por completar ([COMPLETAR: …]). Edítelo antes de emitir")
    datos = json.loads(m.datos or "{}")
    if registrar_baja is None:
        registrar_baja = bool(datos.get("registrar_baja"))
    if registrar_baja and m.tipo == "DESIGNACION":
        raise ReglaNegocio("Una designación no registra bajas")
    efecto = ""
    if registrar_baja and m.tipo != "DESIGNACION":
        if not m.empleado_id:
            raise ReglaNegocio("Para registrar la baja debe vincular el memorándum a un servidor registrado")
        efecto = _efecto_baja(db, m, datos, usuario)          # valida ANTES de consumir el correlativo
    gestion = m.fecha.year
    n = siguiente_correlativo(db, SERIE, gestion)
    cfg = get_config(db)
    m.gestion, m.correlativo = gestion, n
    m.cite = formato_cite(cfg.prefijo, n, gestion)
    m.estado, m.emitido_por, m.emitido_en = "EMITIDO", usuario, datetime.now()
    m.firmante_nombre = m.firmante_nombre or cfg.firmante_nombre or db.get(Entidad, 1).mae_nombre
    m.firmante_cargo = m.firmante_cargo or cfg.firmante_cargo
    if m.empleado:                                              # coherencia con el expediente / planillas
        cont = [c for c in m.empleado.contratos if c.fecha_inicio <= m.fecha_efectiva and (c.fecha_baja is None or c.fecha_baja >= m.fecha_efectiva)]
        if cont:
            c = max(cont, key=lambda x: x.fecha_inicio)
            if m.tipo == "DESIGNACION":
                if not c.nro_documento:
                    c.nro_documento = m.cite
                if datos.get("actualizar_cargo", True) and m.cargo:
                    m.empleado.cargo = m.cargo
                efecto = f"Contrato {c.id}: N° de documento {m.cite}" + ("; cargo actualizado" if datos.get("actualizar_cargo", True) else "")
            elif registrar_baja:
                c.nro_documento = m.cite                         # los desvinculados citan el memorándum
    m.efecto_aplicado, m.datos = efecto, json.dumps(datos, ensure_ascii=False)
    audit.registrar(db, usuario, "EMITIR_MEMORANDUM", "memorandum", m.id, {"cite": m.cite, "tipo": m.tipo, "destinatario": m.destinatario, "efecto": efecto})
    return m


def anular(db: Session, m: Memorandum, motivo: str, usuario: str) -> Memorandum:
    if m.estado != "EMITIDO":
        raise ReglaNegocio("Solo se anula un memorándum EMITIDO (los borradores se eliminan)")
    if len(motivo.strip()) < 10:
        raise ReglaNegocio("Indique el motivo de la anulación (mínimo 10 caracteres)")
    datos = json.loads(m.datos or "{}")
    cid = datos.get("contrato_baja_id")
    if cid:                                                       # revierte la baja que este memorándum registró
        c = db.get(Contrato, cid)
        if c and c.fecha_baja == m.fecha_efectiva:
            exigir_abierto(db, m.fecha_efectiva)
            c.fecha_baja, c.causal_baja = None, ""
            c.empleado.activo = True
    m.estado, m.motivo_anulacion = "ANULADO", motivo.strip()
    audit.registrar(db, usuario, "ANULAR_MEMORANDUM", "memorandum", m.id, {"cite": m.cite, "motivo": motivo})
    return m                                                      # el número NO se reutiliza


# ----------------------------------------------------------------------------- control de cites
def resumen_cites(db: Session, gestion: int) -> dict:
    rows = db.execute(select(Memorandum).where(Memorandum.gestion == gestion).order_by(Memorandum.correlativo)).scalars().unique().all()
    ultimo = db.execute(select(Correlativo.ultimo).where(Correlativo.tipo == SERIE, Correlativo.gestion == gestion)).scalar() or 0
    por_n = {r.correlativo: r for r in rows}
    detalle = []
    for n in range(1, ultimo + 1):
        r = por_n.get(n)
        detalle.append({"n": n, "cite": r.cite if r else "", "estado": r.estado if r else "SALTADO", "tipo": TIPOS.get(r.tipo, "") if r else "",
                        "destinatario": r.destinatario if r else "", "fecha": r.fecha.isoformat() if r else ""})
    return {"gestion": gestion, "ultimo": ultimo, "siguiente": ultimo + 1, "emitidos": sum(1 for r in rows if r.estado == "EMITIDO"),
            "anulados": sum(1 for r in rows if r.estado == "ANULADO"), "saltados": [d["n"] for d in detalle if d["estado"] == "SALTADO"], "detalle": detalle}


def fijar_siguiente(db: Session, gestion: int, numero: int, usuario: str, motivo: str) -> dict:
    """Continúa una numeración llevada antes en papel (p. ej. el próximo memorándum será el N° 083). Nunca retrocede."""
    if len(motivo.strip()) < 10:
        raise ReglaNegocio("Indique el motivo (mínimo 10 caracteres)")
    fila = db.get(Correlativo, (SERIE, gestion))
    if fila is None:
        fila = Correlativo(tipo=SERIE, gestion=gestion, ultimo=0)
        db.add(fila)
        db.flush()
    if numero - 1 < fila.ultimo:
        raise ReglaNegocio(f"No se puede retroceder: el último número usado es {fila.ultimo}; el siguiente mínimo es {fila.ultimo + 1}")
    anterior, fila.ultimo = fila.ultimo, numero - 1
    audit.registrar(db, usuario, "FIJAR_CORRELATIVO_MEMO", "correlativo", f"{SERIE}/{gestion}", {"de": anterior + 1, "a": numero, "motivo": motivo})
    return resumen_cites(db, gestion)


def series_cites(db: Session) -> list[dict]:
    """Vista general de TODAS las series de cites del sistema (memorándums, instructivos, boletas, informes)."""
    nombres = {"MEMORANDUM": "Memorándums", "INSTRUCTIVO": "Instructivos", "BOLETA": "Boletas de permiso", "INFORME_ASIST": "Informes de asistencia"}
    return [{"serie": c.tipo, "nombre": nombres.get(c.tipo, c.tipo), "gestion": c.gestion, "ultimo": c.ultimo, "siguiente": c.ultimo + 1}
            for c in db.execute(select(Correlativo).order_by(Correlativo.gestion.desc(), Correlativo.tipo)).scalars()]
