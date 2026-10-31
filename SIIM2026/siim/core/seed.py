"""Carga de catálogos y tablas base iniciales. Las tablas de la gestión 2004 son EJEMPLOS tomados de la Guía de
Implementación del SIIM; cada municipio debe cargar las vigentes (Resolución Ministerial / ley municipal)."""
import json
from datetime import date

from .paths import resource_dir

MATERIALES = ["ASFALTO", "ADOQUIN", "CEMENTO", "LOSETA", "PIEDRA", "RIPIO", "TIERRA", "LADRILLO"]
CALIDADES_CASA = ["LUJO", "MUY BUENA", "BUENA", "ECONOMICA", "INTERES SOCIAL", "MARGINAL"]
CALIDADES_DEPTO = ["LUJO", "MUY BUENA", "BUENA", "ECONOMICA"]
TIPOS_INMUEBLE = ["CASA", "TERRENO", "DEPARTAMENTO", "RURAL"]
TIPOS_VIA = ["CALLE", "AVENIDA", "PLAZA", "PASAJE"]
INCLINACIONES = ["PLANO", "INCLINADO", "MUY INCLINADO"]
TIPOS_VEHICULO = ["AUTOMOVIL", "JEEP", "VAGONETA", "CAMIONETA", "MINIBUS", "MICROBUS", "BUS", "CAMION", "TRACTOCAMION", "FURGONETA",
                  "MOTOCICLETA", "MOTONETA", "TRIMOVIL", "CUADRATRACK"]
USOS_VEHICULO = ["PARTICULAR", "PUBLICO", "COMERCIAL", "OFICIAL"]
CHASIS = ["", "TORPEDO", "CABINADO"]
CARROCERIAS = ["", "ESTACAS", "MICRO", "BUS", "OTROS"]
PROCEDENCIAS = ["LATINOAMERICA", "MEXICO", "JAPON", "USA", "EUROPA_OCC", "EUROPA_OR", "COREA_ASIA"]
TIPOS_DOC = ["CI", "RUN", "NIT", "PASAPORTE", "CEDULA_EXTRANJERA"]
EXPEDIDO = ["LP", "CB", "SC", "OR", "PT", "CH", "TJ", "BE", "PD", "EX"]
EXENCIONES = ["NINGUNO", "ESTADO", "INSTITUCION_SIN_FINES_LUCRO", "IGLESIA", "MISION_DIPLOMATICA", "BENEMERITO", "COMUNIDAD_ORIGINARIA", "OTRO"]
TIPOS_PUBLICIDAD = ["LUMINOSO_2C", "SIMPLE_2C", "SIMPLE_1C", "MURAL"]
RUBROS_LIQ = {"IPBI": "13310", "IPVA": "13330", "IMT": "13340", "PAF": "15341", "PUB": "15342"}
NOMBRE_RUBRO = {"IPBI": "Impuesto a la Propiedad de Bienes Inmuebles", "IPVA": "Impuesto a la Propiedad de Vehículos Automotores",
                "IMT": "Impuesto Municipal a las Transferencias", "PAF": "Patente Anual de Funcionamiento",
                "PUB": "Patente de Publicidad y Propaganda"}

PARAMS = {
    "municipio": "GOBIERNO AUTÓNOMO MUNICIPAL DE …", "codigo_ine": "", "departamento": "", "direccion": "", "telefono": "",
    "alcalde": "", "responsable_tributario": "", "base_legal": "Ley Municipal Nº … (Patentes y Tasas) – Ley 482 y Ley 154",
    "gestion_desde": str(date.today().year - 4), "gestion_hasta": str(date.today().year),
    "descuento_contado": "10", "imt_alicuota": "3", "reposicion_formulario": "4", "sancion_administrativa": "0",
    "modalidad_recaudacion": "CAJA", "comision_bancaria": "0", "persona_df_min_n": "50", "persona_df_min_j": "240", "df_max": "2400", "df_pct": "10",
    "modo_df_ufv": "DIVISION", "redondeo_deuda": "0", "patente_modalidad": "TOPE_ZONA_SUP", "patente_actualiza_dolar": "0", "patente_minima": "0",
    "licencia_vigencia_meses": "12", "alerta_licencia_dias": "30", "plan_max_cuotas": "36", "plan_tasa_anual": "0.1082", "plan_cuota_inicial_pct": "10",
    "backup_auto_horas": "12", "backup_al_cerrar": "1", "backup_externo": "", "backup_retencion": "30", "backup_clave": "",
    "sesion_minutos": "30", "prescripcion_anios": "4",
}


def _tb(db, table, rows):
    for r in rows:
        cols = ",".join(r)
        q = ",".join("?" * len(r))
        db.execute(f"INSERT OR REPLACE INTO {table}({cols}) VALUES({q})", list(r.values()))


def seed_base(db):
    """Idempotente: puede ejecutarse varias veces."""
    if db.scalar("SELECT COUNT(*) FROM parametros", default=0) > 0:
        return
    S = json.loads((resource_dir() / "data" / "seed.json").read_text(encoding="utf-8"))
    with db.tx():
        for k, v in PARAMS.items():
            db.set_param(k, v)
        for c, d, e in S["ciiu"]:
            db.execute("INSERT OR REPLACE INTO ciiu VALUES(?,?,?)", (c, d, e))
        for c, d in S["act_tipos"]:
            db.execute("INSERT OR REPLACE INTO act_tipos VALUES(?,?)", (c, d))
        for a, c, d in S["act_categorias"]:
            db.execute("INSERT OR REPLACE INTO act_categorias VALUES(?,?,?)", (a, c, d))
        for ge, d in S["historico"].items():
            _seed_historico(db, int(ge), d)
        _seed_2004(db)
        _seed_rubros(db)
        _seed_zonas(db)


def _rangos_cilindrada(db, g):
    veh = [(50, 0, 1200), (51, 1201, 1300), (52, 1301, 1500), (53, 1501, 1600), (54, 1601, 1800), (55, 1801, 2000), (56, 2001, 4000), (57, 4001, 99999)]
    moto = [(50, 0, 124), (51, 125, 249), (52, 250, 349), (53, 350, 549), (54, 550, 749), (55, 750, 999), (56, 1000, 1499), (57, 1500, 99999)]
    for rows, m in ((veh, 0), (moto, 1)):
        for c, a, b in rows:
            db.execute("INSERT OR REPLACE INTO tb_veh_cilindrada VALUES(?,?,?,?,?)", (g, c, a, b, m))


def _seed_historico(db, g, d):
    _rangos_cilindrada(db, g)
    for cod, vals in d.get("veh_valor", []):
        for proc, v in vals.items():
            db.execute("INSERT OR REPLACE INTO tb_veh_valor VALUES(?,?,?,?)", (g, cod, proc, v))
    for cod, v in d.get("moto_valor", []):
        db.execute("INSERT OR REPLACE INTO tb_moto_valor VALUES(?,?,?)", (g, cod, v))
    for i, f in d.get("veh_deprec", []):
        db.execute("INSERT OR REPLACE INTO tb_veh_deprec VALUES(?,?,?)", (g, i, f))
    for o, desde, hasta, cuota, pct, exc in d.get("veh_escala", []):
        db.execute("INSERT OR REPLACE INTO tb_veh_escala VALUES(?,?,?,?,?,?,?)", (g, o, desde, hasta if hasta is not None else 1e12, cuota, pct, exc))
    hasta_ton = {1: 3, 2: 5, 3: 11, 4: 13, 5: 999}
    for t, est, mic, bus, otros, tor, cab in d.get("veh_correccion", []):
        db.execute("INSERT OR REPLACE INTO tb_veh_correccion VALUES(?,?,?,?,?,?,?,?,?)", (g, t, hasta_ton[t], tor, cab, est, mic, bus, otros))


def _seed_2004(db):
    g = 2004
    for k, v in dict(inc_plano=1.0, inc_inclinado=0.9, inc_muy=0.8, serv_minimo=0.2, serv_luz=0.2, serv_agua=0.2, serv_alcant=0.2, serv_telef=0.2,
                     ipbi_rural_alicuota=0.2, veh_deduc_2puertas=0.15, veh_incr_turbo=0.20, veh_incr_doble_tr=0.15).items():
        db.execute("INSERT OR REPLACE INTO tb_param VALUES(?,?,?)", (g, k, v))
    vias = {"A": [75, 0, 0, 70, 68, 65, 62, 0], "B": [62, 0, 0, 59, 56, 54, 52, 0], "C": [40, 0, 0, 39, 37, 36, 35, 0], "D": [23, 0, 0, 28, 20, 17, 10, 0]}
    for z, vals in vias.items():
        for m, v in zip(MATERIALES, vals):
            db.execute("INSERT OR REPLACE INTO tb_material_via VALUES(?,?,?,?)", (g, z, m, v))
    for q, v in zip(CALIDADES_CASA, [1460, 1010, 680, 400, 251, 50]):
        db.execute("INSERT OR REPLACE INTO tb_calidad_const VALUES(?,?,?,?)", (g, "CASA", q, v))
    for q, v in zip(CALIDADES_DEPTO, [1960, 1740, 1678, 1320]):
        db.execute("INSERT OR REPLACE INTO tb_calidad_const VALUES(?,?,?,?)", (g, "DEPARTAMENTO", q, v))
    for a, b, f in [(0, 5, 1.0), (6, 10, .975), (11, 15, .925), (16, 20, .9), (21, 25, .85), (26, 30, .8), (31, 35, .75), (36, 40, .7), (41, 45, .65), (46, 50, .6), (51, 999, .55)]:
        db.execute("INSERT OR REPLACE INTO tb_deprec_inm VALUES(?,?,?,?)", (g, a, b, f))
    for i, (a, b, c, p, e) in enumerate([(1, 340972, 0, .35, 1), (340973, 681944, 1193, .5, 340972), (681945, 1022916, 2898, 1, 681944), (1022917, 1e12, 6308, 1.5, 1022916)], 1):
        db.execute("INSERT OR REPLACE INTO tb_escala_inm VALUES(?,?,?,?,?,?,?)", (g, i, a, b, c, p, e))
    _rangos_cilindrada(db, g)
    cuadro2 = {50: [41290, 58811, 64351, 64411, 75999, 54053, 51388], 51: [47831, 63119, 68132, 70201, 80522, 57230, 54563],
               52: [50929, 67432, 72605, 74329, 84996, 60989, 58285], 53: [55155, 70509, 76047, 78195, 89468, 63882, 65799],
               54: [60905, 80364, 86716, 89124, 110115, 72840, 74742], 55: [68132, 90523, 97384, 100136, 123884, 81800, 83717],
               56: [106331, 141327, 152103, 156234, 192707, 127762, 129681], 57: [146594, 169353, 182382, 172059, 223679, 153204, 160356]}
    # columnas del cuadro: LATINOAM-OTROS, MEXICO, JAPON, USA, EUR OCC, EUR OR, ASIA-COREA
    for cod, vals in cuadro2.items():
        for p, v in zip(["LATINOAMERICA", "MEXICO", "JAPON", "USA", "EUROPA_OCC", "EUROPA_OR", "COREA_ASIA"], vals):
            db.execute("INSERT OR REPLACE INTO tb_veh_valor VALUES(?,?,?,?)", (g, cod, p, v))
    for cod, v in zip(range(50, 58), [8742, 10016, 15006, 16419, 18672, 25022, 31284, 43783]):
        db.execute("INSERT OR REPLACE INTO tb_moto_valor VALUES(?,?,?)", (g, cod, v))
    for i, f in enumerate([0.80, 0.64, 0.51, 0.41, 0.33, 0.26, 0.21, 0.17, 0.13, 0.10]):   # Art. 60 Ley 843 (ejemplo)
        db.execute("INSERT OR REPLACE INTO tb_veh_deprec VALUES(?,?,?)", (g, i, f))
    for i, (a, b, c, p, e) in enumerate([(1, 41475, 0, 1.5, 1), (41476, 124423, 829, 2, 41475), (124424, 248846, 2903, 3, 124424),
                                         (248847, 497692, 7258, 4, 248847), (497693, 1e12, 18455, 5, 497693)], 1):
        db.execute("INSERT OR REPLACE INTO tb_veh_escala VALUES(?,?,?,?,?,?,?)", (g, i, a, b, c, p, e))
    for t, hasta, tor, cab, est, mic, bus, otros in [(1, 3, 0, .10, .12, 0, 0, .25), (2, 5, 0, .10, .12, .40, 0, .25), (3, 11, .20, .40, .12, .40, 1.0, .25),
                                                     (4, 13, 1.5, 2.0, .20, .40, 1.0, .25), (5, 999, 1.7, 2.2, .20, .40, 1.0, .25)]:
        db.execute("INSERT OR REPLACE INTO tb_veh_correccion VALUES(?,?,?,?,?,?,?,?,?)", (g, t, hasta, tor, cab, est, mic, bus, otros))
    # Patentes (Ordenanza modelo de la Guía): zona–superficie–porcentaje y publicidad
    tramos = [(1, 10), (11, 20), (21, 30), (31, 50), (51, 80), (81, 150), (151, 1e9)]
    pct = {"1": [40, 50, 60, 70, 80, 90, 100], "2": [30, 40, 50, 60, 70, 80, 90], "3": [20, 30, 40, 50, 60, 70, 80],
           "4": [10, 20, 30, 40, 50, 60, 70], "5": [5, 10, 20, 30, 40, 50, 60]}
    for z, ps in pct.items():
        for (a, b), p in zip(tramos, ps):
            db.execute("INSERT OR REPLACE INTO tb_act_zona_sup VALUES(?,?,?,?,?)", (g, z, a, b, p))
    for t, v in zip(TIPOS_PUBLICIDAD, [50, 30, 20, 10]):
        db.execute("INSERT OR REPLACE INTO tb_publicidad VALUES(?,?,?)", (g, t, v))
    for z, v in zip(["1", "2", "3", "4", "5"], [12, 9, 7, 5, 3]):
        db.execute("INSERT OR REPLACE INTO tb_act_pua VALUES(?,?,?)", (g, z, v))
    # Topes de ejemplo para la categoría 14 (Comercio en general) y 12 (minorista) – ilustrativos
    for (a, c, tope, fijo) in [("14", "02", 3000, 900), ("14", "03", 4000, 1200), ("14", "05", 4500, 1400), ("12", "01", 600, 240), ("12", "02", 400, 160),
                               ("08", "01", 20000, 6000), ("09", "01", 3500, 1000), ("10", "06", 12000, 3500), ("04", "01", 90000, 30000), ("01", "06", 2500, 800)]:
        db.execute("INSERT OR REPLACE INTO tb_act_tope VALUES(?,?,?,?,?)", (g, a, c, tope, fijo))
    for k in ("IPBI", "IPVA", "PAF"):
        db.execute("INSERT OR REPLACE INTO fechas_venc VALUES(?,?,?,?,?,?)", (k, g, "2005-03-31", "2005-03-31", "2005-06-30", "2005-04-30"))


def _seed_zonas(db):
    for c, d in [("A", "Zona Central"), ("B", "Zona Intermedia"), ("C", "Zona Periférica"), ("D", "Zona Popular")]:
        db.execute("INSERT OR IGNORE INTO zonas VALUES(?,?)", (c, d))
    for c, d in [("1", "Zona 1 – Comercial"), ("2", "Zona 2"), ("3", "Zona 3"), ("4", "Zona 4"), ("5", "Zona 5 – Periférica")]:
        db.execute("INSERT OR IGNORE INTO zonas VALUES(?,?)", (c, d))
    db.execute("INSERT OR IGNORE INTO barrios VALUES('B01','Barrio Centro','A')")
    db.execute("INSERT OR IGNORE INTO barrios VALUES('B02','Barrio Cuarto Centenario','B')")


def _seed_rubros(db):
    R = [("12000", "VENTA DE BIENES Y SERVICIOS DE LAS ADMINISTRACIONES PÚBLICAS", "N", 0, 1), ("12100", "Venta de Bienes de las Administraciones Públicas", "S", 1, 2),
         ("12200", "Venta de Servicios de las Administraciones Públicas", "S", 1, 2), ("12300", "Alquiler de Edificios y/o Equipos", "S", 1, 2),
         ("13000", "INGRESOS TRIBUTARIOS", "N", 0, 1), ("13300", "Impuestos Directos Municipales", "N", 0, 2),
         ("13310", "Impuesto a la Propiedad de Bienes Inmuebles", "S", 0, 3), ("13330", "Impuesto a la Propiedad de Vehículos Automotores", "S", 0, 3),
         ("13340", "Impuesto Municipal a las Transferencias", "S", 0, 3), ("13390", "Otros Impuestos Municipales (ICE Chicha de Maíz)", "S", 1, 3),
         ("15000", "TASAS, DERECHOS Y OTROS INGRESOS", "N", 0, 1), ("15100", "Tasas", "S", 1, 2), ("15200", "Derechos", "S", 1, 2),
         ("15300", "Patentes y Concesiones", "N", 0, 2), ("15340", "Patentes Municipales", "S", 1, 3),
         ("15341", "Patente Anual de Funcionamiento", "S", 0, 4), ("15342", "Patente de Publicidad y Propaganda", "S", 0, 4),
         ("15400", "Contribuciones por Mejoras", "S", 1, 2), ("15900", "Otros Ingresos", "N", 0, 2), ("15910", "Multas y Sanciones", "S", 1, 3),
         ("15990", "Otros Ingresos no Especificados", "S", 1, 3), ("16000", "INTERESES Y OTRAS RENTAS DE LA PROPIEDAD", "N", 0, 1),
         ("16130", "Otros Intereses (mora tributaria)", "S", 0, 2), ("16300", "Alquiler de Tierras y Terrenos", "S", 1, 2)]
    for r in R:
        db.execute("INSERT OR IGNORE INTO rubros VALUES(?,?,?,?,?)", r)
    S = [("151001.", "15100", None, "Tasas por Servicios Técnicos", "AGREGACION", "EVENTUAL", 0, 0),
         ("151001.001", "15100", "151001.", "Aprobación de planos de construcción (por m²)", "ENTRADA", "EVENTUAL", 1.5, 0),
         ("151001.002", "15100", "151001.", "Otorgación de Línea y Nivel (por metro lineal)", "ENTRADA", "EVENTUAL", 4, 0),
         ("151002.", "15100", None, "Tasas por Servicios Públicos", "AGREGACION", "MENSUAL", 0, 0),
         ("151002.001", "15100", "151002.", "Recojo de Basura (aseo urbano)", "ENTRADA", "MENSUAL", 12, 0),
         ("151002.002", "15100", "151002.", "Alumbrado público", "ENTRADA", "MENSUAL", 8, 0),
         ("151003.", "15100", None, "Tasas por Servicios Administrativos", "AGREGACION", "EVENTUAL", 0, 0),
         ("151003.001", "15100", "151003.", "Certificado de Solvencia Municipal", "ENTRADA", "EVENTUAL", 15, 0),
         ("151003.002", "15100", "151003.", "Legalización de fotocopias (por hoja)", "ENTRADA", "EVENTUAL", 2, 0),
         ("151003.003", "15100", "151003.", "Registro de vehículos", "ENTRADA", "EVENTUAL", 30, 0),
         ("151003.004", "15100", "151003.", "Reposición de formulario", "ENTRADA", "EVENTUAL", 4, 0),
         ("123001.", "12300", None, "Alquiler de Mercados", "AGREGACION", "MENSUAL", 0, 0),
         ("123001.001", "12300", "123001.", "Alquiler de caseta de mercado", "ENTRADA", "MENSUAL", 80, 0),
         ("153401.", "15340", None, "Patentes eventuales (Sentajes)", "AGREGACION", "EVENTUAL", 0, 0),
         ("153401.001", "15340", "153401.", "Sentaje – día ordinario", "ENTRADA", "EVENTUAL", 5, 0),
         ("153401.002", "15340", "153401.", "Sentaje – feria / día festivo", "ENTRADA", "EVENTUAL", 15, 0),
         ("153402.", "15340", None, "Espectáculos y recreaciones públicas", "AGREGACION", "EVENTUAL", 0, 0),
         ("153402.001", "15340", "153402.", "Espectáculo deportivo nacional (por fecha)", "ENTRADA", "EVENTUAL", 175, 0),
         ("153402.002", "15340", "153402.", "Espectáculo teatral/musical (por función)", "ENTRADA", "EVENTUAL", 30, 0),
         ("153402.003", "15340", "153402.", "Circo y similares (por función)", "ENTRADA", "EVENTUAL", 50, 0),
         ("153402.004", "15340", "153402.", "Sorteos, rifas y concursos (por vez)", "ENTRADA", "EVENTUAL", 50, 0),
         ("153402.005", "15340", "153402.", "Baile nocturno en fecha ordinaria", "ENTRADA", "EVENTUAL", 50, 0),
         ("153402.006", "15340", "153402.", "Juegos electrónicos (por aparato/mes)", "ENTRADA", "MENSUAL", 20, 0),
         ("153402.007", "15340", "153402.", "Salón de billar (por mesa/mes)", "ENTRADA", "MENSUAL", 30, 0),
         ("159101.", "15910", None, "Multas por infracciones municipales", "AGREGACION", "EVENTUAL", 0, 0),
         ("159101.001", "15910", "159101.", "Multa por venta no autorizada en vía pública", "ENTRADA", "EVENTUAL", 100, 0),
         ("159101.002", "15910", "159101.", "Multa por funcionamiento sin licencia", "ENTRADA", "EVENTUAL", 500, 0),
         ("133901.", "13390", None, "ICE – Chicha de Maíz", "AGREGACION", "EVENTUAL", 0, 0),
         ("133901.001", "13390", "133901.", "ICE Chicha de maíz (por litro, valor actualizado por UFV)", "ENTRADA", "EVENTUAL", 0.43, 0)]
    for c, r, p, d, t, f, m, pc in S:
        db.execute("INSERT OR IGNORE INTO subniveles(codigo,rubro,padre,descripcion,tipo,frecuencia,monto,porcentaje,documento) VALUES(?,?,?,?,?,?,?,?,?)",
                   (c, r, p, d, t, f, m, pc, "Ordenanza / Ley Municipal"))
