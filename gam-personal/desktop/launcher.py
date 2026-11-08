"""Lanzador de escritorio (Windows 10+): servidor local en 127.0.0.1 + ventana nativa.

* Datos en %APPDATA%\\GAMPersonal (SQLite, respaldos, clave de sesión). Nada sale de la PC.
* Ventana nativa con pywebview (WebView2 de Windows); si no está disponible, abre el navegador predeterminado.
* Una sola instancia: si ya está corriendo, abre su ventana en lugar de duplicar el servidor.
Parámetros:  --sin-ventana  (solo servidor, para pruebas)   --puerto N
"""
from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path


def base_dir() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


def data_dir() -> Path:
    raiz = os.environ.get("APPDATA") or str(Path.home() / ".local" / "share")
    d = Path(os.environ.get("GAM_DATA_DIR", Path(raiz) / "GAMPersonal"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def puerto_libre(pref: int | None) -> int:
    for p in ([pref] if pref else []) + [0]:
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return s.getsockname()[1]
            except OSError:
                continue
    raise RuntimeError("Sin puertos libres")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-ventana", action="store_true")
    ap.add_argument("--puerto", type=int, default=None)
    ap.add_argument("--respaldo", action="store_true", help="crea un respaldo cifrado (GAM_BACKUP_PASSWORD) y termina")
    a = ap.parse_args()

    dd = data_dir()
    os.environ["GAM_DATA_DIR"] = str(dd)
    base = base_dir()
    os.environ.setdefault("GAM_FRONTEND_DIR", str(base / "frontend"))
    if not getattr(sys, "frozen", False):
        sys.path.insert(0, str(base / "backend"))

    if a.respaldo:                           # tarea programada de Windows: respaldo cifrado + retención de 90 días
        from app.cli import main as cli
        cli(["backup", "--destino", str(dd / "backups")])
        cli(["retencion", "--dias", "90"])
        return

    lock = dd / "servidor.puerto"
    if lock.exists():                       # ¿ya hay una instancia?
        try:
            p = int(lock.read_text())
            urllib.request.urlopen(f"http://127.0.0.1:{p}/api/salud", timeout=2)
            print(f"Ya hay una instancia en el puerto {p}; abriendo.")
            if not a.sin_ventana:
                webbrowser.open(f"http://127.0.0.1:{p}/")
            return
        except Exception:
            lock.unlink(missing_ok=True)

    import uvicorn
    from app.main import app
    puerto = puerto_libre(a.puerto)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=puerto, log_level="warning"))
    hilo = threading.Thread(target=server.run, daemon=True)
    hilo.start()
    url = f"http://127.0.0.1:{puerto}/"
    for _ in range(100):
        try:
            urllib.request.urlopen(url + "api/salud", timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    else:
        sys.exit("El servidor local no inició")
    lock.write_text(str(puerto))
    print("Servidor local:", url, "| datos:", dd, flush=True)
    try:
        if a.sin_ventana:
            while hilo.is_alive():
                time.sleep(0.5)
        else:
            try:
                import webview
                webview.create_window("Gestión de Personal y Asistencia Municipal", url, width=1366, height=820, min_size=(1000, 650))
                webview.start()
            except Exception:
                webbrowser.open(url)
                print("Ventana nativa no disponible: se abrió el navegador. Cierre esta consola para detener el servidor.")
                while hilo.is_alive():
                    time.sleep(0.5)
    finally:
        server.should_exit = True
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
