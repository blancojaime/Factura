"""Rutas de datos de la aplicación (portables y seguras)."""
import os
import sys
from pathlib import Path


def resource_dir() -> Path:
    """Carpeta de recursos empaquetados (funciona en PyInstaller)."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / "siim"
    return Path(__file__).resolve().parent.parent


def _writable(p: Path) -> bool:
    try:
        p.mkdir(parents=True, exist_ok=True)
        t = p / ".w"
        t.write_text("x")
        t.unlink()
        return True
    except OSError:
        return False


def data_dir() -> Path:
    """Directorio de datos: SIIM_HOME > ProgramData > LocalAppData > ~/.siim2026"""
    env = os.environ.get("SIIM_HOME")
    if env:
        p = Path(env)
        p.mkdir(parents=True, exist_ok=True)
        return p
    cands = []
    if os.name == "nt":
        for var in ("PROGRAMDATA", "LOCALAPPDATA", "APPDATA"):
            if os.environ.get(var):
                cands.append(Path(os.environ[var]) / "SIIM2026")
    cands.append(Path.home() / ".siim2026")
    for c in cands:
        if _writable(c):
            return c
    raise RuntimeError("No se encontró una carpeta con permisos de escritura para los datos.")


def db_path() -> Path:
    return data_dir() / "siim2026.db"


def backup_dir() -> Path:
    p = data_dir() / "backups"
    p.mkdir(parents=True, exist_ok=True)
    return p


def reports_dir() -> Path:
    p = data_dir() / "reportes"
    p.mkdir(parents=True, exist_ok=True)
    return p
