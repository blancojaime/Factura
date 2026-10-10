"""Expediente digital criptografico: genera los PDF (HTML -> WeasyPrint) del tramite.

Cada PDF incluye membrete institucional, marca de agua con el estado del tramite, un QR que apunta a la
verificacion publica de autenticidad y, al pie, el hash SHA-256 del CONTENIDO canonico del documento.

Nota tecnica: un archivo no puede imprimir su propio hash (el hash cambiaria al imprimirlo). Por eso:
  * lo impreso al pie es el SHA-256 del contenido canonico (datos + version de plantilla);
  * el SHA-256 del archivo PDF final se guarda en la base y se muestra/compara en la pagina publica de
    verificacion (`/verificar/{id}`), que tambien permite subir un PDF para comprobar que no fue alterado.
"""
import base64
import hashlib
import io
import json
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import qrcode
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import func, select
from sqlalchemy.orm import Session
try:  # WeasyPrint necesita librerias del sistema (pango); si faltan se guarda el documento en HTML imprimible
    from weasyprint import HTML, URLFetcher
    PDF_DISPONIBLE = True
except (ImportError, OSError):  # pragma: no cover - depende del equipo
    HTML = URLFetcher = None  # type: ignore[assignment,misc]
    PDF_DISPONIBLE = False

from ..config import get_settings
from ..enums import Estado, MetodoFormalizacion, TipoDoc
from ..errors import ReglaNegocioError
from ..models import (
    ContratacionMenor, CotizacionProveedor, DocumentoExpediente, PartidaPresupuestaria, Recepcion, Usuario,
)
from . import bloque_sigep, parametros
from .evaluador_ofertas import OfertaIn
from .evaluador_ofertas import evaluar as evaluar_ofertas
from .numeros_letras import monto_literal
from .storage import get_storage

TEMPLATE_VERSION = "1.0"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

TITULOS = {
    TipoDoc.C1_SOLICITUD: "Formulario C-1 — Solicitud de Contratación Menor",
    TipoDoc.INFORME_EXCEPCION_CHB: "Informe Técnico-Legal de Justificación de Compra fuera del Catálogo CHB",
    TipoDoc.CERTIFICACION_C31: "Certificación de Pre-compromiso Presupuestario (datos espejo C-31 SIGEP)",
    TipoDoc.FICHA_COTIZACION: "Ficha de Cotización",
    TipoDoc.CUADRO_COMPARATIVO: "Cuadro Comparativo de Ofertas y Acta de Calificación",
    TipoDoc.NOTA_ADJUDICACION: "Resolución / Nota de Adjudicación",
    TipoDoc.ORDEN_COMPRA_SERVICIO: "Orden",
    TipoDoc.CONTRATO_ADMINISTRATIVO: "Contrato Administrativo de Contratación Menor",
    TipoDoc.ACTA_RECEPCION_FORM500: "Acta de Recepción Definitiva — Formulario 500 SICOES",
}


def _bs(x) -> str:
    if x is None or x == "":
        return ""
    d = Decimal(str(x))
    s = f"{d:,.2f}"  # 18,500.00
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _fecha(x) -> str:
    if not x:
        return ""
    if isinstance(x, str):
        try:
            x = datetime.fromisoformat(x)
        except ValueError:
            return x
    return x.strftime("%d/%m/%Y")


def _fechahora(x) -> str:
    if not x:
        return ""
    if isinstance(x, str):
        try:
            x = datetime.fromisoformat(x)
        except ValueError:
            return x
    return x.strftime("%d/%m/%Y %H:%M")


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=select_autoescape(["html"]))
    env.filters["bs"] = _bs
    env.filters["fecha"] = _fecha
    env.filters["fechahora"] = _fechahora
    return env


if PDF_DISPONIBLE:
    class _SoloImagenesEmbebidas(URLFetcher):
        """Defensa en profundidad: solo se admiten recursos data: (evita peticiones externas / SSRF)."""

        def fetch(self, url, headers=None):
            if not str(url).startswith("data:"):
                raise ValueError(f"Recurso externo bloqueado: {url}")
            return super().fetch(url, headers)

AVISO_HTML = ('<style>@media print{.aviso-html{display:none}}</style><div class="aviso-html" style="background:#fff4ce;'
              'border:1px solid #e0c36a;padding:8px;font:13px sans-serif;margin:0 0 8px">Vista HTML (modo de prueba sin motor PDF). '
              'Para obtener un PDF use Ctrl+P y elija «Guardar como PDF».</div>')


def qr_data_uri(texto: str) -> str:
    img = qrcode.make(texto, box_size=4, border=1)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def hash_contenido(contexto: dict) -> str:
    canon = json.dumps(contexto, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def url_verificacion(params: dict[str, str], doc_id: uuid.UUID) -> str:
    base = (params.get("url_publica") or get_settings().public_base_url).rstrip("/")
    return f"{base}/verificar/{doc_id}"


# ------------------------------------------------------------------ contexto por documento
def _usuario(db: Session, uid) -> dict:
    u = db.get(Usuario, uid) if uid else None
    return {"nombre": u.nombre_completo if u else "", "cargo": u.cargo if u else ""}


def _base_context(db: Session, c: ContratacionMenor, params: dict[str, str]) -> dict:
    items = [{
        "numero": i.numero, "codigo_unspsc": i.codigo_unspsc, "partida": i.partida_gasto,
        "descripcion": i.descripcion_especifica, "unidad": i.unidad_medida, "cantidad": str(i.cantidad),
        "precio": str(i.precio_unitario_ref), "subtotal": str(i.subtotal), "estado_chb": i.estado_chb,
    } for i in c.items]
    return {
        "gam": {"nombre": params["nombre_gam"], "ciudad": params["ciudad"], "da": params["da"], "ue": params["ue"],
                "logo": params["logo_url"] if params["logo_url"].startswith("data:") else ""},
        "tramite": {
            "correlativo": c.correlativo_interno, "objeto": c.objeto_contratacion, "tipo_objeto": c.tipo_objeto,
            "monto_referencial": str(c.monto_referencial_total), "monto_literal": monto_literal(c.monto_referencial_total),
            "plazo_dias": c.plazo_dias_calendario, "metodo": c.metodo_formalizacion, "modalidad": c.modalidad_cuantia,
            "formulario_110": c.nro_formulario_110, "cuce": c.cuce, "c31": c.preventivo_c31_nro,
            "estado": c.estado, "unidad_solicitante": c.unidad_solicitante, "lugar_entrega": c.lugar_entrega,
            "justificacion": c.justificacion, "especificaciones": c.especificaciones_tecnicas,
            "fecha_limite_ofertas": c.fecha_limite_ofertas.isoformat() if c.fecha_limite_ofertas else None,
        },
        "solicitante": _usuario(db, c.created_by_id),
        "rpa": _usuario(db, c.rpa_id),
        "items": items,
        "fecha_emision": date.today().isoformat(),
    }


def _adjudicada(c: ContratacionMenor) -> CotizacionProveedor | None:
    return next((q for q in c.cotizaciones if q.adjudicado), None)


def construir_contexto(db: Session, c: ContratacionMenor, tipo: TipoDoc, params: dict[str, str],
                       extra: dict | None = None) -> dict:
    ctx = _base_context(db, c, params)
    extra = extra or {}
    if tipo == TipoDoc.INFORME_EXCEPCION_CHB:
        ctx["excepcion"] = {
            "justificacion": c.justificacion_excepcion_chb or "",
            "codigo_autorizacion": c.codigo_autorizacion_chb or "",
            "items": [i for i in ctx["items"] if i["estado_chb"] in ("EXCEPCION_INCOMPATIBILIDAD", "SIN_COINCIDENCIA")],
        }
    elif tipo == TipoDoc.CERTIFICACION_C31:
        lineas = [(p.partida, p.importe) for p in c.preventivos]
        ctx["sigep"] = bloque_sigep.construir(params, lineas)
        ctx["preventivos"] = [{
            "partida": p.partida.codigo_partida, "descripcion": p.partida.descripcion, "importe": str(p.importe),
            "estado": p.estado, "saldo_actual": str(p.partida.saldo_disponible)} for p in c.preventivos]
    elif tipo == TipoDoc.FICHA_COTIZACION:
        ctx["destinatarios"] = extra.get("destinatarios", [])
    elif tipo == TipoDoc.CUADRO_COMPARATIVO:
        ofertas = [OfertaIn(id=str(q.id), razon_social=q.razon_social, monto=q.monto_total_ofertado or Decimal("0"),
                            plazo_dias=q.plazo_ofertado_dias, cumple=q.cumple_especificaciones,
                            fecha_recepcion=q.fecha_recepcion, margen_pct=q.margen_preferencia_pct,
                            registro_valido=q.registro_preferencia_valido) for q in c.cotizaciones]
        ev = evaluar_ofertas(ofertas, c.monto_referencial_total, c.plazo_dias_calendario)
        ctx["evaluacion"] = {
            "criterio": "Precio Evaluado Más Bajo entre las ofertas que cumplen las especificaciones técnicas",
            "desempate": ev.hay_desempate,
            "ofertas": [{
                "razon_social": e.razon_social, "monto": str(e.monto), "plazo": e.plazo_dias,
                "margen": str(e.margen_aplicado_pct), "precio_evaluado": str(e.precio_evaluado),
                "ranking": e.ranking, "recomendada": e.recomendada, "elegible": e.elegible, "motivo": e.motivo,
                "recibida": e.fecha_recepcion.isoformat(),
            } for e in ev.ofertas],
        }
    elif tipo in (TipoDoc.NOTA_ADJUDICACION, TipoDoc.ORDEN_COMPRA_SERVICIO, TipoDoc.CONTRATO_ADMINISTRATIVO):
        adj = _adjudicada(c)
        if adj is None:
            raise ReglaNegocioError("No hay oferta adjudicada", codigo="SIN_ADJUDICADO")
        ctx["adjudicatario"] = {
            "razon_social": adj.razon_social, "nit_ci": adj.nit_ci, "correo": adj.correo, "telefono": adj.telefono,
            "monto": str(adj.monto_total_ofertado), "monto_literal": monto_literal(adj.monto_total_ofertado),
            "plazo": adj.plazo_ofertado_dias}
        ctx["motivo_adjudicacion"] = extra.get("motivo", "")
        if tipo == TipoDoc.ORDEN_COMPRA_SERVICIO:
            ctx["titulo_orden"] = "ORDEN DE COMPRA" if c.metodo_formalizacion == MetodoFormalizacion.ORDEN_COMPRA.value \
                else "ORDEN DE SERVICIO"
    elif tipo == TipoDoc.ACTA_RECEPCION_FORM500:
        adj = _adjudicada(c)
        rec: Recepcion | None = extra.get("recepcion")
        if rec is None:
            raise ReglaNegocioError("No hay recepción registrada", codigo="SIN_RECEPCION")
        ctx["adjudicatario"] = {"razon_social": adj.razon_social, "nit_ci": adj.nit_ci,
                                "monto": str(adj.monto_total_ofertado)} if adj else {}
        ctx["recepcion"] = {
            "fecha": rec.fecha_recepcion.isoformat(), "conforme": rec.conforme, "observaciones": rec.observaciones,
            "nia": rec.nro_nia, "dias_retraso": rec.dias_retraso, "detalle": rec.detalle,
            "responsable": _usuario(db, rec.created_by_id)}
    return ctx


# ------------------------------------------------------------------ generacion
def _plantilla(tipo: TipoDoc) -> str:
    return f"docs/{tipo.value.lower()}.html"


def generar_documento(db: Session, c: ContratacionMenor, tipo: TipoDoc, usuario: Usuario | None,
                      extra: dict | None = None) -> DocumentoExpediente:
    params = parametros.obtener_todos(db)
    contexto = construir_contexto(db, c, tipo, params, extra)
    doc_id = uuid.uuid4()
    contenido_canonico = {"tipo": tipo.value, "plantilla": TEMPLATE_VERSION, "estado": c.estado, "datos": contexto}
    h_contenido = hash_contenido(contenido_canonico)
    version = (db.scalar(select(func.count()).select_from(DocumentoExpediente).where(
        DocumentoExpediente.contratacion_id == c.id, DocumentoExpediente.tipo_doc == tipo.value)) or 0) + 1
    titulo = TITULOS[tipo]
    if tipo == TipoDoc.ORDEN_COMPRA_SERVICIO:
        titulo = contexto["titulo_orden"].title().replace("De", "de")
    html = _env().get_template(_plantilla(tipo)).render(
        tipo=tipo.value, titulo=titulo, ctx=contexto, estado=c.estado.replace("_", " "), version=version,
        hash_contenido=h_contenido, qr=qr_data_uri(url_verificacion(params, doc_id)),
        url_verificacion=url_verificacion(params, doc_id), generado=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
        generado_por=usuario.nombre_completo if usuario else "Sistema")
    if PDF_DISPONIBLE:
        pdf, ext, mime = HTML(string=html, url_fetcher=_SoloImagenesEmbebidas()).write_pdf(), "pdf", "application/pdf"
    else:
        pdf, ext, mime = html.replace("<body>", "<body>" + AVISO_HTML, 1).encode("utf-8"), "html", "text/html"
    h_archivo = hashlib.sha256(pdf).hexdigest()
    clave = f"expedientes/{c.correlativo_interno}/{tipo.value}_v{version}_{doc_id}.{ext}"
    get_storage().put(clave, pdf, mime)
    doc = DocumentoExpediente(
        id=doc_id, contratacion=c, tipo_doc=tipo.value, ruta_archivo=clave, hash_sha256=h_archivo,
        hash_contenido=h_contenido, version=version, estado_tramite=c.estado,
        generado_por_id=usuario.id if usuario else None)
    db.add(doc)
    db.flush()
    return doc
