"""Modelo relacional (PostgreSQL 15+). PK UUIDv4, timestamps con zona horaria y CHECKs.

Los enumerados se almacenan como texto con CHECK (portable y facil de migrar).
Las columnas marcadas (+) amplian el esquema minimo del requerimiento porque el flujo las necesita.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON, BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, LargeBinary,
    Numeric, String, Text, UniqueConstraint, Uuid, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .enums import (
    Estado, EstadoCHB, EstadoPreventivo, MetodoFormalizacion, ModalidadCuantia, Rol, TipoDoc,
    TipoObjeto, sql_in,
)

JSONType = JSON().with_variant(JSONB(), "postgresql")
Money = Numeric(14, 2)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (CheckConstraint(sql_in("rol", Rol), name="ck_usuarios_rol"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    nombre_completo: Mapped[str] = mapped_column(String(160))
    cargo: Mapped[str] = mapped_column(String(120), default="")
    rol: Mapped[str] = mapped_column(String(30))
    email: Mapped[str] = mapped_column(String(160), default="")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # (+) bloqueo por intentos fallidos
    intentos_fallidos: Mapped[int] = mapped_column(Integer, default=0)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RefreshToken(Base):
    """(+) Refresh tokens revocables y rotativos (se guarda solo el hash)."""
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)  # jti
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ParametroInstitucional(Base):
    """(+) Parametros del GAM y de las reglas (clave/valor)."""
    __tablename__ = "parametros_institucionales"

    clave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[str] = mapped_column(Text, default="")
    descripcion: Mapped[str] = mapped_column(String(255), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Secuencia(Base):
    """(+) Contadores de correlativos (se bloquean con FOR UPDATE)."""
    __tablename__ = "secuencias"

    clave: Mapped[str] = mapped_column(String(60), primary_key=True)
    ultimo: Mapped[int] = mapped_column(BigInteger, default=0)


class PartidaPresupuestaria(Base):
    __tablename__ = "partidas_presupuestarias"
    __table_args__ = (
        CheckConstraint("saldo_disponible >= 0", name="ck_partida_saldo_no_negativo"),
        # Clasificador 1xxxx a 4xxxx
        CheckConstraint("length(codigo_partida) = 5 AND codigo_partida >= '10000' AND codigo_partida <= '49999'",
                        name="ck_partida_clasificador"),
        UniqueConstraint("codigo_partida", "gestion", "programa", "proyecto", "actividad", "fuente", "organismo",
                         name="uq_partida_estructura"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    codigo_partida: Mapped[str] = mapped_column(String(5), index=True)
    descripcion: Mapped[str] = mapped_column(String(200))
    saldo_disponible: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    gestion: Mapped[int] = mapped_column(Integer)
    # (+) estructura programatica para el bloque SIGEP
    programa: Mapped[str] = mapped_column(String(10), default="")
    proyecto: Mapped[str] = mapped_column(String(10), default="")
    actividad: Mapped[str] = mapped_column(String(10), default="")
    fuente: Mapped[str] = mapped_column(String(10), default="")
    organismo: Mapped[str] = mapped_column(String(10), default="")
    monto_aprobado: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))


class CatalogoCHB(Base):
    __tablename__ = "catalogo_chb"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    codigo_unspsc: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    descripcion_bien: Mapped[str] = mapped_column(String(250))
    unidad_medida: Mapped[str] = mapped_column(String(40), default="")
    precio_referencial_nacional: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class ContratacionMenor(Base):
    __tablename__ = "contrataciones_menores"
    __table_args__ = (
        CheckConstraint(sql_in("tipo_objeto", TipoObjeto), name="ck_cm_tipo_objeto"),
        CheckConstraint(sql_in("estado", Estado), name="ck_cm_estado"),
        CheckConstraint("metodo_formalizacion IS NULL OR " + sql_in("metodo_formalizacion", MetodoFormalizacion),
                        name="ck_cm_metodo"),
        CheckConstraint("modalidad_cuantia IS NULL OR " + sql_in("modalidad_cuantia", ModalidadCuantia),
                        name="ck_cm_modalidad"),
        # Contratacion Menor: Bs 1 a Bs 50.000 (art. 54 NB-SABS segun la especificacion)
        CheckConstraint("monto_referencial_total >= 0 AND monto_referencial_total <= 50000", name="ck_cm_cuantia"),
        CheckConstraint("plazo_dias_calendario >= 1", name="ck_cm_plazo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    correlativo_interno: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    objeto_contratacion: Mapped[str] = mapped_column(String(400))
    tipo_objeto: Mapped[str] = mapped_column(String(20))
    monto_referencial_total: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    plazo_dias_calendario: Mapped[int] = mapped_column(Integer, default=1)
    metodo_formalizacion: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cuce: Mapped[str | None] = mapped_column(String(40), nullable=True)
    preventivo_c31_nro: Mapped[str | None] = mapped_column(String(30), nullable=True)
    estado: Mapped[str] = mapped_column(String(30), default=Estado.BORRADOR.value, index=True)
    requiere_excepcion_chb: Mapped[bool] = mapped_column(Boolean, default=False)
    justificacion_excepcion_chb: Mapped[str | None] = mapped_column(Text, nullable=True)
    codigo_autorizacion_chb: Mapped[str | None] = mapped_column(String(60), nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    rpa_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    # (+) campos del flujo
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    unidad_solicitante: Mapped[str] = mapped_column(String(160), default="")
    justificacion: Mapped[str] = mapped_column(Text, default="")
    especificaciones_tecnicas: Mapped[str] = mapped_column(Text, default="")  # ET / TdR
    lugar_entrega: Mapped[str] = mapped_column(String(200), default="")
    modalidad_cuantia: Mapped[str | None] = mapped_column(String(30), nullable=True)
    nro_formulario_110: Mapped[str | None] = mapped_column(String(40), nullable=True)
    fecha_limite_ofertas: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ofertas_abiertas: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_cierre: Mapped[str | None] = mapped_column(Text, nullable=True)  # anulacion / desierto
    ultima_observacion: Mapped[str | None] = mapped_column(Text, nullable=True)  # p. ej. motivo de devolucion
    fecha_adjudicacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_formalizacion: Mapped[date | None] = mapped_column(Date, nullable=True)

    items: Mapped[list["ContratacionItem"]] = relationship(
        back_populates="contratacion", cascade="all, delete-orphan", order_by="ContratacionItem.numero")
    cotizaciones: Mapped[list["CotizacionProveedor"]] = relationship(
        back_populates="contratacion", cascade="all, delete-orphan", order_by="CotizacionProveedor.fecha_recepcion")
    documentos: Mapped[list["DocumentoExpediente"]] = relationship(
        back_populates="contratacion", cascade="all, delete-orphan", order_by="DocumentoExpediente.fecha_generacion")
    preventivos: Mapped[list["PreventivoC31"]] = relationship(back_populates="contratacion", cascade="all, delete-orphan")
    recepciones: Mapped[list["Recepcion"]] = relationship(back_populates="contratacion", cascade="all, delete-orphan")


class ContratacionItem(Base):
    __tablename__ = "contrataciones_items"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_item_cantidad"),
        CheckConstraint("precio_unitario_ref > 0", name="ck_item_precio"),
        CheckConstraint(sql_in("estado_chb", EstadoCHB), name="ck_item_estado_chb"),
        UniqueConstraint("contratacion_id", "numero", name="uq_item_numero"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    contratacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contrataciones_menores.id", ondelete="CASCADE"), index=True)
    codigo_unspsc: Mapped[str] = mapped_column(String(8), default="")
    partida_gasto: Mapped[str] = mapped_column(String(5))
    descripcion_especifica: Mapped[str] = mapped_column(String(400))
    unidad_medida: Mapped[str] = mapped_column(String(40))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    precio_unitario_ref: Mapped[Decimal] = mapped_column(Money)
    subtotal: Mapped[Decimal] = mapped_column(Money)
    # (+)
    numero: Mapped[int] = mapped_column(Integer)
    partida_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("partidas_presupuestarias.id"), nullable=True)
    fuera_catalogo_chb: Mapped[bool] = mapped_column(Boolean, default=False)
    estado_chb: Mapped[str] = mapped_column(String(30), default=EstadoCHB.NO_APLICA.value)

    contratacion: Mapped[ContratacionMenor] = relationship(back_populates="items")


class CotizacionProveedor(Base):
    __tablename__ = "cotizaciones_proveedores"
    __table_args__ = (
        CheckConstraint("margen_preferencia_pct >= 0 AND margen_preferencia_pct <= 100", name="ck_cot_margen"),
        CheckConstraint("plazo_ofertado_dias >= 1", name="ck_cot_plazo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    contratacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contrataciones_menores.id", ondelete="CASCADE"), index=True)
    nit_ci: Mapped[str] = mapped_column(String(20))
    razon_social: Mapped[str] = mapped_column(String(200))
    correo: Mapped[str] = mapped_column(String(160), default="")
    telefono: Mapped[str] = mapped_column(String(40), default="")
    monto_total_ofertado: Mapped[Decimal | None] = mapped_column(Money, nullable=True)  # visible tras la apertura
    plazo_ofertado_dias: Mapped[int] = mapped_column(Integer)
    cumple_especificaciones: Mapped[bool] = mapped_column(Boolean, default=False)
    margen_preferencia_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    observaciones: Mapped[str] = mapped_column(Text, default="")
    adjudicado: Mapped[bool] = mapped_column(Boolean, default=False)
    # (+)
    monto_cifrado: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    fecha_recepcion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    registro_preferencia: Mapped[str] = mapped_column(String(20), default="NINGUNO")  # NINGUNO | PRO_BOLIVIA | MYPE
    registro_preferencia_valido: Mapped[bool] = mapped_column(Boolean, default=False)
    precio_evaluado: Mapped[Decimal | None] = mapped_column(Money, nullable=True)
    ranking: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recomendada: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_descalificacion: Mapped[str | None] = mapped_column(String(300), nullable=True)

    contratacion: Mapped[ContratacionMenor] = relationship(back_populates="cotizaciones")


class DocumentoExpediente(Base):
    __tablename__ = "documentos_expediente"
    __table_args__ = (CheckConstraint(sql_in("tipo_doc", TipoDoc), name="ck_doc_tipo"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    contratacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contrataciones_menores.id", ondelete="CASCADE"), index=True)
    tipo_doc: Mapped[str] = mapped_column(String(40))
    ruta_archivo: Mapped[str] = mapped_column(String(300))
    hash_sha256: Mapped[str] = mapped_column(String(64))  # del archivo PDF final
    fecha_generacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # (+)
    hash_contenido: Mapped[str] = mapped_column(String(64))  # del contenido canonico: es el impreso en el pie
    version: Mapped[int] = mapped_column(Integer, default=1)
    estado_tramite: Mapped[str] = mapped_column(String(30), default="")
    generado_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)

    contratacion: Mapped[ContratacionMenor] = relationship(back_populates="documentos")


class PreventivoC31(Base):
    """(+) Reserva presupuestaria por partida asociada a una contratacion."""
    __tablename__ = "preventivos_c31"
    __table_args__ = (
        CheckConstraint("importe > 0", name="ck_prev_importe"),
        CheckConstraint(sql_in("estado", EstadoPreventivo), name="ck_prev_estado"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    contratacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contrataciones_menores.id", ondelete="CASCADE"), index=True)
    partida_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("partidas_presupuestarias.id"))
    importe: Mapped[Decimal] = mapped_column(Money)
    estado: Mapped[str] = mapped_column(String(15), default=EstadoPreventivo.ACTIVO.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    contratacion: Mapped[ContratacionMenor] = relationship(back_populates="preventivos")
    partida: Mapped[PartidaPresupuestaria] = relationship()


class Recepcion(Base):
    """(+) Verificacion cuantitativa y cualitativa (origen del Acta Formulario 500)."""
    __tablename__ = "recepciones"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    contratacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contrataciones_menores.id", ondelete="CASCADE"), index=True)
    fecha_recepcion: Mapped[date] = mapped_column(Date)
    conforme: Mapped[bool] = mapped_column(Boolean)
    observaciones: Mapped[str] = mapped_column(Text, default="")
    nro_nia: Mapped[str | None] = mapped_column(String(30), nullable=True)  # Nota de Ingreso a Almacen
    detalle: Mapped[dict] = mapped_column(JSONType, default=dict)
    dias_retraso: Mapped[int] = mapped_column(Integer, default=0)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    contratacion: Mapped[ContratacionMenor] = relationship(back_populates="recepciones")


class AuditLog(Base):
    """Registro de auditoria inalterable: solo INSERT (trigger en PostgreSQL) y encadenado con hashes."""
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    accion: Mapped[str] = mapped_column(String(60), index=True)
    tabla_afectada: Mapped[str] = mapped_column(String(60), default="")
    registro_id: Mapped[str] = mapped_column(String(60), default="")
    datos_previos_json: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    datos_nuevos_json: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(64), default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # (+) cadena de integridad
    secuencia: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    hash_previo: Mapped[str] = mapped_column(String(64), default="")
    hash_registro: Mapped[str] = mapped_column(String(64), default="")
