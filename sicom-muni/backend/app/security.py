"""Contrasenas (Argon2id) y tokens JWT (access 15 min en el cuerpo; refresh en cookie HTTP-only)."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from .config import get_settings

_ph = PasswordHasher()  # Argon2id con parametros por defecto de argon2-cffi
ALGORITMO = "HS256"


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_error(password: str) -> str | None:
    """Politica: >= 10 caracteres con mayuscula, minuscula y digito."""
    if len(password) < 10:
        return "La contraseña debe tener al menos 10 caracteres"
    if not (any(c.isupper() for c in password) and any(c.islower() for c in password)
            and any(c.isdigit() for c in password)):
        return "La contraseña debe combinar mayúsculas, minúsculas y números"
    return None


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def crear_access_token(usuario_id: uuid.UUID, rol: str) -> str:
    s = get_settings()
    ahora = _ahora()
    payload = {"sub": str(usuario_id), "rol": rol, "type": "access", "iat": ahora,
               "exp": ahora + timedelta(minutes=s.access_token_minutes)}
    return jwt.encode(payload, s.secret_key, algorithm=ALGORITMO)


def crear_refresh_token(usuario_id: uuid.UUID) -> tuple[str, uuid.UUID, str, datetime]:
    """Devuelve (token, jti, hash_sha256_del_token, expira)."""
    s = get_settings()
    ahora = _ahora()
    jti = uuid.uuid4()
    expira = ahora + timedelta(days=s.refresh_token_days)
    token = jwt.encode({"sub": str(usuario_id), "jti": str(jti), "type": "refresh", "iat": ahora, "exp": expira,
                        "nonce": secrets.token_hex(8)}, s.secret_key, algorithm=ALGORITMO)
    return token, jti, hashlib.sha256(token.encode()).hexdigest(), expira


def decodificar(token: str, tipo: str) -> dict:
    """Lanza jwt.PyJWTError si el token es invalido, expiro o es de otro tipo."""
    datos = jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITMO])
    if datos.get("type") != tipo:
        raise jwt.InvalidTokenError("Tipo de token incorrecto")
    return datos


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
