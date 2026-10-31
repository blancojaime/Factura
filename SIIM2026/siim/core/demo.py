"""Datos de DEMOSTRACIÓN para capacitación y pruebas (gestión 2004, valores ilustrativos). No usar en producción."""
from datetime import date, timedelta

from ..services import padron
from ..services.base import Ctx

UFV_A, UFV_B = 1.08593, 1.10293        # 31/12/2004 y 21/04/2005 (ejemplo de los Apuntes Tributarios)


def cargar_cotizaciones_demo(db):
    d0, d1 = date(2002, 12, 26), date(2005, 12, 31)
    with db.tx():
        # puntos conocidos de los Apuntes: 26/12/2002 UFV 1.00815 / USD 7.49 ; 15/01/2002 USD 6.86
        db.execute("INSERT OR REPLACE INTO cotizaciones VALUES('2002-01-15','HABIL',6.86,0.97)")
        db.execute("INSERT OR REPLACE INTO cotizaciones VALUES('2002-12-26','HABIL',7.49,1.00815)")
        db.execute("INSERT OR REPLACE INTO cotizaciones VALUES('2004-12-31','HABIL',8.06,?)", (UFV_A,))
        d, n = date(2005, 1, 1), 0
        span = (date(2005, 4, 21) - date(2004, 12, 31)).days
        while d <= date(2005, 12, 31):
            k = (d - date(2004, 12, 31)).days
            ufv = UFV_A + (UFV_B - UFV_A) * k / span
            tipo = "FERIADO" if d.weekday() >= 5 else "HABIL"
            db.execute("INSERT OR REPLACE INTO cotizaciones VALUES(?,?,?,?)", (d.isoformat(), tipo, round(8.06 + 0.0004 * k, 2), round(ufv, 5)))
            d += timedelta(days=1)
        db.execute("INSERT OR REPLACE INTO cotizaciones VALUES('2005-04-21','HABIL',8.10,?)", (UFV_B,))
        db.execute("INSERT OR REPLACE INTO tasas_interes VALUES('2004-01-01',0.1082)")
        db.set_param("gestion_desde", "2004")
        db.set_param("gestion_hasta", "2004")
        db.set_param("municipio", "GOBIERNO AUTÓNOMO MUNICIPAL DE DEMOSTRACIÓN")


def cargar_padron_demo(ctx: Ctx) -> dict:
    ids = {}
    n = lambda **k: padron.nuevo_contribuyente(ctx, {**dict(tipo_doc="CI", expedido="LP", tipo_via="CALLE"), **k}, nro_orden=str(len(ids) + 1), fecha="2005-01-10")
    ids["perez"] = n(persona="N", nro_doc="4455667", paterno="Pérez", materno="Vedia", nombre="Fernando", zona="A", barrio="B01", calle="Bolívar", numero="123")
    ids["lopez"] = n(persona="N", nro_doc="3322110", paterno="López", materno="Gómez", nombre="Roberto", zona="B", barrio="B02", calle="Sucre", numero="45")
    ids["caballero"] = n(persona="N", nro_doc="6677889", paterno="Caballero", materno="Gutiérrez", nombre="Fausto", zona="C", calle="Murillo", numero="900")
    ids["fideos"] = n(persona="J", tipo_doc="NIT", nro_doc="1023456029", nit="1023456029", razon_social="Fábrica de Fideos CONSUELO S.R.L.", zona="B", calle="La Paz", numero="701")
    ids["farmacia"] = n(persona="N", nro_doc="5544332", paterno="Mamani", materno="Quispe", nombre="Rosa", zona="1", calle="Comercio", numero="210")
    ids["bene"] = n(persona="N", nro_doc="1100220", paterno="Vargas", materno="Ríos", nombre="Anselmo", zona="D", calle="Chaco", numero="12", benemerito=1)
    I = lambda pmc, **k: padron.guardar_objeto(ctx, "inmuebles", pmc, {**dict(tipo_via="CALLE", inclinacion="PLANO", exento="NINGUNO"), **k})
    ids["inm_perez"] = I(ids["perez"], tipo="CASA", zona="A", calle="Bolívar", numero="123", material_via="ASFALTO", superficie=250, luz=1, agua=1, alcantarillado=1, telefono=1,
                         calidad="BUENA", sup_construida=180, anio_construccion=1995, cod_catastral="01-023-004")
    ids["inm_lopez"] = I(ids["lopez"], tipo="CASA", zona="B", calle="Sucre", numero="45", material_via="LOSETA", superficie=300, luz=1, agua=1, alcantarillado=0, telefono=0,
                         calidad="ECONOMICA", sup_construida=120, anio_construccion=2001, cod_catastral="02-011-008")
    ids["inm_cab"] = I(ids["caballero"], tipo="TERRENO", zona="C", calle="Murillo", numero="900", material_via="RIPIO", superficie=500, luz=1, agua=0, alcantarillado=0, telefono=0,
                       inclinacion="INCLINADO")
    ids["inm_rural"] = I(ids["caballero"], tipo="RURAL", zona="D", calle="Camino Viejo", superficie=20000, valor_declarado=150000)
    ids["inm_fideos"] = I(ids["fideos"], tipo="CASA", zona="B", calle="La Paz", numero="701", material_via="ASFALTO", superficie=800, luz=1, agua=1, alcantarillado=1, telefono=1,
                          calidad="MUY BUENA", sup_construida=600, anio_construccion=1988)
    ids["inm_bene"] = I(ids["bene"], tipo="CASA", zona="D", calle="Chaco", numero="12", material_via="TIERRA", superficie=200, luz=1, agua=1, calidad="ECONOMICA",
                        sup_construida=80, anio_construccion=1970, exento="BENEMERITO")
    V = lambda pmc, **k: padron.guardar_objeto(ctx, "vehiculos", pmc, {**dict(exento="NINGUNO", uso="PARTICULAR"), **k})
    ids["veh_perez"] = V(ids["perez"], placa="1234-ABC", tipo="VAGONETA", marca="Toyota", modelo="Land Cruiser", procedencia="JAPON", anio_fab=2001, cilindrada=4200, puertas=4, doble_traccion=1)
    ids["veh_lopez"] = V(ids["lopez"], placa="2210-XYZ", tipo="AUTOMOVIL", marca="Suzuki", modelo="Swift", procedencia="JAPON", anio_fab=1998, cilindrada=1300, puertas=2)
    ids["veh_fideos"] = V(ids["fideos"], placa="3030-CAM", tipo="CAMION", marca="Volvo", modelo="FM", procedencia="EUROPA_OCC", anio_fab=1999, cilindrada=4800, toneladas=8,
                          chasis="CABINADO", carroceria="ESTACAS", plazas=3)
    ids["veh_moto"] = V(ids["farmacia"], placa="777-MOT", tipo="MOTOCICLETA", marca="Honda", modelo="XR", procedencia="JAPON", anio_fab=2003, cilindrada=250)
    A = lambda pmc, **k: padron.guardar_objeto(ctx, "actividades", pmc, {**dict(exento="NINGUNO", habitualidad="PERMANENTE", tipo_via="CALLE"), **k})
    ids["act_farm"] = A(ids["farmacia"], act="14", cat="05", nombre_comercial="Farmacia La Salud", zona="1", superficie=45, fecha_inicio="2001-03-15", calle="Comercio", numero="210", ciiu="52311")
    ids["act_tienda"] = A(ids["lopez"], act="12", cat="01", nombre_comercial="Tienda Doña Rosa", zona="3", superficie=12, fecha_inicio="2004-07-01", calle="Sucre", numero="45")
    ids["act_ferr"] = A(ids["perez"], act="14", cat="03", nombre_comercial="Ferretería El Tornillo", zona="2", superficie=90, fecha_inicio="1999-01-10", calle="Bolívar", numero="125")
    ids["act_fideos"] = A(ids["fideos"], act="01", cat="06", nombre_comercial="Fideos CONSUELO", zona="2", superficie=600, fecha_inicio="1988-05-01", calle="La Paz", numero="701")
    ids["act_hotel"] = A(ids["perez"], act="08", cat="01", nombre_comercial="Hotel Plaza", zona="1", superficie=400, fecha_inicio="2002-01-01", fecha_cese="2004-06-30", calle="Plaza Principal", numero="1")
    ids["pub"] = padron.guardar_objeto(ctx, "publicidad", ids["farmacia"], dict(tipo="LUMINOSO_2C", descripcion="Letrero luminoso Farmacia La Salud", ubicacion="Av. Comercio 210", ancho=2, alto=1.5, exento="NINGUNO"))
    return ids
