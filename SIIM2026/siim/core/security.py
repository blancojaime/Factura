"""Usuarios, contraseñas (PBKDF2-SHA256), roles/permisos, bloqueo por intentos y bitácora encadenada."""
import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta

ITER = 600_000
MAX_INTENTOS = 5
BLOQUEO_MIN = 15

ROLES = {
    "ADMINISTRADOR": {"*"},
    "SUPERVISOR": {"padron.ver", "padron.editar", "padron.baja", "liq.ejecutar", "liq.masiva", "rec.cobrar", "rec.anular",
                   "otros.fuc", "otros.anular", "mant.ver", "mant.editar", "reportes", "fiscal", "plan.crear", "util.backup"},
    "EMPADRONADOR": {"padron.ver", "padron.editar", "reportes"},
    "LIQUIDADOR": {"padron.ver", "liq.ejecutar", "reportes", "plan.crear"},
    "CAJERO": {"padron.ver", "rec.cobrar", "otros.fuc", "reportes"},
    "CONSULTA": {"padron.ver", "reportes"},
}


def hash_password(pw: str, salt: bytes = None) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, ITER)
    return f"pbkdf2${ITER}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, it, salt, dk = stored.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", pw.encode(), base64.b64decode(salt), int(it))
        return hmac.compare_digest(calc, base64.b64decode(dk))
    except Exception:
        return False


def password_policy(pw: str):
    """Devuelve lista de problemas (vacía = válida)."""
    p = []
    if len(pw) < 8:
        p.append("mínimo 8 caracteres")
    if not any(c.isdigit() for c in pw):
        p.append("al menos un número")
    if not any(c.isalpha() for c in pw):
        p.append("al menos una letra")
    return p


class AuthError(Exception):
    pass


class Session:
    def __init__(self, user_row):
        self.id = user_row["id"]
        self.usuario = user_row["usuario"]
        self.nombre = user_row["nombre"]
        self.rol = user_row["rol"]

    def can(self, perm: str) -> bool:
        perms = ROLES.get(self.rol, set())
        return "*" in perms or perm in perms


def has_users(db) -> bool:
    return db.scalar("SELECT COUNT(*) FROM usuarios", default=0) > 0


def create_user(db, usuario, nombre, rol, password, cambiar_clave=False):
    if rol not in ROLES:
        raise ValueError("Rol inválido")
    prob = password_policy(password)
    if prob:
        raise ValueError("Contraseña débil: " + ", ".join(prob))
    return db.insert("usuarios", dict(usuario=usuario.strip().lower(), nombre=nombre, rol=rol, hash=hash_password(password),
                                      cambiar_clave=int(cambiar_clave), creado=datetime.now().isoformat(timespec="seconds")))


def login(db, usuario, password) -> Session:
    u = db.one("SELECT * FROM usuarios WHERE usuario=?", (usuario.strip().lower(),))
    msg = "Usuario o contraseña incorrectos"
    if not u or not u["activo"]:
        audit(db, usuario, "LOGIN_FALLIDO", detalle="usuario inexistente o inactivo")
        raise AuthError(msg)
    if u["bloqueado_hasta"] and datetime.fromisoformat(u["bloqueado_hasta"]) > datetime.now():
        raise AuthError("Cuenta bloqueada temporalmente por intentos fallidos. Intente más tarde.")
    if not verify_password(password, u["hash"]):
        n = u["intentos"] + 1
        bl = (datetime.now() + timedelta(minutes=BLOQUEO_MIN)).isoformat(timespec="seconds") if n >= MAX_INTENTOS else None
        db.update("usuarios", dict(intentos=0 if bl else n, bloqueado_hasta=bl), "id=?", (u["id"],))
        audit(db, u["usuario"], "LOGIN_FALLIDO", detalle=f"intento {n}")
        raise AuthError(msg)
    db.update("usuarios", dict(intentos=0, bloqueado_hasta=None, ultimo_acceso=datetime.now().isoformat(timespec="seconds")), "id=?", (u["id"],))
    audit(db, u["usuario"], "LOGIN")
    return Session(u)


def change_password(db, usuario, nueva):
    prob = password_policy(nueva)
    if prob:
        raise ValueError("Contraseña débil: " + ", ".join(prob))
    db.update("usuarios", dict(hash=hash_password(nueva), cambiar_clave=0, intentos=0, bloqueado_hasta=None), "usuario=?", (usuario,))
    audit(db, usuario, "CAMBIO_CLAVE")


# ---------------- Bitácora con cadena de hashes (evidencia de manipulación) ----------------
def audit(db, usuario, accion, tabla=None, registro=None, detalle=None):
    with db.tx():
        last = db.one("SELECT hash FROM bitacora ORDER BY id DESC LIMIT 1")
        prev = last[0] if last and last[0] else "GENESIS"
        fecha = datetime.now().isoformat(timespec="seconds")
        if isinstance(detalle, (dict, list)):
            detalle = json.dumps(detalle, ensure_ascii=False, default=str)
        h = _h(prev, fecha, usuario, accion, tabla, registro, detalle)
        db.insert("bitacora", dict(fecha=fecha, usuario=usuario, accion=accion, tabla=tabla, registro=None if registro is None else str(registro),
                                   detalle=detalle, prev_hash=prev, hash=h))


def _h(*parts):
    return hashlib.sha256("|".join("" if p is None else str(p) for p in parts).encode()).hexdigest()


def verify_audit_chain(db):
    """(ok, id_primer_error). Detecta modificación o borrado de registros de bitácora."""
    prev = "GENESIS"
    for r in db.all("SELECT * FROM bitacora ORDER BY id"):
        if r["prev_hash"] != prev or r["hash"] != _h(prev, r["fecha"], r["usuario"], r["accion"], r["tabla"], r["registro"], r["detalle"]):
            return False, r["id"]
        prev = r["hash"]
    return True, None


def new_temp_password():
    return secrets.token_urlsafe(9) + "7"
