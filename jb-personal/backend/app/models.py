"""Modelo relacional. Compatible con SQLite y PostgreSQL (mismo ORM, mismo esquema)."""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (Boolean, LargeBinary, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String,
                        Text, Time, UniqueConstraint, func, text)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

MONEY = Numeric(14, 2)
DIAS = Numeric(8, 2)

MODALIDADES = ("PERMANENTE", "EVENTUAL", "CONSULTOR_LINEA")


class Base(DeclarativeBase):
    pass


# ----------------------------------------------------------------- Módulo A: institución
class Entidad(Base):
    """Parámetros del municipio (una sola fila, id=1)."""
    __tablename__ = "entidad"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), default="Gobierno Autónomo Municipal de [Municipio]")
    sigla: Mapped[str] = mapped_column(String(20), default="GAM")
    codigo_sigep: Mapped[str] = mapped_column(String(30), default="")
    direccion: Mapped[str] = mapped_column(String(250), default="")
    ciudad: Mapped[str] = mapped_column(String(100), default="")
    mae_nombre: Mapped[str] = mapped_column(String(150), default="")
    mae_cargo: Mapped[str] = mapped_column(String(150), default="Alcalde(sa) Municipal")
    rrhh_nombre: Mapped[str] = mapped_column(String(150), default="")
    rrhh_cargo: Mapped[str] = mapped_column(String(150), default="Responsable de Recursos Humanos")
    aprobador_nombre: Mapped[str] = mapped_column(String(150), default="")
    aprobador_cargo: Mapped[str] = mapped_column(String(150), default="Secretario(a) Municipal Administrativo Financiero")
    prefijo_cite: Mapped[str] = mapped_column(String(40), default="GAM-RRHH")
    reglamento_rip: Mapped[str] = mapped_column(String(200), default="Decreto Edil N° [XXX/AAAA]")
    # --- reglas de cálculo (todas editables)
    escala_modo: Mapped[str] = mapped_column(String(10), default="MINUTOS")       # MINUTOS | CANTIDAD
    factor_falta_planta: Mapped[Decimal] = mapped_column(DIAS, default=Decimal("2"))  # Art. 22 D.S. 25749 según el informe tipo
    factor_falta_consultor: Mapped[Decimal] = mapped_column(DIAS, default=Decimal("1"))
    contar_salida_anticipada: Mapped[bool] = mapped_column(Boolean, default=False)
    tolerancia_cuenta_total: Mapped[bool] = mapped_column(Boolean, default=True)
    max_justificados_consultor: Mapped[Decimal] = mapped_column(DIAS, default=Decimal("1"))
    tasa_afp: Mapped[Decimal] = mapped_column(Numeric(7, 4), default=Decimal("0.1271"))
    tasa_patronal: Mapped[Decimal] = mapped_column(Numeric(7, 4), default=Decimal("0.1721"))
    dias_mes_comercial: Mapped[int] = mapped_column(Integer, default=30)
    horas_jornada: Mapped[Decimal] = mapped_column(DIAS, default=Decimal("8"))


class UnidadOrganizacional(Base):
    __tablename__ = "unidad_organizacional"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), unique=True)
    codigo: Mapped[str] = mapped_column(String(30), default="")


class Horario(Base):
    __tablename__ = "horario"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    es_defecto: Mapped[bool] = mapped_column(Boolean, default=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    tolerancia_min: Mapped[int] = mapped_column(Integer, default=10)        # minutos libres
    umbral_grave_min: Mapped[int] = mapped_column(Integer, default=30)      # > umbral = retraso grave
    dias_laborables: Mapped[str] = mapped_column(String(7), default="01234")  # 0=lunes ... 6=domingo
    turnos: Mapped[list["Turno"]] = relationship(back_populates="horario", cascade="all, delete-orphan",
                                                  order_by="Turno.orden", lazy="selectin")


class Turno(Base):
    __tablename__ = "turno"
    __table_args__ = (UniqueConstraint("horario_id", "orden"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    horario_id: Mapped[int] = mapped_column(ForeignKey("horario.id", ondelete="CASCADE"))
    orden: Mapped[int] = mapped_column(Integer)
    nombre: Mapped[str] = mapped_column(String(30))                          # Mañana / Tarde
    hora_entrada: Mapped[time] = mapped_column(Time)
    hora_salida: Mapped[time] = mapped_column(Time)
    horario: Mapped[Horario] = relationship(back_populates="turnos")


class EscalaSancion(Base):
    """Escala de sanción por retrasos acumulados en el mes (RIP). Editable."""
    __tablename__ = "escala_sancion"
    id: Mapped[int] = mapped_column(primary_key=True)
    modo: Mapped[str] = mapped_column(String(10))          # MINUTOS | CANTIDAD
    desde: Mapped[int] = mapped_column(Integer)
    hasta: Mapped[int | None] = mapped_column(Integer, nullable=True)  # NULL = sin tope
    dias_descuento: Mapped[Decimal] = mapped_column(DIAS, default=Decimal("0"))
    sancion: Mapped[str] = mapped_column(String(200))


class Feriado(Base):
    __tablename__ = "feriado"
    fecha: Mapped[date] = mapped_column(Date, primary_key=True)
    descripcion: Mapped[str] = mapped_column(String(150))


# ----------------------------------------------------------------- Personal y contratos
class Empleado(Base):
    __tablename__ = "empleado"
    __table_args__ = (UniqueConstraint("ci", "complemento"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)             # ID en el reloj biométrico
    ci: Mapped[str] = mapped_column(String(20), index=True)
    complemento: Mapped[str] = mapped_column(String(5), default="")
    expedido: Mapped[str] = mapped_column(String(4), default="")
    nombres: Mapped[str] = mapped_column(String(120))
    apellidos: Mapped[str] = mapped_column(String(120))
    cargo: Mapped[str] = mapped_column(String(200), default="")
    unidad_id: Mapped[int | None] = mapped_column(ForeignKey("unidad_organizacional.id"), nullable=True)
    horario_id: Mapped[int | None] = mapped_column(ForeignKey("horario.id"), nullable=True)
    nro_cua: Mapped[str] = mapped_column(String(20), default="")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    unidad: Mapped[UnidadOrganizacional | None] = relationship(lazy="joined")
    contratos: Mapped[list["Contrato"]] = relationship(back_populates="empleado", order_by="Contrato.fecha_inicio",
                                                       lazy="selectin")

    @property
    def nombre_completo(self) -> str:
        return f"{self.apellidos} {self.nombres}".strip()

    @property
    def ci_completo(self) -> str:
        return f"{self.ci}{('-' + self.complemento) if self.complemento else ''}"


class Contrato(Base):
    __tablename__ = "contrato"
    __table_args__ = (
        CheckConstraint("modalidad in ('PERMANENTE','EVENTUAL','CONSULTOR_LINEA')", name="ck_contrato_modalidad"),
        Index("ix_contrato_emp_inicio", "empleado_id", "fecha_inicio"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    empleado_id: Mapped[int] = mapped_column(ForeignKey("empleado.id"))
    modalidad: Mapped[str] = mapped_column(String(20))
    partida: Mapped[str] = mapped_column(String(10), default="")             # 12100 / 25200 / 25800 ...
    haber_basico: Mapped[Decimal] = mapped_column(MONEY)                     # haber mensual u honorario pactado
    bono_antiguedad: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    rc_iva: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))     # retención mensual RC-IVA (dato externo)
    aplica_aporte: Mapped[bool] = mapped_column(Boolean, default=True)       # AFP/Gestora (consultor: según caso)
    tasa_afp: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)       # sobreescribe tasa general
    tasa_patronal: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_fin: Mapped[date | None] = mapped_column(Date, nullable=True)      # vigencia pactada
    fecha_baja: Mapped[date | None] = mapped_column(Date, nullable=True)     # desvinculación efectiva
    causal_baja: Mapped[str] = mapped_column(String(40), default="")         # RENUNCIA/CONCLUSION_CONTRATO/DESTITUCION/...
    nro_documento: Mapped[str] = mapped_column(String(60), default="")      # memorándum / contrato
    empleado: Mapped[Empleado] = relationship(back_populates="contratos")


# ----------------------------------------------------------------- Módulo B: biometría
class ImportBiometrico(Base):
    __tablename__ = "import_biometrico"
    id: Mapped[int] = mapped_column(primary_key=True)
    archivo: Mapped[str] = mapped_column(String(250))
    sha256: Mapped[str] = mapped_column(String(64))
    formato: Mapped[str] = mapped_column(String(20))
    usuario: Mapped[str] = mapped_column(String(60), default="")
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    leidas: Mapped[int] = mapped_column(Integer, default=0)
    nuevas: Mapped[int] = mapped_column(Integer, default=0)
    duplicadas: Mapped[int] = mapped_column(Integer, default=0)
    rechazadas: Mapped[int] = mapped_column(Integer, default=0)
    detalle_rechazo: Mapped[str] = mapped_column(Text, default="")


class PerfilBiometrico(Base):
    """Perfil de mapeo de columnas para un modelo/marca de reloj (se reutiliza en cada importación)."""
    __tablename__ = "perfil_biometrico"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    marca: Mapped[str] = mapped_column(String(60), default="")
    config: Mapped[str] = mapped_column(Text)                     # JSON validado por biometrico.validar_perfil
    creado_por: Mapped[str] = mapped_column(String(60), default="")
    creado: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Marca(Base):
    """Marca biométrica CRUDA e inalterable (SAFCO): nunca se edita; se corrige con justificaciones."""
    __tablename__ = "marca"
    __table_args__ = (UniqueConstraint("identificador", "fecha_hora", "dispositivo", name="uq_marca"),
                      Index("ix_marca_fecha", "fecha_hora"))
    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("import_biometrico.id"))
    identificador: Mapped[str] = mapped_column(String(30), index=True)       # ID/C.I. tal como lo entrega el reloj
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)
    tipo_evento: Mapped[str] = mapped_column(String(40), default="")
    metodo: Mapped[str] = mapped_column(String(40), default="")
    dispositivo: Mapped[str] = mapped_column(String(60), default="")


# ----------------------------------------------------------------- Módulo C: permisos e instructivos
class PermisoTipo(Base):
    __tablename__ = "permiso_tipo"
    codigo: Mapped[str] = mapped_column(String(30), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    categoria: Mapped[str] = mapped_column(String(15))       # VACACION | LICENCIA | PERMISO | COMISION
    con_goce: Mapped[bool] = mapped_column(Boolean, default=True)
    max_dias: Mapped[Decimal | None] = mapped_column(DIAS, nullable=True)   # informativo (según RIP / norma)
    base_legal: Mapped[str] = mapped_column(String(200), default="")


class Permiso(Base):
    __tablename__ = "permiso"
    __table_args__ = (Index("ix_permiso_emp_fecha", "empleado_id", "fecha_desde", "fecha_hasta"),
                      CheckConstraint("estado in ('PENDIENTE','APROBADO','RECHAZADO','ANULADO')", name="ck_permiso_estado"))
    id: Mapped[int] = mapped_column(primary_key=True)
    nro_boleta: Mapped[str] = mapped_column(String(40), unique=True)
    empleado_id: Mapped[int] = mapped_column(ForeignKey("empleado.id"))
    tipo_codigo: Mapped[str] = mapped_column(ForeignKey("permiso_tipo.codigo"))
    fecha_desde: Mapped[date] = mapped_column(Date)
    fecha_hasta: Mapped[date] = mapped_column(Date)
    hora_desde: Mapped[time | None] = mapped_column(Time, nullable=True)    # NULL = jornada completa
    hora_hasta: Mapped[time | None] = mapped_column(Time, nullable=True)
    motivo: Mapped[str] = mapped_column(Text, default="")
    doc_respaldo: Mapped[str] = mapped_column(String(200), default="")
    estado: Mapped[str] = mapped_column(String(10), default="PENDIENTE")
    autorizado_por: Mapped[str] = mapped_column(String(150), default="")     # inmediato superior / fiscal de servicio
    gestion_vacacion: Mapped[str] = mapped_column(String(15), default="")
    saldo_vacacion: Mapped[str] = mapped_column(String(40), default="")
    creado_por: Mapped[str] = mapped_column(String(60), default="")
    creado: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    empleado: Mapped[Empleado] = relationship(lazy="joined")
    tipo: Mapped[PermisoTipo] = relationship(lazy="joined")


class Correlativo(Base):
    __tablename__ = "correlativo"
    tipo: Mapped[str] = mapped_column(String(20), primary_key=True)
    gestion: Mapped[int] = mapped_column(Integer, primary_key=True)
    ultimo: Mapped[int] = mapped_column(Integer, default=0)


class Instructivo(Base):
    __tablename__ = "instructivo"
    id: Mapped[int] = mapped_column(primary_key=True)
    cite: Mapped[str] = mapped_column(String(60), unique=True)
    gestion: Mapped[int] = mapped_column(Integer)
    correlativo: Mapped[int] = mapped_column(Integer)
    titulo: Mapped[str] = mapped_column(String(250))
    contenido: Mapped[str] = mapped_column(Text)
    fecha_emision: Mapped[date] = mapped_column(Date)
    criterio: Mapped[str] = mapped_column(Text, default="")                 # JSON: unidades/cargos/modalidades/empleados
    estado: Mapped[str] = mapped_column(String(10), default="BORRADOR")     # BORRADOR | EMITIDO | ANULADO
    creado_por: Mapped[str] = mapped_column(String(60), default="")
    destinatarios: Mapped[list["InstructivoDestinatario"]] = relationship(
        back_populates="instructivo", cascade="all, delete-orphan", lazy="selectin")


class InstructivoDestinatario(Base):
    __tablename__ = "instructivo_destinatario"
    __table_args__ = (UniqueConstraint("instructivo_id", "empleado_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    instructivo_id: Mapped[int] = mapped_column(ForeignKey("instructivo.id", ondelete="CASCADE"))
    empleado_id: Mapped[int] = mapped_column(ForeignKey("empleado.id"))
    notificacion: Mapped[str] = mapped_column(String(12), default="PENDIENTE")  # PENDIENTE | NOTIFICADO | RECIBIDO
    fecha_notificacion: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    observacion: Mapped[str] = mapped_column(String(250), default="")
    instructivo: Mapped[Instructivo] = relationship(back_populates="destinatarios")
    empleado: Mapped[Empleado] = relationship(lazy="joined")


# ----------------------------------------------------------------- Resultados del motor
class Periodo(Base):
    __tablename__ = "periodo"
    anio: Mapped[int] = mapped_column(Integer, primary_key=True)
    mes: Mapped[int] = mapped_column(Integer, primary_key=True)
    estado: Mapped[str] = mapped_column(String(10), default="ABIERTO")      # ABIERTO | CERRADO
    procesado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cerrado_por: Mapped[str] = mapped_column(String(60), default="")
    cerrado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AsistenciaDia(Base):
    __tablename__ = "asistencia_dia"
    __table_args__ = (UniqueConstraint("empleado_id", "fecha"), Index("ix_asis_fecha", "fecha"))
    id: Mapped[int] = mapped_column(primary_key=True)
    empleado_id: Mapped[int] = mapped_column(ForeignKey("empleado.id"))
    fecha: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(25))
    marcas: Mapped[str] = mapped_column(String(120), default="")           # "08:02 12:01 14:31 18:35"
    min_retraso: Mapped[int] = mapped_column(Integer, default=0)
    nro_retrasos: Mapped[int] = mapped_column(Integer, default=0)
    min_salida_anticipada: Mapped[int] = mapped_column(Integer, default=0)
    falta: Mapped[Decimal] = mapped_column(DIAS, default=Decimal("0"))      # fracción de día injustificada
    justificado: Mapped[Decimal] = mapped_column(DIAS, default=Decimal("0"))
    justificado_sin_goce: Mapped[Decimal] = mapped_column(DIAS, default=Decimal("0"))
    parcial: Mapped[Decimal] = mapped_column(DIAS, default=Decimal("0"), server_default=text("0"))
    parcial_sin_goce: Mapped[Decimal] = mapped_column(DIAS, default=Decimal("0"), server_default=text("0"))
    categoria_just: Mapped[str] = mapped_column(String(15), default="")
    permiso_id: Mapped[int | None] = mapped_column(ForeignKey("permiso.id"), nullable=True)
    observacion: Mapped[str] = mapped_column(String(250), default="")
    empleado: Mapped[Empleado] = relationship(lazy="joined")


class Liquidacion(Base):
    __tablename__ = "liquidacion"
    __table_args__ = (UniqueConstraint("anio", "mes", "empleado_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    anio: Mapped[int] = mapped_column(Integer)
    mes: Mapped[int] = mapped_column(Integer)
    empleado_id: Mapped[int] = mapped_column(ForeignKey("empleado.id"))
    contrato_id: Mapped[int] = mapped_column(ForeignKey("contrato.id"))
    modalidad: Mapped[str] = mapped_column(String(20))
    haber_basico: Mapped[Decimal] = mapped_column(MONEY)
    dias_trabajados: Mapped[Decimal] = mapped_column(DIAS)                  # base comercial 30
    bono_antiguedad: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    total_ganado: Mapped[Decimal] = mapped_column(MONEY)
    aporte_laboral: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    aporte_patronal: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    rc_iva: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    # asistencia
    dias_laborables: Mapped[Decimal] = mapped_column(DIAS)
    dias_asistidos: Mapped[Decimal] = mapped_column(DIAS)
    faltas: Mapped[Decimal] = mapped_column(DIAS)
    min_retraso: Mapped[int] = mapped_column(Integer)
    nro_retrasos: Mapped[int] = mapped_column(Integer, default=0)
    dias_justificados: Mapped[Decimal] = mapped_column(DIAS)
    # días de descuento (R.I.P.) y su importe
    dias_desc_faltas: Mapped[Decimal] = mapped_column(DIAS, default=Decimal("0"))
    dias_desc_atrasos: Mapped[Decimal] = mapped_column(DIAS, default=Decimal("0"))
    dias_desc_sin_goce: Mapped[Decimal] = mapped_column(DIAS, default=Decimal("0"))
    dias_desc_exceso_consultor: Mapped[Decimal] = mapped_column(DIAS, default=Decimal("0"))
    desc_faltas: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    desc_atrasos: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    desc_otros: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    desc_multas: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"), server_default=text("0"))
    horas_permiso: Mapped[Decimal] = mapped_column(DIAS, default=Decimal("0"), server_default=text("0"))
    dias_descuento: Mapped[Decimal] = mapped_column(DIAS, default=Decimal("0"))
    desc_asistencia: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0"))
    total_descuentos: Mapped[Decimal] = mapped_column(MONEY)
    liquido_pagable: Mapped[Decimal] = mapped_column(MONEY)
    sancion: Mapped[str] = mapped_column(String(200), default="")
    observacion: Mapped[str] = mapped_column(String(400), default="")
    empleado: Mapped[Empleado] = relationship(lazy="joined")
    contrato: Mapped[Contrato] = relationship(lazy="joined")


# ----------------------------------------------------------------- Seguridad y auditoría
class Usuario(Base):
    __tablename__ = "usuario"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True)
    nombre: Mapped[str] = mapped_column(String(150), default="")
    password_hash: Mapped[str] = mapped_column(String(200))
    rol: Mapped[str] = mapped_column(String(10), default="RRHH")            # ADMIN | RRHH | CONSULTA
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLog(Base):
    """Bitácora encadenada por hash (SAFCO / auditoría posterior). Triggers impiden UPDATE/DELETE."""
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime)
    usuario: Mapped[str] = mapped_column(String(60))
    accion: Mapped[str] = mapped_column(String(40))
    entidad: Mapped[str] = mapped_column(String(40))
    entidad_id: Mapped[str] = mapped_column(String(40), default="")
    detalle: Mapped[str] = mapped_column(Text, default="")
    hash_prev: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))


class BackupRegistro(Base):
    __tablename__ = "backup_registro"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    archivo: Mapped[str] = mapped_column(String(300))
    sha256: Mapped[str] = mapped_column(String(64))
    bytes: Mapped[int] = mapped_column(Integer)
    usuario: Mapped[str] = mapped_column(String(60), default="")
    tipo: Mapped[str] = mapped_column(String(15), default="MANUAL")


class Licencia(Base):
    """Estado de activación (una fila). 'codigo' es el código de activación firmado por el emisor (JB-Activador)."""
    __tablename__ = "licencia"
    id: Mapped[int] = mapped_column(primary_key=True)
    primer_uso: Mapped[date] = mapped_column(Date)                # inicio del periodo de prueba
    codigo: Mapped[str] = mapped_column(Text, default="")
    entidad: Mapped[str] = mapped_column(String(200), default="")
    vence: Mapped[date | None] = mapped_column(Date, nullable=True)
    activada: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Ajuste(Base):
    """Multas y descuentos adicionales (manuales) que se descuentan en la planilla del mes: aparecen en TODOS los reportes."""
    __tablename__ = "ajuste"
    __table_args__ = (CheckConstraint("tipo in ('MULTA','DESCUENTO')", name="ck_ajuste_tipo"),
                      CheckConstraint("estado in ('ACTIVO','ANULADO')", name="ck_ajuste_estado"),
                      Index("ix_ajuste_periodo", "anio", "mes", "empleado_id"))
    id: Mapped[int] = mapped_column(primary_key=True)
    anio: Mapped[int] = mapped_column(Integer)
    mes: Mapped[int] = mapped_column(Integer)
    empleado_id: Mapped[int] = mapped_column(ForeignKey("empleado.id"))
    tipo: Mapped[str] = mapped_column(String(10), default="MULTA")
    concepto: Mapped[str] = mapped_column(String(200))
    monto: Mapped[Decimal] = mapped_column(MONEY)
    referencia: Mapped[str] = mapped_column(String(100), default="")          # memorándum / resolución que lo sustenta
    estado: Mapped[str] = mapped_column(String(10), default="ACTIVO")
    creado_por: Mapped[str] = mapped_column(String(60), default="")
    creado: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    empleado: Mapped[Empleado] = relationship(lazy="joined")


# ----------------------------------------------------------------- Memorándums
class MemoConfig(Base):
    """Membrete y parámetros de los memorándums (una fila, id=1)."""
    __tablename__ = "memo_config"
    id: Mapped[int] = mapped_column(primary_key=True)
    prefijo: Mapped[str] = mapped_column(String(60), default="GAM/MAE/RRHH")   # cite: <prefijo>/N°001/2026
    encabezado: Mapped[str] = mapped_column(Text, default="")                  # líneas bajo el nombre (una por línea)
    lema: Mapped[str] = mapped_column(String(200), default="")
    pie: Mapped[str] = mapped_column(Text, default="")                         # dirección / contactos (una por línea)
    decreto_estructura: Mapped[str] = mapped_column(String(120), default="")   # p. ej. Decreto Municipal N° 018/2025
    firmante_nombre: Mapped[str] = mapped_column(String(150), default="")
    firmante_cargo: Mapped[str] = mapped_column(String(150), default="Alcalde Municipal")
    logo: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    logo_mime: Mapped[str] = mapped_column(String(40), default="")


class MemoPlantilla(Base):
    """Redacción editable de cada tipo de memorándum (variables entre llaves: {cargo}, {fecha_efectiva}...)."""
    __tablename__ = "memo_plantilla"
    tipo: Mapped[str] = mapped_column(String(25), primary_key=True)
    referencia: Mapped[str] = mapped_column(String(200))
    cuerpo: Mapped[str] = mapped_column(Text)


class Memorandum(Base):
    __tablename__ = "memorandum"
    __table_args__ = (
        CheckConstraint("tipo in ('DESIGNACION','ACEPTACION_RENUNCIA','AGRADECIMIENTO')", name="ck_memo_tipo"),
        CheckConstraint("estado in ('BORRADOR','EMITIDO','ANULADO')", name="ck_memo_estado"),
        UniqueConstraint("gestion", "correlativo", name="uq_memo_correlativo"),
        Index("ix_memo_gestion", "gestion", "correlativo"))
    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(25))
    estado: Mapped[str] = mapped_column(String(10), default="BORRADOR")
    cite: Mapped[str] = mapped_column(String(100), default="")                  # se asigna al EMITIR (correlativo oficial)
    gestion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    correlativo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fecha: Mapped[date] = mapped_column(Date)
    fecha_efectiva: Mapped[date] = mapped_column(Date)
    empleado_id: Mapped[int | None] = mapped_column(ForeignKey("empleado.id"), nullable=True)
    destinatario: Mapped[str] = mapped_column(String(200))
    destinatario_ci: Mapped[str] = mapped_column(String(40), default="")
    cargo: Mapped[str] = mapped_column(String(250))
    referencia: Mapped[str] = mapped_column(String(300), default="")
    datos: Mapped[str] = mapped_column(Text, default="{}")                      # JSON: variables adicionales (fecha_renuncia, plazos...)
    cuerpo: Mapped[str] = mapped_column(Text)
    firmante_nombre: Mapped[str] = mapped_column(String(150), default="")
    firmante_cargo: Mapped[str] = mapped_column(String(150), default="")
    efecto_aplicado: Mapped[str] = mapped_column(String(200), default="")      # p. ej. "Baja registrada (contrato 12)"
    recibido_fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    recibido_por: Mapped[str] = mapped_column(String(150), default="")
    motivo_anulacion: Mapped[str] = mapped_column(String(300), default="")
    creado_por: Mapped[str] = mapped_column(String(60), default="")
    creado: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    emitido_por: Mapped[str] = mapped_column(String(60), default="")
    emitido_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    empleado: Mapped[Empleado | None] = relationship(lazy="joined")
