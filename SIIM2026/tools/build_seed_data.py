"""Genera siim/data/seed.json a partir de las tablas DBF del SIIM 98 (DATA/) y de la Guía de Implementación.
Uso: python tools/build_seed_data.py <carpeta DATA del SIIM98> <guia.txt> <salida.json>
(Sólo se ejecuta al preparar el repositorio; el resultado ya está incluido.)"""
import json
import re
import struct
import sys


def rd(path):
    d = open(path, "rb").read()
    n, hl, rl = struct.unpack("<IHH", d[4:12])
    fl, p = [], 32
    while d[p] != 0x0D:
        fl.append((d[p:p + 11].split(b"\0")[0].decode(), d[p + 16]))
        p += 32
    rows = []
    for i in range(n):
        r = d[hl + i * rl:hl + (i + 1) * rl]
        if r[:1] == b"*":      # registro borrado
            continue
        o, row = 1, {}
        for nm, ln in fl:
            row[nm] = r[o:o + ln].decode("cp1252").strip()
            o += ln
        rows.append(row)
    return rows


def main(data, guia, out):
    S = {}
    S["ciiu"] = [[r["CIIU"], r["DESCRIP"], 1 if r["TIPO"] == "S" else 0] for r in rd(f"{data}/SATCIIU.DBF")]
    # --- históricos: las tablas vienen agrupadas por gestión en orden descendente
    def group(rows):
        g = {}
        for r in rows:
            if any(v == "" for v in r.values()):   # plantillas vacías (gestión sin datos)
                continue
            g.setdefault(int(r["GESTION"]), []).append(r)
        return g
    hist = {}
    for g, rs in group(rd(f"{data}/SAT_D_VE.DBF")).items():
        hist.setdefault(g, {})["veh_deprec"] = [[i, float(r["FACTOR"])] for i, r in enumerate(rs)]
    for g, rs in group(rd(f"{data}/SAT_P_VE.DBF")).items():
        t, prev = [], 0
        for i, r in enumerate(rs):
            t.append([i + 1, float(r["EXCEDENTE"]), None, float(r["CUOTAFIJA"]), float(r["MASPORCENT"]), float(r["EXCEDENTE"])])
        for i in range(len(t) - 1):
            t[i][2] = t[i + 1][1] - 1
        hist.setdefault(g, {})["veh_escala"] = t
    for g, rs in group(rd(f"{data}/SAT_CIPR.DBF")).items():
        hist.setdefault(g, {})["veh_valor"] = [[50 + i, {"MEXICO": float(r["MEXICO"]), "JAPON": float(r["ASIA"]), "USA": float(r["USA"]), "EUROPA_OCC": float(r["EUROPAOCC"]),
                                                      "EUROPA_OR": float(r["EUROPAORI"]), "LATINOAMERICA": float(r["LATINOAM"]), "COREA_ASIA": float(r["COREA"])}] for i, r in enumerate(rs)]
    for g, rs in group(rd(f"{data}/SAT_MOTO.DBF")).items():
        hist.setdefault(g, {})["moto_valor"] = [[50 + i, float(r["BOLIVIANOS"])] for i, r in enumerate(rs)]
    for g, rs in group(rd(f"{data}/SAT_CARR.DBF")).items():
        ch = group(rd(f"{data}/SAT_CHAS.DBF")).get(g, [])
        hist.setdefault(g, {})["veh_correccion"] = [[i + 1, float(r["ESTACAS"]), float(r["MICROS"]), float(r["BUSES"]), float(r["OTROS"]),
                                                       float(ch[i]["TORPEDO"]) if i < len(ch) else 0, float(ch[i]["CABINADO"]) if i < len(ch) else 0] for i, r in enumerate(rs)]
    S["historico"] = {str(k): v for k, v in sorted(hist.items())}
    # --- estructura de actividades (Guía, modelo de patentes anuales)
    lines = open(guia, encoding="utf-8").read().splitlines()
    ini = next(i for i, l in enumerate(lines) if l.startswith("**Modelo de Estructura de las Patentes"))
    tipos, cats, cur = [], [], None
    for l in lines[ini:]:
        if l.startswith("## **Modelo de Ordenanza de Tasas"):
            break
        m = re.match(r"\|\*\*(\d\d)\*\*\|\*\*(.+?)\*\*\|\*\*Categor", l)
        if m:
            cur = m.group(1)
            tipos.append([cur, re.sub(r"<br>", " ", m.group(2)).replace("  ", " ").strip()])
            continue
        m = re.match(r"\|(\d+)\|(.+?)\|Actividad\|", l)
        if m and cur:
            cats.append([cur, f"{int(m.group(1)):02d}", re.sub(r"<br>", " ", m.group(2)).strip()])
    S["act_tipos"] = tipos
    S["act_categorias"] = cats
    json.dump(S, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(len(S["ciiu"]), "ciiu;", len(tipos), "tipos;", len(cats), "categorías;", sorted(hist))


if __name__ == "__main__":
    main(*sys.argv[1:4])
