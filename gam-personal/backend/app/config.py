"""Configuración por variables de entorno (misma base de código para web y escritorio)."""
import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("GAM_DATA_DIR", Path.cwd() / "data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

# SQLite por defecto (escritorio / instalación simple). PostgreSQL: postgresql+psycopg://user:pass@host/db
DATABASE_URL = os.environ.get("GAM_DATABASE_URL", f"sqlite:///{(DATA_DIR / 'gam_personal.db').as_posix()}")
BACKUP_DIR = Path(os.environ.get("GAM_BACKUP_DIR", DATA_DIR / "backups")).resolve()
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _secret() -> str:
    env = os.environ.get("GAM_SECRET_KEY")
    if env:
        return env
    f = DATA_DIR / ".secret_key"          # se genera una vez por instalación
    if not f.exists():
        f.write_text(secrets.token_urlsafe(48))
        try:
            f.chmod(0o600)
        except OSError:
            pass
    return f.read_text().strip()


SECRET_KEY = _secret()
TOKEN_HORAS = int(os.environ.get("GAM_TOKEN_HORAS", "10"))
FRONTEND_DIR = Path(os.environ.get("GAM_FRONTEND_DIR", BASE_DIR.parent.parent / "frontend"))
TEMPLATE_INFORME = BASE_DIR / "templates" / "informe_asistencia.docx"
