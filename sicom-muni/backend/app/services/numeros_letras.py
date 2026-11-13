"""Monto en literal (Bolivianos) para documentos: 'Son: DIECIOCHO MIL QUINIENTOS 00/100 BOLIVIANOS'."""
from decimal import ROUND_HALF_UP, Decimal

_U = ["", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce",
      "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve", "veinte", "veintiuno",
      "veintidós", "veintitrés", "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho",
      "veintinueve"]
_D = ["", "", "", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"]
_C = ["", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos", "setecientos",
      "ochocientos", "novecientos"]


def _centenas(n: int, apocope: bool = False) -> str:
    if n == 100:
        return "cien"
    c, d = divmod(n, 100)
    partes = [_C[c]] if c else []
    if d:
        if d < 30:
            partes.append(_U[d])
        else:
            u = d % 10
            partes.append(_D[d // 10] + (f" y {_U[u]}" if u else ""))
    s = " ".join(partes).strip()
    if apocope:
        if s.endswith("veintiuno"):
            s = s[:-3] + "ún"
        elif s.endswith(" uno") or s == "uno":
            s = s[:-1]
    return s


def _entero_a_letras(n: int) -> str:
    if n == 0:
        return "cero"
    millones, resto = divmod(n, 1_000_000)
    miles, unidades = divmod(resto, 1000)
    s = ""
    if millones:
        s += "un millón " if millones == 1 else _centenas(millones, True) + " millones "
    if miles:
        s += "mil " if miles == 1 else _centenas(miles, True) + " mil "
    if unidades:
        s += _centenas(unidades)
    return s.strip()


def monto_literal(monto: Decimal | float | str) -> str:
    monto = Decimal(str(monto)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    entero = int(monto)
    centavos = int((monto - entero) * 100)
    return f"Son: {_entero_a_letras(entero).upper()} {centavos:02d}/100 BOLIVIANOS"
