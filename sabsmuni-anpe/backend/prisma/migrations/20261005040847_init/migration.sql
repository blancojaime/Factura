-- CreateEnum
CREATE TYPE "NombreRol" AS ENUM ('UNIDAD_SOLICITANTE', 'RESPONSABLE_PRESUPUESTO', 'RESPONSABLE_CONTRATACIONES', 'AUTORIDAD_RPA', 'ADMINISTRADOR_SISTEMA');

-- CreateEnum
CREATE TYPE "TipoObjeto" AS ENUM ('BIENES', 'SERVICIOS', 'OBRAS');

-- CreateEnum
CREATE TYPE "MetodoSeleccion" AS ENUM ('PRECIO_EVALUADO_MAS_BAJO', 'CALIDAD_PROPUESTA_COSTO');

-- CreateEnum
CREATE TYPE "EstadoFlujo" AS ENUM ('BORRADOR', 'REQUERIMIENTO_VALIDADO', 'PRESUPUESTO_CERTIFICADO', 'DBC_ELABORADO', 'DBC_APROBADO', 'PUBLICADO', 'EVALUACION', 'RECOMENDACION_EMITIDA', 'ADJUDICADO', 'DESIERTO', 'CONTRATO_FORMALIZADO', 'RECEPCION', 'LIQUIDADO', 'CANCELADO');

-- CreateEnum
CREATE TYPE "CategoriaProponente" AS ENUM ('NACIONAL_GENERAL', 'MYPE_APP_OECA', 'EXTRANJERO');

-- CreateEnum
CREATE TYPE "TipoInstrumento" AS ENUM ('CONTRATO', 'ORDEN_COMPRA', 'ORDEN_SERVICIO');

-- CreateEnum
CREATE TYPE "TipoDocumento" AS ENUM ('SOLICITUD_C1', 'JUSTIFICACION_CHB', 'PREVENTIVO_C31', 'DBC', 'INFORME_V1', 'CUADRO_COMPARATIVO', 'INFORME_EVALUACION', 'ACTA_ADJUDICACION', 'CONTRATO', 'ORDEN_COMPRA_SERVICIO', 'ACTA_RECEPCION', 'DEVENGADO_C31', 'EXPEDIENTE_UNICO', 'OTRO');

-- CreateTable
CREATE TABLE "roles" (
    "id" SERIAL NOT NULL,
    "nombre" "NombreRol" NOT NULL,
    "descripcion" TEXT NOT NULL,

    CONSTRAINT "roles_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "usuarios" (
    "id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "nombre" TEXT NOT NULL,
    "cargo" TEXT,
    "unidad" TEXT,
    "password_hash" TEXT NOT NULL,
    "activo" BOOLEAN NOT NULL DEFAULT true,
    "rol_id" INTEGER NOT NULL,
    "creado_en" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "usuarios_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "sesiones" (
    "id" TEXT NOT NULL,
    "usuario_id" TEXT NOT NULL,
    "refresh_hash" TEXT NOT NULL,
    "ip" TEXT,
    "user_agent" TEXT,
    "creada_en" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "expira_en" TIMESTAMP(3) NOT NULL,
    "revocada_en" TIMESTAMP(3),

    CONSTRAINT "sesiones_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "logs_auditoria" (
    "id" BIGSERIAL NOT NULL,
    "fecha" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "usuario_id" TEXT,
    "usuario_email" TEXT,
    "ip" TEXT,
    "accion" TEXT NOT NULL,
    "entidad" TEXT NOT NULL,
    "entidad_id" TEXT,
    "estado_previo" JSONB,
    "estado_posterior" JSONB,
    "hash_previo" TEXT NOT NULL,
    "hash" TEXT NOT NULL,

    CONSTRAINT "logs_auditoria_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "config_institucional" (
    "id" INTEGER NOT NULL DEFAULT 1,
    "nombre_gam" TEXT NOT NULL,
    "nit" TEXT NOT NULL,
    "da" TEXT NOT NULL,
    "ue" TEXT NOT NULL,
    "ciudad" TEXT NOT NULL,
    "departamento" TEXT NOT NULL,
    "direccion" TEXT NOT NULL,
    "rpa_nombre" TEXT NOT NULL,
    "rpa_cargo" TEXT NOT NULL,
    "margenes" JSONB,
    "plazos" JSONB,

    CONSTRAINT "config_institucional_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "feriados" (
    "id" SERIAL NOT NULL,
    "fecha" DATE NOT NULL,
    "descripcion" TEXT NOT NULL,
    "ambito" TEXT NOT NULL DEFAULT 'NACIONAL',

    CONSTRAINT "feriados_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "catalogo_partidas" (
    "codigo" TEXT NOT NULL,
    "descripcion" TEXT NOT NULL,
    "grupo" TEXT NOT NULL,

    CONSTRAINT "catalogo_partidas_pkey" PRIMARY KEY ("codigo")
);

-- CreateTable
CREATE TABLE "catalogo_chb" (
    "id" TEXT NOT NULL,
    "codigo_unspsc" TEXT NOT NULL,
    "descripcion" TEXT NOT NULL,
    "productor" TEXT,
    "ficha_url" TEXT,
    "vigente" BOOLEAN NOT NULL DEFAULT true,

    CONSTRAINT "catalogo_chb_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "marcas_registradas" (
    "id" SERIAL NOT NULL,
    "nombre" TEXT NOT NULL,

    CONSTRAINT "marcas_registradas_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "procesos_anpe" (
    "id" TEXT NOT NULL,
    "codigo" TEXT NOT NULL,
    "cuce_provisorio" TEXT NOT NULL,
    "objeto_contratacion" TEXT NOT NULL,
    "tipo_objeto" "TipoObjeto" NOT NULL,
    "precio_referencial_total" DECIMAL(14,2) NOT NULL DEFAULT 0,
    "metodo_seleccion" "MetodoSeleccion" NOT NULL,
    "estado_flujo" "EstadoFlujo" NOT NULL DEFAULT 'BORRADOR',
    "id_solicitante" TEXT NOT NULL,
    "id_rpa" TEXT,
    "plazo_ejecucion_dias" INTEGER,
    "requerimiento" JSONB,
    "evaluacion" JSONB,
    "propuesta_adjudicada_id" TEXT,
    "resolucion_obs" TEXT,
    "resolucion_fecha" TIMESTAMP(3),
    "creado_en" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "actualizado_en" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "procesos_anpe_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "items_contratacion" (
    "id" TEXT NOT NULL,
    "proceso_id" TEXT NOT NULL,
    "numero" INTEGER NOT NULL,
    "codigo_unspsc" TEXT NOT NULL,
    "partida_gasto" TEXT NOT NULL,
    "descripcion_tecnica" TEXT NOT NULL,
    "unidad_medida" TEXT NOT NULL,
    "cantidad" DECIMAL(14,3) NOT NULL,
    "precio_unitario" DECIMAL(14,2) NOT NULL,
    "precio_total" DECIMAL(14,2) NOT NULL,
    "ficha_chb_id" TEXT,
    "requiere_excepcion_chb" BOOLEAN NOT NULL DEFAULT false,
    "incompatibilidad_tecnica" TEXT,
    "resultado_chb" TEXT,

    CONSTRAINT "items_contratacion_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "cronogramas_anpe" (
    "id" TEXT NOT NULL,
    "proceso_id" TEXT NOT NULL,
    "fecha_publicacion" DATE NOT NULL,
    "fecha_apertura" DATE NOT NULL,
    "fecha_adjudicacion" DATE NOT NULL,
    "fecha_presentacion_doc" DATE NOT NULL,
    "fecha_contrato" DATE NOT NULL,

    CONSTRAINT "cronogramas_anpe_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "certificaciones_presupuesto" (
    "id" TEXT NOT NULL,
    "proceso_id" TEXT NOT NULL,
    "da" TEXT NOT NULL,
    "ue" TEXT NOT NULL,
    "programa" TEXT NOT NULL,
    "proyecto" TEXT NOT NULL,
    "actividad_obra" TEXT NOT NULL,
    "fuente" TEXT NOT NULL,
    "organismo" TEXT NOT NULL,
    "partida" TEXT NOT NULL,
    "importe" DECIMAL(14,2) NOT NULL,
    "c31_preventivo_numero" TEXT,

    CONSTRAINT "certificaciones_presupuesto_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "propuestas_rupe" (
    "id" TEXT NOT NULL,
    "proceso_id" TEXT NOT NULL,
    "orden" INTEGER NOT NULL,
    "nit_proveedor" TEXT NOT NULL,
    "razon_social" TEXT NOT NULL,
    "categoria" "CategoriaProponente" NOT NULL DEFAULT 'NACIONAL_GENERAL',
    "monto_ofertado" DECIMAL(14,2) NOT NULL,
    "monto_subasta" DECIMAL(14,2),
    "plazo_dias" INTEGER NOT NULL,
    "puntaje_tecnico" DECIMAL(5,2),
    "v1" JSONB NOT NULL DEFAULT '{}',
    "califica_v1" BOOLEAN NOT NULL DEFAULT false,
    "margen_probolivia_mype" DECIMAL(5,2) NOT NULL DEFAULT 0,

    CONSTRAINT "propuestas_rupe_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "contratos" (
    "id" TEXT NOT NULL,
    "proceso_id" TEXT NOT NULL,
    "tipo" "TipoInstrumento" NOT NULL,
    "numero" TEXT NOT NULL,
    "propuesta_id" TEXT NOT NULL,
    "monto" DECIMAL(14,2) NOT NULL,
    "plazo_dias" INTEGER NOT NULL,
    "fecha_firma" DATE NOT NULL,
    "garantia_porcentaje" DECIMAL(5,2) NOT NULL,
    "garantia_monto" DECIMAL(14,2) NOT NULL,
    "garantia_instrumento" TEXT,
    "poliza_numero" TEXT,
    "poliza_entidad" TEXT,
    "poliza_vigencia_hasta" DATE,
    "fecha_recepcion" DATE,
    "observacion_recepcion" TEXT,

    CONSTRAINT "contratos_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "documentos_expediente" (
    "id" TEXT NOT NULL,
    "proceso_id" TEXT NOT NULL,
    "tipo_documento" "TipoDocumento" NOT NULL,
    "ruta_archivo" TEXT NOT NULL,
    "hash_sha256" TEXT NOT NULL,
    "hash_contenido" TEXT,
    "version" INTEGER NOT NULL,
    "generado" BOOLEAN NOT NULL DEFAULT true,
    "paginas" INTEGER,
    "creado_por" TEXT,
    "creado_en" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "documentos_expediente_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "roles_nombre_key" ON "roles"("nombre");

-- CreateIndex
CREATE UNIQUE INDEX "usuarios_email_key" ON "usuarios"("email");

-- CreateIndex
CREATE UNIQUE INDEX "sesiones_refresh_hash_key" ON "sesiones"("refresh_hash");

-- CreateIndex
CREATE INDEX "sesiones_usuario_id_idx" ON "sesiones"("usuario_id");

-- CreateIndex
CREATE INDEX "logs_auditoria_entidad_entidad_id_idx" ON "logs_auditoria"("entidad", "entidad_id");

-- CreateIndex
CREATE INDEX "logs_auditoria_fecha_idx" ON "logs_auditoria"("fecha");

-- CreateIndex
CREATE UNIQUE INDEX "feriados_fecha_key" ON "feriados"("fecha");

-- CreateIndex
CREATE INDEX "catalogo_chb_codigo_unspsc_idx" ON "catalogo_chb"("codigo_unspsc");

-- CreateIndex
CREATE UNIQUE INDEX "catalogo_chb_codigo_unspsc_productor_key" ON "catalogo_chb"("codigo_unspsc", "productor");

-- CreateIndex
CREATE UNIQUE INDEX "marcas_registradas_nombre_key" ON "marcas_registradas"("nombre");

-- CreateIndex
CREATE UNIQUE INDEX "procesos_anpe_codigo_key" ON "procesos_anpe"("codigo");

-- CreateIndex
CREATE UNIQUE INDEX "procesos_anpe_propuesta_adjudicada_id_key" ON "procesos_anpe"("propuesta_adjudicada_id");

-- CreateIndex
CREATE INDEX "procesos_anpe_estado_flujo_idx" ON "procesos_anpe"("estado_flujo");

-- CreateIndex
CREATE INDEX "procesos_anpe_id_solicitante_idx" ON "procesos_anpe"("id_solicitante");

-- CreateIndex
CREATE UNIQUE INDEX "items_contratacion_proceso_id_numero_key" ON "items_contratacion"("proceso_id", "numero");

-- CreateIndex
CREATE UNIQUE INDEX "cronogramas_anpe_proceso_id_key" ON "cronogramas_anpe"("proceso_id");

-- CreateIndex
CREATE INDEX "certificaciones_presupuesto_proceso_id_idx" ON "certificaciones_presupuesto"("proceso_id");

-- CreateIndex
CREATE UNIQUE INDEX "propuestas_rupe_proceso_id_nit_proveedor_key" ON "propuestas_rupe"("proceso_id", "nit_proveedor");

-- CreateIndex
CREATE UNIQUE INDEX "propuestas_rupe_proceso_id_orden_key" ON "propuestas_rupe"("proceso_id", "orden");

-- CreateIndex
CREATE UNIQUE INDEX "contratos_proceso_id_key" ON "contratos"("proceso_id");

-- CreateIndex
CREATE INDEX "documentos_expediente_hash_sha256_idx" ON "documentos_expediente"("hash_sha256");

-- CreateIndex
CREATE INDEX "documentos_expediente_hash_contenido_idx" ON "documentos_expediente"("hash_contenido");

-- CreateIndex
CREATE UNIQUE INDEX "documentos_expediente_proceso_id_tipo_documento_version_key" ON "documentos_expediente"("proceso_id", "tipo_documento", "version");

-- AddForeignKey
ALTER TABLE "usuarios" ADD CONSTRAINT "usuarios_rol_id_fkey" FOREIGN KEY ("rol_id") REFERENCES "roles"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "sesiones" ADD CONSTRAINT "sesiones_usuario_id_fkey" FOREIGN KEY ("usuario_id") REFERENCES "usuarios"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "procesos_anpe" ADD CONSTRAINT "procesos_anpe_id_solicitante_fkey" FOREIGN KEY ("id_solicitante") REFERENCES "usuarios"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "procesos_anpe" ADD CONSTRAINT "procesos_anpe_id_rpa_fkey" FOREIGN KEY ("id_rpa") REFERENCES "usuarios"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "items_contratacion" ADD CONSTRAINT "items_contratacion_proceso_id_fkey" FOREIGN KEY ("proceso_id") REFERENCES "procesos_anpe"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "cronogramas_anpe" ADD CONSTRAINT "cronogramas_anpe_proceso_id_fkey" FOREIGN KEY ("proceso_id") REFERENCES "procesos_anpe"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "certificaciones_presupuesto" ADD CONSTRAINT "certificaciones_presupuesto_proceso_id_fkey" FOREIGN KEY ("proceso_id") REFERENCES "procesos_anpe"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "propuestas_rupe" ADD CONSTRAINT "propuestas_rupe_proceso_id_fkey" FOREIGN KEY ("proceso_id") REFERENCES "procesos_anpe"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "contratos" ADD CONSTRAINT "contratos_proceso_id_fkey" FOREIGN KEY ("proceso_id") REFERENCES "procesos_anpe"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "documentos_expediente" ADD CONSTRAINT "documentos_expediente_proceso_id_fkey" FOREIGN KEY ("proceso_id") REFERENCES "procesos_anpe"("id") ON DELETE CASCADE ON UPDATE CASCADE;
