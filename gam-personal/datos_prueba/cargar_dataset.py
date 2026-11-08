#!/usr/bin/env python3
"""Carga el dataset de prueba en un servidor en marcha (web o escritorio) y descarga los 6 reportes.

Uso:
  python cargar_dataset.py --url http://127.0.0.1:8000 --usuario admin --clave 'Su#Clave2026' --salida ./reportes_prueba
Requiere:  pip install httpx
"""
import argparse
import csv
from pathlib import Path

import httpx

AQUI = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--usuario", default="admin")
    ap.add_argument("--clave", required=True)
    ap.add_argument("--salida", default=str(AQUI / "reportes_prueba"))
    ap.add_argument("--formato", choices=["csv", "dat", "xlsx"], default="csv", help="formato del biométrico a importar")
    a = ap.parse_args()
    c = httpx.Client(base_url=a.url, timeout=120)
    r = c.post("/api/auth/login", json={"username": a.usuario, "password": a.clave})
    if r.status_code == 401 and not c.get("/api/auth/estado").json()["inicializado"]:
        r = c.post("/api/auth/setup", json={"username": a.usuario, "password": a.clave, "nombre": "Administrador"})
    r.raise_for_status()
    c.headers["Authorization"] = "Bearer " + r.json()["token"]

    ent = c.get("/api/entidad").json()
    ent.update(nombre="Gobierno Autónomo Municipal de Villa Ejemplo", sigla="VE", ciudad="Villa Ejemplo",
               codigo_sigep="01-913-00099", mae_nombre="Ana Ejemplo Lima", rrhh_nombre="Pedro Prueba Rojas",
               aprobador_nombre="Rosa Modelo Vega", reglamento_rip="Decreto Edil N° 012/2024")
    c.put("/api/entidad", json=ent).raise_for_status()

    def subir(url, nombre):
        with open(AQUI / nombre, "rb") as f:
            x = c.post(url, files={"archivo": (nombre, f)})
        print(url, x.status_code, x.text[:200])
        return x

    subir("/api/personal/importar", "personal.csv")
    ids = {e["codigo"]: e["id"] for e in c.get("/api/empleados").json()}
    subir("/api/biometrico/importar", f"biometrico_octubre_2026.{a.formato}")
    with open(AQUI / "permisos_octubre_2026.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            body = {"empleado_id": ids[row["codigo_empleado"]], "tipo_codigo": row["tipo"], "fecha_desde": row["desde"],
                    "fecha_hasta": row["hasta"], "motivo": row["motivo"], "doc_respaldo": row["doc_respaldo"],
                    "autorizado_por": row["autorizado_por"], "aprobar": row["estado"] == "APROBADO"}
            if row["hora_desde"]:
                body["hora_desde"], body["hora_hasta"] = row["hora_desde"], row["hora_hasta"]
            x = c.post("/api/permisos", json=body)
            print("permiso", row["tipo"], x.status_code)
    print("procesar:", c.post("/api/periodos/2026/10/procesar").json())
    out = Path(a.salida)
    out.mkdir(parents=True, exist_ok=True)
    for nombre, ruta in [("1_Informe_Asistencia.docx", "informe.docx"), ("2_Planilla_Nuevo_Personal.xlsx", "nuevos.xlsx"),
                         ("3_Planilla_Desvinculados.xlsx", "desvinculados.xlsx"), ("4_Planilla_Sueldos.xlsx", "planilla.xlsx"),
                         ("5_Reporte_Asistencia.xlsx", "asistencia.xlsx"), ("6_Consolidado_Auditoria.txt", "auditoria.txt")]:
        x = c.get(f"/api/reportes/2026/10/{ruta}")
        x.raise_for_status()
        (out / nombre).write_bytes(x.content)
        print("OK", nombre, len(x.content), "bytes")


if __name__ == "__main__":
    main()
