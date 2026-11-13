"""Certificacion POA, nota PAC e importaciones desde Excel

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-11 20:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

TIPOS_ANTES = ('C1_SOLICITUD', 'INFORME_EXCEPCION_CHB', 'CERTIFICACION_C31', 'FICHA_COTIZACION', 'CUADRO_COMPARATIVO',
               'NOTA_ADJUDICACION', 'ORDEN_COMPRA_SERVICIO', 'CONTRATO_ADMINISTRATIVO', 'ACTA_RECEPCION_FORM500')
TIPOS_AHORA = TIPOS_ANTES + ('CERTIFICACION_POA', 'NOTA_SOLICITUD_PAC')


def _in(tipos):
    return "tipo_doc IN (" + ", ".join(f"'{t}'" for t in tipos) + ")"


def upgrade() -> None:
    op.add_column('partidas_presupuestarias', sa.Column('descripcion_apertura', sa.String(length=250), nullable=False, server_default=''))
    op.add_column('partidas_presupuestarias', sa.Column('monto_ejecutado', sa.Numeric(precision=14, scale=2), nullable=False, server_default='0'))
    op.add_column('catalogo_chb', sa.Column('fecha_registro', sa.Date(), nullable=True))
    op.add_column('contrataciones_menores', sa.Column('justificacion_poa', sa.Text(), nullable=False, server_default=''))
    op.add_column('contrataciones_menores', sa.Column('fecha_publicacion_estimada', sa.Date(), nullable=True))
    op.create_table('objetivos_poa',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('gestion', sa.Integer(), nullable=False),
        sa.Column('programa', sa.String(length=10), nullable=False),
        sa.Column('denominacion_programa', sa.String(length=250), nullable=False),
        sa.Column('codigo_objetivo', sa.String(length=30), nullable=False),
        sa.Column('descripcion_objetivo', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gestion', 'programa', name='uq_objetivo_poa_programa'))
    op.drop_constraint('ck_doc_tipo', 'documentos_expediente', type_='check')
    op.create_check_constraint('ck_doc_tipo', 'documentos_expediente', _in(TIPOS_AHORA))


def downgrade() -> None:
    op.execute("DELETE FROM documentos_expediente WHERE tipo_doc IN ('CERTIFICACION_POA', 'NOTA_SOLICITUD_PAC')")
    op.drop_constraint('ck_doc_tipo', 'documentos_expediente', type_='check')
    op.create_check_constraint('ck_doc_tipo', 'documentos_expediente', _in(TIPOS_ANTES))
    op.drop_table('objetivos_poa')
    op.drop_column('contrataciones_menores', 'fecha_publicacion_estimada')
    op.drop_column('contrataciones_menores', 'justificacion_poa')
    op.drop_column('catalogo_chb', 'fecha_registro')
    op.drop_column('partidas_presupuestarias', 'monto_ejecutado')
    op.drop_column('partidas_presupuestarias', 'descripcion_apertura')
