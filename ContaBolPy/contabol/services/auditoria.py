"""Módulo de Auditoría (MAF financiera y MAI tributaria): encargos, planificación, papeles de trabajo, hallazgos, ajustes, dictámenes y cierre inmutable."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime

from ..security import verificar
from ..sistema import ErrorNegocio
from ..util import fdate, iso, r2, to_date
from . import auditoria_plantillas as P

FACTOR_RIESGO = {"B": 0.4, "M": 0.7, "A": 1.0}
NIVEL_NOMBRE = {"B": "Bajo", "M": "Medio", "A": "Alto"}
BASES = {"ACTIVO": ("Activo total", 1.0), "INGRESOS": ("Ingresos operativos", 0.5), "UTILIDAD_BRUTA": ("Utilidad bruta", 2.0),
         "PATRIMONIO": ("Patrimonio", 2.0), "UTILIDAD": ("Resultado antes de impuestos", 5.0)}
ROLES_EQUIPO = ["Socio", "Gerente", "Supervisor", "Auditor senior", "Auditor asistente"]


class AuditoriaService:
    def __init__(self, ctx):
        self.ctx = ctx
        self.db = ctx.db

    # ------------------------------------------------------------ utilidades
    def _permiso(self, tipo: str) -> None:
        self.ctx.requiere("AUD.FINANCIERA" if tipo == "F" else "AUD.TRIBUTARIA")

    def encargo(self, eid: int) -> dict:
        e = self.db.one("SELECT * FROM auditoria_encargo WHERE id=?", (eid,))
        if not e:
            raise ErrorNegocio("Encargo de auditoría inexistente.")
        self._permiso(e["tipo"])
        return e

    def _abierto(self, eid: int) -> dict:
        e = self.encargo(eid)
        if e["estado"] == "CERRADO":
            raise ErrorNegocio("El encargo de auditoría está CERRADO: los papeles de trabajo son de solo lectura.")
        return e

    def _iniciales(self) -> str:
        n = self.ctx.usuario["nombre"].split()
        return ("".join(p[0] for p in n[:2]) or self.ctx.usuario["login"][:2]).upper()

    def trail(self, encargo_id, entidad: str, entidad_id, accion: str, detalle: str = "") -> None:
        """Bitácora encadenada (cada registro incluye el hash del anterior): permite detectar alteraciones."""
        prev = self.db.scalar("SELECT hash FROM auditoria_trail ORDER BY id DESC LIMIT 1", default="")
        fecha = datetime.now().isoformat(timespec="seconds")
        usuario = self.ctx.usuario["login"]
        base = "|".join(str(x) for x in (prev, fecha, usuario, encargo_id, entidad, entidad_id, accion, detalle))
        h = hashlib.sha256(base.encode("utf-8")).hexdigest()
        self.db.insert("auditoria_trail", fecha=fecha, usuario=usuario, encargo_id=encargo_id, entidad=entidad, entidad_id=entidad_id, accion=accion, detalle=(detalle or "")[:500], hash_prev=prev, hash=h)

    def verificar_trail(self) -> bool:
        prev = ""
        for r in self.db.query("SELECT * FROM auditoria_trail ORDER BY id"):
            base = "|".join(str(x) for x in (prev, r["fecha"], r["usuario"], r["encargo_id"], r["entidad"], r["entidad_id"], r["accion"], r["detalle"] or ""))
            if hashlib.sha256(base.encode("utf-8")).hexdigest() != r["hash"] or (r["hash_prev"] or "") != prev:
                return False
            prev = r["hash"]
        return True

    # --------------------------------------------------------------- encargos
    def listar(self, tipo: str | None = None) -> list[dict]:
        sql, p = "SELECT * FROM auditoria_encargo WHERE 1=1", []
        if tipo:
            sql += " AND tipo=?"
            p.append(tipo)
        return self.db.query(sql + " ORDER BY id DESC", p)

    def crear_encargo(self, tipo: str, nombre: str, periodo_ini=None, periodo_fin=None, plantillas: bool = True) -> int:
        self._permiso(tipo)
        ctx = self.ctx
        if tipo not in ("F", "T"):
            raise ErrorNegocio("Tipo de auditoría no válido.")
        if not (nombre or "").strip():
            raise ErrorNegocio("Indique el nombre del encargo.")
        ini, fin = to_date(periodo_ini) or ctx.inicio, to_date(periodo_fin) or ctx.fin
        if fin < ini:
            raise ErrorNegocio("El período es inválido.")
        n = self.db.scalar("SELECT COUNT(*) FROM auditoria_encargo WHERE tipo=?", (tipo,), 0) + 1
        codigo = f"{'AF' if tipo == 'F' else 'AT'}-{ctx.gestion['anio']}-{n:03d}"
        with self.db.tx():
            eid = self.db.insert("auditoria_encargo", tipo=tipo, codigo=codigo, nombre=nombre.strip(), periodo_ini=ini.isoformat(), periodo_fin=fin.isoformat(), creado_por=ctx.usuario["id"],
                                 creado_en=datetime.now().isoformat(timespec="seconds"))
            self.db.insert("auditoria_equipo", encargo_id=eid, nombre=ctx.usuario["nombre"], rol="Socio", iniciales=self._iniciales(), usuario_id=ctx.usuario["id"])
            self.db.insert("auditoria_memorando", encargo_id=eid, terminos=self._terminos_defecto(tipo, ini, fin), normativa_aplicable=self._normativa_defecto(tipo), actualizado_en=datetime.now().isoformat(timespec="seconds"))
            for s, sig, col in P.MARCAS:
                self.db.insert("marca_auditoria", encargo_id=eid, simbolo=s, significado=sig, color=col)
            self.trail(eid, "encargo", eid, "CREAR", f"{codigo} {nombre}")
            if plantillas:
                self.memorando_guardar(eid, {})
                self.materialidad_calcular(eid, "INGRESOS" if tipo == "T" else "ACTIVO")
                self.riesgos_generar(eid)
                self.programas_generar(eid)
        return eid

    def _terminos_defecto(self, tipo, ini, fin) -> str:
        e = self.ctx.empresa
        if tipo == "F":
            return (f"Auditoría de los estados financieros de {e['razon_social']} (NIT {e.get('nit') or 's/n'}) por el período comprendido entre el {fdate(ini)} y el {fdate(fin)}, "
                    "con el objetivo de expresar una opinión sobre su razonable presentación de acuerdo con las Normas de Contabilidad Generalmente Aceptadas en Bolivia, "
                    "conforme a las Normas de Auditoría Generalmente Aceptadas y las Normas Internacionales de Auditoría (NIA) adoptadas.")
        return (f"Auditoría tributaria de {e['razon_social']} (NIT {e.get('nit') or 's/n'}) por el período {fdate(ini)} a {fdate(fin)}: verificar el cumplimiento de las obligaciones "
                "tributarias (IVA, IT, IUE, RC-IVA y retenciones), la bancarización y los deberes formales, y emitir el dictamen y los informes tributarios correspondientes.")

    def _normativa_defecto(self, tipo) -> str:
        if tipo == "F":
            return ("Normas de Auditoría del CAUB/CTNAC (NA 1 a 5) y NIA adoptadas (IFAC/IAASB); Normas de Contabilidad del CTNAC (NC 1 a 14: NC 1, NC 3, NC 6, NC 8, NC 11); "
                    "Código de Comercio (Libro Primero, Título III: contabilidad y libros obligatorios).")
        return ("Ley 843 (Texto Ordenado) y D.S. 21530 (IVA), 21531 (RC-IVA), 21532 (IT), 24051 (IUE); Ley 2492 (Código Tributario) y reglamentos; RND del SIN vigentes sobre "
                "dictamen tributario / información tributaria complementaria, facturación en línea y medios fehacientes de pago (bancarización).")

    def equipo(self, eid: int) -> list[dict]:
        self.encargo(eid)
        return self.db.query("SELECT * FROM auditoria_equipo WHERE encargo_id=? ORDER BY id", (eid,))

    def equipo_agregar(self, eid: int, nombre: str, rol: str, iniciales: str) -> int:
        self._abierto(eid)
        if not nombre.strip() or not iniciales.strip():
            raise ErrorNegocio("Nombre e iniciales son obligatorios.")
        i = self.db.insert("auditoria_equipo", encargo_id=eid, nombre=nombre.strip(), rol=rol, iniciales=iniciales.strip().upper()[:4])
        self.trail(eid, "equipo", i, "AGREGAR", nombre)
        return i

    # ---------------------------------------------------- planificación: MPA
    def memorando(self, eid: int) -> dict:
        self.encargo(eid)
        return self.db.one("SELECT * FROM auditoria_memorando WHERE encargo_id=?", (eid,))

    def memorando_guardar(self, eid: int, d: dict) -> dict:
        self._abierto(eid)
        m = self.memorando(eid)
        ri = d.get("riesgo_inherente", m["riesgo_inherente"])
        rc = d.get("riesgo_control", m["riesgo_control"])
        ra = float(d.get("riesgo_auditoria_aceptable", m["riesgo_auditoria_aceptable"]))
        if ri not in FACTOR_RIESGO or rc not in FACTOR_RIESGO:
            raise ErrorNegocio("Los niveles de riesgo deben ser B, M o A.")
        if not 0 < ra < 1:
            raise ErrorNegocio("El riesgo de auditoría aceptable debe estar entre 0 y 1 (ej. 0,05).")
        rd = round(ra / (FACTOR_RIESGO[ri] * FACTOR_RIESGO[rc]), 4)   # RA = RI × RC × RD
        vals = {k: d[k] for k in ("terminos", "negocio", "sector", "control_interno", "normativa_aplicable", "conclusion") if k in d}
        self.db.update("auditoria_memorando", m["id"], riesgo_inherente=ri, riesgo_control=rc, riesgo_auditoria_aceptable=ra, riesgo_deteccion=rd,
                       actualizado_en=datetime.now().isoformat(timespec="seconds"), **vals)
        self.trail(eid, "memorando", m["id"], "GUARDAR", f"RI={ri} RC={rc} RD={rd}")
        return self.memorando(eid)

    @staticmethod
    def interpretar_rd(rd: float) -> str:
        if rd >= 0.5:
            return "Riesgo de detección ALTO: se admiten pruebas sustantivas más limitadas."
        if rd >= 0.25:
            return "Riesgo de detección MEDIO: pruebas sustantivas de alcance normal."
        return "Riesgo de detección BAJO: ampliar el alcance de las pruebas sustantivas y la muestra."

    # -------------------------------------------------------- materialidad
    def _valor_base(self, base: str, hasta) -> float:
        est = self.ctx.estados
        if base == "ACTIVO":
            return est.balance_general(hasta, 1)["total_activo"]
        if base == "PATRIMONIO":
            return est.balance_general(hasta, 1)["total_patrimonio"]
        er = est.estado_resultados(self.ctx.inicio, hasta, 1)
        return {"INGRESOS": er["ventas"], "UTILIDAD_BRUTA": er["utilidad_bruta"], "UTILIDAD": er["antes_impuestos"]}[base]

    def materialidad_calcular(self, eid: int, base: str, pct_global: float | None = None, pct_desempeno: float = 75.0, pct_trivial: float = 5.0, justificacion: str = "") -> dict:
        e = self._abierto(eid)
        if base not in BASES:
            raise ErrorNegocio("Base de materialidad no válida.")
        valor = abs(self._valor_base(base, e["periodo_fin"]))
        pct = BASES[base][1] if pct_global is None else float(pct_global)
        if pct <= 0 or pct > 100:
            raise ErrorNegocio("El porcentaje de materialidad no es válido.")
        glob = r2(valor * pct / 100)
        des = r2(glob * pct_desempeno / 100)
        triv = r2(glob * pct_trivial / 100)
        vals = dict(base=base, valor_base=r2(valor), pct_global=pct, materialidad_global=glob, pct_desempeno=pct_desempeno, materialidad_desempeno=des, pct_trivial=pct_trivial,
                    umbral_trivial=triv, justificacion=justificacion or f"Se utiliza {BASES[base][0].lower()} como parámetro de referencia ({pct:g} %).", calculado_en=datetime.now().isoformat(timespec="seconds"))
        ex = self.db.one("SELECT id FROM auditoria_materialidad WHERE encargo_id=?", (eid,))
        if ex:
            self.db.update("auditoria_materialidad", ex["id"], **vals)
        else:
            self.db.insert("auditoria_materialidad", encargo_id=eid, **vals)
        self.trail(eid, "materialidad", ex["id"] if ex else None, "CALCULAR", f"{base} {pct:g}% => {glob}")
        return self.materialidad(eid)

    def materialidad(self, eid: int) -> dict | None:
        self.encargo(eid)
        return self.db.one("SELECT * FROM auditoria_materialidad WHERE encargo_id=?", (eid,))

    # --------------------------------------------------------------- riesgos
    def riesgos_generar(self, eid: int) -> int:
        e = self._abierto(eid)
        if self.db.scalar("SELECT COUNT(*) FROM auditoria_riesgo WHERE encargo_id=?", (eid,), 0):
            return 0
        prog = P.PROGRAMAS_F if e["tipo"] == "F" else P.PROGRAMAS_T
        m = self.memorando(eid)
        nivel_base = "A" if m["riesgo_inherente"] == "A" or m["riesgo_control"] == "A" else "M"
        n = 0
        for indice, (comp, _obj, pasos) in prog.items():
            aseveraciones = P.ASEVERACIONES
            for a in aseveraciones:
                rel = [p for p in pasos if a.split(" ")[0].lower() in p[1].lower()]
                if not rel and e["tipo"] == "F":
                    continue
                self.db.insert("auditoria_riesgo", encargo_id=eid, componente=comp, aseveracion=a, descripcion=f"Riesgo de incorrección material en «{a}» de {comp.lower()}.",
                               nivel=nivel_base if rel else "B", respuesta=rel[0][0] if rel else "", programa_ref=indice)
                n += 1
        self.trail(eid, "riesgo", None, "GENERAR", f"{n} filas")
        return n

    def riesgos(self, eid: int) -> list[dict]:
        self.encargo(eid)
        return self.db.query("SELECT * FROM auditoria_riesgo WHERE encargo_id=? ORDER BY programa_ref, id", (eid,))

    def riesgo_actualizar(self, rid: int, nivel: str, respuesta: str, descripcion: str | None = None) -> None:
        r = self.db.one("SELECT * FROM auditoria_riesgo WHERE id=?", (rid,))
        self._abierto(r["encargo_id"])
        if nivel not in FACTOR_RIESGO:
            raise ErrorNegocio("Nivel de riesgo no válido (B, M o A).")
        self.db.update("auditoria_riesgo", rid, nivel=nivel, respuesta=respuesta, **({"descripcion": descripcion} if descripcion else {}))
        self.trail(r["encargo_id"], "riesgo", rid, "ACTUALIZAR", f"{r['componente']}/{r['aseveracion']} -> {nivel}")

    # -------------------------------------------------------------- programas
    def programas_generar(self, eid: int) -> int:
        e = self._abierto(eid)
        if self.db.scalar("SELECT COUNT(*) FROM auditoria_programa WHERE encargo_id=?", (eid,), 0):
            return 0
        prog = P.PROGRAMAS_F if e["tipo"] == "F" else P.PROGRAMAS_T
        n = 0
        for indice, (comp, objetivo, pasos) in prog.items():
            pid = self.db.insert("auditoria_programa", encargo_id=eid, indice=indice, componente=comp, objetivo=objetivo)
            for i, (proc, ase, base) in enumerate(pasos, 1):
                self.db.insert("auditoria_programa_paso", programa_id=pid, nro=i, procedimiento=proc, aseveracion=ase, base_normativa=base)
                n += 1
        self.trail(eid, "programa", None, "GENERAR", f"{n} procedimientos")
        return n

    def programas(self, eid: int) -> list[dict]:
        self.encargo(eid)
        out = self.db.query("SELECT * FROM auditoria_programa WHERE encargo_id=? ORDER BY id", (eid,))
        for p in out:
            p["pasos"] = self.db.query("SELECT * FROM auditoria_programa_paso WHERE programa_id=? ORDER BY nro", (p["id"],))
        return out

    def paso_actualizar(self, paso_id: int, estado: str, conclusion: str = "", referencia_pt: str = "", responsable: str | None = None) -> None:
        r = self.db.one("SELECT p.encargo_id FROM auditoria_programa_paso s JOIN auditoria_programa p ON p.id=s.programa_id WHERE s.id=?", (paso_id,))
        self._abierto(r["encargo_id"])
        if estado not in ("P", "E", "R", "N"):
            raise ErrorNegocio("Estado de procedimiento no válido (P pendiente, E en ejecución, R realizado, N no aplica).")
        self.db.update("auditoria_programa_paso", paso_id, estado=estado, conclusion=conclusion, referencia_pt=referencia_pt, responsable=responsable or self._iniciales(),
                       fecha=datetime.now().date().isoformat())
        self.trail(r["encargo_id"], "programa_paso", paso_id, "ACTUALIZAR", f"estado={estado}")

    def avance(self, eid: int) -> dict:
        t = self.db.one("SELECT COUNT(*) n, SUM(CASE WHEN s.estado IN ('R','N') THEN 1 ELSE 0 END) h FROM auditoria_programa_paso s JOIN auditoria_programa p ON p.id=s.programa_id WHERE p.encargo_id=?", (eid,))
        n, h = t["n"] or 0, t["h"] or 0
        return {"total": n, "hechos": h, "pct": round(h / n * 100, 1) if n else 0.0}

    # -------------------------------------------------- cédulas y papeles de trabajo
    def _saldo_prefijos(self, prefijos: list[str], hasta, naturaleza: str) -> float:
        sal = self.ctx.estados._saldos_a(hasta)
        plan = {c["codigo"]: c["id"] for c in self.db.query("SELECT id, codigo FROM cuenta")}
        tot = 0.0
        for pf in prefijos:
            cid = plan.get(pf)
            if cid is not None:
                tot += sal.get(cid, 0.0)
        return r2(tot if naturaleza == "D" else -tot)

    def sumarias_generar(self, eid: int) -> int:
        """Cédulas sumarias (indexadas A,B,C… activos; AA,BB… pasivos) conectadas a los saldos del sistema contable, con sus analíticas."""
        e = self._abierto(eid)
        catalogo = P.SUMARIAS_F if e["tipo"] == "F" else P.SUMARIAS_T
        sal = self.ctx.estados._saldos_a(e["periodo_fin"])
        n = 0
        for indice, titulo, prefijos, nat in catalogo:
            if self.db.scalar("SELECT COUNT(*) FROM cedula_sumaria WHERE encargo_id=? AND indice=?", (eid, indice), 0):
                continue
            saldo = self._saldo_prefijos(prefijos, e["periodo_fin"], nat)
            sid = self.db.insert("cedula_sumaria", encargo_id=eid, indice=indice, titulo=titulo, cuentas=",".join(prefijos), naturaleza=nat, saldo_sistema=saldo, saldo_auditado=saldo)
            k = 0
            for c in self.db.query("SELECT * FROM cuenta WHERE es_movimiento=1 ORDER BY codigo"):
                if any(c["codigo"] == pf or c["codigo"].startswith(pf + ".") or (c["codigo"].split(".")[0] == pf and len(pf) == 1) for pf in prefijos) and abs(sal.get(c["id"], 0.0)) >= 0.005:
                    k += 1
                    v = sal.get(c["id"], 0.0)
                    v = v if nat == "D" else -v
                    self.db.insert("cedula_analitica", sumaria_id=sid, indice=f"{indice}-{k}", cuenta_codigo=c["codigo"], concepto=c["nombre"], saldo_libros=r2(v))
            n += 1
        self.trail(eid, "cedula_sumaria", None, "GENERAR", f"{n} cédulas")
        return n

    def sumarias(self, eid: int) -> list[dict]:
        self.encargo(eid)
        return self.db.query("SELECT * FROM cedula_sumaria WHERE encargo_id=? ORDER BY id", (eid,))

    def analiticas(self, sumaria_id: int) -> list[dict]:
        return self.db.query("SELECT * FROM cedula_analitica WHERE sumaria_id=? ORDER BY id", (sumaria_id,))

    def analitica_guardar(self, aid: int, saldo_verificado: float | None, marcas: str, comentario: str = "", referencia: str = "") -> None:
        a = self.db.one("SELECT a.*, s.encargo_id FROM cedula_analitica a JOIN cedula_sumaria s ON s.id=a.sumaria_id WHERE a.id=?", (aid,))
        self._abierto(a["encargo_id"])
        validas = {m["simbolo"] for m in self.db.query("SELECT simbolo FROM marca_auditoria WHERE encargo_id=?", (a["encargo_id"],))}
        ms = [x for x in (marcas or "").replace(" ", "").split(",") if x]
        mal = [x for x in ms if x not in validas]
        if mal:
            raise ErrorNegocio(f"Marca(s) no definida(s): {', '.join(mal)}. Use la leyenda del encargo.")
        dif = None if saldo_verificado is None else r2(saldo_verificado - a["saldo_libros"])
        self.db.update("cedula_analitica", aid, saldo_verificado=saldo_verificado, diferencia=dif, marcas=",".join(ms), comentario=comentario, referencia=referencia)
        self.trail(a["encargo_id"], "cedula_analitica", aid, "ACTUALIZAR", f"{a['indice']} marcas={','.join(ms)} dif={dif}")

    def cedula_firmar(self, sumaria_id: int, rol: str, conclusion: str | None = None) -> None:
        s = self.db.one("SELECT * FROM cedula_sumaria WHERE id=?", (sumaria_id,))
        self._abierto(s["encargo_id"])
        ahora = datetime.now().date().isoformat()
        ini = self._iniciales()
        if rol == "PREPARADO":
            self.db.update("cedula_sumaria", sumaria_id, preparado_por=ini, preparado_en=ahora, **({"conclusion": conclusion} if conclusion is not None else {}))
        elif rol == "REVISADO":
            if not s["preparado_por"]:
                raise ErrorNegocio("La cédula debe ser preparada antes de ser revisada.")
            if s["preparado_por"] == ini and len(self.equipo(s["encargo_id"])) > 1:
                raise ErrorNegocio("La revisión debe realizarla una persona distinta de quien preparó la cédula.")
            self.db.update("cedula_sumaria", sumaria_id, revisado_por=ini, revisado_en=ahora)
        else:
            raise ErrorNegocio("Rol de firma no válido.")
        self.trail(s["encargo_id"], "cedula_sumaria", sumaria_id, "FIRMA_" + rol, f"{s['indice']} por {ini}")

    def recalcular_sumarias(self, eid: int) -> None:
        """Actualiza la columna de ajustes con los asientos ACEPTADOS (y reclasificaciones) y el saldo auditado."""
        e = self._abierto(eid)
        planes = {c["id"]: c["codigo"] for c in self.db.query("SELECT id, codigo FROM cuenta")}
        det = self.db.query("SELECT d.cuenta_id, d.debe, d.haber, a.tipo FROM asiento_ajuste_det d JOIN asiento_ajuste_propuesto a ON a.id=d.ajuste_id WHERE a.encargo_id=? AND a.estado='ACEPTADO'", (eid,))
        for s in self.sumarias(eid):
            aj = rc = 0.0
            pref = s["cuentas"].split(",")
            for d in det:
                cod = planes[d["cuenta_id"]]
                if any(cod == p or cod.startswith(p + ".") for p in pref):
                    m = (d["debe"] - d["haber"]) if s["naturaleza"] == "D" else (d["haber"] - d["debe"])
                    if d["tipo"] == "AJU":
                        aj += m
                    else:
                        rc += m
            self.db.update("cedula_sumaria", s["id"], ajustes=r2(aj), reclasificaciones=r2(rc), saldo_auditado=r2(s["saldo_sistema"] + aj + rc))
        self.trail(eid, "cedula_sumaria", None, "RECALCULAR", "ajustes aceptados")

    # ---------------------------------------------------------------- pruebas
    def guardar_prueba(self, eid: int, clave: str, resultado: dict, indice_pt: str = "", parametros: dict | None = None) -> int:
        self._abierto(eid)
        i = self.db.insert("auditoria_prueba", encargo_id=eid, clave=clave, titulo=resultado.get("titulo", clave), parametros=json.dumps(parametros or {}, default=str, ensure_ascii=False),
                           resultado=json.dumps(resultado, default=str, ensure_ascii=False), conforme=1 if resultado.get("conforme") else 0, indice_pt=indice_pt,
                           ejecutado_por=self._iniciales(), ejecutado_en=datetime.now().isoformat(timespec="seconds"))
        self.trail(eid, "prueba", i, "GUARDAR", f"{clave} conforme={bool(resultado.get('conforme'))}")
        return i

    def pruebas(self, eid: int) -> list[dict]:
        self.encargo(eid)
        out = self.db.query("SELECT * FROM auditoria_prueba WHERE encargo_id=? ORDER BY id", (eid,))
        for p in out:
            p["datos"] = json.loads(p["resultado"])
        return out

    # --------------------------------------------------------------- hallazgos
    def hallazgo_guardar(self, eid: int, d: dict) -> int:
        self._abierto(eid)
        for k, et in (("condicion", "Condición"), ("criterio", "Criterio")):
            if not (d.get(k) or "").strip():
                raise ErrorNegocio(f"El hallazgo requiere «{et}» (los 4 elementos: condición, criterio, causa y efecto).")
        for k, et in (("causa", "Causa"), ("efecto", "Efecto")):
            if not (d.get(k) or "").strip():
                raise ErrorNegocio(f"El hallazgo requiere «{et}».")
        if d.get("nivel", "M") not in FACTOR_RIESGO:
            raise ErrorNegocio("Nivel de riesgo no válido.")
        vals = dict(componente=d.get("componente"), condicion=d["condicion"].strip(), criterio=d["criterio"].strip(), causa=d["causa"].strip(), efecto=d["efecto"].strip(),
                    recomendacion=d.get("recomendacion"), descargo_gerencia=d.get("descargo_gerencia"), nivel=d.get("nivel", "M"), impacto_monto=r2(d.get("impacto_monto") or 0),
                    estado=d.get("estado", "ABIERTO"), referencia_pt=d.get("referencia_pt"))
        if d.get("id"):
            self.db.update("hallazgo_auditoria", d["id"], **vals)
            self.trail(eid, "hallazgo", d["id"], "ACTUALIZAR", vals["condicion"][:80])
            return d["id"]
        n = self.db.scalar("SELECT COUNT(*) FROM hallazgo_auditoria WHERE encargo_id=?", (eid,), 0) + 1
        i = self.db.insert("hallazgo_auditoria", encargo_id=eid, codigo=f"H-{n:02d}", creado_en=datetime.now().isoformat(timespec="seconds"), **vals)
        self.trail(eid, "hallazgo", i, "CREAR", vals["condicion"][:80])
        return i

    def hallazgos(self, eid: int) -> list[dict]:
        self.encargo(eid)
        return self.db.query("SELECT * FROM hallazgo_auditoria WHERE encargo_id=? ORDER BY id", (eid,))

    # ----------------------------------------------------------------- ajustes
    def ajuste_guardar(self, eid: int, tipo: str, descripcion: str, lineas: list[dict], hallazgo_id: int | None = None) -> int:
        """lineas: [{cuenta_id, debe, haber, glosa}]. AJU = ajuste; REC = reclasificación."""
        self._abierto(eid)
        if tipo not in ("AJU", "REC"):
            raise ErrorNegocio("Tipo de asiento no válido.")
        if len(lineas) < 2:
            raise ErrorNegocio("El asiento propuesto necesita al menos dos líneas.")
        d = r2(sum(l.get("debe") or 0 for l in lineas))
        h = r2(sum(l.get("haber") or 0 for l in lineas))
        if abs(d - h) > 0.005:
            raise ErrorNegocio(f"El asiento propuesto no cuadra (debe {d:,.2f} / haber {h:,.2f}).")
        efecto = 0.0
        for l in lineas:
            c = self.ctx.cuentas.obtener(l["cuenta_id"])
            if c["tipo"] == "I":
                efecto += (l.get("haber") or 0) - (l.get("debe") or 0)
            elif c["tipo"] == "G":
                efecto -= (l.get("debe") or 0) - (l.get("haber") or 0)
        n = self.db.scalar("SELECT COALESCE(MAX(numero),0) FROM asiento_ajuste_propuesto WHERE encargo_id=?", (eid,), 0) + 1
        with self.db.tx():
            aid = self.db.insert("asiento_ajuste_propuesto", encargo_id=eid, numero=n, tipo=tipo, descripcion=descripcion.strip(), hallazgo_id=hallazgo_id, efecto_resultado=r2(efecto),
                                 creado_en=datetime.now().isoformat(timespec="seconds"))
            for l in lineas:
                self.db.insert("asiento_ajuste_det", ajuste_id=aid, cuenta_id=l["cuenta_id"], debe=r2(l.get("debe") or 0), haber=r2(l.get("haber") or 0), glosa=l.get("glosa"))
            self.trail(eid, "ajuste", aid, "PROPONER", f"{tipo}-{n} efecto en resultados {r2(efecto)}")
        return aid

    def ajustes(self, eid: int) -> list[dict]:
        self.encargo(eid)
        out = self.db.query("SELECT * FROM asiento_ajuste_propuesto WHERE encargo_id=? ORDER BY numero", (eid,))
        for a in out:
            a["lineas"] = self.db.query("SELECT d.*, c.codigo, c.nombre FROM asiento_ajuste_det d JOIN cuenta c ON c.id=d.cuenta_id WHERE d.ajuste_id=? ORDER BY d.id", (a["id"],))
        return out

    def ajuste_estado(self, aid: int, estado: str) -> None:
        a = self.db.one("SELECT * FROM asiento_ajuste_propuesto WHERE id=?", (aid,))
        self._abierto(a["encargo_id"])
        if estado not in ("PROPUESTO", "ACEPTADO", "NO_CORREGIDO"):
            raise ErrorNegocio("Estado no válido.")
        self.db.update("asiento_ajuste_propuesto", aid, estado=estado)
        self.trail(a["encargo_id"], "ajuste", aid, "ESTADO", estado)
        self.recalcular_sumarias(a["encargo_id"])

    def resumen_desvios(self, eid: int) -> dict:
        """Cédula de resumen de desvíos y ajustes: aceptados vs. no corregidos, y su impacto frente a la materialidad."""
        mat = self.materialidad(eid)
        filas = self.ajustes(eid)
        acept = r2(sum(a["efecto_resultado"] for a in filas if a["estado"] == "ACEPTADO"))
        nocor = r2(sum(a["efecto_resultado"] for a in filas if a["estado"] == "NO_CORREGIDO"))
        trivial = mat["umbral_trivial"] if mat else 0.0
        no_triviales = [a for a in filas if a["estado"] == "NO_CORREGIDO" and abs(a["efecto_resultado"]) > trivial]
        acum = r2(sum(abs(a["efecto_resultado"]) for a in no_triviales))
        glob = mat["materialidad_global"] if mat else 0.0
        des = mat["materialidad_desempeno"] if mat else 0.0
        veredicto = ("No supera la materialidad de desempeño" if acum < des else "Supera la materialidad de desempeño pero no la global" if acum < glob
                     else "SUPERA la materialidad global: evaluar opinión modificada")
        return {"ajustes": filas, "efecto_aceptados": acept, "efecto_no_corregidos": nocor, "no_corregidos_no_triviales": acum, "materialidad_global": glob, "materialidad_desempeno": des,
                "umbral_trivial": trivial, "veredicto": veredicto}

    def sugerir_opinion(self, eid: int) -> tuple[str, str]:
        """Sugerencia (no vinculante) del tipo de opinión según NIA 705, a partir de errores no corregidos y hallazgos críticos."""
        r = self.resumen_desvios(eid)
        h = [x for x in self.hallazgos(eid) if x["estado"] != "CERRADO" and x["nivel"] == "A"]
        limit = [x for x in h if (x["componente"] or "").upper() == "LIMITACION"]
        if limit:
            return "ABSTENCION", "Existen limitaciones al alcance de nivel alto que impiden obtener evidencia suficiente (NIA 705)."
        glob = r["materialidad_global"] or 1
        acum = r["no_corregidos_no_triviales"]
        if acum >= 3 * glob:
            return "ADVERSA", "Las incorrecciones no corregidas son materiales y generalizadas (≥ 3 veces la materialidad global)."
        if acum >= glob:
            return "SALVEDAD", "Las incorrecciones no corregidas superan la materialidad global pero no son generalizadas."
        return "LIMPIA", "Las incorrecciones no corregidas no superan la materialidad global."

    # ---------------------------------------------------------------- cierre
    def _canon(self, eid: int) -> str:
        """Representación canónica de TODOS los papeles de trabajo del encargo (base del SHA-256)."""
        data: dict[str, list] = {}
        e = self.db.one("SELECT id, tipo, codigo, nombre, periodo_ini, periodo_fin, creado_por, creado_en FROM auditoria_encargo WHERE id=?", (eid,))
        data["encargo"] = [e]
        for t in ("auditoria_equipo", "auditoria_memorando", "auditoria_materialidad", "auditoria_riesgo", "auditoria_programa", "marca_auditoria", "cedula_sumaria", "hallazgo_auditoria",
                  "asiento_ajuste_propuesto", "gasto_no_deducible_iue", "anexo_tributario_itc", "auditoria_prueba", "auditoria_dictamen"):
            data[t] = self.db.query(f"SELECT * FROM {t} WHERE encargo_id=? ORDER BY id", (eid,))
        data["auditoria_programa_paso"] = self.db.query("SELECT s.* FROM auditoria_programa_paso s JOIN auditoria_programa p ON p.id=s.programa_id WHERE p.encargo_id=? ORDER BY s.id", (eid,))
        data["cedula_analitica"] = self.db.query("SELECT a.* FROM cedula_analitica a JOIN cedula_sumaria s ON s.id=a.sumaria_id WHERE s.encargo_id=? ORDER BY a.id", (eid,))
        data["asiento_ajuste_det"] = self.db.query("SELECT d.* FROM asiento_ajuste_det d JOIN asiento_ajuste_propuesto a ON a.id=d.ajuste_id WHERE a.encargo_id=? ORDER BY d.id", (eid,))
        return json.dumps(data, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))

    def calcular_hash(self, eid: int) -> str:
        return hashlib.sha256(self._canon(eid).encode("utf-8")).hexdigest()

    def cerrar_encargo(self, eid: int, clave: str) -> str:
        """Cierre y firma: congela los papeles de trabajo (solo lectura por disparadores) y guarda la huella SHA-256 de la evidencia."""
        e = self._abierto(eid)
        if not self.db.scalar("SELECT COUNT(*) FROM auditoria_dictamen WHERE encargo_id=?", (eid,), 0):
            raise ErrorNegocio("Antes de cerrar debe emitir el dictamen o informe del encargo.")
        u = self.ctx.sistema.db.one("SELECT hash, salt, login FROM usuario WHERE id=?", (self.ctx.usuario["id"],))
        if not verificar(clave or "", u["salt"], u["hash"]):
            raise ErrorNegocio("La contraseña de firma no es correcta.")
        self.trail(eid, "encargo", eid, "CERRAR", f"firmado por {u['login']}")
        h = self.calcular_hash(eid)
        self.db.execute("UPDATE auditoria_encargo SET estado='CERRADO', fase='CERRADO', cerrado_por=?, cerrado_en=?, sha256=? WHERE id=?",
                        (u["login"], datetime.now().isoformat(timespec="seconds"), h, eid))
        self.ctx.auditar("Auditoría", "CERRAR_ENCARGO", f"{e['codigo']} sha256={h[:16]}…")
        return h

    def verificar_integridad(self, eid: int) -> dict:
        e = self.encargo(eid)
        actual = self.calcular_hash(eid)
        ok = e["estado"] == "CERRADO" and actual == e["sha256"]
        return {"cerrado": e["estado"] == "CERRADO", "sha256_guardado": e["sha256"], "sha256_actual": actual, "integro": ok, "bitacora_integra": self.verificar_trail()}

    # ------------------------------------------------------------- dictámenes
    def dictamen_guardar(self, eid: int, clase: str, opinion: str, texto: str, kam: str = "", enfasis: str = "", firmante: str = "") -> int:
        self._abierto(eid)
        if not texto.strip():
            raise ErrorNegocio("El texto del dictamen no puede estar vacío.")
        i = self.db.insert("auditoria_dictamen", encargo_id=eid, clase=clase, opinion=opinion, texto=texto, kam=kam, enfasis=enfasis, fecha=datetime.now().date().isoformat(),
                           firmante=firmante or self.ctx.usuario["nombre"], creado_en=datetime.now().isoformat(timespec="seconds"))
        self.trail(eid, "dictamen", i, "EMITIR", f"{clase} {opinion}")
        return i

    def dictamenes(self, eid: int) -> list[dict]:
        self.encargo(eid)
        return self.db.query("SELECT * FROM auditoria_dictamen WHERE encargo_id=? ORDER BY id", (eid,))
