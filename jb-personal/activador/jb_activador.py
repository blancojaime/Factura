#!/usr/bin/env python3
"""JB-Activador — herramienta EXTERNA del emisor para generar códigos de activación de JB-Personal.

NO se instala en las entidades. Guarda la clave PRIVADA (Ed25519) en  %APPDATA%\\JB-Activador\\clave_privada.pem
(o ~/.jb-activador). Quien tenga ese archivo puede emitir licencias: respáldelo y protéjalo.

Interfaz web local:   python jb_activador.py                 (abre el navegador en 127.0.0.1)
Línea de comandos:    python jb_activador.py --emitir --entidad "GAM Villa Ejemplo" --equipo JBP-AAAAA-BBBBB-CCCCC [--vence 2027-12-31 | --dias 365]
                      python jb_activador.py --equipo '*' ...      (licencia válida en cualquier equipo; úsela con cuidado)
                      python jb_activador.py --publica             (clave pública para embeber en la aplicación)
                      python jb_activador.py --nueva-clave         (¡invalida las licencias emitidas con la clave anterior!)
Opción global:        --datos CARPETA   (carpeta de la clave y del historial; por defecto la indicada arriba)
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import html
import json
import os
import re
import secrets
import shutil
import sys
import threading
import webbrowser
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from cryptography.hazmat.primitives import serialization as S
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

PRODUCTO = "JB-Personal"
PREFIJO = "JBP1"
EQUIPO_RE = re.compile(r"^JBP-[0-9A-F]{5}-[0-9A-F]{5}-[0-9A-F]{5}$")


def carpeta_datos(arg: str | None = None) -> Path:
    if arg:
        d = Path(arg)
    elif os.environ.get("APPDATA"):
        d = Path(os.environ["APPDATA"]) / "JB-Activador"
    else:
        d = Path.home() / ".jb-activador"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cargar_clave(datos: Path, crear: bool = True) -> tuple[Ed25519PrivateKey, bool]:
    """Devuelve (clave, es_nueva). Busca la clave en la carpeta de datos o junto al programa (se copia a datos)."""
    f = datos / "clave_privada.pem"
    junto = Path(__file__).resolve().parent / "clave_privada.pem"
    if not f.exists() and junto.exists():
        shutil.copy(junto, f)
    nueva = False
    if not f.exists():
        if not crear:
            raise SystemExit("No hay clave privada. Use --nueva-clave o copie clave_privada.pem a " + str(datos))
        f.write_bytes(Ed25519PrivateKey.generate().private_bytes(S.Encoding.PEM, S.PrivateFormat.PKCS8, S.NoEncryption()))
        nueva = True
    try:
        f.chmod(0o600)
    except OSError:
        pass
    return S.load_pem_private_key(f.read_bytes(), None), nueva


def publica_b64(k: Ed25519PrivateKey) -> str:
    return base64.b64encode(k.public_key().public_bytes(S.Encoding.Raw, S.PublicFormat.Raw)).decode()


def _b64(x: bytes) -> str:
    return base64.urlsafe_b64encode(x).rstrip(b"=").decode()


def emitir(k: Ed25519PrivateKey, entidad: str, equipo: str, vence: str | None, datos: Path | None = None) -> str:
    entidad = " ".join(entidad.split())
    if not entidad:
        raise ValueError("Indique el nombre de la entidad")
    equipo = equipo.strip().upper()
    if equipo != "*" and not EQUIPO_RE.match(equipo):
        raise ValueError("El código de equipo debe tener el formato JBP-XXXXX-XXXXX-XXXXX (cópielo desde la pantalla Licencia de JB-Personal)")
    if vence:
        if date.fromisoformat(vence) < date.today():
            raise ValueError("La fecha de vencimiento ya pasó")
    carga = {"p": PRODUCTO, "e": entidad, "m": equipo, "i": date.today().isoformat(), "v": vence or None}
    raw = json.dumps(carga, separators=(",", ":"), ensure_ascii=False).encode()
    codigo = f"{PREFIJO}.{_b64(raw)}.{_b64(k.sign(raw))}"
    if datos:
        nuevo = not (datos / "emitidas.csv").exists()
        with open(datos / "emitidas.csv", "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if nuevo:
                w.writerow(["emitida", "entidad", "equipo", "vence", "huella_codigo"])
            w.writerow([datetime.now().isoformat(timespec="seconds"), entidad, equipo, vence or "perpetua",
                        hashlib.sha256(codigo.encode()).hexdigest()[:12]])
    return codigo


def historial(datos: Path) -> list[list[str]]:
    f = datos / "emitidas.csv"
    if not f.exists():
        return []
    with open(f, encoding="utf-8") as fh:
        return list(csv.reader(fh))[1:][::-1][:50]


# ------------------------------------------------------------------------------------------ interfaz web local
CSS = """body{font:15px system-ui,Segoe UI,Arial;background:#FBF5EC;color:#3A2A1E;margin:0}header{background:#7A3210;color:#fff;padding:14px 26px;font-size:18px}
main{max-width:860px;margin:20px auto;padding:0 16px}.card{background:#FFFDF9;border:1px solid #E3D3BF;border-radius:10px;padding:16px;margin-bottom:16px}
label{display:block;margin:10px 0 4px;font-size:13px;color:#6b5848}input,select,textarea{width:100%;padding:8px;border:1px solid #D2BBA0;border-radius:6px;font:inherit;box-sizing:border-box}
button{background:#8A3B12;color:#fff;border:0;border-radius:6px;padding:9px 16px;font:inherit;cursor:pointer;margin-top:12px}button.s{background:#fff;color:#8A3B12;border:1px solid #8A3B12}
textarea{font-family:Consolas,monospace;font-size:12px;height:120px}table{border-collapse:collapse;width:100%;font-size:13px}td,th{border-bottom:1px solid #F0E3D2;padding:5px 8px;text-align:left}th{background:#8A3B12;color:#fff}
.ok{background:#E3F4E6;border:1px solid #9CCFA5;padding:10px;border-radius:8px}.mal{background:#FBDCD8;border:1px solid #E0948C;padding:10px;border-radius:8px}.row{display:flex;gap:12px}.row>div{flex:1}"""


def pagina(token: str, datos: Path, msg: str = "", codigo: str = "", entidad: str = "", equipo: str = "", error: str = "") -> bytes:
    e = html.escape
    filas = "".join("<tr>" + "".join(f"<td>{e(c)}</td>" for c in r) + "</tr>" for r in historial(datos)) or "<tr><td colspan=5>Aún no hay licencias emitidas</td></tr>"
    bloque = ""
    if error:
        bloque = f'<div class="mal">{e(error)}</div>'
    elif codigo:
        bloque = (f'<div class="ok"><b>Código de activación emitido</b> para {e(entidad)} · equipo {e(equipo)}.<br>Envíelo a la entidad; se pega en '
                  f'JB-Personal → Licencia (o se guarda como <code>licencia.jbp</code> en la carpeta de datos).</div>'
                  f'<label>Código</label><textarea readonly onclick="this.select()">{e(codigo)}</textarea>'
                  f'<a href="/licencia.jbp?k={token}&c={e(codigo)}"><button class="s" type="button">Descargar licencia.jbp</button></a>')
    html_ = f"""<!doctype html><html lang="es"><meta charset="utf-8"><title>JB-Activador</title><style>{CSS}</style>
<header>JB-Activador · emisión de licencias de JB-Personal</header><main>
<div class="card"><form method="post" action="/emitir?k={token}">
<div class="row"><div><label>Entidad (se muestra en la licencia)</label><input name="entidad" value="{e(entidad)}" required maxlength="150"></div>
<div><label>Código de equipo (pantalla Licencia del cliente)</label><input name="equipo" value="{e(equipo)}" placeholder="JBP-XXXXX-XXXXX-XXXXX" required></div></div>
<div class="row"><div><label>Vigencia</label><select name="vig"><option value="perpetua">Sin vencimiento (perpetua)</option><option value="dias">Por cantidad de días</option><option value="fecha">Hasta una fecha</option></select></div>
<div><label>Días (si aplica)</label><input name="dias" type="number" min="1" max="3650" value="365"></div>
<div><label>Fecha (si aplica)</label><input name="fecha" type="date"></div></div>
<button>Emitir código de activación</button></form>{bloque}</div>
<div class="card"><b>Licencias emitidas (últimas 50)</b><table><tr><th>Emitida</th><th>Entidad</th><th>Equipo</th><th>Vence</th><th>Huella</th></tr>{filas}</table></div>
<div class="card"><b>Clave pública</b> (la que lleva incorporada la aplicación): <code>{e(msg)}</code><br>
<form method="post" action="/cerrar?k={token}"><button class="s">Cerrar el activador</button></form></div></main></html>"""
    return html_.encode("utf-8")


def servir(datos: Path, abrir: bool = True, puerto: int = 0):
    k, nueva = cargar_clave(datos)
    token = secrets.token_urlsafe(16)
    pub = publica_b64(k)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _ok(self, cuerpo: bytes, ctype="text/html; charset=utf-8", extra=None):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Frame-Options", "DENY")
            for a, b in (extra or {}).items():
                self.send_header(a, b)
            self.end_headers()
            self.wfile.write(cuerpo)

        def _auth(self):
            q = parse_qs(urlparse(self.path).query)
            if q.get("k", [""])[0] != token or self.headers.get("Host", "").split(":")[0] not in ("127.0.0.1", "localhost"):
                self.send_error(403, "Acceso denegado")
                return None
            return q

        def do_GET(self):
            q = self._auth()
            if q is None:
                return
            ruta = urlparse(self.path).path
            if ruta == "/licencia.jbp":
                self._ok(q.get("c", [""])[0].encode(), "application/octet-stream", {"Content-Disposition": 'attachment; filename="licencia.jbp"'})
            else:
                self._ok(pagina(token, datos, pub))

        def do_POST(self):
            if self._auth() is None:
                return
            ruta = urlparse(self.path).path
            if ruta == "/cerrar":
                self._ok(b"<meta charset=utf-8><p>JB-Activador cerrado. Puede cerrar esta pestana.</p>")
                threading.Thread(target=srv.shutdown, daemon=True).start()
                return
            n = int(self.headers.get("Content-Length", 0))
            f = {a: b[0] for a, b in parse_qs(self.rfile.read(min(n, 10000)).decode("utf-8")).items()}
            try:
                vence = None
                if f.get("vig") == "dias":
                    vence = (date.today() + timedelta(days=int(f.get("dias", "365")))).isoformat()
                elif f.get("vig") == "fecha":
                    vence = f.get("fecha") or None
                    if not vence:
                        raise ValueError("Indique la fecha de vencimiento")
                cod = emitir(k, f.get("entidad", ""), f.get("equipo", ""), vence, datos)
                self._ok(pagina(token, datos, pub, cod, f["entidad"], f["equipo"].upper()))
            except (ValueError, KeyError) as ex:
                self._ok(pagina(token, datos, pub, error=str(ex), entidad=f.get("entidad", ""), equipo=f.get("equipo", "")))

    srv = ThreadingHTTPServer(("127.0.0.1", puerto), H)
    url = f"http://127.0.0.1:{srv.server_port}/?k={token}"
    print("JB-Activador en", url)
    if nueva:
        print("AVISO: se generó una clave nueva. La clave pública debe incorporarse a la aplicación:", pub)
    if abrir:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    finally:
        srv.server_close()


def main(argv=None):
    if sys.stdout is None:                       # pythonw.exe (sin consola)
        sys.stdout = sys.stderr = open(os.devnull, "w")
    ap = argparse.ArgumentParser(description="Emisor de licencias de JB-Personal")
    ap.add_argument("--datos")
    ap.add_argument("--emitir", action="store_true")
    ap.add_argument("--entidad", default="")
    ap.add_argument("--equipo", default="")
    ap.add_argument("--vence")
    ap.add_argument("--dias", type=int)
    ap.add_argument("--publica", action="store_true")
    ap.add_argument("--nueva-clave", action="store_true")
    ap.add_argument("--sin-navegador", action="store_true")
    a = ap.parse_args(argv)
    datos = carpeta_datos(a.datos)
    if a.nueva_clave:
        f = datos / "clave_privada.pem"
        if f.exists():
            f.rename(datos / f"clave_privada.{datetime.now():%Y%m%d%H%M%S}.bak")
        k, _ = cargar_clave(datos)
        print("Clave nueva creada. Clave pública:", publica_b64(k))
        return
    if a.publica:
        print(publica_b64(cargar_clave(datos, False)[0]))
        return
    if a.emitir:
        vence = a.vence or ((date.today() + timedelta(days=a.dias)).isoformat() if a.dias else None)
        try:
            print(emitir(cargar_clave(datos)[0], a.entidad, a.equipo, vence, datos))
        except ValueError as e:
            sys.exit(f"ERROR: {e}")
        return
    servir(datos, not a.sin_navegador)


if __name__ == "__main__":
    main()
