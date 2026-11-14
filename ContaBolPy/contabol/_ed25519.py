"""Ed25519 (RFC 8032) en Python puro: firma, verificación y lectura/escritura de claves PEM (PKCS#8 y SPKI).

Se usa en lugar de la biblioteca `cryptography` porque sus versiones recientes (escritas en Rust) ya no funcionan en Windows 7.
Es la implementación de referencia del RFC 8032: suficiente para verificar un código de activación (milisegundos) y para que el proveedor
emita códigos. La firma no es de tiempo constante: úsela solo en el equipo del proveedor, no en servicios expuestos.
"""
from __future__ import annotations

import base64
import hashlib
import os

_P = 2 ** 255 - 19
_Q = 2 ** 252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_SQRT_M1 = pow(2, (_P - 1) // 4, _P)
_PKCS8_PREFIX = bytes.fromhex("302e020100300506032b657004220420")


def _inv(x: int) -> int:
    return pow(x, _P - 2, _P)


def _suma(a, b):
    A = (a[1] - a[0]) * (b[1] - b[0]) % _P
    B = (a[1] + a[0]) * (b[1] + b[0]) % _P
    C = 2 * a[3] * b[3] * _D % _P
    D = 2 * a[2] * b[2] % _P
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % _P, G * H % _P, F * G % _P, E * H % _P)


def _mul(s: int, punto):
    q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            q = _suma(q, punto)
        punto = _suma(punto, punto)
        s >>= 1
    return q


def _iguales(a, b) -> bool:
    return (a[0] * b[2] - b[0] * a[2]) % _P == 0 and (a[1] * b[2] - b[1] * a[2]) % _P == 0


def _recuperar_x(y: int, signo: int):
    if y >= _P:
        return None
    x2 = (y * y - 1) * _inv(_D * y * y + 1) % _P
    if x2 == 0:
        return None if signo else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P != 0:
        x = x * _SQRT_M1 % _P
    if (x * x - x2) % _P != 0:
        return None
    if (x & 1) != signo:
        x = _P - x
    return x


_GY = 4 * _inv(5) % _P
_GX = _recuperar_x(_GY, 0)
_G = (_GX, _GY, 1, _GX * _GY % _P)


def _comprimir(p) -> bytes:
    zi = _inv(p[2])
    x, y = p[0] * zi % _P, p[1] * zi % _P
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _descomprimir(s: bytes):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    signo = y >> 255
    y &= (1 << 255) - 1
    x = _recuperar_x(y, signo)
    return None if x is None else (x, y, 1, x * y % _P)


def _h(s: bytes) -> int:
    return int.from_bytes(hashlib.sha512(s).digest(), "little") % _Q


def _expandir(semilla: bytes):
    if len(semilla) != 32:
        raise ValueError("La clave privada debe tener 32 bytes.")
    h = hashlib.sha512(semilla).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def clave_publica(semilla: bytes) -> bytes:
    return _comprimir(_mul(_expandir(semilla)[0], _G))


def firmar(semilla: bytes, mensaje: bytes) -> bytes:
    a, prefijo = _expandir(semilla)
    A = _comprimir(_mul(a, _G))
    r = _h(prefijo + mensaje)
    Rs = _comprimir(_mul(r, _G))
    s = (r + _h(Rs + A + mensaje) * a) % _Q
    return Rs + int.to_bytes(s, 32, "little")


def verificar(publica: bytes, mensaje: bytes, firma: bytes) -> bool:
    if len(publica) != 32 or len(firma) != 64:
        return False
    A = _descomprimir(publica)
    Rs = firma[:32]
    R = _descomprimir(Rs)
    if A is None or R is None:
        return False
    s = int.from_bytes(firma[32:], "little")
    if s >= _Q:
        return False
    h = _h(Rs + publica + mensaje)
    return _iguales(_mul(s, _G), _suma(R, _mul(h, A)))


# ------------------------------------------------------------------ PEM
def semilla_desde_pem(pem: bytes) -> bytes:
    """Lee una clave privada Ed25519 en PEM (PKCS#8, sin contraseña)."""
    txt = pem.decode("ascii", "ignore")
    if "BEGIN PRIVATE KEY" not in txt:
        raise ValueError("El archivo no es una clave privada PEM (PKCS#8).")
    cuerpo = "".join(l for l in txt.splitlines() if l and not l.startswith("-----"))
    try:
        der = base64.b64decode(cuerpo)
    except Exception:  # noqa: BLE001
        raise ValueError("La clave privada está dañada.") from None
    if len(der) != 48 or not der.startswith(_PKCS8_PREFIX):
        raise ValueError("La clave privada no es de tipo Ed25519.")
    return der[16:]


def pem_desde_semilla(semilla: bytes) -> bytes:
    b64 = base64.b64encode(_PKCS8_PREFIX + semilla).decode()
    return ("-----BEGIN PRIVATE KEY-----\n" + b64 + "\n-----END PRIVATE KEY-----\n").encode("ascii")


def generar_par() -> tuple:
    """Devuelve (clave privada PEM, clave pública en hexadecimal)."""
    semilla = os.urandom(32)
    return pem_desde_semilla(semilla), clave_publica(semilla).hex()
