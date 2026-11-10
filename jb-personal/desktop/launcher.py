"""Lanzador de JB-Personal (Windows 10+).

Modos
  --servicio   Servidor en segundo plano SIN ventana ni sesión de usuario (lo ejecuta la tarea programada «JB-Personal»
               al arrancar el equipo, como SYSTEM). Escribe un registro en <datos>\\logs\\servicio.log.
  (sin flags)  «Abrir»: si el servicio responde abre el navegador; si no, levanta un servidor temporal en esta sesión.
  --respaldo   Crea un respaldo cifrado (GAM_BACKUP_PASSWORD) y termina.
  --sin-ventana / --puerto N   (pruebas)
Configuración: <datos>\\config.ini  ->  [servidor] host=127.0.0.1  port=8765   (host=0.0.0.0 permite acceso desde la red local)
Datos: %PROGRAMDATA%\\JB-Personal (Windows) — compartidos por el servicio y por cualquier usuario de la PC.
"""
from __future__ import annotations

import argparse
import configparser
import logging
import logging.handlers
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

PUERTO_DEFECTO = 8765


def base_dir() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


def data_dir() -> Path:
    if os.environ.get("GAM_DATA_DIR"):
        d = Path(os.environ["GAM_DATA_DIR"])
    elif os.name == "nt":
        d = Path(os.environ.get("PROGRAMDATA") or r"C:\ProgramData") / "JB-Personal"
    else:
        d = Path.home() / ".local" / "share" / "JB-Personal"
    d.mkdir(parents=True, exist_ok=True)
    return d


def leer_config(dd: Path) -> tuple[str, int]:
    """host/puerto de config.ini. Tolera BOM (PowerShell 5.1 lo escribe con -Encoding UTF8) y archivos dañados."""
    f = dd / "config.ini"
    if not f.exists():
        f.write_text(f"[servidor]\nhost = 127.0.0.1\nport = {PUERTO_DEFECTO}\n", encoding="ascii")
    cfg = configparser.ConfigParser()
    try:
        cfg.read_string(f.read_text(encoding="utf-8-sig", errors="replace"))
        return cfg.get("servidor", "host", fallback="127.0.0.1"), cfg.getint("servidor", "port", fallback=PUERTO_DEFECTO)
    except (configparser.Error, ValueError):
        registrar_fallo(dd, "config.ini ilegible; se usan los valores por defecto (127.0.0.1:%d)" % PUERTO_DEFECTO)
        return "127.0.0.1", PUERTO_DEFECTO


def registrar_fallo(dd: Path, texto: str):
    """Deja constancia en <datos>\\logs\\fallos.log aunque el logging aún no esté configurado (pythonw no tiene consola)."""
    try:
        (dd / "logs").mkdir(exist_ok=True)
        with open(dd / "logs" / "fallos.log", "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {texto}\n")
    except OSError:
        pass


def responde(puerto: int, host: str = "127.0.0.1") -> bool:
    try:
        urllib.request.urlopen(f"http://{host}:{puerto}/api/salud", timeout=2)
        return True
    except Exception:
        return False


def puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def preparar_log(dd: Path) -> logging.Logger:
    (dd / "logs").mkdir(exist_ok=True)
    h = logging.handlers.RotatingFileHandler(dd / "logs" / "servicio.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    raiz = logging.getLogger()
    raiz.setLevel(logging.INFO)
    raiz.addHandler(h)
    if sys.stdout is None or sys.stderr is None:             # pythonw.exe no tiene consola
        sys.stdout = sys.stderr = open(dd / "logs" / "salida.log", "a", encoding="utf-8", buffering=1)
    return logging.getLogger("jb-personal")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--servicio", action="store_true")
    ap.add_argument("--sin-ventana", action="store_true")
    ap.add_argument("--puerto", type=int, default=None)
    ap.add_argument("--respaldo", action="store_true", help="respaldo cifrado (GAM_BACKUP_PASSWORD) y termina")
    a = ap.parse_args(argv)

    dd = data_dir()
    os.environ["GAM_DATA_DIR"] = str(dd)
    base = base_dir()
    os.environ.setdefault("GAM_FRONTEND_DIR", str(base / "frontend"))
    if not getattr(sys, "frozen", False):
        sys.path.insert(0, str(base / "backend"))
    host, puerto = leer_config(dd)
    if a.puerto:
        puerto = a.puerto

    if a.respaldo:
        from app.cli import main as cli
        cli(["backup", "--destino", str(dd / "backups")])
        cli(["retencion", "--dias", "90"])
        return

    visible = "127.0.0.1" if host in ("0.0.0.0", "") else host
    if a.servicio:
        log = preparar_log(dd)
        log.info("Iniciando JB-Personal en %s:%s (datos: %s)", host, puerto, dd)
        import uvicorn
        from app.main import app
        try:
            uvicorn.Server(uvicorn.Config(app, host=host, port=puerto, log_config=None, log_level="info")).run()
        except Exception:
            log.exception("El servicio terminó con error")
            raise SystemExit(1)
        return

    # Modo «abrir»
    if responde(puerto, visible) and not a.sin_ventana:
        print(f"JB-Personal ya está en ejecución (servicio). Abriendo http://{visible}:{puerto}/")
        webbrowser.open(f"http://{visible}:{puerto}/")
        return

    import uvicorn
    from app.main import app
    puerto_tmp = a.puerto or (puerto if not responde(puerto, visible) else puerto_libre())
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=puerto_tmp, log_level="warning"))
    hilo = threading.Thread(target=server.run, daemon=True)
    hilo.start()
    url = f"http://127.0.0.1:{puerto_tmp}/"
    for _ in range(100):
        if responde(puerto_tmp):
            break
        time.sleep(0.2)
    else:
        sys.exit("El servidor local no inició")
    print("Servidor temporal:", url, "| datos:", dd, "\n(Este modo depende de esta ventana; para uso permanente instale el servicio.)", flush=True)
    try:
        if a.sin_ventana:
            while hilo.is_alive():
                time.sleep(0.5)
        else:
            try:
                import webview
                webview.create_window("JB-Personal", url, width=1366, height=820, min_size=(1000, 650))
                webview.start()
            except Exception:
                webbrowser.open(url)
                while hilo.is_alive():
                    time.sleep(0.5)
    finally:
        server.should_exit = True


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        import traceback
        registrar_fallo(data_dir(), "ERROR FATAL al iniciar:\n" + traceback.format_exc())
        raise
