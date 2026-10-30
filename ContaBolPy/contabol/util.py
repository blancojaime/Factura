"""Utilidades generales: dinero, fechas, formato boliviano y número en letras."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

MESES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def D(x) -> Decimal:
    """Convierte a Decimal de forma segura (None/'' = 0)."""
    if x is None or x == "":
        return Decimal(0)
    if isinstance(x, Decimal):
        return x
    if isinstance(x, float):
        return Decimal(repr(x))
    try:
        return Decimal(str(x).strip())
    except InvalidOperation:
        return Decimal(0)


def r2(x) -> float:
    """Redondea a 2 decimales (mitad hacia arriba) y devuelve float para almacenar."""
    return float(D(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def rn(x, n: int) -> float:
    return float(D(x).quantize(Decimal(1).scaleb(-n), rounding=ROUND_HALF_UP))


def nz(x, default=0.0):
    return default if x is None else x


def fmt(x, dec: int = 2, cero: str = "0,00") -> str:
    """Formato boliviano: 1.234.567,89"""
    if x is None:
        return ""
    v = rn(x, dec)
    s = f"{abs(v):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if v < 0:
        s = "-" + s
    return s


def parse_num(text) -> float:
    """Acepta '1.234,56', '1234.56', '1,234.56' y similares."""
    if text is None:
        return 0.0
    if isinstance(text, (int, float)):
        return float(text)
    s = str(text).strip().replace(" ", "").replace("Bs", "").replace("$", "")
    if not s:
        return 0.0
    neg = s.startswith("-") or (s.startswith("(") and s.endswith(")"))
    s = s.strip("-()")
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        partes = s.split(",")
        if len(partes) == 2 and len(partes[1]) <= 4:
            s = partes[0] + "." + partes[1]
        else:
            s = s.replace(",", "")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    try:
        v = float(s)
    except ValueError:
        return 0.0
    return -v if neg else v


def to_date(x) -> date | None:
    if x is None or x == "":
        return None
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x
    s = str(x).strip()[:10]
    for f in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def iso(d) -> str | None:
    d = to_date(d)
    return d.isoformat() if d else None


def fdate(d) -> str:
    d = to_date(d)
    return d.strftime("%d/%m/%Y") if d else ""


def fin_de_mes(anio: int, mes: int) -> date:
    if mes == 12:
        return date(anio, 12, 31)
    return date(anio, mes + 1, 1) - timedelta(days=1)


def meses_entre(d1: date, d2: date) -> int:
    return (d2.year - d1.year) * 12 + d2.month - d1.month


def anios_meses_dias(desde: date, hasta: date) -> tuple[int, int, int]:
    """Antigüedad en años, meses y días (convención 30/360)."""
    d1 = min(desde.day, 30)
    d2 = min(hasta.day, 30)
    total = (hasta.year - desde.year) * 360 + (hasta.month - desde.month) * 30 + (d2 - d1) + 1
    total = max(total, 0)
    return total // 360, (total % 360) // 30, (total % 360) % 30


_U = ["", "un", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce",
      "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve", "veinte", "veintiún",
      "veintidós", "veintitrés", "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho", "veintinueve"]
_D = ["", "", "", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"]
_C = ["", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos", "setecientos",
      "ochocientos", "novecientos"]


def _centenas(n: int) -> str:
    if n == 0:
        return ""
    if n == 100:
        return "cien"
    c, r = divmod(n, 100)
    out = _C[c]
    if r:
        if r < 30:
            out += " " + _U[r]
        else:
            d, u = divmod(r, 10)
            out += " " + _D[d] + (" y " + _U[u] if u else "")
    return out.strip()


def numero_a_letras(n: int) -> str:
    if n == 0:
        return "cero"
    partes = []
    millones, resto = divmod(n, 1_000_000)
    miles, unidades = divmod(resto, 1000)
    if millones:
        partes.append("un millón" if millones == 1 else _centenas(millones).replace("un ", "un ") + " millones")
    if miles:
        partes.append("mil" if miles == 1 else _centenas(miles) + " mil")
    if unidades:
        partes.append(_centenas(unidades))
    s = " ".join(partes)
    return s.replace("uno mil", "un mil")


def monto_en_letras(monto, moneda: str = "BS") -> str:
    """'Son: Mil doscientos treinta y cuatro 56/100 Bolivianos'"""
    v = D(monto).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    ent = int(abs(v))
    cent = int((abs(v) - ent) * 100)
    nom = "Bolivianos" if moneda.upper() in ("BS", "BOB") else "Dólares Americanos"
    txt = numero_a_letras(ent)
    txt = txt[:1].upper() + txt[1:]
    return f"Son: {txt} {cent:02d}/100 {nom}"


def limpiar(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def mes_nombre(m: int) -> str:
    return MESES[m] if 1 <= m <= 12 else ""
