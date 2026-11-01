"""API local de solo lectura (JSON) para los módulos de auditoría.

Se expone únicamente en 127.0.0.1 y exige un token (cabecera `Authorization: Bearer <token>`). No modifica datos contables.
Uso:  python -m contabol.api --empresa DEMO --anio 2025 --usuario admin   (la contraseña se pide por teclado)
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .sistema import ErrorNegocio

PREFIJO = "/api/v1"


def _enc(p) -> int:
    try:
        return int(p["encargo"][0])
    except (KeyError, ValueError, IndexError):
        raise ErrorNegocio("Parámetro obligatorio: encargo (id del encargo de auditoría).")


def _num(p, k, defecto, tipo=float):
    return tipo(p[k][0]) if k in p else defecto


# ruta -> (descripción, función(ctx, params))
RUTAS = {
    "/auditoria/encargos": ("Lista de encargos de auditoría", lambda c, p: c.auditoria.listar(p.get("tipo", [None])[0])),
    "/auditoria/materialidad": ("Materialidad global, de desempeño y umbral trivial", lambda c, p: c.auditoria.materialidad(_enc(p))),
    "/auditoria/resumen-desvios": ("Resumen de desvíos y ajustes frente a la materialidad", lambda c, p: {k: v for k, v in c.auditoria.resumen_desvios(_enc(p)).items() if k != "ajustes"}),
    "/auditoria/integridad": ("Verificación SHA-256 del encargo cerrado y de la bitácora", lambda c, p: c.auditoria.verificar_integridad(_enc(p))),
    "/inventarios/muestreo-recuento": ("Muestra para recuento físico", lambda c, p: c.aud_pruebas.muestreo_recuento(_enc(p), _num(p, "n", 10, int), _num(p, "semilla", 2025, int))),
    "/inventarios/corte-documental": ("Prueba de corte documental", lambda c, p: c.aud_pruebas.corte_documental(_enc(p), _num(p, "dias", 5, int))),
    "/inventarios/vnr-obsolescencia": ("Valor neto de realización y obsolescencia", lambda c, p: c.aud_pruebas.vnr_obsolescencia(_enc(p), _num(p, "costos_venta_pct", 0.0))),
    "/costos/conversion": ("MP, MOD y CIF por orden y cuota de aplicación", lambda c, p: c.aud_pruebas.costos_produccion(_enc(p))),
    "/activos/depreciacion-vs-ds24051": ("Depreciación registrada vs D.S. 24051", lambda c, p: c.aud_pruebas.depreciacion_vs_ds24051(_enc(p))),
    "/planillas/conciliacion": ("Planilla vs aportes, provisiones y RC-IVA", lambda c, p: c.aud_pruebas.conciliar_planilla(_enc(p))),
    "/tributario/conciliacion-iva-it": ("Débito/Crédito fiscal e IT vs libros", lambda c, p: c.aud_trib.conciliacion_iva_it(_enc(p))),
    "/tributario/bancarizacion": ("Operaciones sujetas a bancarización", lambda c, p: c.aud_trib.bancarizacion(_enc(p))),
    "/tributario/depuracion-iue": ("Cédula de depuración de gastos e IUE", lambda c, p: c.aud_trib.cedula_iue(_enc(p))),
    "/tributario/anexos-itc": ("Anexos de la Información Tributaria Complementaria", lambda c, p: c.aud_trib.anexos(_enc(p))),
    "/tributario/contingencia": ("Cálculo de contingencia (Ley 2492)", lambda c, p: c.aud_trib.contingencia(_num(p, "monto", 0.0), p["vencimiento"][0], p["calculo"][0], _num(p, "tasa", None), _num(p, "sancion", 0.0))),
}


def despachar(ctx, ruta: str, params: dict | None = None):
    """Núcleo sin red (probado en los tests): devuelve (código_http, objeto_json)."""
    params = params or {}
    if ruta == "/":
        return 200, {"api": "CONTA JB · auditoría", "version": "v1", "solo_lectura": True, "rutas": {k: v[0] for k, v in RUTAS.items()}}
    r = RUTAS.get(ruta)
    if not r:
        return 404, {"error": "Ruta no encontrada"}
    try:
        return 200, r[1](ctx, params)
    except ErrorNegocio as ex:
        return 400, {"error": str(ex)}
    except KeyError as ex:
        return 400, {"error": f"Falta el parámetro {ex}"}


def servir(ctx, token: str, puerto: int = 8765):
    if not token or len(token) < 8:
        raise ErrorNegocio("Defina un token de al menos 8 caracteres.")

    class H(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.headers.get("Authorization") != f"Bearer {token}":
                return self._enviar(401, {"error": "Token inválido"})
            u = urlparse(self.path)
            ruta = u.path[len(PREFIJO):] if u.path.startswith(PREFIJO) else u.path
            self._enviar(*despachar(ctx, ruta or "/", parse_qs(u.query)))

        def _enviar(self, cod, obj):
            b = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(cod)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def log_message(self, *a):  # silencioso
            pass
    srv = ThreadingHTTPServer(("127.0.0.1", puerto), H)
    return srv


if __name__ == "__main__":  # pragma: no cover
    import argparse
    import getpass
    import os
    import secrets

    from .sistema import Sistema
    ap = argparse.ArgumentParser(description="API local de auditoría (solo lectura)")
    ap.add_argument("--datos", default=os.path.join(os.path.expanduser("~"), "ContaJB", "datos"))
    ap.add_argument("--empresa", required=True)
    ap.add_argument("--anio", type=int, required=True)
    ap.add_argument("--usuario", default="admin")
    ap.add_argument("--puerto", type=int, default=8765)
    a = ap.parse_args()
    sis = Sistema(a.datos)
    u = sis.autenticar(a.usuario, getpass.getpass("Contraseña: "))
    emp = next(e for e in sis.empresas_de(u) if e["codigo"] == a.empresa)
    ges = next(g for g in sis.gestiones(emp["id"]) if g["anio"] == a.anio)
    ctx = sis.abrir_contexto(u, emp["id"], ges["id"])
    tok = secrets.token_urlsafe(16)
    print(f"API en http://127.0.0.1:{a.puerto}{PREFIJO}/   Token: {tok}")
    servir(ctx, tok, a.puerto).serve_forever()
