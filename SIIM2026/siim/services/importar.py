"""Migración / carga masiva del padrón desde Excel (hojas: contribuyentes, inmuebles, vehiculos, actividades, publicidad)."""
from datetime import date, datetime

from . import padron
from .base import Ctx, ServiceError, hoy

HOJAS = {"contribuyentes": padron.CAMPOS_CONTRIB, **{k: v for k, v in padron.CAMPOS_OBJ.items()}}
ENLACE = "nro_doc"          # en las hojas de bienes: columna pmc o nro_doc del titular


def plantilla(path):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    wb.remove(wb.active)
    ejemplo = {"contribuyentes": ["N", "CI", "1234567", "LP", "Pérez", "Vedia", "Juan", "", "", "A", "", "CALLE", "Bolívar", "123"],
               "inmuebles": ["1234567", "CASA", "A", "", "CALLE", "Bolívar", "123"], "vehiculos": ["1234567", "1234-ABC", "", "AUTOMOVIL", "Toyota", "Corolla"],
               "actividades": ["1234567", "14", "02", "Ferretería El Tornillo", "", "", "", "2020-01-15"], "publicidad": ["1234567", "SIMPLE_1C", "Letrero"]}
    for h, campos in HOJAS.items():
        ws = wb.create_sheet(h)
        cols = campos if h == "contribuyentes" else ["nro_doc"] + campos
        ws.append(cols)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1F3A5F")
        ws.append(ejemplo[h])
        ws.freeze_panes = "A2"
    ws = wb.create_sheet("LEEME")
    for l in ["Plantilla de carga masiva del padrón (SIIM 2026)", "• Cada hoja corresponde a una tabla. No cambie los encabezados.",
              "• Hojas de bienes: la columna nro_doc (o pmc) identifica al titular, que debe existir en la hoja 'contribuyentes' o en el padrón.",
              "• Fechas en formato AAAA-MM-DD. Valores lógicos: 1 = sí, 0 = no.", "• Valide primero (simulación); sólo se importan los registros sin errores.", "• Borre la fila de ejemplo antes de importar."]:
        ws.append([l])
    wb.save(path)


def _leer(path):
    from openpyxl import load_workbook
    wb = load_workbook(path, read_only=True, data_only=True)
    out = {}
    for ws in wb.worksheets:
        if ws.title not in HOJAS:
            continue
        it = ws.iter_rows(values_only=True)
        try:
            head = [str(h).strip() if h is not None else "" for h in next(it)]
        except StopIteration:
            continue
        rows = []
        for r in it:
            if all(v in (None, "") for v in r):
                continue
            d = {}
            for h, v in zip(head, r):
                if isinstance(v, (datetime, date)):
                    v = v.strftime("%Y-%m-%d")
                d[h] = None if v in ("", None) else (str(v).strip() if isinstance(v, str) else v)
            rows.append(d)
        out[ws.title] = rows
    return out


def importar_padron(ctx: Ctx, path, simular=True):
    """Devuelve dict(resumen, errores). Con simular=False graba en una sola transacción los registros válidos."""
    ctx.require("padron.editar")
    datos = _leer(path)
    if not datos:
        raise ServiceError("El archivo no tiene hojas reconocidas (contribuyentes, inmuebles, vehiculos, actividades, publicidad).")
    db = ctx.db
    errores, resumen = [], {k: 0 for k in HOJAS}
    docs = {}      # nro_doc -> pmc (existentes o creados en esta carga)
    for r in db.all("SELECT pmc, nro_doc FROM contribuyentes WHERE nro_doc IS NOT NULL"):
        docs[str(r["nro_doc"])] = r["pmc"]
    sim_pmc = [max(db.scalar("SELECT MAX(pmc) FROM contribuyentes", default=padron.PMC_INICIAL), padron.PMC_INICIAL)]

    def run():
        for i, d in enumerate(datos.get("contribuyentes", []), 2):
            nd = str(d.get("nro_doc") or d.get("nit") or "")
            try:
                if nd and nd in docs:
                    raise ServiceError(f"el documento {nd} ya existe en el padrón (PMC {docs[nd]})")
                falt = padron.faltantes_contribuyente({**d, "persona": d.get("persona") or "N"})
                if falt:
                    raise ServiceError("faltan: " + ", ".join(falt))
                if simular:
                    sim_pmc[0] += 1
                    docs[nd] = sim_pmc[0]
                else:
                    docs[nd] = padron.nuevo_contribuyente(ctx, d, nro_orden="IMPORT", fecha=hoy())
                resumen["contribuyentes"] += 1
            except ServiceError as e:
                errores.append(("contribuyentes", i, str(e)))
        for hoja in ("inmuebles", "vehiculos", "actividades", "publicidad"):
            for i, d in enumerate(datos.get(hoja, []), 2):
                try:
                    pmc = d.get("pmc") or docs.get(str(d.get("nro_doc") or ""))
                    if not pmc:
                        raise ServiceError("titular no encontrado (nro_doc/pmc)")
                    if not simular:
                        padron.guardar_objeto(ctx, hoja, int(pmc), d, None, "F-019")
                    resumen[hoja] += 1
                except (ServiceError, ValueError, TypeError) as e:
                    errores.append((hoja, i, str(e)))

    if simular:
        run()
    else:
        with db.tx():
            run()
            ctx.log("IMPORTA_PADRON", None, None, {"archivo": str(path), **resumen, "errores": len(errores)})
    return dict(resumen=resumen, errores=errores, simulado=simular)
