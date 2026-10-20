"""Núcleo del importador: valida el libro Excel, arma el plan y lo escribe en las
tablas DBF del VSIAF reproduciendo lo que hacen sus pantallas (Activos Fijos,
Revalúo técnico, Transferencia, Dar de baja, Oficinas, Responsables, Auxiliares).
"""
from __future__ import annotations

import datetime as dt
import os
import zipfile
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .calc import Valuation, valuate
from .dbf import DbfError, find_file_ci
from .excelio import Row, WorkbookData, as_date, as_number, as_text
from .ufv import UfvMissing, UfvTable
from .vsiafdb import VsiafDb, norm, registry_incesp_enabled, vsiaf_running

ERROR, WARN, INFO = "ERROR", "AVISO", "INFO"
DEPS = "DADO DE BAJA"                    # texto que el VSIAF guarda en OBSERV al dar de baja


@dataclass
class Issue:
    sheet: str
    row: int
    column: str
    level: str
    message: str


@dataclass
class Options:
    default_unit: str = ""
    user: str = "admin"
    calc_date: dt.date = field(default_factory=dt.date.today)
    default_state: str = "ELABORADO"      # estado de los activos si la fila no lo indica
    only_valid: bool = False              # importar solo las filas válidas aunque haya errores
    make_backup: bool = True
    allow_incesp: Optional[bool] = None   # None = lo que indique el registro de Windows (llave DGCF)
    today: dt.date = field(default_factory=dt.date.today)


@dataclass
class Result:
    issues: List[Issue] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=dict)      # operaciones planificadas por tipo
    skipped: Dict[str, int] = field(default_factory=dict)     # filas con error por hoja
    computed: Dict[str, List[dict]] = field(default_factory=dict)
    applied: bool = False
    backup_path: Optional[str] = None
    notes: List[str] = field(default_factory=list)

    @property
    def errors(self) -> int:
        return sum(1 for i in self.issues if i.level == ERROR)

    @property
    def warnings(self) -> int:
        return sum(1 for i in self.issues if i.level == WARN)


class ImportAbort(Exception):
    pass


# =============================================================================== contexto de fila
class _Ctx:
    def __init__(self, res: Result, sheet: str, row: Row):
        self.res, self.sheet, self.row = res, sheet, row
        self.ok = True

    def err(self, col: str, msg: str) -> None:
        self.ok = False
        self.res.issues.append(Issue(self.sheet, self.row.row, col, ERROR, msg))

    def warn(self, col: str, msg: str) -> None:
        self.res.issues.append(Issue(self.sheet, self.row.row, col, WARN, msg))

    def raw(self, col: str) -> Any:
        return self.row.data.get(col)

    def text(self, col: str, maxlen: Optional[int] = None, required: bool = False) -> str:
        v = as_text(self.raw(col))
        if required and not v:
            self.err(col, "Dato obligatorio vacío.")
        if maxlen and len(v) > maxlen:
            self.err(col, f"Excede el largo máximo de {maxlen} caracteres ({len(v)}).")
        return v

    def number(self, col: str, required: bool = False) -> Optional[float]:
        try:
            v = as_number(self.raw(col))
        except ValueError as e:
            self.err(col, str(e))
            return None
        if v is None and required:
            self.err(col, "Dato obligatorio vacío.")
        return v

    def date(self, col: str, required: bool = False) -> Optional[dt.date]:
        try:
            v = as_date(self.raw(col))
        except ValueError as e:
            self.err(col, str(e))
            return None
        if v is None and required:
            self.err(col, "Dato obligatorio vacío.")
        return v

    def yesno(self, col: str) -> bool:
        v = norm(as_text(self.raw(col)))
        if v in ("", "NO", "N", "0", "FALSO", "FALSE"):
            return False
        if v in ("SI", "S", "1", "VERDADERO", "TRUE", "X"):
            return True
        self.err(col, f"Valor «{v}» no válido: use SI o NO.")
        return False


def _unit_text(v: Any) -> str:
    return as_text(v).strip()


# =============================================================================== estado virtual de la BD
class _State:
    """Copia en memoria de lo que el importador necesita consultar y va modificando."""

    def __init__(self, db: VsiafDb):
        self.entidad = db.entidad
        self.units: Dict[str, dict] = {u["unidad"]: dict(u, new=False) for u in db.unidades()}
        self.oficinas: Dict[Tuple[str, int], dict] = {}
        self.of_by_name: Dict[Tuple[str, str], int] = {}
        for r in db.table("OFICINA").records():
            if r["ENTIDAD"].strip() != self.entidad:
                continue
            u, c = r["UNIDAD"].strip(), int(r["CODOFIC"])
            self.oficinas[(u, c)] = dict(nom=r["NOMOFIC"], api=r["API_ESTADO"], new=False)
            self.of_by_name[(u, norm(r["NOMOFIC"]))] = c
        self.resp: Dict[Tuple[str, int, int], dict] = {}
        self.resp_by_name: Dict[Tuple[str, int, str], int] = {}
        for r in db.table("RESP").records():
            if r["ENTIDAD"].strip() != self.entidad:
                continue
            u, o, c = r["UNIDAD"].strip(), int(r["CODOFIC"]), int(r["CODRESP"])
            self.resp[(u, o, c)] = dict(nom=r["NOMRESP"], api=r["API_ESTADO"], new=False)
            self.resp_by_name[(u, o, norm(r["NOMRESP"]))] = c
        self.aux: Dict[Tuple[str, int, int], str] = {}
        self.aux_by_name: Dict[Tuple[str, int, str], int] = {}
        for r in db.table("AUXILIAR").records():
            if r["ENTIDAD"].strip() != self.entidad:
                continue
            u, g, c = r["UNIDAD"].strip(), int(r["CODCONT"]), int(r["CODAUX"])
            self.aux[(u, g, c)] = r["NOMAUX"]
            self.aux_by_name[(u, g, norm(r["NOMAUX"]))] = c
        self.assets: Dict[Tuple[str, str], dict] = {}
        self.dead_codes: set = set()
        for r in db.table("ACTUAL").records(include_deleted=True):
            if r["ENTIDAD"].strip() != self.entidad:
                continue
            key = (r["UNIDAD"].strip(), r["CODIGO"].strip().upper())
            if r.deleted:
                self.dead_codes.add(key)
                continue
            d = dict(r.values)
            d.update(_new=False, _src="VSIAF")
            self.assets[key] = d
        self.reval_keys = set()
        for r in db.table("REVAL").records():
            if r["ENTIDAD"].strip() == self.entidad:
                self.reval_keys.add((r["UNIDAD"].strip(), r["CODIGO"].strip().upper(), norm(r["RESOLUCION"])))
        for r in db.table("BAJAS").records():
            if r["ENTIDAD"].strip() == self.entidad:
                self.dead_codes.add((r["UNIDAD"].strip(), r["CODIGO"].strip().upper()))

    def next_oficina(self, unit: str) -> int:
        return max([c for (u, c) in self.oficinas if u == unit] or [0]) + 1

    def next_resp(self, unit: str, ofic: int) -> int:
        return max([c for (u, o, c) in self.resp if u == unit and o == ofic] or [0]) + 1

    def next_aux(self, unit: str, grupo: int) -> int:
        return max([c for (u, g, c) in self.aux if u == unit and g == grupo] or [0]) + 1


# =============================================================================== importador
class Importer:
    def __init__(self, db: VsiafDb, ufv: UfvTable, options: Optional[Options] = None,
                 log: Optional[Callable[[str], None]] = None):
        self.db, self.ufv = db, ufv
        self.opt = options or Options()
        self.log = log or (lambda m: None)
        self.res = Result()
        self.state = _State(db)
        self.grupos = {g["codcont"]: g for g in db.grupos()}
        self.grupos_by_name = {norm(g["nombre"]): g["codcont"] for g in self.grupos.values()}
        self.estados = {norm(e["nombre"]): e["codigo"] for e in db.estados()}
        self.estados_codes = {e["codigo"] for e in db.estados()}
        self.motivos = {int(m["codigo"]): m["nombre"] for m in db.motivos_baja()}
        self.motivos_by_name = {norm(v): k for k, v in self.motivos.items()}
        self.org_codes = {o["codigo"] for o in db.organismos()}
        self.deptos = {}
        for d in db.departamentos():
            self.deptos[norm(d["sigla"])] = d["codigo"]
            self.deptos[norm(d["nombre"])] = d["codigo"]
            self.deptos[str(d["codigo"])] = d["codigo"]
        self.incesp_ok = self.opt.allow_incesp if self.opt.allow_incesp is not None else registry_incesp_enabled()
        self.ops: List[Tuple[str, dict]] = []
        self.rows_total: Dict[str, int] = {}

    # ------------------------------------------------------------------ utilidades
    def _unit(self, ctx: _Ctx, col: str = "unidad") -> Optional[str]:
        u = _unit_text(ctx.raw(col)) or self.opt.default_unit
        if not u:
            ctx.err(col, "Falta la unidad: complete la columna o elija una unidad por defecto en el importador.")
            return None
        if len(u) > 5:
            ctx.err(col, "El código de unidad excede 5 caracteres.")
            return None
        if u not in self.state.units:
            ctx.err(col, f"La unidad «{u}» no existe en el VSIAF ni en la hoja UNIDADES.")
            return None
        return u

    def _grupo(self, ctx: _Ctx, col: str = "grupo_contable") -> Optional[dict]:
        v = as_text(ctx.raw(col))
        if not v:
            ctx.err(col, "Dato obligatorio vacío.")
            return None
        if v.isdigit() and int(v) in self.grupos:
            return self.grupos[int(v)]
        n = norm(v)
        if n in self.grupos_by_name:
            return self.grupos[self.grupos_by_name[n]]
        cand = [c for k, c in self.grupos_by_name.items() if k.startswith(n)] if len(n) >= 5 else []
        if len(cand) == 1:
            return self.grupos[cand[0]]
        ctx.err(col, f"Grupo contable «{v}» no reconocido (use el código 1-40 o el nombre de la hoja CATALOGOS).")
        return None

    def _oficina(self, ctx: _Ctx, unit: str, col: str, need_active: bool = True) -> Optional[int]:
        v = as_text(ctx.raw(col))
        if not v:
            ctx.err(col, "Dato obligatorio vacío.")
            return None
        c = self.state.of_by_name.get((unit, norm(v)))
        if c is None:
            ctx.err(col, f"La oficina «{v}» no existe en la unidad {unit} (créela en la hoja OFICINAS).")
            return None
        if need_active and self.state.oficinas[(unit, c)]["api"] != 1:
            ctx.err(col, f"La oficina «{v}» está INACTIVA.")
            return None
        return c

    def _resp(self, ctx: _Ctx, unit: str, ofic: int, col: str) -> Optional[int]:
        v = as_text(ctx.raw(col))
        if not v:
            ctx.err(col, "Dato obligatorio vacío.")
            return None
        c = self.state.resp_by_name.get((unit, ofic, norm(v)))
        if c is None:
            ctx.err(col, f"El responsable «{v}» no existe en esa oficina (créelo en la hoja RESPONSABLES).")
            return None
        if self.state.resp[(unit, ofic, c)]["api"] != 1:
            ctx.err(col, f"El responsable «{v}» está INACTIVO.")
            return None
        return c

    def _asset(self, ctx: _Ctx, unit_col: str, need_approved: bool = True) -> Optional[Tuple[Tuple[str, str], dict]]:
        unit = self._unit(ctx, unit_col)
        codigo = ctx.text("codigo", 15, True).upper()
        if not unit or not codigo:
            return None
        key = (unit, codigo)
        a = self.state.assets.get(key)
        if a is None:
            ctx.err("codigo", f"No existe el activo «{codigo}» en la unidad {unit}"
                    + (" (ya fue dado de baja)." if key in self.state.dead_codes else "."))
            return None
        if need_approved and a["API_ESTADO"] != 3:
            ctx.err("codigo", f"El activo «{codigo}» está ELABORADO: apruébelo primero (el VSIAF solo permite "
                    "revalúos, transferencias y bajas de activos APROBADOS).")
            return None
        return key, a

    def _val(self, a: dict, calc: dt.date) -> Valuation:
        g = self.grupos.get(int(a["CODCONT"]), {"depreciar": True, "actualizar": True})
        inc = dt.date(int(a["ANO"]), int(a["MES"]), int(a["DIA"]))
        return valuate(self.ufv, float(a["COSTO"] or 0), float(a["DEPACU"] or 0), float(a["VIDAUTIL"] or 0),
                       inc, calc, g["depreciar"], g["actualizar"])

    # ------------------------------------------------------------------ UNIDADES
    def _s_unidades(self, rows: List[Row]) -> None:
        for r in rows:
            c = _Ctx(self.res, "UNIDADES", r)
            u = c.text("unidad", 5, True)
            desc = c.text("descripcion", 120, True)
            city = c.text("ciudad", 20)
            if c.ok and u in self.state.units:
                c.warn("unidad", f"La unidad {u} ya existe: se omite.")
                continue
            if not c.ok:
                self._skip("UNIDADES")
                continue
            self.state.units[u] = dict(unidad=u, descripcion=desc, ciudad=city, estado=1, new=True)
            self.ops.append(("unidad", dict(ENTIDAD=self.state.entidad, UNIDAD=u, DESCRIP=desc, CIUDAD=city,
                                            ESTADOUNI=1)))

    # ------------------------------------------------------------------ OFICINAS
    def _s_oficinas(self, rows: List[Row]) -> None:
        for r in rows:
            c = _Ctx(self.res, "OFICINAS", r)
            unit = self._unit(c)
            nom = c.text("oficina", 65, True)
            obs = c.text("observacion")
            if not c.ok:
                self._skip("OFICINAS")
                continue
            if (unit, norm(nom)) in self.state.of_by_name:
                c.warn("oficina", f"La oficina «{nom}» ya existe en la unidad {unit}: se omite.")
                continue
            cod = self.state.next_oficina(unit)
            self.state.oficinas[(unit, cod)] = dict(nom=nom, api=1, new=True)
            self.state.of_by_name[(unit, norm(nom))] = cod
            self.ops.append(("oficina", dict(ENTIDAD=self.state.entidad, UNIDAD=unit, CODOFIC=cod, NOMOFIC=nom,
                                             OBSERV=obs or None, FEULT=self.opt.today, USUAR=self.opt.user,
                                             API_ESTADO=1)))

    # ------------------------------------------------------------------ RESPONSABLES
    def _s_responsables(self, rows: List[Row]) -> None:
        for r in rows:
            c = _Ctx(self.res, "RESPONSABLES", r)
            unit = self._unit(c)
            nom = c.text("responsable", 35, True)
            cargo = c.text("cargo", 35, True)
            ci = c.text("ci", 20)
            exp = c.text("expedido")
            obs = c.text("observacion")
            ofic = self._oficina(c, unit, "oficina", need_active=False) if unit else None
            cod_exp = 0
            if exp:
                cod_exp = self.deptos.get(norm(exp), 0)
                if not cod_exp:
                    c.err("expedido", f"Departamento «{exp}» no reconocido (LPZ, CBB, SCZ, ORU, PTS, CHQ, TAR, BEN, PAN, OTR).")
            if not c.ok or ofic is None:
                self._skip("RESPONSABLES")
                continue
            if (unit, ofic, norm(nom)) in self.state.resp_by_name:
                c.warn("responsable", f"«{nom}» ya existe en esa oficina: se omite.")
                continue
            cod = self.state.next_resp(unit, ofic)
            self.state.resp[(unit, ofic, cod)] = dict(nom=nom, api=1, new=True)
            self.state.resp_by_name[(unit, ofic, norm(nom))] = cod
            self.ops.append(("resp", dict(ENTIDAD=self.state.entidad, UNIDAD=unit, CODOFIC=ofic, CODRESP=cod,
                                          NOMRESP=nom, CARGO=cargo, OBSERV=obs or None, CI=ci,
                                          FEULT=self.opt.today, USUAR=self.opt.user, COD_EXP=cod_exp,
                                          API_ESTADO=1)))

    # ------------------------------------------------------------------ AUXILIARES
    def _s_auxiliares(self, rows: List[Row]) -> None:
        for r in rows:
            c = _Ctx(self.res, "AUXILIARES", r)
            unit = self._unit(c)
            g = self._grupo(c)
            nom = c.text("auxiliar", 50, True)
            obs = c.text("observacion")
            if not c.ok or g is None:
                self._skip("AUXILIARES")
                continue
            if (unit, g["codcont"], norm(nom)) in self.state.aux_by_name:
                c.warn("auxiliar", f"El auxiliar «{nom}» ya existe en el grupo {g['codcont']}: se omite.")
                continue
            cod = self.state.next_aux(unit, g["codcont"])
            self.state.aux[(unit, g["codcont"], cod)] = nom
            self.state.aux_by_name[(unit, g["codcont"], norm(nom))] = cod
            self.ops.append(("aux", dict(ENTIDAD=self.state.entidad, UNIDAD=unit, CODCONT=g["codcont"], CODAUX=cod,
                                         NOMAUX=nom, OBSERV=obs or None, FEULT=self.opt.today,
                                         USUAR=self.opt.user)))

    # ------------------------------------------------------------------ ACTIVOS
    def _s_activos(self, rows: List[Row]) -> None:
        out: List[dict] = []
        for r in rows:
            c = _Ctx(self.res, "ACTIVOS", r)
            unit = self._unit(c)
            codigo = c.text("codigo", 15, True).upper()
            cod_sec = c.text("codigo_adicional", 15).upper()
            desc = c.text("descripcion", 150, True)
            g = self._grupo(c)
            nom_aux = c.text("auxiliar", None, True)
            ofic = self._oficina(c, unit, "oficina") if unit else None
            resp = self._resp(c, unit, ofic, "responsable") if (unit and ofic is not None) else None
            est_txt = c.text("estado_bien", None, True)
            inc = c.date("fecha_incorporacion", True)
            costo = c.number("costo_inicial", True)
            vida_in = c.number("vida_util")
            dep_in = c.number("dep_acumulada_inicial") or 0.0
            rube = c.text("cod_rube", 15)
            org = c.text("organismo_financiador", None, True)
            conv = c.text("nro_convenio", 10)
            obs = c.text("observaciones")
            est_reg = norm(c.text("estado_registro")) or self.opt.default_state
            incesp = c.yesno("incorporacion_especial")

            # código único
            if unit and codigo:
                key = (unit, codigo)
                prev = self.state.assets.get(key)
                if prev is not None:
                    where = "en el VSIAF" if not prev["_new"] else f"en la fila {prev['_src']} de este libro"
                    c.err("codigo", f"El código «{codigo}» ya existe {where} (unidad {unit}).")
                elif key in self.state.dead_codes:
                    c.warn("codigo", f"El código «{codigo}» corresponde a un activo dado de baja; verifique que no sea un duplicado.")
            # estado del bien
            cod_estado = None
            if est_txt:
                cod_estado = self.estados.get(norm(est_txt))
                if cod_estado is None and est_txt.isdigit() and int(est_txt) in self.estados_codes:
                    cod_estado = int(est_txt)
                if cod_estado is None:
                    c.err("estado_bien", f"Estado «{est_txt}» no válido (Bueno, Regular o Malo).")
            # organismo financiador
            if org:
                o = "000" if norm(org) == "NC" else (org.zfill(3) if org.isdigit() else org)
                if o not in self.org_codes:
                    c.err("organismo_financiador", f"Organismo financiador «{org}» no existe en el clasificador.")
                org = o
            # estado de registro
            if est_reg not in ("ELABORADO", "APROBADO"):
                c.err("estado_registro", "Use ELABORADO o APROBADO.")
            # auxiliar
            codaux = None
            if g is not None and unit and nom_aux:
                codaux = self.state.aux_by_name.get((unit, g["codcont"], norm(nom_aux)))
                if codaux is None:
                    c.err("auxiliar", f"El auxiliar «{nom_aux}» no existe en el grupo «{g['nombre']}» "
                          f"de la unidad {unit} (créelo en la hoja AUXILIARES).")
            # fecha
            if inc is not None:
                if inc > self.opt.today:
                    c.err("fecha_incorporacion", "La fecha de incorporación no puede ser futura.")
                elif not self.ufv.has(inc):
                    c.err("fecha_incorporacion", f"No hay UFV registrada para {inc:%d/%m/%Y} "
                          "(el VSIAF no permite operar sin índice).")
                elif inc.year < self.opt.today.year:
                    c.warn("fecha_incorporacion", "Activo de una gestión anterior: el VSIAF recalcula su "
                           "actualización y depreciación desde esa fecha; revise el Reporte 6 luego de importar.")
            # costo / vida útil / dep. acumulada
            vida, banderas = 0.0, "0"
            if costo is not None and costo <= 0:
                c.err("costo_inicial", "El costo debe ser mayor a cero.")
            if g is not None:
                vg = float(g["vida_util"])
                if incesp:
                    if not self.incesp_ok:
                        c.err("incorporacion_especial", "Este equipo no tiene habilitadas las Incorporaciones "
                              "Especiales (llave de la DGCF). El importador no puede saltarse esa autorización.")
                    elif vida_in is None and g["depreciar"]:
                        c.err("vida_util", "Indique la vida útil de la incorporación especial.")
                    vida = float(vida_in if vida_in is not None else vg)
                    banderas = "1"
                else:
                    if vida_in is not None and abs(vida_in - vg) > 1e-9:
                        c.err("vida_util", f"La vida útil ({vida_in:g}) difiere de la del grupo ({vg:g} años). "
                              "Solo se permite como Incorporación Especial autorizada por la DGCF.")
                    vida = vg
                    if dep_in:
                        c.err("dep_acumulada_inicial", "El VSIAF solo admite depreciación acumulada inicial en "
                              "incorporaciones especiales (en un alta normal la calcula desde la fecha).")
                if g["depreciar"] and vida <= 0:
                    c.err("vida_util", "La vida útil no puede ser cero en un grupo que se deprecia.")
                if not g["depreciar"]:
                    vida = 0.0
                    if dep_in:
                        c.err("dep_acumulada_inicial", "El grupo no se deprecia.")
                if costo is not None and dep_in > costo:
                    c.err("dep_acumulada_inicial", "La depreciación acumulada no puede superar el costo.")
            if not c.ok or unit is None or g is None or inc is None or costo is None:
                self._skip("ACTIVOS")
                continue

            rec = dict(UNIDAD=unit, ENTIDAD=self.state.entidad, CODIGO=codigo, CODCONT=g["codcont"], CODAUX=codaux,
                       VIDAUTIL=vida, DESCRIP=desc, COSTO=costo, DEPACU=dep_in, MES=inc.month, ANO=inc.year,
                       B_REV=False, DIA=inc.day, CODOFIC=ofic, CODRESP=resp, OBSERV=obs or None,
                       BAND_UFV=False, CODESTADO=cod_estado, COD_RUBE=rube, NRO_CONV=conv, ORG_FIN=org,
                       FEULT=self.opt.today, USUAR=self.opt.user, API_ESTADO=3 if est_reg == "APROBADO" else 1,
                       CODIGOSEC=cod_sec, BANDERAS=banderas, USU_MOD="")
            st = dict(rec, _new=True, _src=r.row)
            self.state.assets[(unit, codigo)] = st
            self.ops.append(("actual_new", rec))
            try:
                v = self._val(rec, max(self.opt.calc_date, inc))
                out.append(self._calc_row(r.row, rec, g, v, est_reg))
            except UfvMissing as e:
                c.warn("fecha_incorporacion", f"No se pudo calcular la vista previa: {e}")
        self.res.computed["ACTIVOS"] = out

    @staticmethod
    def _calc_row(row: int, rec: dict, g: dict, v: Valuation, est: str) -> dict:
        return {
            "fila": row, "unidad": rec["UNIDAD"], "codigo": rec["CODIGO"], "grupo": g["nombre"],
            "codcont": g["codcont"], "estado": est, "incorporacion": dt.date(rec["ANO"], rec["MES"], rec["DIA"]),
            "vida_util": rec["VIDAUTIL"], "costo_historico": v.costo, "factor": v.factor,
            "costo_actualizado_inicial": v.valor_actualizado_ini, "actualizacion_gestion": v.actualizacion_gestion,
            "costo_total_actualizado": v.valor_actualizado, "dep_gestion": v.dep_gestion,
            "dep_acumulada_inicial": v.dep_acumulada_ini, "actualizacion_dep_acumulada": v.actualizacion_dep,
            "dep_acumulada": v.dep_acumulada, "valor_neto": v.valor_neto, "dias": v.dias_totales,
        }

    # ------------------------------------------------------------------ REVALUOS
    def _s_revaluos(self, rows: List[Row]) -> None:
        out: List[dict] = []
        pend = []
        for r in rows:       # se procesan en orden cronológico por activo
            try:
                d = as_date(r.data.get("fecha_revaluo"))
            except ValueError:
                d = None
            pend.append((d or dt.date.max, r.row, r))
        for _d, _n, r in sorted(pend, key=lambda t: (t[0], t[1])):
            c = _Ctx(self.res, "REVALUOS", r)
            got = self._asset(c, "unidad")
            fecha = c.date("fecha_revaluo", True)
            costo_n = c.number("nuevo_costo", True)
            vida_n = c.number("nueva_vida_util", True)
            resol = c.text("disposicion_respaldo", 16, True)
            motivo = c.text("motivo")
            if got is None or not c.ok:
                self._skip("REVALUOS")
                continue
            key, a = got
            g = self.grupos.get(int(a["CODCONT"]), {"depreciar": True, "actualizar": True, "nombre": ""})
            base = dt.date(int(a["ANO"]), int(a["MES"]), int(a["DIA"]))
            if fecha is not None:
                if fecha > self.opt.today:
                    c.err("fecha_revaluo", "La fecha del revalúo no puede ser futura.")
                elif fecha < base:
                    c.err("fecha_revaluo", f"La fecha del revalúo es anterior a la fecha base del activo ({base:%d/%m/%Y}).")
                elif not (self.ufv.has(fecha) and self.ufv.has(fecha + dt.timedelta(days=1))):
                    c.err("fecha_revaluo", f"No hay UFV registrada para {fecha:%d/%m/%Y} (o el día siguiente).")
            if costo_n is not None and costo_n <= 0:
                c.err("nuevo_costo", "El nuevo costo debe ser mayor a cero.")
            if vida_n is not None and vida_n <= 0 and g["depreciar"]:
                c.err("nueva_vida_util", "La nueva vida útil no puede ser cero.")
            if resol and (key[0], key[1], norm(resol)) in self.state.reval_keys:
                c.err("disposicion_respaldo", f"Ya existe un revalúo del activo con la disposición «{resol}».")
            if not c.ok:
                self._skip("REVALUOS")
                continue
            try:
                v = self._val(a, fecha)
            except UfvMissing as e:
                c.err("fecha_revaluo", str(e))
                self._skip("REVALUOS")
                continue
            nueva_base = fecha + dt.timedelta(days=1)
            rv = dict(ENTIDAD=self.state.entidad, UNIDAD=key[0], CODIGO=key[1], COSTO=a["COSTO"],
                      DEPACU_ANT=a["DEPACU"] or 0, D_REVAL=fecha.day, DIA=a["DIA"], M_REVAL=fecha.month, MES=a["MES"],
                      A_REVAL=fecha.year, ANO=a["ANO"], VIDAUTIL=a["VIDAUTIL"], RESOLUCION=resol,
                      OBSERV=motivo or None, USUAR=self.opt.user, FEULT=self.opt.today, DEPACU=v.snap_depacu,
                      ACTUA=v.snap_actua, DEPGESTION=v.dep_gestion, USU_MOD="")
            upd = dict(DIA=nueva_base.day, MES=nueva_base.month, ANO=nueva_base.year, B_REV=True, COSTO=costo_n,
                       VIDAUTIL=vida_n if g["depreciar"] else 0.0, DEPACU=0)
            self.ops.append(("reval", dict(row=rv, key=key, update=upd)))
            self.state.reval_keys.add((key[0], key[1], norm(resol)))
            a.update(upd)
            out.append(dict(fila=r.row, unidad=key[0], codigo=key[1], fecha_revaluo=fecha, costo_anterior=rv["COSTO"],
                            vida_anterior=rv["VIDAUTIL"], valor_actualizado=v.valor_actualizado,
                            dep_gestion=v.dep_gestion, dep_acumulada_anterior=v.snap_depacu,
                            valor_neto_anterior=v.snap_actua, nuevo_costo=costo_n, nueva_vida=upd["VIDAUTIL"],
                            nueva_fecha_base=nueva_base, resolucion=resol))
        self.res.computed["REVALUOS"] = out

    # ------------------------------------------------------------------ TRANSFERENCIAS
    def _s_transferencias(self, rows: List[Row]) -> None:
        out: List[dict] = []
        for r in rows:
            c = _Ctx(self.res, "TRANSFERENCIAS", r)
            got = self._asset(c, "unidad_origen")
            dest_txt = _unit_text(c.raw("unidad_destino"))
            if got is None:
                self._skip("TRANSFERENCIAS")
                continue
            key, a = got
            dest = dest_txt or key[0]
            if dest not in self.state.units:
                c.err("unidad_destino", f"La unidad destino «{dest}» no existe.")
            ofic = self._oficina(c, dest, "oficina_destino") if dest in self.state.units else None
            resp = self._resp(c, dest, ofic, "responsable_destino") if ofic is not None else None
            codaux = int(a["CODAUX"])
            aux_txt = c.text("auxiliar_destino")
            if dest != key[0]:
                if (dest, key[1]) in self.state.assets:
                    c.err("unidad_destino", f"Ya existe un activo «{key[1]}» en la unidad {dest}: "
                          "no se puede transferir (el VSIAF lo impide).")
                if not aux_txt:
                    c.err("auxiliar_destino", "Al transferir entre unidades se debe indicar el auxiliar de destino.")
                else:
                    codaux_n = self.state.aux_by_name.get((dest, int(a["CODCONT"]), norm(aux_txt)))
                    if codaux_n is None:
                        c.err("auxiliar_destino", f"El auxiliar «{aux_txt}» no existe en el grupo del activo en la unidad {dest}.")
                    else:
                        codaux = codaux_n
            if not c.ok:
                self._skip("TRANSFERENCIAS")
                continue
            if dest == key[0] and ofic == a["CODOFIC"] and resp == a["CODRESP"]:
                c.warn("codigo", "La oficina y el responsable de destino son los mismos que los actuales: se omite.")
                continue
            self.ops.append(("trasfe", dict(
                key=key, update=dict(CODOFIC=ofic, CODRESP=resp, UNIDAD=dest, CODAUX=codaux),
                row=dict(ENTIDAD=self.state.entidad, UNIDAD=dest, CODIGO=key[1], CODOFIC=ofic, CODRESP=resp,
                         FEULT=self.opt.today, USUAR=self.opt.user, UNIDADINI=key[0]))))
            del self.state.assets[key]
            a.update(UNIDAD=dest, CODOFIC=ofic, CODRESP=resp, CODAUX=codaux)
            self.state.assets[(dest, key[1])] = a
            out.append(dict(fila=r.row, codigo=key[1], unidad_origen=key[0], unidad_destino=dest,
                            oficina=self.state.oficinas[(dest, ofic)]["nom"],
                            responsable=self.state.resp[(dest, ofic, resp)]["nom"]))
        self.res.computed["TRANSFERENCIAS"] = out

    # ------------------------------------------------------------------ BAJAS
    def _s_bajas(self, rows: List[Row]) -> None:
        out: List[dict] = []
        pend = []
        for r in rows:
            try:
                d = as_date(r.data.get("fecha_baja"))
            except ValueError:
                d = None
            pend.append((d or dt.date.max, r.row, r))
        for _d, _n, r in sorted(pend, key=lambda t: (t[0], t[1])):
            c = _Ctx(self.res, "BAJAS", r)
            got = self._asset(c, "unidad")
            fecha = c.date("fecha_baja", True)
            mot_txt = c.text("motivo_baja", None, True)
            resol = c.text("disposicion_respaldo", 16, True)
            obs = c.text("observaciones", 120)
            codbaja = None
            if mot_txt:
                if mot_txt.isdigit() and int(mot_txt) in self.motivos:
                    codbaja = int(mot_txt)
                else:
                    codbaja = self.motivos_by_name.get(norm(mot_txt))
                    if codbaja is None:
                        cand = [k for n, k in self.motivos_by_name.items() if n.startswith(norm(mot_txt))]
                        codbaja = cand[0] if len(cand) == 1 else None
                if codbaja is None:
                    c.err("motivo_baja", f"Motivo de baja «{mot_txt}» no reconocido (códigos 1-9, ver hoja CATALOGOS).")
            if got is None or not c.ok:
                self._skip("BAJAS")
                continue
            key, a = got
            base = dt.date(int(a["ANO"]), int(a["MES"]), int(a["DIA"]))
            if fecha is not None:
                if fecha > self.opt.today:
                    c.err("fecha_baja", "La fecha de baja no puede ser futura.")
                elif fecha < base:
                    c.err("fecha_baja", f"La fecha de baja es anterior a la fecha base del activo ({base:%d/%m/%Y}).")
                elif not self.ufv.has(fecha):
                    c.err("fecha_baja", f"No hay UFV registrada para {fecha:%d/%m/%Y}.")
            if codbaja == 9 and fecha is not None and base.year != fecha.year:
                c.err("motivo_baja", "«Error de transcripción» solo puede aplicarse a activos incorporados en la "
                      "gestión vigente (el VSIAF exige regularizarlo con la DGCF).")
            if not c.ok:
                self._skip("BAJAS")
                continue
            try:
                v = self._val(a, fecha)
            except UfvMissing as e:
                c.err("fecha_baja", str(e))
                self._skip("BAJAS")
                continue
            if len(a["DESCRIP"]) > 120:
                c.warn("codigo", "La descripción se recorta a 120 caracteres en la tabla BAJAS (igual que el VSIAF).")
            bj = dict(ENTIDAD=self.state.entidad, UNIDAD=key[0], CODIGO=key[1], CODBAJA=codbaja, CODCONT=a["CODCONT"],
                      CODAUX=a["CODAUX"], CODOFIC=a["CODOFIC"], CODRESP=a["CODRESP"], COSTO=a["COSTO"],
                      DEPACU_ANT=v.dep_acumulada_ini, DESCRIP=a["DESCRIP"][:120], D_BAJA=fecha.day, DIA=a["DIA"],
                      M_BAJA=fecha.month, MES=a["MES"], A_BAJA=fecha.year, ANO=a["ANO"], B_REV=bool(a["B_REV"]),
                      VIDAUTIL=a["VIDAUTIL"], RESOLUCION=resol, OBSERV=DEPS, MOTIVO=obs, DEPACU=v.snap_depacu,
                      ACTUA=v.snap_actua, DEPGESTION=v.dep_gestion, COSBAJINI=v.valor_actualizado_ini,
                      COSDAINI=v.dep_acumulada_ini, COSACTBAJ=v.valor_actualizado, ACTDABAJ=v.actualizacion_dep,
                      USUAR=self.opt.user, FEULT=self.opt.today, USU_MOD="")
            self.ops.append(("baja", dict(row=bj, key=key)))
            del self.state.assets[key]
            self.state.dead_codes.add(key)
            out.append(dict(fila=r.row, unidad=key[0], codigo=key[1], fecha_baja=fecha,
                            motivo=self.motivos[codbaja], costo=a["COSTO"], costo_actualizado=v.valor_actualizado,
                            dep_gestion=v.dep_gestion, dep_acumulada=v.dep_acumulada, valor_neto=v.valor_neto,
                            resolucion=resol))
        self.res.computed["BAJAS"] = out

    def _skip(self, sheet: str) -> None:
        self.res.skipped[sheet] = self.res.skipped.get(sheet, 0) + 1

    # ------------------------------------------------------------------ validación / plan
    def plan(self, wb: WorkbookData) -> Result:
        for p in wb.problems:
            lvl = ERROR if "falta la columna" in p or "ninguna hoja" in p else WARN
            self.res.issues.append(Issue("(estructura)", 0, "", lvl, p))
        lc = self.ufv.last_change
        if lc and (self.opt.calc_date - lc).days > 75:
            self.res.issues.append(Issue("(UFV)", 0, "", WARN,
                                         f"Las UFV del VSIAF parecen desactualizadas: el último cambio de índice es del "
                                         f"{lc:%d/%m/%Y}. Ejecute el actualizador de UFV del Ministerio (cada día 10) para que "
                                         "el importador y el VSIAF calculen con índices vigentes."))
        if self.db.gestion_cerrada():
            self.res.issues.append(Issue("(BD)", 0, "", ERROR,
                                         "La gestión de esta base está CERRADA: el VSIAF no permite modificarla."))
        handlers = [("UNIDADES", self._s_unidades), ("OFICINAS", self._s_oficinas),
                    ("RESPONSABLES", self._s_responsables), ("AUXILIARES", self._s_auxiliares),
                    ("ACTIVOS", self._s_activos), ("REVALUOS", self._s_revaluos),
                    ("TRANSFERENCIAS", self._s_transferencias), ("BAJAS", self._s_bajas)]
        for name, fn in handlers:
            rows = wb.rows(name)
            self.rows_total[name] = len(rows)
            if rows:
                self.log(f"Validando hoja {name} ({len(rows)} filas)…")
                fn(rows)
        kinds = {"unidad": "UNIDADES", "oficina": "OFICINAS", "resp": "RESPONSABLES", "aux": "AUXILIARES",
                 "actual_new": "ACTIVOS", "reval": "REVALUOS", "trasfe": "TRANSFERENCIAS", "baja": "BAJAS"}
        for k, _ in self.ops:
            self.res.counts[kinds[k]] = self.res.counts.get(kinds[k], 0) + 1
        return self.res

    # ------------------------------------------------------------------ aplicar
    def apply(self, wb_path: str = "") -> Result:
        """Escribe el plan en la BD.  Debe llamarse después de ``plan``."""
        res = self.res
        blocking = [i for i in res.issues if i.level == ERROR and i.sheet in ("(BD)", "(estructura)")]
        if blocking:
            raise ImportAbort(blocking[0].message)
        if res.errors and not self.opt.only_valid:
            raise ImportAbort(f"Hay {res.errors} error(es) en el libro. Corríjalos o active «importar solo filas válidas».")
        if not self.ops:
            raise ImportAbort("No hay nada que importar.")
        if vsiaf_running():
            raise ImportAbort("El VSIAF está abierto. Ciérrelo antes de importar.")
        db = self.db
        if self.opt.make_backup:
            res.backup_path = make_backup(db, f"Importación desde Excel ({os.path.basename(wb_path)})" if wb_path
                                          else "Importación desde Excel")
            self.log(f"Respaldo creado: {res.backup_path}")
        originals = {p: open(p, "rb").read() for p in db.dirty_files() if os.path.exists(p)}
        try:
            self._write()
            db.save_all()
            self._verify()
        except Exception:
            for p, data in originals.items():           # deshacer: restaurar los archivos tal como estaban
                with open(p, "wb") as fh:
                    fh.write(data)
            raise
        res.applied = True
        return res

    def _write(self) -> None:
        db = self.db
        t_act, t_rev, t_baj, t_tra = (db.table(n) for n in ("ACTUAL", "REVAL", "BAJAS", "TRASFE"))
        recno: Dict[Tuple[str, str], int] = {}
        ent = self.state.entidad
        for r in t_act.records(include_deleted=True):
            if r["ENTIDAD"].strip() == ent and not r.deleted:
                recno[(r["UNIDAD"].strip(), r["CODIGO"].strip().upper())] = r.recno
        tables = {"unidad": "UNIDADADMIN", "oficina": "OFICINA", "resp": "RESP", "aux": "AUXILIAR"}
        for kind, d in self.ops:
            if kind in tables:
                db.table(tables[kind]).append(d)
            elif kind == "actual_new":
                recno[(d["UNIDAD"], d["CODIGO"])] = t_act.append(d)
            elif kind == "reval":
                t_rev.append(d["row"])
                t_act.update(recno[d["key"]], d["update"])
            elif kind == "trasfe":
                t_tra.append(d["row"])
                n = recno.pop(d["key"])
                t_act.update(n, d["update"])
                recno[(d["update"]["UNIDAD"], d["key"][1])] = n
            elif kind == "baja":
                t_baj.append(d["row"])
                n = recno.pop(d["key"])
                t_act.update(n, {"OBSERV": DEPS})
                t_act.set_deleted(n, True)

    def _verify(self) -> None:
        """Relee los archivos desde el disco y comprueba que el resultado coincide con el plan."""
        from .dbf import DbfTable
        want = {"actual_new": 0, "reval": 0, "baja": 0, "trasfe": 0, "oficina": 0, "resp": 0, "aux": 0, "unidad": 0}
        for k, _ in self.ops:
            want[k] += 1
        files = {"ACTUAL": "actual_new", "REVAL": "reval", "BAJAS": "baja", "TRASFE": "trasfe", "OFICINA": "oficina",
                 "RESP": "resp", "AUXILIAR": "aux", "UNIDADADMIN": "unidad"}
        for name, kind in files.items():
            t = self.db.table(name)
            fresh = DbfTable(t.path)
            if fresh.nrec != t.nrec:
                raise DbfError(f"Verificación fallida en {name}: {fresh.nrec} registros en disco, se esperaban {t.nrec}.")
            if want[kind]:                      # decodifica lo recién escrito (campos y memos)
                for n in range(max(1, fresh.nrec - want[kind] + 1), fresh.nrec + 1):
                    fresh.read(n)


# =============================================================================== respaldo
def make_backup(db: VsiafDb, description: str) -> str:
    """Respaldo compatible con *Respaldos BD → Restaurar* del VSIAF (zip plano de ``dbfs`` + .gtz)."""
    bdir = find_file_ci(db.install_dir, "backups") or os.path.join(db.install_dir, "backups")
    os.makedirs(bdir, exist_ok=True)
    stamp = dt.datetime.now().strftime("%d%m%y%H%M")
    base = f"VSIMPXL{stamp}"
    zpath = os.path.join(bdir, base + ".zip")
    comment = f"Backup de la entidad «{db.entidad}» en fecha {dt.date.today():%d/%m/%Y}: {description}"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(os.listdir(db.dbfs_dir)):
            fp = os.path.join(db.dbfs_dir, fn)
            if os.path.isfile(fp) and not fn.endswith(".vsiaf_imp_tmp"):
                z.write(fp, fn)
        z.comment = comment.encode("cp1252", "replace")
    with open(os.path.join(bdir, base + ".gtz"), "wb") as fh:
        fh.write(comment.encode("cp1252", "replace"))
    return zpath
