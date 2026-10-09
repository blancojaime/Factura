"""Cifrado de montos ofertados (propuestas selladas) con Fernet (AES-128-CBC + HMAC).

El monto queda cifrado en la base hasta la apertura de ofertas; el Responsable de Contrataciones
"desencripta" las propuestas con `abrir_ofertas` cuando vence el plazo de presentacion.
"""
from decimal import Decimal

from cryptography.fernet import Fernet

from ..config import get_settings


def _f() -> Fernet:
    return Fernet(get_settings().fernet_key_effective)


def cifrar_monto(monto: Decimal) -> bytes:
    return _f().encrypt(str(Decimal(monto).quantize(Decimal("0.01"))).encode())


def descifrar_monto(token: bytes) -> Decimal:
    return Decimal(_f().decrypt(token).decode())
