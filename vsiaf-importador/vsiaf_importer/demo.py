"""Datos de demostración: estructura de las tablas del VSIAF 2.0, una base de datos sintética
(para pruebas / ensayo del importador sin tocar su base real) y filas de ejemplo para la plantilla.

La estructura de ``SPECS`` es la de las tablas reales del VSIAF 2.0 (campo, tipo, largo, decimales).
"""
from __future__ import annotations

import datetime as dt
import os
from typing import Any, Dict, List

from .dbf import DbfTable, create_table
from .vsiafdb import load_bundled_catalogs

SPECS = {'ACTUAL': {'lang': 3,
            'version': 245,
            'fields': [('UNIDAD', 'C', 5, 0),
                       ('ENTIDAD', 'C', 4, 0),
                       ('CODIGO', 'C', 15, 0),
                       ('CODCONT', 'N', 2, 0),
                       ('CODAUX', 'N', 3, 0),
                       ('VIDAUTIL', 'N', 6, 2),
                       ('DESCRIP', 'C', 150, 0),
                       ('COSTO', 'N', 15, 2),
                       ('DEPACU', 'N', 15, 2),
                       ('MES', 'N', 2, 0),
                       ('ANO', 'N', 4, 0),
                       ('B_REV', 'L', 1, 0),
                       ('DIA', 'N', 2, 0),
                       ('CODOFIC', 'N', 4, 0),
                       ('CODRESP', 'N', 5, 0),
                       ('OBSERV', 'M', 10, 0),
                       ('DIA_ANT', 'N', 2, 0),
                       ('MES_ANT', 'N', 2, 0),
                       ('ANO_ANT', 'N', 4, 0),
                       ('VUT_ANT', 'N', 3, 0),
                       ('COSTO_ANT', 'N', 15, 2),
                       ('BAND_UFV', 'L', 1, 0),
                       ('CODESTADO', 'N', 2, 0),
                       ('COD_RUBE', 'C', 15, 0),
                       ('NRO_CONV', 'C', 10, 0),
                       ('ORG_FIN', 'C', 3, 0),
                       ('FEULT', 'D', 8, 0),
                       ('USUAR', 'C', 8, 0),
                       ('API_ESTADO', 'N', 1, 0),
                       ('CODIGOSEC', 'C', 15, 0),
                       ('BANDERAS', 'C', 12, 0),
                       ('FEC_MOD', 'D', 8, 0),
                       ('USU_MOD', 'C', 8, 0)]},
 'REVAL': {'lang': 3,
           'version': 245,
           'fields': [('ENTIDAD', 'C', 4, 0),
                      ('UNIDAD', 'C', 5, 0),
                      ('CODIGO', 'C', 15, 0),
                      ('COSTO', 'N', 15, 2),
                      ('DEPACU_ANT', 'N', 15, 2),
                      ('D_REVAL', 'N', 2, 0),
                      ('DIA', 'N', 2, 0),
                      ('M_REVAL', 'N', 2, 0),
                      ('MES', 'N', 2, 0),
                      ('A_REVAL', 'N', 4, 0),
                      ('ANO', 'N', 4, 0),
                      ('VIDAUTIL', 'N', 5, 2),
                      ('RESOLUCION', 'C', 16, 0),
                      ('OBSERV', 'M', 10, 0),
                      ('USUAR', 'C', 8, 0),
                      ('FEULT', 'D', 8, 0),
                      ('DEPACU', 'N', 15, 2),
                      ('ACTUA', 'N', 15, 2),
                      ('DEPGESTION', 'N', 15, 2),
                      ('FEC_MOD', 'D', 8, 0),
                      ('USU_MOD', 'C', 8, 0)]},
 'BAJAS': {'lang': 3,
           'version': 245,
           'fields': [('ENTIDAD', 'C', 4, 0),
                      ('UNIDAD', 'C', 5, 0),
                      ('CODIGO', 'C', 15, 0),
                      ('CODBAJA', 'N', 2, 0),
                      ('CODCONT', 'N', 2, 0),
                      ('CODAUX', 'N', 3, 0),
                      ('CODOFIC', 'N', 4, 0),
                      ('CODRESP', 'N', 5, 0),
                      ('COSTO', 'N', 15, 2),
                      ('DEPACU_ANT', 'N', 15, 2),
                      ('DESCRIP', 'C', 120, 0),
                      ('D_BAJA', 'N', 2, 0),
                      ('DIA', 'N', 2, 0),
                      ('M_BAJA', 'N', 2, 0),
                      ('MES', 'N', 2, 0),
                      ('A_BAJA', 'N', 4, 0),
                      ('ANO', 'N', 4, 0),
                      ('B_REV', 'L', 1, 0),
                      ('VIDAUTIL', 'N', 5, 2),
                      ('RESOLUCION', 'C', 16, 0),
                      ('OBSERV', 'M', 10, 0),
                      ('MOTIVO', 'C', 120, 0),
                      ('DEPACU', 'N', 15, 2),
                      ('ACTUA', 'N', 15, 2),
                      ('DEPGESTION', 'N', 15, 2),
                      ('COSBAJINI', 'N', 15, 2),
                      ('COSDAINI', 'N', 15, 2),
                      ('COSACTBAJ', 'N', 15, 2),
                      ('ACTDABAJ', 'N', 15, 2),
                      ('USUAR', 'C', 8, 0),
                      ('FEULT', 'D', 8, 0),
                      ('FEC_MOD', 'D', 8, 0),
                      ('USU_MOD', 'C', 8, 0)]},
 'BAJA': {'lang': 3, 'version': 3, 'fields': [('CODBAJA', 'N', 2, 0), ('DESCBAJA', 'C', 120, 0)]},
 'TRASFE': {'lang': 3,
            'version': 3,
            'fields': [('ENTIDAD', 'C', 4, 0),
                       ('UNIDAD', 'C', 5, 0),
                       ('CODIGO', 'C', 15, 0),
                       ('CODOFIC', 'N', 4, 0),
                       ('CODRESP', 'N', 5, 0),
                       ('FEULT', 'D', 8, 0),
                       ('USUAR', 'C', 8, 0),
                       ('UNIDADINI', 'C', 5, 0)]},
 'OFICINA': {'lang': 3,
             'version': 245,
             'fields': [('ENTIDAD', 'C', 4, 0),
                        ('UNIDAD', 'C', 5, 0),
                        ('CODOFIC', 'N', 4, 0),
                        ('NOMOFIC', 'C', 65, 0),
                        ('OBSERV', 'M', 10, 0),
                        ('FEULT', 'D', 8, 0),
                        ('USUAR', 'C', 8, 0),
                        ('API_ESTADO', 'N', 1, 0)]},
 'RESP': {'lang': 3,
          'version': 245,
          'fields': [('ENTIDAD', 'C', 4, 0),
                     ('UNIDAD', 'C', 5, 0),
                     ('CODOFIC', 'N', 4, 0),
                     ('CODRESP', 'N', 5, 0),
                     ('NOMRESP', 'C', 35, 0),
                     ('CARGO', 'C', 35, 0),
                     ('OBSERV', 'M', 10, 0),
                     ('CI', 'C', 20, 0),
                     ('FEULT', 'D', 8, 0),
                     ('USUAR', 'C', 8, 0),
                     ('COD_EXP', 'N', 2, 0),
                     ('API_ESTADO', 'N', 1, 0)]},
 'AUXILIAR': {'lang': 2,
              'version': 245,
              'fields': [('ENTIDAD', 'C', 4, 0),
                         ('UNIDAD', 'C', 5, 0),
                         ('CODCONT', 'N', 2, 0),
                         ('CODAUX', 'N', 3, 0),
                         ('NOMAUX', 'C', 50, 0),
                         ('OBSERV', 'M', 10, 0),
                         ('FEULT', 'D', 8, 0),
                         ('USUAR', 'C', 8, 0)]},
 'UNIDADADMIN': {'lang': 3,
                 'version': 3,
                 'fields': [('ENTIDAD', 'C', 4, 0),
                            ('UNIDAD', 'C', 5, 0),
                            ('DESCRIP', 'C', 120, 0),
                            ('CIUDAD', 'C', 20, 0),
                            ('ESTADOUNI', 'N', 1, 0)]},
 'CODCONT': {'lang': 3,
             'version': 245,
             'fields': [('CODCONT', 'N', 2, 0),
                        ('NOMBRE', 'C', 50, 0),
                        ('VIDAUTIL', 'N', 4, 0),
                        ('OBSERV', 'M', 10, 0),
                        ('DEPRECIAR', 'L', 1, 0),
                        ('ACTUALIZAR', 'L', 1, 0),
                        ('FEULT', 'D', 8, 0),
                        ('USUAR', 'C', 8, 0)]},
 'ESTADO': {'lang': 3, 'version': 48, 'fields': [('CODESTADO', 'N', 2, 0), ('NOMESTADO', 'C', 10, 0)]},
 'ORGANISMO_FIN': {'lang': 3,
                   'version': 3,
                   'fields': [('GESTION', 'N', 4, 0), ('OF', 'C', 3, 0), ('DES', 'C', 100, 0), ('SIGLA', 'C', 15, 0)]},
 'CLA_DEPTS': {'lang': 3, 'version': 3, 'fields': [('CODIGO', 'N', 2, 0), ('DESC', 'C', 15, 0), ('SIGLA', 'C', 10, 0)]},
 'CONFIG': {'lang': 3,
            'version': 3,
            'fields': [('ENTIDAD', 'C', 4, 0),
                       ('DESCENT', 'C', 120, 0),
                       ('UNIDAD', 'C', 5, 0),
                       ('DESCUNI', 'C', 120, 0),
                       ('USUARIO', 'C', 10, 0)]}}


def make_demo_install(root: str, entidad: str = "9999", entidad_nombre: str = "ENTIDAD DE DEMOSTRACION",
                      unidad: str = "1", unidad_desc: str = "UNIDAD ADMINISTRATIVA DEMO") -> str:
    """Crea ``root/dbfs`` con tablas vacías del VSIAF + catálogos y devuelve ``root``."""
    dbfs = os.path.join(root, "dbfs")
    os.makedirs(dbfs, exist_ok=True)
    os.makedirs(os.path.join(root, "backups"), exist_ok=True)
    for name, sp in SPECS.items():
        create_table(os.path.join(dbfs, name + ".DBF"), sp["fields"], lang=sp["lang"], version=sp["version"])
    cat = load_bundled_catalogs()
    t = DbfTable(os.path.join(dbfs, "CODCONT.DBF"))
    for g in cat["grupos"]:
        t.append(dict(CODCONT=g["codcont"], NOMBRE=g["nombre"], VIDAUTIL=int(g["vida_util"]),
                      DEPRECIAR=g["depreciar"], ACTUALIZAR=g["actualizar"]))
    t.save()
    for name, rows, mapper in (
        ("ESTADO", cat["estados"], lambda r: dict(CODESTADO=r["codigo"], NOMESTADO=r["nombre"])),
        ("BAJA", cat["motivos_baja"], lambda r: dict(CODBAJA=r["codigo"], DESCBAJA=r["nombre"])),
        ("ORGANISMO_FIN", cat["organismos_financiadores"],
         lambda r: dict(GESTION=2013, OF=r["codigo"], DES=r["nombre"], SIGLA=r["sigla"])),
        ("CLA_DEPTS", cat["departamentos"], lambda r: dict(CODIGO=r["codigo"], DESC=r["nombre"], SIGLA=r["sigla"])),
    ):
        t = DbfTable(os.path.join(dbfs, name + ".DBF"))
        for r in rows:
            t.append(mapper(r))
        t.save()
    t = DbfTable(os.path.join(dbfs, "CONFIG.DBF"))
    t.append(dict(ENTIDAD=entidad, DESCENT=entidad_nombre, UNIDAD=unidad, DESCUNI=unidad_desc, USUARIO="admin"))
    t.save()
    t = DbfTable(os.path.join(dbfs, "UNIDADADMIN.DBF"))
    t.append(dict(ENTIDAD=entidad, UNIDAD=unidad, DESCRIP=unidad_desc, CIUDAD="LA PAZ", ESTADOUNI=1))
    t.save()
    return root


def demo_rows(today: dt.date | None = None) -> Dict[str, List[Dict[str, Any]]]:
    """Filas de ejemplo (autocontenidas) para la plantilla «con ejemplos»."""
    today = today or dt.date.today()
    cap = dt.date(2026, 12, 31)                 # fin de la tabla UFV incluida
    ref = min(today, cap)
    d = lambda n: (ref - dt.timedelta(days=n))
    f = lambda x: x.strftime("%d/%m/%Y")
    return {
        "UNIDADES": [dict(unidad="901", descripcion="UNIDAD DE EJEMPLO", ciudad="LA PAZ")],
        "OFICINAS": [dict(unidad="901", oficina="ADMINISTRACION"), dict(unidad="901", oficina="ALMACEN")],
        "RESPONSABLES": [
            dict(unidad="901", oficina="ADMINISTRACION", responsable="ANA PEREZ MAMANI", cargo="JEFE ADMINISTRATIVO",
                 ci="1234567", expedido="LPZ"),
            dict(unidad="901", oficina="ALMACEN", responsable="CARLOS QUISPE", cargo="ENCARGADO DE ALMACEN",
                 ci="7654321", expedido="CBB")],
        "AUXILIARES": [dict(unidad="901", grupo_contable="EQUIPOS DE COMPUTACION", auxiliar="LAPTOP"),
                       dict(unidad="901", grupo_contable="MUEBLES Y ENSERES DE OFICINA", auxiliar="ESCRITORIO")],
        "ACTIVOS": [
            dict(unidad="901", codigo="EJ-0001", descripcion="LAPTOP DELL LATITUDE 5420 CORE I5 8GB",
                 grupo_contable="EQUIPOS DE COMPUTACION", auxiliar="LAPTOP", oficina="ADMINISTRACION",
                 responsable="ANA PEREZ MAMANI", estado_bien="Bueno", fecha_incorporacion=f(d(90)),
                 costo_inicial=9500.00, organismo_financiador="111", estado_registro="APROBADO"),
            dict(unidad="901", codigo="EJ-0002", descripcion="ESCRITORIO DE MELAMINA 1.40 X 0.70",
                 grupo_contable="MUEBLES Y ENSERES DE OFICINA", auxiliar="ESCRITORIO", oficina="ALMACEN",
                 responsable="CARLOS QUISPE", estado_bien="Regular", fecha_incorporacion=f(d(60)),
                 costo_inicial=1800.00, organismo_financiador="113", estado_registro="APROBADO"),
            dict(unidad="901", codigo="EJ-0003", descripcion="LAPTOP HP 250 G8 (ELABORADO)",
                 grupo_contable=15, auxiliar="LAPTOP", oficina="ADMINISTRACION", responsable="ANA PEREZ MAMANI",
                 estado_bien="Bueno", fecha_incorporacion=f(d(10)), costo_inicial=6200.00,
                 organismo_financiador="111")],
        "REVALUOS": [dict(unidad="901", codigo="EJ-0002", fecha_revaluo=f(d(20)), nuevo_costo=2100.00,
                          nueva_vida_util=10, disposicion_respaldo="R-001/2026", motivo="REVALUO TECNICO")],
        "TRANSFERENCIAS": [dict(unidad_origen="901", codigo="EJ-0001", oficina_destino="ALMACEN",
                                responsable_destino="CARLOS QUISPE")],
        "BAJAS": [dict(unidad="901", codigo="EJ-0002", fecha_baja=f(d(5)), motivo_baja="Inutilización",
                       disposicion_respaldo="B-010/2026", observaciones="DETERIORO IRREPARABLE")],
    }
