"""Genera db/seeds.sql a partir de app/seeds.py (misma fuente que las pruebas).

Uso:  python scripts/make_seeds.py [--gestion 2026] > ../db/seeds.sql
"""
import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import security, seeds  # noqa: E402
from app.services import parametros  # noqa: E402


def q(v: str) -> str:
    return "'" + str(v).replace("'", "''") + "'"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gestion", type=int, default=date.today().year)
    a = ap.parse_args()
    h = security.hash_password(seeds.PASSWORD_DEMO)
    out = [
        "-- SICOM-MUNI: datos de prueba (FICTICIOS). Generado por scripts/make_seeds.py",
        f"-- Contraseña de TODOS los usuarios de prueba: {seeds.PASSWORD_DEMO}   (cámbiela de inmediato)",
        "-- Es idempotente: puede ejecutarse varias veces.", "BEGIN;", "",
        "-- Usuarios (Argon2id)"]
    for username, nombre, cargo, rol, email in seeds.USUARIOS:
        out.append("INSERT INTO usuarios (id, username, password_hash, nombre_completo, cargo, rol, email, activo, "
                   "intentos_fallidos) VALUES (" + ", ".join([
                       q(seeds._id(f"usuario:{username}")), q(username), q(h), q(nombre), q(cargo), q(rol.value),
                       q(email), "true", "0"]) + ") ON CONFLICT (username) DO NOTHING;")
    out += ["", "-- Parámetros institucionales"]
    for clave, (valor, desc) in parametros.DEFAULTS.items():
        v = str(a.gestion) if clave == "gestion" else valor
        out.append(f"INSERT INTO parametros_institucionales (clave, valor, descripcion) VALUES ({q(clave)}, {q(v)}, "
                   f"{q(desc)}) ON CONFLICT (clave) DO NOTHING;")
    out += ["", "-- Presupuesto inicial (partidas ilustrativas del clasificador 1xxxx a 4xxxx)"]
    e = seeds.ESTRUCTURA
    for codigo, desc, saldo in seeds.PARTIDAS:
        out.append("INSERT INTO partidas_presupuestarias (id, codigo_partida, descripcion, saldo_disponible, monto_aprobado, "
                   "gestion, programa, proyecto, actividad, fuente, organismo) VALUES (" + ", ".join([
                       q(seeds._id(f"partida:{codigo}:{a.gestion}")), q(codigo), q(desc), str(saldo), str(saldo),
                       str(a.gestion), q(e["programa"]), q(e["proyecto"]), q(e["actividad"]), q(e["fuente"]),
                       q(e["organismo"])]) + ") ON CONFLICT ON CONSTRAINT uq_partida_estructura DO NOTHING;")
    out += ["", "-- Catálogo Compro Hecho en Bolivia (EJEMPLO)"]
    for codigo, desc, unidad, precio in seeds.CATALOGO:
        out.append("INSERT INTO catalogo_chb (id, codigo_unspsc, descripcion_bien, unidad_medida, "
                   "precio_referencial_nacional, activo) VALUES (" + ", ".join([
                       q(seeds._id(f"chb:{codigo}")), q(codigo), q(desc), q(unidad), str(precio), "true"]) +
                   ") ON CONFLICT (codigo_unspsc) DO NOTHING;")
    out += ["", "COMMIT;", ""]
    sys.stdout.write("\n".join(out))


if __name__ == "__main__":
    main()
