-- Esquema del Sistema de Gestión de Personal y Asistencia Municipal (sqlite)
-- Generado desde app/models.py (python -m app.cli ddl). No editar a mano.

PRAGMA foreign_keys = ON;

CREATE TABLE audit_log (
	id INTEGER NOT NULL, 
	ts DATETIME NOT NULL, 
	usuario VARCHAR(60) NOT NULL, 
	accion VARCHAR(40) NOT NULL, 
	entidad VARCHAR(40) NOT NULL, 
	entidad_id VARCHAR(40) NOT NULL, 
	detalle TEXT NOT NULL, 
	hash_prev VARCHAR(64) NOT NULL, 
	hash VARCHAR(64) NOT NULL, 
	PRIMARY KEY (id)
);


CREATE TABLE backup_registro (
	id INTEGER NOT NULL, 
	ts DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	archivo VARCHAR(300) NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	bytes INTEGER NOT NULL, 
	usuario VARCHAR(60) NOT NULL, 
	tipo VARCHAR(15) NOT NULL, 
	PRIMARY KEY (id)
);


CREATE TABLE correlativo (
	tipo VARCHAR(20) NOT NULL, 
	gestion INTEGER NOT NULL, 
	ultimo INTEGER NOT NULL, 
	PRIMARY KEY (tipo, gestion)
);


CREATE TABLE entidad (
	id INTEGER NOT NULL, 
	nombre VARCHAR(200) NOT NULL, 
	sigla VARCHAR(20) NOT NULL, 
	codigo_sigep VARCHAR(30) NOT NULL, 
	direccion VARCHAR(250) NOT NULL, 
	ciudad VARCHAR(100) NOT NULL, 
	mae_nombre VARCHAR(150) NOT NULL, 
	mae_cargo VARCHAR(150) NOT NULL, 
	rrhh_nombre VARCHAR(150) NOT NULL, 
	rrhh_cargo VARCHAR(150) NOT NULL, 
	aprobador_nombre VARCHAR(150) NOT NULL, 
	aprobador_cargo VARCHAR(150) NOT NULL, 
	prefijo_cite VARCHAR(40) NOT NULL, 
	reglamento_rip VARCHAR(200) NOT NULL, 
	escala_modo VARCHAR(10) NOT NULL, 
	factor_falta_planta NUMERIC(8, 2) NOT NULL, 
	factor_falta_consultor NUMERIC(8, 2) NOT NULL, 
	contar_salida_anticipada BOOLEAN NOT NULL, 
	tolerancia_cuenta_total BOOLEAN NOT NULL, 
	max_justificados_consultor NUMERIC(8, 2) NOT NULL, 
	tasa_afp NUMERIC(7, 4) NOT NULL, 
	tasa_patronal NUMERIC(7, 4) NOT NULL, 
	dias_mes_comercial INTEGER NOT NULL, 
	horas_jornada NUMERIC(8, 2) NOT NULL, 
	PRIMARY KEY (id)
);


CREATE TABLE escala_sancion (
	id INTEGER NOT NULL, 
	modo VARCHAR(10) NOT NULL, 
	desde INTEGER NOT NULL, 
	hasta INTEGER, 
	dias_descuento NUMERIC(8, 2) NOT NULL, 
	sancion VARCHAR(200) NOT NULL, 
	PRIMARY KEY (id)
);


CREATE TABLE feriado (
	fecha DATE NOT NULL, 
	descripcion VARCHAR(150) NOT NULL, 
	PRIMARY KEY (fecha)
);


CREATE TABLE horario (
	id INTEGER NOT NULL, 
	nombre VARCHAR(100) NOT NULL, 
	es_defecto BOOLEAN NOT NULL, 
	activo BOOLEAN NOT NULL, 
	tolerancia_min INTEGER NOT NULL, 
	umbral_grave_min INTEGER NOT NULL, 
	dias_laborables VARCHAR(7) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (nombre)
);


CREATE TABLE import_biometrico (
	id INTEGER NOT NULL, 
	archivo VARCHAR(250) NOT NULL, 
	sha256 VARCHAR(64) NOT NULL, 
	formato VARCHAR(20) NOT NULL, 
	usuario VARCHAR(60) NOT NULL, 
	fecha DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	leidas INTEGER NOT NULL, 
	nuevas INTEGER NOT NULL, 
	duplicadas INTEGER NOT NULL, 
	rechazadas INTEGER NOT NULL, 
	detalle_rechazo TEXT NOT NULL, 
	PRIMARY KEY (id)
);


CREATE TABLE instructivo (
	id INTEGER NOT NULL, 
	cite VARCHAR(60) NOT NULL, 
	gestion INTEGER NOT NULL, 
	correlativo INTEGER NOT NULL, 
	titulo VARCHAR(250) NOT NULL, 
	contenido TEXT NOT NULL, 
	fecha_emision DATE NOT NULL, 
	criterio TEXT NOT NULL, 
	estado VARCHAR(10) NOT NULL, 
	creado_por VARCHAR(60) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (cite)
);


CREATE TABLE periodo (
	anio INTEGER NOT NULL, 
	mes INTEGER NOT NULL, 
	estado VARCHAR(10) NOT NULL, 
	procesado_en DATETIME, 
	cerrado_por VARCHAR(60) NOT NULL, 
	cerrado_en DATETIME, 
	PRIMARY KEY (anio, mes)
);


CREATE TABLE permiso_tipo (
	codigo VARCHAR(30) NOT NULL, 
	nombre VARCHAR(120) NOT NULL, 
	categoria VARCHAR(15) NOT NULL, 
	con_goce BOOLEAN NOT NULL, 
	max_dias NUMERIC(8, 2), 
	base_legal VARCHAR(200) NOT NULL, 
	PRIMARY KEY (codigo)
);


CREATE TABLE unidad_organizacional (
	id INTEGER NOT NULL, 
	nombre VARCHAR(200) NOT NULL, 
	codigo VARCHAR(30) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (nombre)
);


CREATE TABLE usuario (
	id INTEGER NOT NULL, 
	username VARCHAR(60) NOT NULL, 
	nombre VARCHAR(150) NOT NULL, 
	password_hash VARCHAR(200) NOT NULL, 
	rol VARCHAR(10) NOT NULL, 
	activo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (username)
);


CREATE TABLE empleado (
	id INTEGER NOT NULL, 
	codigo VARCHAR(30) NOT NULL, 
	ci VARCHAR(20) NOT NULL, 
	complemento VARCHAR(5) NOT NULL, 
	expedido VARCHAR(4) NOT NULL, 
	nombres VARCHAR(120) NOT NULL, 
	apellidos VARCHAR(120) NOT NULL, 
	cargo VARCHAR(200) NOT NULL, 
	unidad_id INTEGER, 
	horario_id INTEGER, 
	nro_cua VARCHAR(20) NOT NULL, 
	activo BOOLEAN NOT NULL, 
	creado DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (ci, complemento), 
	UNIQUE (codigo), 
	FOREIGN KEY(unidad_id) REFERENCES unidad_organizacional (id), 
	FOREIGN KEY(horario_id) REFERENCES horario (id)
);

CREATE INDEX ix_empleado_ci ON empleado (ci);

CREATE TABLE marca (
	id INTEGER NOT NULL, 
	lote_id INTEGER NOT NULL, 
	identificador VARCHAR(30) NOT NULL, 
	fecha_hora DATETIME NOT NULL, 
	tipo_evento VARCHAR(40) NOT NULL, 
	metodo VARCHAR(40) NOT NULL, 
	dispositivo VARCHAR(60) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_marca UNIQUE (identificador, fecha_hora, dispositivo), 
	FOREIGN KEY(lote_id) REFERENCES import_biometrico (id)
);

CREATE INDEX ix_marca_fecha ON marca (fecha_hora);
CREATE INDEX ix_marca_identificador ON marca (identificador);

CREATE TABLE turno (
	id INTEGER NOT NULL, 
	horario_id INTEGER NOT NULL, 
	orden INTEGER NOT NULL, 
	nombre VARCHAR(30) NOT NULL, 
	hora_entrada TIME NOT NULL, 
	hora_salida TIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (horario_id, orden), 
	FOREIGN KEY(horario_id) REFERENCES horario (id) ON DELETE CASCADE
);


CREATE TABLE contrato (
	id INTEGER NOT NULL, 
	empleado_id INTEGER NOT NULL, 
	modalidad VARCHAR(20) NOT NULL, 
	partida VARCHAR(10) NOT NULL, 
	haber_basico NUMERIC(14, 2) NOT NULL, 
	bono_antiguedad NUMERIC(14, 2) NOT NULL, 
	rc_iva NUMERIC(14, 2) NOT NULL, 
	aplica_aporte BOOLEAN NOT NULL, 
	tasa_afp NUMERIC(7, 4), 
	tasa_patronal NUMERIC(7, 4), 
	fecha_inicio DATE NOT NULL, 
	fecha_fin DATE, 
	fecha_baja DATE, 
	causal_baja VARCHAR(40) NOT NULL, 
	nro_documento VARCHAR(60) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_contrato_modalidad CHECK (modalidad in ('PERMANENTE','EVENTUAL','CONSULTOR_LINEA')), 
	FOREIGN KEY(empleado_id) REFERENCES empleado (id)
);

CREATE INDEX ix_contrato_emp_inicio ON contrato (empleado_id, fecha_inicio);

CREATE TABLE instructivo_destinatario (
	id INTEGER NOT NULL, 
	instructivo_id INTEGER NOT NULL, 
	empleado_id INTEGER NOT NULL, 
	notificacion VARCHAR(12) NOT NULL, 
	fecha_notificacion DATETIME, 
	observacion VARCHAR(250) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (instructivo_id, empleado_id), 
	FOREIGN KEY(instructivo_id) REFERENCES instructivo (id) ON DELETE CASCADE, 
	FOREIGN KEY(empleado_id) REFERENCES empleado (id)
);


CREATE TABLE permiso (
	id INTEGER NOT NULL, 
	nro_boleta VARCHAR(40) NOT NULL, 
	empleado_id INTEGER NOT NULL, 
	tipo_codigo VARCHAR(30) NOT NULL, 
	fecha_desde DATE NOT NULL, 
	fecha_hasta DATE NOT NULL, 
	hora_desde TIME, 
	hora_hasta TIME, 
	motivo TEXT NOT NULL, 
	doc_respaldo VARCHAR(200) NOT NULL, 
	estado VARCHAR(10) NOT NULL, 
	autorizado_por VARCHAR(150) NOT NULL, 
	gestion_vacacion VARCHAR(15) NOT NULL, 
	saldo_vacacion VARCHAR(40) NOT NULL, 
	creado_por VARCHAR(60) NOT NULL, 
	creado DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_permiso_estado CHECK (estado in ('PENDIENTE','APROBADO','RECHAZADO','ANULADO')), 
	UNIQUE (nro_boleta), 
	FOREIGN KEY(empleado_id) REFERENCES empleado (id), 
	FOREIGN KEY(tipo_codigo) REFERENCES permiso_tipo (codigo)
);

CREATE INDEX ix_permiso_emp_fecha ON permiso (empleado_id, fecha_desde, fecha_hasta);

CREATE TABLE asistencia_dia (
	id INTEGER NOT NULL, 
	empleado_id INTEGER NOT NULL, 
	fecha DATE NOT NULL, 
	estado VARCHAR(25) NOT NULL, 
	marcas VARCHAR(120) NOT NULL, 
	min_retraso INTEGER NOT NULL, 
	nro_retrasos INTEGER NOT NULL, 
	min_salida_anticipada INTEGER NOT NULL, 
	falta NUMERIC(8, 2) NOT NULL, 
	justificado NUMERIC(8, 2) NOT NULL, 
	justificado_sin_goce NUMERIC(8, 2) NOT NULL, 
	categoria_just VARCHAR(15) NOT NULL, 
	permiso_id INTEGER, 
	observacion VARCHAR(250) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (empleado_id, fecha), 
	FOREIGN KEY(empleado_id) REFERENCES empleado (id), 
	FOREIGN KEY(permiso_id) REFERENCES permiso (id)
);

CREATE INDEX ix_asis_fecha ON asistencia_dia (fecha);

CREATE TABLE liquidacion (
	id INTEGER NOT NULL, 
	anio INTEGER NOT NULL, 
	mes INTEGER NOT NULL, 
	empleado_id INTEGER NOT NULL, 
	contrato_id INTEGER NOT NULL, 
	modalidad VARCHAR(20) NOT NULL, 
	haber_basico NUMERIC(14, 2) NOT NULL, 
	dias_trabajados NUMERIC(8, 2) NOT NULL, 
	bono_antiguedad NUMERIC(14, 2) NOT NULL, 
	total_ganado NUMERIC(14, 2) NOT NULL, 
	aporte_laboral NUMERIC(14, 2) NOT NULL, 
	aporte_patronal NUMERIC(14, 2) NOT NULL, 
	rc_iva NUMERIC(14, 2) NOT NULL, 
	dias_laborables NUMERIC(8, 2) NOT NULL, 
	dias_asistidos NUMERIC(8, 2) NOT NULL, 
	faltas NUMERIC(8, 2) NOT NULL, 
	min_retraso INTEGER NOT NULL, 
	nro_retrasos INTEGER NOT NULL, 
	dias_justificados NUMERIC(8, 2) NOT NULL, 
	dias_desc_faltas NUMERIC(8, 2) NOT NULL, 
	dias_desc_atrasos NUMERIC(8, 2) NOT NULL, 
	dias_desc_sin_goce NUMERIC(8, 2) NOT NULL, 
	dias_desc_exceso_consultor NUMERIC(8, 2) NOT NULL, 
	desc_faltas NUMERIC(14, 2) NOT NULL, 
	desc_atrasos NUMERIC(14, 2) NOT NULL, 
	desc_otros NUMERIC(14, 2) NOT NULL, 
	dias_descuento NUMERIC(8, 2) NOT NULL, 
	desc_asistencia NUMERIC(14, 2) NOT NULL, 
	total_descuentos NUMERIC(14, 2) NOT NULL, 
	liquido_pagable NUMERIC(14, 2) NOT NULL, 
	sancion VARCHAR(200) NOT NULL, 
	observacion VARCHAR(400) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (anio, mes, empleado_id), 
	FOREIGN KEY(empleado_id) REFERENCES empleado (id), 
	FOREIGN KEY(contrato_id) REFERENCES contrato (id)
);


-- Inalterabilidad de la bitácora y de las marcas biométricas (SAFCO)
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_log BEGIN SELECT RAISE(ABORT,'audit_log es inalterable'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_log BEGIN SELECT RAISE(ABORT,'audit_log es inalterable'); END;
CREATE TRIGGER IF NOT EXISTS marca_no_update BEFORE UPDATE ON marca BEGIN SELECT RAISE(ABORT,'las marcas biometricas son inalterables'); END;
