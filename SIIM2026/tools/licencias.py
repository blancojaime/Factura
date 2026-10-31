#!/usr/bin/env python3
"""Herramienta EXTERNA del proveedor para emitir licencias de SIIM 2026. No se distribuye a los clientes.

  python licencias.py init                                   # crea el par de claves (una sola vez) y copia la clave PÚBLICA al proyecto
  python licencias.py emitir --codigo 21D9-8F59-6D4F-2152 --cliente "GAM Ejemplo" --dias 365
  python licencias.py emitir --codigo ... --cliente "GAM Ejemplo" --perpetua
  python licencias.py verificar licencia.siimlic
  python licencias.py registro                               # historial de licencias emitidas

La clave PRIVADA queda en ~/.siim_vendor/license_private.pem: protéjala y haga copia de seguridad. Quien la tenga puede emitir licencias.
"""
import argparse
import base64
import csv
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

HOME = Path(os.environ.get("SIIM_VENDOR_DIR", Path.home() / ".siim_vendor"))
PRIV = HOME / "license_private.pem"
PROJ_PUB = Path(__file__).resolve().parent.parent / "siim" / "resources" / "license_pub.pem"
PREFIX = "SIIM1"


def b64e(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def cmd_init(a):
    HOME.mkdir(parents=True, exist_ok=True)
    if PRIV.exists() and not a.forzar:
        sys.exit(f"Ya existe una clave privada en {PRIV}. Use --forzar sólo si entiende que las licencias anteriores dejarán de ser válidas.")
    k = Ed25519PrivateKey.generate()
    PRIV.write_bytes(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    try:
        os.chmod(PRIV, 0o600)
    except OSError:
        pass
    pub = k.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    (HOME / "license_public.pem").write_bytes(pub)
    PROJ_PUB.parent.mkdir(parents=True, exist_ok=True)
    PROJ_PUB.write_bytes(pub)
    print(f"Clave privada: {PRIV}\nClave pública copiada a: {PROJ_PUB}\nAhora compile el instalador: la app sólo aceptará licencias firmadas con ESTA clave.")


def _priv():
    if not PRIV.exists():
        sys.exit("No hay clave privada. Ejecute primero: licencias.py init")
    return serialization.load_pem_private_key(PRIV.read_bytes(), None)


def cmd_emitir(a):
    cod = a.codigo.strip().upper()
    if a.universal:
        cod = "*"
    elif not re.fullmatch(r"[0-9A-F]{4}(-[0-9A-F]{4}){3}", cod):
        sys.exit("Código de instalación inválido (formato XXXX-XXXX-XXXX-XXXX).")
    vence = None
    if a.dias:
        vence = (date.today() + timedelta(days=a.dias)).isoformat()
    elif a.vence:
        vence = date.fromisoformat(a.vence).isoformat()
    elif not a.perpetua:
        sys.exit("Indique --dias, --vence o --perpetua.")
    payload = json.dumps(dict(cliente=a.cliente, maquina=cod, vence=vence, emitida=date.today().isoformat(), producto="SIIM2026", plan=a.plan), sort_keys=True, ensure_ascii=False).encode()
    texto = f"{PREFIX}.{b64e(payload)}.{b64e(_priv().sign(payload))}"
    out = Path(a.salida or f"licencia_{re.sub(r'[^A-Za-z0-9]+', '_', a.cliente)}_{cod.replace('*', 'UNIVERSAL')}.siimlic")
    out.write_text(texto, encoding="utf-8")
    HOME.mkdir(parents=True, exist_ok=True)
    reg = HOME / "registro.csv"
    nuevo = not reg.exists()
    with open(reg, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["fecha_emision", "cliente", "codigo", "vence", "plan", "archivo"])
        w.writerow([date.today().isoformat(), a.cliente, cod, vence or "perpetua", a.plan, out.name])
    print(f"Licencia generada: {out}\nCliente: {a.cliente}\nEquipo: {cod}\nVence: {vence or 'perpetua'}")
    if a.universal:
        print("ATENCIÓN: licencia universal (sin atar a un equipo). Úsela sólo para contratos institucionales controlados.")


def cmd_verificar(a):
    pre, body, sig = Path(a.archivo).read_text(encoding="utf-8").strip().split(".")
    pub = _priv().public_key()
    pub.verify(b64d(sig), b64d(body))
    print("Firma válida:", json.dumps(json.loads(b64d(body)), ensure_ascii=False, indent=1))


def cmd_registro(a):
    reg = HOME / "registro.csv"
    print(reg.read_text(encoding="utf-8") if reg.exists() else "Sin licencias emitidas.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    i = s.add_parser("init"); i.add_argument("--forzar", action="store_true"); i.set_defaults(f=cmd_init)
    e = s.add_parser("emitir")
    e.add_argument("--codigo", default=""); e.add_argument("--cliente", required=True); e.add_argument("--dias", type=int); e.add_argument("--vence"); e.add_argument("--perpetua", action="store_true")
    e.add_argument("--universal", action="store_true"); e.add_argument("--plan", default="COMPLETO"); e.add_argument("--salida"); e.set_defaults(f=cmd_emitir)
    v = s.add_parser("verificar"); v.add_argument("archivo"); v.set_defaults(f=cmd_verificar)
    r = s.add_parser("registro"); r.set_defaults(f=cmd_registro)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
