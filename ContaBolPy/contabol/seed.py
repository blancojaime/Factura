"""Siembra de datos iniciales de una gestión: tipos de comprobante, plan de cuentas, parámetros y catálogos."""
from __future__ import annotations

from .db import Database
from .normativa import GRUPOS_ACTIVO
from .seed_plan import LINEAS

TIPOS_COMPROBANTE = [
    ("I", "Ingreso", "I"), ("E", "Egreso", "E"), ("T", "Traspaso", "T"),
    ("AP", "Apertura", "AP"), ("AJ", "Ajuste", "AJ"), ("CI", "Cierre", "CI"),
]

PARAMETROS = {
    "IVA_PCT": "13", "IT_PCT": "3", "IT_SIN_FACTURA": "1", "NIVEL_IMPRESION": "5", "STOCK_NEGATIVO": "0",
    "CONTROL_PRESUPUESTO": "0", "TC_DEFECTO": "6.96", "IUE_PROVISION": "0", "COSTEO": "PROMEDIO",
    "CTA_CAJA": "1.1.1.01.001", "CTA_CF_IVA": "1.1.2.03.001", "CTA_DF_IVA": "2.1.2.01.001",
    "CTA_IT_GASTO": "5.3.1.03.001", "CTA_IT_PAGAR": "2.1.2.01.002", "CTA_IUE_GASTO": "5.3.1.03.002",
    "CTA_IUE_PAGAR": "2.1.2.01.003", "CTA_CXC": "1.1.2.01.001", "CTA_CXP": "2.1.1.01.001",
    "CTA_ANT_CLI": "2.1.1.02.001", "CTA_ANT_PROV": "1.1.2.02.001", "CTA_INVENT": "1.1.3.01.001",
    "CTA_VENTAS": "4.1.1.01.001", "CTA_COSTO_VTA": "5.1.1.01.001", "CTA_DESC_VEN": "4.1.1.02.001",
    "CTA_REC_VEN": "4.2.1.01.003", "CTA_DESC_COMP": "4.2.1.01.007", "CTA_REC_COMP": "5.4.1.01.006",
    "CTA_MERMAS": "5.4.1.01.005", "CTA_AJUSTE_ING": "4.2.1.01.005", "CTA_AJUSTE_EGR": "5.5.1.01.004",
    "CTA_DIFCAMBIO_ING": "4.2.1.01.004", "CTA_DIFCAMBIO_EGR": "5.5.1.01.003", "CTA_RESULTADO": "3.2.1.01.002",
    "CTA_RESULT_ACUM": "3.2.1.01.001", "CTA_MP": "1.1.3.02.001", "CTA_PT": "1.1.3.02.003", "CTA_MOD": "5.2.1.01.002",
    "CTA_CIF": "5.2.1.01.003", "CTA_AJUSTE_AF": "4.2.1.01.005", "CTA_BAJA_AF": "5.6.1.01.002",
    "CTA_ACREEDORES": "2.1.1.03.001", "CTA_SUELDOS": "5.3.1.01.001", "CTA_BONO_ANTIG": "5.3.1.01.002",
    "CTA_HEXTRAS": "5.3.1.01.003", "CTA_OTROS_BONOS": "5.3.1.01.012", "CTA_SUELDOS_PAGAR": "2.1.3.01.001",
    "CTA_AFP_LAB_PAGAR": "2.1.3.01.002", "CTA_AFP_PAT_PAGAR": "2.1.3.01.003", "CTA_CNS_PAGAR": "2.1.3.01.004",
    "CTA_VIVIENDA_PAGAR": "2.1.3.01.005", "CTA_SOLIDARIO_PAGAR": "2.1.3.01.006", "CTA_RCIVA_PAGAR": "2.1.2.01.006",
    "CTA_ANTICIPO_PERS": "1.1.2.02.002", "CTA_GASTO_CNS": "5.3.1.01.008", "CTA_GASTO_RIESGO": "5.3.1.01.009",
    "CTA_GASTO_VIVIENDA": "5.3.1.01.010", "CTA_GASTO_SOLIDARIO": "5.3.1.01.011", "CTA_GASTO_AGUINALDO": "5.3.1.01.004",
    "CTA_PROV_AGUINALDO": "2.1.3.02.001", "CTA_GASTO_INDEM": "5.3.1.01.006", "CTA_PROV_INDEM": "2.2.1.02.001",
}

# ---- Clasificación para el flujo de efectivo (método directo) y estados -----------------------------------------
# flujo: EFECTIVO | COBROS | PAGOS_PROV | PAGOS_PERS | IMPUESTOS | OTROS_OP | INV | FIN | NOCASH | TC | NA


def _flujo(cod: str, tipo: str) -> str:
    p = cod
    if p.startswith("1.1.1"):
        return "EFECTIVO"
    if p.startswith("1.1.2.01") or p.startswith("1.1.2.05"):
        return "COBROS"
    if p.startswith("1.1.2.02.001"):
        return "PAGOS_PROV"
    if p.startswith("1.1.2.02.002"):
        return "PAGOS_PERS"
    if p.startswith("1.1.2.03"):
        return "IMPUESTOS"
    if p.startswith("1.1.2"):
        return "OTROS_OP"
    if p.startswith("1.1.3") or p.startswith("1.1.4"):
        return "PAGOS_PROV"
    if p.startswith("1.2.1.02") or p.startswith("1.2.2.01.003"):
        return "NOCASH"
    if p.startswith("1.2"):
        return "INV"
    if p.startswith("2.1.1.01"):
        return "PAGOS_PROV"
    if p.startswith("2.1.1.02"):
        return "COBROS"
    if p.startswith("2.1.1"):
        return "OTROS_OP"
    if p.startswith("2.1.2"):
        return "IMPUESTOS"
    if p.startswith("2.1.3"):
        return "PAGOS_PERS"
    if p.startswith("2.1.4.01.003"):
        return "OTROS_OP"
    if p.startswith("2.1.4") or p.startswith("2.2.1.01"):
        return "FIN"
    if p.startswith("2.2.1.02.001"):
        return "PAGOS_PERS"
    if p.startswith("2.2"):
        return "OTROS_OP"
    if p.startswith("3.1.1.01.003") or p.startswith("3.1.2.01.002") or p.startswith("3.1.2.01.003"):
        return "NOCASH"
    if p.startswith("3.1") or p.startswith("3.2.1.01.001"):
        return "FIN"
    if p.startswith("3.2.1.01.002"):
        return "NA"
    if p.startswith("4.2.1.01.004") or p.startswith("5.5.1.01.003"):
        return "TC"
    if p.startswith("4.2.1.01.005") or p.startswith("5.5.1.01.004") or p.startswith("5.3.1.04") or p.startswith("5.3.1.05"):
        return "NOCASH"
    if p.startswith("4.2.1.01.007"):
        return "PAGOS_PROV"
    if p.startswith("4.1"):
        return "COBROS"
    if p.startswith("4.2"):
        return "OTROS_OP"
    if p.startswith("5.1") or p.startswith("5.2.1.01.001") or p.startswith("5.2.1.01.003"):
        return "PAGOS_PROV"
    if p.startswith("5.2.1.01.002") or p.startswith("5.3.1.01"):
        return "PAGOS_PERS"
    if p.startswith("5.3.1.02") or p.startswith("5.4"):
        return "PAGOS_PROV"
    if p.startswith("5.3.1.03"):
        return "IMPUESTOS"
    if p.startswith("5.5") or p.startswith("5.6"):
        return "OTROS_OP"
    return "NA"


def _patr_col(cod: str) -> str | None:
    if cod.startswith("3.1.1.01.003"):
        return "AJCAPITAL"
    if cod.startswith("3.1.1"):
        return "CAPITAL"
    if cod.startswith("3.1.2"):
        return "RESERVAS"
    if cod.startswith("3.2"):
        return "RESULT"
    return None


def sembrar_gestion(db: Database, datos_empresa: dict, anio: int) -> None:
    """Crea tipos de comprobante, plan de cuentas, parámetros y catálogos básicos en una gestión nueva."""
    with db.tx():
        for t in TIPOS_COMPROBANTE:
            db.execute("INSERT INTO tipo_comprobante (codigo, nombre, prefijo) VALUES (?,?,?)", t)
        ids: dict[str, int] = {}
        for linea in LINEAS:
            partes = linea.split(";")
            cod, nombre = partes[0], partes[1]
            ind = partes[2] if len(partes) > 2 else ""
            nivel = cod.count(".") + 1
            padre = ".".join(cod.split(".")[:-1]) if nivel > 1 else None
            tipo = {"1": "A", "2": "P", "3": "T", "4": "I", "5": "G", "6": "O", "7": "O"}[cod[0]]
            nat = {"A": "D", "P": "C", "T": "C", "I": "C", "G": "D"}.get(tipo, "D" if cod[0] == "6" else "C")
            reg = 1 if "-" in ind else 0
            if reg:
                nat = "C" if nat == "D" else "D"
            flujo = _flujo(cod, tipo)
            corriente = 1 if (cod.startswith("1.1") or cod.startswith("2.1")) else 0
            ids[cod] = db.insert(
                "cuenta", codigo=cod, nombre=nombre, nivel=nivel, padre_id=ids.get(padre) if padre else None,
                es_movimiento=1 if nivel == 5 else 0, tipo=tipo, naturaleza=nat,
                moneda_extranjera=1 if "U" in ind else 0, ajustable=1 if "A" in ind else 0,
                es_banco=1 if "B" in ind else 0, es_efectivo=1 if cod.startswith("1.1.1") and nivel == 5 else 0,
                regularizadora=reg, corriente=corriente, flujo=flujo, patr_col=_patr_col(cod),
                costo_tipo="F" if "F" in ind else ("V" if "V" in ind else None),
                presupuestable=1 if tipo in ("G",) and nivel == 5 else 0)
        for k, v in PARAMETROS.items():
            db.execute("INSERT INTO parametro (clave, valor) VALUES (?,?)", (k, v))
        for k, v in {"EMP_NOMBRE": datos_empresa.get("razon_social", ""), "EMP_NIT": datos_empresa.get("nit", "") or "",
                     "EMP_DIRECCION": datos_empresa.get("direccion", "") or "", "EMP_CIUDAD": datos_empresa.get("ciudad", "") or "",
                     "EMP_GESTION": str(anio)}.items():
            db.execute("INSERT INTO parametro (clave, valor) VALUES (?,?)", (k, v))
        for nombre, vida, pct, ca, cd, cg in GRUPOS_ACTIVO:
            db.execute("INSERT INTO activo_grupo (nombre, vida_anios, pct, cta_activo, cta_dep, cta_gasto) VALUES (?,?,?,?,?,?)",
                       (nombre, vida, pct, ca, cd, cg))
        db.insert("almacen", codigo="ALM01", nombre="Almacén Central")
        db.insert("unidad", codigo="UN", nombre="Unidad")
        db.insert("unidad", codigo="KG", nombre="Kilogramo")
        db.insert("unidad", codigo="LT", nombre="Litro")
        db.insert("unidad", codigo="CJ", nombre="Caja")
        db.insert("grupo_item", codigo="GEN", nombre="General")
        db.insert("centro_costo", codigo="ADM", nombre="Administración")
        db.insert("centro_costo", codigo="VTA", nombre="Ventas")
        db.insert("centro_costo", codigo="PRD", nombre="Producción")
