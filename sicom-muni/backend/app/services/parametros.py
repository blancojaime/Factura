"""Parametros institucionales y de reglas (tabla parametros_institucionales + valores por defecto)."""
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ParametroInstitucional

DEFAULTS: dict[str, tuple[str, str]] = {
    "nombre_gam": ("GOBIERNO AUTÓNOMO MUNICIPAL DE EJEMPLO", "Nombre del GAM para el membrete de los documentos"),
    "ciudad": ("", "Ciudad que figura en los documentos"),
    "da": ("01", "Código de Dirección Administrativa (DA)"),
    "ue": ("001", "Código de Unidad Ejecutora (UE)"),
    "gestion": (str(date.today().year), "Gestión fiscal vigente"),
    "logo_url": ("", "URL o ruta del logotipo oficial"),
    "tope_contratacion_menor": ("50000", "Bs. Límite de Contratación Menor (verificar con la norma vigente)"),
    "tope_compra_directa": ("20000", "Bs. Hasta este monto: compra directa sin consulta de precios SICOES"),
    "plazo_orden_max_dias": ("15", "Días calendario: hasta este plazo se emite Orden; sobre él, Contrato"),
    "min_cotizaciones_consulta": ("3", "Cotizaciones mínimas con consulta de precios (supuesto; verificar)"),
    "min_cotizaciones_directa": ("1", "Cotizaciones mínimas en compra directa"),
    "chb_min_justificacion": ("80", "Longitud mínima de la justificación de excepción CHB"),
    "url_publica": ("", "URL pública base para los QR de verificación (si vacío, usa PUBLIC_BASE_URL)"),
}


def obtener_todos(db: Session) -> dict[str, str]:
    valores = {k: v[0] for k, v in DEFAULTS.items()}
    for p in db.scalars(select(ParametroInstitucional)):
        valores[p.clave] = p.valor
    return valores


def get_decimal(params: dict[str, str], clave: str) -> Decimal:
    return Decimal(params.get(clave) or DEFAULTS[clave][0])


def get_int(params: dict[str, str], clave: str) -> int:
    return int(params.get(clave) or DEFAULTS[clave][0])


def guardar(db: Session, clave: str, valor: str) -> ParametroInstitucional:
    p = db.get(ParametroInstitucional, clave)
    if p is None:
        p = ParametroInstitucional(clave=clave, valor=valor, descripcion=DEFAULTS.get(clave, ("", ""))[1])
        db.add(p)
    else:
        p.valor = valor
    return p
