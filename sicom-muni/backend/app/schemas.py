"""Esquemas Pydantic v2 de entrada y salida de la API."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import Rol, TipoObjeto


class Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------- auth / usuarios
class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=1, max_length=200)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UsuarioOut(Base):
    id: uuid.UUID
    username: str
    nombre_completo: str
    cargo: str
    rol: str
    email: str
    activo: bool
    created_at: datetime


class UsuarioCreate(BaseModel):
    username: str = Field(min_length=3, max_length=60, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str
    nombre_completo: str = Field(min_length=3, max_length=160)
    cargo: str = ""
    rol: Rol
    email: str = ""


class UsuarioUpdate(BaseModel):
    nombre_completo: str | None = None
    cargo: str | None = None
    rol: Rol | None = None
    email: str | None = None
    activo: bool | None = None
    password: str | None = None


# ---------------- parametros / partidas / catalogo
class ParametroOut(BaseModel):
    clave: str
    valor: str
    descripcion: str = ""


class ParametroIn(BaseModel):
    valor: str = Field(max_length=100_000)


class PartidaIn(BaseModel):
    codigo_partida: str = Field(pattern=r"^[1-4]\d{4}$")
    descripcion: str = Field(min_length=3, max_length=200)
    saldo_disponible: Decimal = Field(ge=0)
    gestion: int = Field(ge=2000, le=2100)
    programa: str = ""
    proyecto: str = ""
    actividad: str = ""
    fuente: str = ""
    organismo: str = ""


class PartidaOut(Base):
    id: uuid.UUID
    codigo_partida: str
    descripcion: str
    saldo_disponible: Decimal
    gestion: int
    programa: str
    proyecto: str
    actividad: str
    fuente: str
    organismo: str
    monto_aprobado: Decimal


class CatalogoOut(Base):
    id: uuid.UUID
    codigo_unspsc: str
    descripcion_bien: str
    unidad_medida: str
    precio_referencial_nacional: Decimal | None
    activo: bool


class CatalogoIn(BaseModel):
    codigo_unspsc: str = Field(pattern=r"^\d{8}$")
    descripcion_bien: str = Field(min_length=3, max_length=250)
    unidad_medida: str = ""
    precio_referencial_nacional: Decimal | None = None
    activo: bool = True


class ConsultaCHBOut(BaseModel):
    codigo_unspsc: str
    en_catalogo: bool
    descripcion_bien: str | None = None
    unidad_medida: str | None = None
    precio_referencial_nacional: Decimal | None = None
    mensaje: str


# ---------------- contrataciones
class ContratacionCreate(BaseModel):
    objeto_contratacion: str = Field(min_length=5, max_length=400)
    tipo_objeto: TipoObjeto
    plazo_dias_calendario: int = Field(ge=1, le=3650)
    unidad_solicitante: str = Field(default="", max_length=160)
    justificacion: str = ""
    especificaciones_tecnicas: str = ""
    lugar_entrega: str = Field(default="", max_length=200)


class ContratacionUpdate(BaseModel):
    objeto_contratacion: str | None = Field(default=None, min_length=5, max_length=400)
    tipo_objeto: TipoObjeto | None = None
    plazo_dias_calendario: int | None = Field(default=None, ge=1, le=3650)
    unidad_solicitante: str | None = None
    justificacion: str | None = None
    especificaciones_tecnicas: str | None = None
    lugar_entrega: str | None = None
    justificacion_excepcion_chb: str | None = None
    codigo_autorizacion_chb: str | None = None


class ItemIn(BaseModel):
    codigo_unspsc: str = Field(default="", pattern=r"^(\d{8})?$")
    partida_id: uuid.UUID
    descripcion_especifica: str = Field(min_length=3, max_length=400)
    unidad_medida: str = Field(min_length=1, max_length=40)
    cantidad: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    precio_unitario_ref: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    fuera_catalogo_chb: bool = False


class ItemOut(Base):
    id: uuid.UUID
    numero: int
    codigo_unspsc: str
    partida_id: uuid.UUID | None
    partida_gasto: str
    descripcion_especifica: str
    unidad_medida: str
    cantidad: Decimal
    precio_unitario_ref: Decimal
    subtotal: Decimal
    fuera_catalogo_chb: bool
    estado_chb: str


class CotizacionIn(BaseModel):
    nit_ci: str = Field(pattern=r"^[0-9A-Za-z-]{5,20}$")
    razon_social: str = Field(min_length=2, max_length=200)
    correo: str = ""
    telefono: str = ""
    monto_total_ofertado: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    plazo_ofertado_dias: int = Field(ge=1, le=3650)
    fecha_recepcion: datetime | None = None  # por defecto, el momento del registro


class CotizacionCalificacion(BaseModel):
    cumple_especificaciones: bool
    observaciones: str = ""
    registro_preferencia: str = Field(default="NINGUNO", pattern=r"^(NINGUNO|PRO_BOLIVIA|MYPE)$")
    registro_preferencia_valido: bool = False
    margen_preferencia_pct: Decimal = Field(default=Decimal("0"), ge=0, le=100)


class CotizacionOut(Base):
    id: uuid.UUID
    nit_ci: str
    razon_social: str
    correo: str
    telefono: str
    monto_total_ofertado: Decimal | None
    plazo_ofertado_dias: int
    cumple_especificaciones: bool
    margen_preferencia_pct: Decimal
    observaciones: str
    adjudicado: bool
    fecha_recepcion: datetime
    registro_preferencia: str
    registro_preferencia_valido: bool
    precio_evaluado: Decimal | None
    ranking: int | None
    recomendada: bool
    motivo_descalificacion: str | None
    sellada: bool = False


class DocumentoOut(Base):
    id: uuid.UUID
    tipo_doc: str
    version: int
    hash_sha256: str
    hash_contenido: str
    fecha_generacion: datetime
    estado_tramite: str


class PreventivoOut(BaseModel):
    partida_id: uuid.UUID
    codigo_partida: str
    descripcion: str
    importe: Decimal
    estado: str


class RecepcionOut(Base):
    id: uuid.UUID
    fecha_recepcion: date
    conforme: bool
    observaciones: str
    nro_nia: str | None
    dias_retraso: int
    detalle: dict[str, Any]


class ContratacionOut(Base):
    id: uuid.UUID
    correlativo_interno: str
    objeto_contratacion: str
    tipo_objeto: str
    monto_referencial_total: Decimal
    plazo_dias_calendario: int
    metodo_formalizacion: str | None
    cuce: str | None
    preventivo_c31_nro: str | None
    estado: str
    requiere_excepcion_chb: bool
    justificacion_excepcion_chb: str | None
    codigo_autorizacion_chb: str | None
    created_by_id: uuid.UUID
    rpa_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    unidad_solicitante: str
    justificacion: str
    especificaciones_tecnicas: str
    lugar_entrega: str
    modalidad_cuantia: str | None
    nro_formulario_110: str | None
    fecha_limite_ofertas: datetime | None
    ofertas_abiertas: bool
    motivo_cierre: str | None
    ultima_observacion: str | None
    items: list[ItemOut] = []
    cotizaciones: list[CotizacionOut] = []
    documentos: list[DocumentoOut] = []
    recepciones: list[RecepcionOut] = []
    preventivos: list[PreventivoOut] = []
    acciones: list[str] = []
    mensaje_cuantia: str = ""


class ContratacionResumen(Base):
    id: uuid.UUID
    correlativo_interno: str
    objeto_contratacion: str
    tipo_objeto: str
    monto_referencial_total: Decimal
    plazo_dias_calendario: int
    metodo_formalizacion: str | None
    estado: str
    modalidad_cuantia: str | None
    created_at: datetime
    updated_at: datetime


# ---------------- acciones del flujo
class MotivoIn(BaseModel):
    motivo: str = Field(min_length=10, max_length=2000)


class CertificarIn(BaseModel):
    preventivo_c31_nro: str | None = Field(default=None, max_length=30)


class C31NroIn(BaseModel):
    preventivo_c31_nro: str = Field(min_length=1, max_length=30)


class Formulario110In(BaseModel):
    nro_formulario_110: str = Field(min_length=3, max_length=40)
    fecha_limite_ofertas: datetime
    cuce: str | None = Field(default=None, max_length=40)


class DestinatarioIn(BaseModel):
    razon_social: str = Field(min_length=2, max_length=200)
    correo: str = ""
    telefono: str = ""


class FichasIn(BaseModel):
    destinatarios: list[DestinatarioIn] = Field(min_length=1, max_length=50)
    canales: list[str] = Field(default=["IMPRESO"])

    @field_validator("canales")
    @classmethod
    def _canales(cls, v: list[str]) -> list[str]:
        validos = {"EMAIL", "WHATSAPP", "IMPRESO"}
        if not v or any(c not in validos for c in v):
            raise ValueError("Canales válidos: EMAIL, WHATSAPP, IMPRESO")
        return v


class AdjudicarIn(BaseModel):
    cotizacion_id: uuid.UUID | None = None  # por defecto la recomendada
    motivo: str = ""


class FormalizarIn(BaseModel):
    cuce: str | None = Field(default=None, max_length=40)
    metodo_formalizacion: str | None = None  # solo informativo: se valida contra la regla del plazo


class RecepcionItemIn(BaseModel):
    numero: int
    cantidad_recibida: Decimal = Field(ge=0)
    conforme: bool = True


class RecepcionIn(BaseModel):
    fecha_recepcion: date
    conforme: bool
    observaciones: str = ""
    detalle: list[RecepcionItemIn] = []


class ReglaOut(BaseModel):
    modalidad: str | None
    requiere_formulario_110: bool
    bloqueado: bool
    mensaje: str
    metodo_formalizacion: str | None


class BloqueSigepOut(BaseModel):
    encabezado: list[str]
    filas: list[list[str]]
    texto_pipe: str
    texto_tsv: str
    total: str
    origen: str  # PREVENTIVO | PREVISTO


class DashboardOut(BaseModel):
    por_estado: dict[str, int]
    pendientes: list[ContratacionResumen]
    total: int
