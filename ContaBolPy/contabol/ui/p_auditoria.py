"""Pantallas de los módulos de Auditoría Financiera (MAF) y Tributaria (MAI): Planificación, Ejecución y Comunicación."""
from __future__ import annotations

from PySide6.QtWidgets import (QDialog, QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QPlainTextEdit, QSplitter, QTabWidget, QVBoxLayout, QWidget)

from ..util import fmt
from . import tema
from .base import Pantalla
from .formularios import Campo, FormDialog
from .widgets import Columna, Combo, CampoImporte, TablaDatos, aviso, boton, confirmar, hbox, info, intentar

NIVELES = [("B", "Bajo"), ("M", "Medio"), ("A", "Alto")]
BASES = [("ACTIVO", "Activo total"), ("INGRESOS", "Ingresos operativos"), ("UTILIDAD_BRUTA", "Utilidad bruta"), ("PATRIMONIO", "Patrimonio"), ("UTILIDAD", "Resultado antes de impuestos")]
ESTADOS_PASO = [("P", "Pendiente"), ("E", "En ejecución"), ("R", "Realizado"), ("N", "No aplica")]


def _cols_de(filas: list[dict], max_cols: int = 10) -> list[Columna]:
    if not filas:
        return [Columna("sin_datos", "Sin datos", 200, estirar=True)]
    out = []
    for k, v in list(filas[0].items())[:max_cols]:
        if k.endswith("_id") or isinstance(v, (dict, list)):
            continue
        out.append(Columna(k, k.replace("_", " ").capitalize(), 120 if not isinstance(v, str) else 180, "money" if isinstance(v, float) else "txt", estirar=False))
    return out


class _Tabla(QWidget):
    """Tabla genérica con título y pie de conclusión."""

    def __init__(self, columnas: list[Columna], titulo: str = ""):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.titulo = QLabel(titulo)
        self.titulo.setObjectName("h2")
        self.tabla = TablaDatos(columnas)
        self.pie = QLabel("")
        self.pie.setWordWrap(True)
        if titulo:
            lay.addWidget(self.titulo)
        lay.addWidget(self.tabla, 1)
        lay.addWidget(self.pie)

    def cargar(self, filas, pie=""):
        self.tabla.cargar(filas)
        self.pie.setText(pie)


class AuditoriaPantalla(Pantalla):
    """tipo='F' (financiera, MAF) o 'T' (tributaria, MAI)."""

    def __init__(self, ctx, tipo: str = "F", ventana=None):
        self.tipo = tipo
        self.titulo = "Auditoría financiera (MAF)" if tipo == "F" else "Auditoría tributaria (MAI)"
        self.subtitulo = ("Planificación, ejecución con cédulas sumarias y comunicación de resultados (NIA)." if tipo == "F"
                          else "Conciliaciones IVA/IT, bancarización, depuración del IUE, anexos ITC y contingencias.")
        super().__init__(ctx, ventana)
        self.a = ctx.auditoria
        self.eid: int | None = None
        self.cb = Combo()
        self.cb.currentIndexChanged.connect(self._cambio_encargo)
        b_nuevo, b_cerrar, b_ver, b_inf = boton("Nuevo encargo", "primario"), boton("Cerrar y firmar"), boton("Verificar integridad"), boton("Informes…")
        b_nuevo.clicked.connect(self.nuevo)
        b_cerrar.clicked.connect(self.cerrar)
        b_ver.clicked.connect(self.verificar)
        b_inf.clicked.connect(self.informes)
        self.cuerpo.addLayout(hbox(QLabel("Encargo:"), self.cb, None, b_nuevo, b_inf, b_ver, b_cerrar))
        self.estado = QLabel("")
        self.estado.setWordWrap(True)
        self.cuerpo.addWidget(self.estado)
        self.tabs = QTabWidget()
        self.cuerpo.addWidget(self.tabs, 1)
        self._construir_tabs()
        self.refrescar()

    # --------------------------------------------------------------- estructura
    def _construir_tabs(self):
        self.tabs.addTab(self._tab_planificacion(), "A · Planificación")
        self.tabs.addTab(self._tab_programas(), "A · Programas")
        if self.tipo == "F":
            self.tabs.addTab(self._tab_cedulas(), "B · Cédulas")
            self.tabs.addTab(self._tab_pruebas_f(), "B · Pruebas sustantivas")
        else:
            self.tabs.addTab(self._tab_pruebas_t(), "B · Pruebas tributarias")
            self.tabs.addTab(self._tab_iue(), "B · Depuración IUE")
            self.tabs.addTab(self._tab_anexos(), "B · Anexos ITC")
        self.tabs.addTab(self._tab_hallazgos(), "C · Hallazgos")
        self.tabs.addTab(self._tab_ajustes(), "C · Ajustes y desvíos")
        self.tabs.addTab(self._tab_dictamen(), "C · Dictamen / informe")

    def _enc(self) -> int | None:
        if self.eid is None:
            aviso(self, "Cree o seleccione un encargo de auditoría.")
        return self.eid

    def refrescar(self):
        actual = self.eid
        self.cb.blockSignals(True)
        enc = self.a.listar(self.tipo)
        self.cb.cargar([(e["id"], f"{e['codigo']} · {e['nombre']}" + (" (cerrado)" if e["estado"] == "CERRADO" else "")) for e in enc])
        if actual:
            self.cb.set_valor(actual)
        self.cb.blockSignals(False)
        self.eid = self.cb.valor()
        self._cargar_todo()

    def _cambio_encargo(self):
        self.eid = self.cb.valor()
        self._cargar_todo()

    def _cargar_todo(self):
        if self.eid is None:
            self.estado.setText("No hay encargos. Use «Nuevo encargo» para iniciar la planificación.")
            return
        e = self.a.encargo(self.eid)
        av = self.a.avance(self.eid)
        t = f"Período {e['periodo_ini']} al {e['periodo_fin']} · Avance de programas: {av['pct']} % ({av['hechos']}/{av['total']})"
        if e["estado"] == "CERRADO":
            t += f"  —  CERRADO por {e['cerrado_por']} el {e['cerrado_en']}  ·  SHA-256 {e['sha256'][:24]}…  (solo lectura)"
        self.estado.setText(t)
        self.estado.setStyleSheet(f"color:{tema.ROJO if e['estado'] == 'CERRADO' else '#5B6675'};")
        for fn in self._cargadores:
            fn()

    _cargadores: list = []

    def _reg(self, fn):
        if "_cargadores" not in self.__dict__:
            self._cargadores = []
        self._cargadores.append(fn)

    # ------------------------------------------------------------------ acciones
    def nuevo(self):
        def guardar(v):
            self.eid = self.a.crear_encargo(self.tipo, v["nombre"], v["ini"], v["fin"])
            self.ctx.auditar("Auditoría", "CREAR_ENCARGO", v["nombre"])
        dlg = FormDialog("Nuevo encargo de auditoría", [Campo("nombre", "Nombre del encargo", obligatorio=True, ancho=2, defecto=f"Auditoría {'de estados financieros' if self.tipo == 'F' else 'tributaria'} {self.ctx.gestion['anio']}"),
                                                        Campo("ini", "Período desde", "date", defecto=self.ctx.inicio), Campo("fin", "Período hasta", "date", defecto=self.ctx.fin)],
                         guardar=guardar, ayuda="Se generan automáticamente el memorándum, materialidad, matriz de riesgos y programas de auditoría.", parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.refrescar()

    def cerrar(self):
        if not self._enc():
            return
        clave, ok = QInputDialog.getText(self, "Cierre y firma", "Reingrese su contraseña para firmar y bloquear los papeles de trabajo (solo lectura):", QLineEdit.Password)
        if not ok:
            return
        if not confirmar(self, "Al cerrar, los papeles de trabajo quedan INMUTABLES y se registra su huella SHA-256. ¿Continuar?", "Cerrar encargo", peligro=True):
            return
        r, h = intentar(self, self.a.cerrar_encargo, self.eid, clave)
        if r:
            info(self, f"Encargo cerrado.\n\nHuella SHA-256:\n{h}")
            self.refrescar()

    def verificar(self):
        if not self._enc():
            return
        r = self.a.verificar_integridad(self.eid)
        if not r["cerrado"]:
            info(self, "El encargo aún está abierto: la huella se genera al cerrarlo.\nBitácora encadenada: " + ("íntegra" if r["bitacora_integra"] else "ALTERADA"))
        elif r["integro"]:
            info(self, "Integridad VERIFICADA: los papeles de trabajo no han sido alterados desde el cierre.\n\nSHA-256:\n" + r["sha256_actual"])
        else:
            aviso(self, "¡ALERTA! Los papeles de trabajo no coinciden con la huella firmada.\n\nGuardada: " + r["sha256_guardado"] + "\nActual:   " + r["sha256_actual"])

    def informes(self):
        if not self._enc():
            return
        from .reportes_ui import abrir_informe
        ids = (["aud_mpa", "aud_riesgos", "aud_programas", "aud_sumarias", "aud_pruebas", "aud_hallazgos", "aud_desvios", "aud_dictamen", "aud_trail"] if self.tipo == "F"
               else ["aud_mpa", "aud_programas", "aud_iva_it", "aud_bancarizacion", "aud_iue", "aud_anexos_itc", "aud_contingencias", "aud_hallazgos", "aud_dictamen", "aud_trail"])
        from ..reports import catalogo
        ops = [(i, catalogo.buscar(i).titulo) for i in ids]
        dlg = FormDialog("Informes del encargo", [Campo("informe", "Informe", "combo", opciones=ops, ancho=2)], texto_ok="Ver informe", parent=self, ancho=480)
        if dlg.exec() == QDialog.Accepted:
            abrir_informe(self.ventana or self, self.ctx, dlg.valores()["informe"], {"encargo": self.eid}, False)

    # ------------------------------------------------------- A · planificación
    def _tab_planificacion(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.t_term, self.t_neg, self.t_ci = QPlainTextEdit(), QPlainTextEdit(), QPlainTextEdit()
        for t, l in ((self.t_term, "Términos del encargo"), (self.t_neg, "Comprensión del negocio y del sector"), (self.t_ci, "Control interno")):
            t.setPlaceholderText(l)
            t.setMaximumHeight(70)
            lay.addWidget(QLabel(l))
            lay.addWidget(t)
        self.c_ri, self.c_rc = Combo(NIVELES), Combo(NIVELES)
        self.e_ra = QLineEdit("0,05")
        self.l_rd = QLabel("")
        b = boton("Guardar memorándum y calcular RD", "primario")
        b.clicked.connect(self._guardar_mpa)
        lay.addLayout(hbox(QLabel("Riesgo inherente"), self.c_ri, QLabel("Riesgo de control"), self.c_rc, QLabel("Riesgo aceptable (RA)"), self.e_ra, b, None))
        lay.addWidget(self.l_rd)
        self.c_base = Combo(BASES)
        self.e_pct = QLineEdit("")
        self.e_pct.setPlaceholderText("% (vacío = sugerido)")
        bm = boton("Calcular materialidad")
        bm.clicked.connect(self._calc_mat)
        self.l_mat = QLabel("")
        lay.addLayout(hbox(QLabel("Base de materialidad"), self.c_base, self.e_pct, bm, None))
        lay.addWidget(self.l_mat)
        self.t_riesgos = _Tabla([Columna("programa_ref", "Prog.", 50), Columna("componente", "Componente", 150), Columna("aseveracion", "Aseveración", 150), Columna("descripcion", "Riesgo", 300, estirar=True),
                                 Columna("nivel_t", "Nivel", 70), Columna("respuesta", "Respuesta de auditoría", 300)], "Matriz de riesgos por aseveración (doble clic para editar)")
        self.t_riesgos.tabla.doble_clic.connect(self._editar_riesgo)
        lay.addWidget(self.t_riesgos, 1)
        self._reg(self._cargar_mpa)
        return w

    def _cargar_mpa(self):
        m = self.a.memorando(self.eid)
        self.t_term.setPlainText(m["terminos"] or "")
        self.t_neg.setPlainText(m["negocio"] or "")
        self.t_ci.setPlainText(m["control_interno"] or "")
        self.c_ri.set_valor(m["riesgo_inherente"])
        self.c_rc.set_valor(m["riesgo_control"])
        self.e_ra.setText(str(m["riesgo_auditoria_aceptable"]).replace(".", ","))
        self.l_rd.setText(f"RD = RA / (RI × RC) = {m['riesgo_deteccion']:.2%}.  {self.a.interpretar_rd(m['riesgo_deteccion'])}")
        mt = self.a.materialidad(self.eid)
        if mt:
            self.c_base.set_valor(mt["base"])
            self.l_mat.setText(f"Base {fmt(mt['valor_base'])} · Global {fmt(mt['materialidad_global'])} ({mt['pct_global']:g} %) · Desempeño {fmt(mt['materialidad_desempeno'])} · Trivial {fmt(mt['umbral_trivial'])}")
        rs = self.a.riesgos(self.eid)
        for r in rs:
            r["nivel_t"] = dict(NIVELES)[r["nivel"]]
        self.t_riesgos.cargar(rs)

    def _guardar_mpa(self):
        if not self._enc():
            return
        ra = float(self.e_ra.text().replace(",", ".") or 0.05)
        ok, _ = intentar(self, self.a.memorando_guardar, self.eid, {"terminos": self.t_term.toPlainText(), "negocio": self.t_neg.toPlainText(), "control_interno": self.t_ci.toPlainText(),
                                                                      "riesgo_inherente": self.c_ri.valor(), "riesgo_control": self.c_rc.valor(), "riesgo_auditoria_aceptable": ra})
        if ok:
            self._cargar_mpa()

    def _calc_mat(self):
        if not self._enc():
            return
        pct = float(self.e_pct.text().replace(",", ".")) if self.e_pct.text().strip() else None
        ok, _ = intentar(self, self.a.materialidad_calcular, self.eid, self.c_base.valor(), pct)
        if ok:
            self._cargar_mpa()

    def _editar_riesgo(self, f):
        FormDialog("Riesgo por aseveración", [Campo("nivel", "Nivel de riesgo", "combo", opciones=NIVELES), Campo("respuesta", "Respuesta de auditoría", "memo", ancho=2)], {"nivel": f["nivel"], "respuesta": f["respuesta"]},
                   guardar=lambda v: self.a.riesgo_actualizar(f["id"], v["nivel"], v["respuesta"]), ayuda=f"{f['componente']} · {f['aseveracion']}", parent=self).exec()
        self._cargar_mpa()

    # --------------------------------------------------------- A · programas
    def _tab_programas(self):
        self.t_prog = _Tabla([Columna("prog", "Prog.", 50), Columna("nro", "Nº", 40), Columna("procedimiento", "Procedimiento", 420, estirar=True), Columna("aseveracion", "Aseveración", 130),
                              Columna("base_normativa", "Base", 90), Columna("estado_t", "Estado", 100), Columna("referencia_pt", "Ref. PT", 70), Columna("responsable", "Resp.", 60)],
                             "Programas de auditoría por componente (doble clic para registrar el avance)")
        self.t_prog.tabla.doble_clic.connect(self._editar_paso)
        self._reg(self._cargar_prog)
        return self.t_prog

    def _cargar_prog(self):
        filas = []
        for p in self.a.programas(self.eid):
            filas.append({"prog": p["indice"], "nro": "", "procedimiento": f"{p['componente'].upper()} — {p['objetivo']}", "aseveracion": "", "base_normativa": "", "estado_t": "", "referencia_pt": "", "responsable": ""})
            for s in p["pasos"]:
                filas.append({**s, "prog": "", "estado_t": dict(ESTADOS_PASO)[s["estado"]], "es_paso": True})
        self.t_prog.cargar(filas)

    def _editar_paso(self, f):
        if not f.get("es_paso"):
            return
        FormDialog("Procedimiento de auditoría", [Campo("estado", "Estado", "combo", opciones=ESTADOS_PASO), Campo("referencia_pt", "Referencia a papel de trabajo"), Campo("conclusion", "Conclusión", "memo", ancho=2)],
                   {"estado": f["estado"], "referencia_pt": f["referencia_pt"], "conclusion": f["conclusion"]},
                   guardar=lambda v: self.a.paso_actualizar(f["id"], v["estado"], v["conclusion"], v["referencia_pt"]), ayuda=f["procedimiento"], parent=self).exec()
        self._cargar_todo()

    # -------------------------------------------------------- B · cédulas (F)
    def _tab_cedulas(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        bg, bp, br = boton("Generar desde saldos del sistema", "primario"), boton("Firmar preparación"), boton("Firmar revisión")
        bg.clicked.connect(lambda: self._sumarias_accion("gen"))
        bp.clicked.connect(lambda: self._sumarias_accion("prep"))
        br.clicked.connect(lambda: self._sumarias_accion("rev"))
        lay.addLayout(hbox(bg, bp, br, None))
        self.t_sum = _Tabla([Columna("indice", "Índice", 60), Columna("titulo", "Rubro", 300, estirar=True), Columna("saldo_sistema", "Saldo sistema", 120, "money"), Columna("ajustes", "Ajustes", 100, "money"),
                             Columna("reclasificaciones", "Reclasif.", 100, "money"), Columna("saldo_auditado", "Saldo auditado", 120, "money"), Columna("preparado_por", "Prep.", 50), Columna("revisado_por", "Rev.", 50)],
                            "Cédulas sumarias: A, B, C… activos · AA, BB… pasivos (doble clic: analíticas y marcas)")
        self.t_sum.tabla.doble_clic.connect(self._abrir_analiticas)
        lay.addWidget(self.t_sum, 1)
        self.l_marcas = QLabel("")
        self.l_marcas.setWordWrap(True)
        lay.addWidget(self.l_marcas)
        self._reg(self._cargar_sum)
        return w

    def _cargar_sum(self):
        self.t_sum.cargar(self.a.sumarias(self.eid))
        self.l_marcas.setText("Leyenda de marcas: " + " · ".join(f"[{m['simbolo']}] {m['significado']}" for m in self.ctx.db.query("SELECT * FROM marca_auditoria WHERE encargo_id=?", (self.eid,))))

    def _sumarias_accion(self, que):
        if not self._enc():
            return
        if que == "gen":
            ok, n = intentar(self, self.a.sumarias_generar, self.eid)
            if ok:
                info(self, f"Se generaron {n} cédulas sumarias con sus analíticas.")
        else:
            f = self.t_sum.tabla.fila_actual()
            if not f:
                aviso(self, "Seleccione una cédula.")
                return
            intentar(self, self.a.cedula_firmar, f["id"], "PREPARADO" if que == "prep" else "REVISADO")
        self._cargar_todo()

    def _abrir_analiticas(self, f):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Cédula {f['indice']} — {f['titulo']}")
        dlg.resize(980, 520)
        lay = QVBoxLayout(dlg)
        t = _Tabla([Columna("indice", "Índice", 70), Columna("cuenta_codigo", "Cuenta", 110), Columna("concepto", "Concepto", 300, estirar=True), Columna("saldo_libros", "Saldo libros", 120, "money"),
                    Columna("saldo_verificado", "Saldo verificado", 120, "money"), Columna("diferencia", "Diferencia", 100, "money"), Columna("marcas", "Marcas", 80), Columna("comentario", "Comentario", 200)],
                   "Doble clic para registrar el saldo verificado y las marcas de auditoría")
        t.cargar(self.a.analiticas(f["id"]))

        def editar(a):
            FormDialog("Analítica", [Campo("saldo_verificado", "Saldo verificado", "money", defecto=a["saldo_verificado"] if a["saldo_verificado"] is not None else a["saldo_libros"]),
                                      Campo("marcas", "Marcas (separadas por coma, ej. V,S,D)"), Campo("comentario", "Comentario", "memo", ancho=2)],
                       {"marcas": a["marcas"], "comentario": a["comentario"]}, guardar=lambda v: self.a.analitica_guardar(a["id"], v["saldo_verificado"], v["marcas"], v["comentario"]), ayuda=a["concepto"], parent=dlg).exec()
            t.cargar(self.a.analiticas(f["id"]))
        t.tabla.doble_clic.connect(editar)
        lay.addWidget(t)
        dlg.exec()

    # ------------------------------------------------ B · pruebas financieras
    def _tab_pruebas_f(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        p = self.ctx.aud_pruebas
        self.c_prueba = Combo([(k, v[1]) for k, v in p.CATALOGO.items()])
        b = boton("Ejecutar y guardar como papel de trabajo", "primario")
        b.clicked.connect(self._ejecutar_f)
        lay.addLayout(hbox(QLabel("Prueba:"), self.c_prueba, b, None))
        self.r_f = _Tabla([Columna("sin_datos", "Ejecute una prueba", 200, estirar=True)])
        lay.addWidget(self.r_f, 1)
        return w

    def _mostrar_res(self, tabla: _Tabla, res: dict):
        filas = res.get("filas", [])
        tabla.tabla.setColumnCount(0)
        cols = _cols_de(filas)
        tabla.tabla.columnas = cols
        tabla.tabla.setColumnCount(len(cols))
        tabla.tabla.setHorizontalHeaderLabels([c.titulo for c in cols])
        for i, c in enumerate(cols):
            tabla.tabla.setColumnWidth(i, c.ancho)
        res_txt = "  ·  ".join(f"{k.replace('_', ' ')}: {fmt(v) if isinstance(v, float) else v}" for k, v in (res.get("resumen") or {}).items())
        tabla.cargar(filas, f"{'✔ CONFORME' if res.get('conforme') else '⚠ CON DIFERENCIAS'} — {res.get('conclusion', '')}\n{res_txt}")

    def _ejecutar_f(self):
        if not self._enc():
            return
        ok, res = intentar(self, self.ctx.aud_pruebas.ejecutar, self.eid, self.c_prueba.valor())
        if ok:
            self._mostrar_res(self.r_f, res)

    # ------------------------------------------------ B · pruebas tributarias
    def _tab_pruebas_t(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        ops = [("conciliacion_iva_it", "Conciliación DF / CF / IT vs Libros"), ("bancarizacion", "Bancarización (≥ umbral)")]
        self.c_pt = Combo(ops)
        b = boton("Ejecutar y guardar", "primario")
        b.clicked.connect(self._ejecutar_t)
        bc = boton("Calculadora de contingencias…")
        bc.clicked.connect(self._contingencia)
        lay.addLayout(hbox(QLabel("Prueba:"), self.c_pt, b, bc, None))
        self.r_t = _Tabla([Columna("sin_datos", "Ejecute una prueba", 200, estirar=True)])
        lay.addWidget(self.r_t, 1)
        return w

    def _ejecutar_t(self):
        if not self._enc():
            return
        clave = self.c_pt.valor()
        ok, res = intentar(self, getattr(self.ctx.aud_trib, clave), self.eid)
        if ok:
            self.a.guardar_prueba(self.eid, clave, res, "T")
            self._mostrar_res(self.r_t, res)

    def _contingencia(self):
        def calc(v):
            r = self.ctx.aud_trib.contingencia(v["monto"], v["venc"], v["calc"], v["tasa"] or None, v["sancion"])
            info(self, "\n".join(f"{k.replace('_', ' ').capitalize()}: {fmt(x) if isinstance(x, float) else x}" for k, x in r.items() if x != ""))
        FormDialog("Calculadora de contingencia (Ley 2492)", [Campo("monto", "Tributo omitido (Bs)", "money"), Campo("venc", "Fecha de vencimiento", "date", defecto=self.ctx.fin), Campo("calc", "Fecha de cálculo", "date", defecto=self.ctx.fin),
                                                                 Campo("tasa", "Tasa de interés anual (%)", "money"), Campo("sancion", "Sanción (%)", "money")],
                   guardar=calc, ayuda="Actualiza por UFV y aplica interés. Verifique tasas y sanciones vigentes en la Ley 2492 y la normativa del SIN.", texto_ok="Calcular", parent=self).exec()

    def _tab_iue(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        bd, bm, bc, bx = boton("Depurar (sugerir gastos no deducibles)", "primario"), boton("Agregar manual…"), boton("Confirmar"), boton("Descartar")
        bd.clicked.connect(self._depurar)
        bm.clicked.connect(self._gasto_manual)
        bc.clicked.connect(lambda: self._gasto_estado("CONFIRMADO"))
        bx.clicked.connect(lambda: self._gasto_estado("DESCARTADO"))
        lay.addLayout(hbox(bd, bm, bc, bx, None))
        self.t_iue = _Tabla([Columna("cuenta_codigo", "Cuenta", 100), Columna("concepto", "Concepto", 260), Columna("motivo", "Motivo", 300, estirar=True), Columna("base_legal", "Base legal", 160),
                             Columna("monto", "Monto", 110, "money"), Columna("estado", "Estado", 100)], "Cédula de depuración de gastos (D.S. 24051)")
        lay.addWidget(self.t_iue, 1)
        self._reg(self._cargar_iue)
        return w

    def _cargar_iue(self):
        c = self.ctx.aud_trib.cedula_iue(self.eid)
        r = c["resumen"]
        self.t_iue.cargar(c["gastos"], f"Utilidad contable {fmt(r['utilidad_contable'])} + no deducibles {fmt(r['no_deducibles_confirmados'])} = imponible {fmt(r['utilidad_imponible'])} → IUE {fmt(r['iue'])}   |   {c['conclusion']}")

    def _depurar(self):
        if self._enc():
            if intentar(self, self.ctx.aud_trib.depuracion_iue, self.eid)[0]:
                self._cargar_iue()

    def _gasto_manual(self):
        if self._enc():
            FormDialog("Gasto no deducible (manual)", [Campo("concepto", "Concepto", obligatorio=True, ancho=2), Campo("monto", "Monto (Bs)", "money"), Campo("base", "Base legal"), Campo("motivo", "Motivo", "memo", ancho=2)],
                       guardar=lambda v: self.ctx.aud_trib.gasto_manual(self.eid, v["concepto"], v["monto"], v["motivo"], v["base"]), parent=self).exec()
            self._cargar_iue()

    def _gasto_estado(self, est):
        f = self.t_iue.tabla.fila_actual()
        if f and intentar(self, self.ctx.aud_trib.gasto_estado, f["id"], est)[0]:
            self._cargar_iue()

    def _tab_anexos(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        b = boton("Llenar anexos automáticamente", "primario")
        b.clicked.connect(self._gen_anexos)
        lay.addLayout(hbox(b, QLabel("Formatos referenciales: adecúelos al formato oficial vigente del SIN antes de presentarlos."), None))
        self.t_anx = _Tabla([Columna("numero", "Nº", 50, "int"), Columna("titulo", "Anexo", 500, estirar=True), Columna("filas", "Filas", 80, "int"), Columna("generado_en", "Generado", 160)])
        lay.addWidget(self.t_anx, 1)
        self._reg(self._cargar_anx)
        return w

    def _cargar_anx(self):
        self.t_anx.cargar([{**a, "filas": len(a["datos"])} for a in self.ctx.aud_trib.anexos(self.eid)])

    def _gen_anexos(self):
        if self._enc() and intentar(self, self.ctx.aud_trib.generar_anexos, self.eid)[0]:
            self._cargar_anx()

    # ------------------------------------------------------ C · comunicación
    def _tab_hallazgos(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        bn, be = boton("Nuevo hallazgo", "primario"), boton("Editar / descargo de la Gerencia")
        bn.clicked.connect(lambda: self._hallazgo(None))
        be.clicked.connect(lambda: self._hallazgo(self.t_hall.tabla.fila_actual()))
        lay.addLayout(hbox(bn, be, None))
        self.t_hall = _Tabla([Columna("codigo", "Cód.", 50), Columna("condicion", "Condición", 260, estirar=True), Columna("criterio", "Criterio", 200), Columna("causa", "Causa", 160), Columna("efecto", "Efecto", 160),
                              Columna("nivel", "Nivel", 50), Columna("impacto_monto", "Impacto Bs", 100, "money"), Columna("estado", "Estado", 80)], "Hallazgos: Condición · Criterio · Causa · Efecto + Recomendación y Descargo")
        self.t_hall.tabla.doble_clic.connect(self._hallazgo)
        lay.addWidget(self.t_hall, 1)
        self._reg(lambda: self.t_hall.cargar(self.a.hallazgos(self.eid)))
        return w

    def _hallazgo(self, f):
        if not self._enc():
            return
        v = dict(f or {})
        FormDialog("Hallazgo de auditoría", [Campo("componente", "Componente / rubro"), Campo("nivel", "Nivel", "combo", opciones=NIVELES, defecto="M"), Campo("condicion", "Condición (lo que se encontró)", "memo", True, 2),
                                              Campo("criterio", "Criterio (norma o parámetro incumplido)", "memo", True, 2), Campo("causa", "Causa", "memo", True, 2), Campo("efecto", "Efecto", "memo", True, 2),
                                              Campo("recomendacion", "Recomendación", "memo", ancho=2), Campo("descargo_gerencia", "Descargo de la Gerencia", "memo", ancho=2), Campo("impacto_monto", "Impacto estimado (Bs)", "money")],
                   v, guardar=lambda x: self.a.hallazgo_guardar(self.eid, {**x, "id": v.get("id")}), parent=self, ancho=760).exec()
        self._cargar_todo()

    def _tab_ajustes(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        bn, ba, bx = boton("Proponer asiento", "primario"), boton("Aceptar"), boton("Marcar no corregido")
        bn.clicked.connect(self._ajuste)
        ba.clicked.connect(lambda: self._aj_estado("ACEPTADO"))
        bx.clicked.connect(lambda: self._aj_estado("NO_CORREGIDO"))
        lay.addLayout(hbox(bn, ba, bx, None))
        self.t_aj = _Tabla([Columna("numero", "Nº", 40, "int"), Columna("tipo", "Tipo", 50), Columna("descripcion", "Descripción", 400, estirar=True), Columna("efecto_resultado", "Efecto en resultados", 130, "money"), Columna("estado", "Estado", 120)],
                           "Asientos de ajuste (AJU) y reclasificación (REC) propuestos")
        lay.addWidget(self.t_aj, 1)
        self._reg(self._cargar_aj)
        return w

    def _cargar_aj(self):
        r = self.a.resumen_desvios(self.eid)
        op, mot = self.a.sugerir_opinion(self.eid)
        self.t_aj.cargar(r["ajustes"], f"Aceptados: {fmt(r['efecto_aceptados'])} · No corregidos: {fmt(r['efecto_no_corregidos'])} (no triviales {fmt(r['no_corregidos_no_triviales'])}) · "
                                       f"Materialidad {fmt(r['materialidad_global'])} → {r['veredicto']}.  Opinión sugerida: {op} — {mot}")

    def _ajuste(self):
        if not self._enc():
            return
        cuentas = [(c["id"], f"{c['codigo']}  {c['nombre']}") for c in self.ctx.cuentas.listar(solo_movimiento=True)]
        FormDialog("Proponer asiento de ajuste", [Campo("tipo", "Tipo", "combo", opciones=[("AJU", "Ajuste"), ("REC", "Reclasificación")]), Campo("monto", "Monto (Bs)", "money"),
                                                  Campo("debe", "Cuenta al DEBE", "combo", opciones=cuentas, ancho=2), Campo("haber", "Cuenta al HABER", "combo", opciones=cuentas, ancho=2),
                                                  Campo("descripcion", "Descripción", "memo", True, 2)],
                   guardar=lambda v: self.a.ajuste_guardar(self.eid, v["tipo"], v["descripcion"], [{"cuenta_id": v["debe"], "debe": v["monto"]}, {"cuenta_id": v["haber"], "haber": v["monto"]}]), parent=self, ancho=720).exec()
        self._cargar_todo()

    def _aj_estado(self, est):
        f = self.t_aj.tabla.fila_actual()
        if f and intentar(self, self.a.ajuste_estado, f["id"], est)[0]:
            self._cargar_todo()

    def _tab_dictamen(self):
        from ..services.auditoria_informes import CLASES_F, CLASES_T, OPINIONES
        w = QWidget()
        lay = QVBoxLayout(w)
        self.c_clase = Combo(list((CLASES_F if self.tipo == "F" else CLASES_T).items()))
        self.c_op = Combo(list(OPINIONES.items()))
        bb, be = boton("Generar borrador"), boton("Emitir (guardar)", "primario")
        bb.clicked.connect(self._borrador)
        be.clicked.connect(self._emitir)
        if self.tipo == "F":
            lay.addLayout(hbox(QLabel("Opinión (NIA 700/705/706):"), self.c_op, bb, be, None))
        else:
            lay.addLayout(hbox(QLabel("Informe:"), self.c_clase, bb, be, None))
        self.t_dic = QPlainTextEdit()
        lay.addWidget(self.t_dic, 1)
        self.t_emit = _Tabla([Columna("fecha", "Fecha", 90), Columna("clase", "Clase", 200), Columna("opinion", "Opinión", 120), Columna("firmante", "Firmante", 200, estirar=True)], "Dictámenes e informes emitidos")
        self.t_emit.setMaximumHeight(150)
        lay.addWidget(self.t_emit)
        self._reg(lambda: self.t_emit.cargar(self.a.dictamenes(self.eid)))
        return w

    def _borrador(self):
        if not self._enc():
            return
        inf = self.ctx.aud_informes
        ok, b = intentar(self, (lambda: inf.borrador_nia700(self.eid, self.c_op.valor())) if self.tipo == "F" else (lambda: inf.borrador_tributario(self.eid, self.c_clase.valor())))
        if ok:
            self._borr = b
            self.t_dic.setPlainText(b["texto"])

    def _emitir(self):
        if not self._enc() or not getattr(self, "_borr", None):
            aviso(self, "Genere primero el borrador.")
            return
        if intentar(self, self.ctx.aud_informes.emitir, self.eid, self._borr, self.t_dic.toPlainText())[0]:
            self._cargar_todo()


class AuditoriaFinancieraPantalla(AuditoriaPantalla):
    def __init__(self, ctx, ventana=None):
        super().__init__(ctx, "F", ventana)


class AuditoriaTributariaPantalla(AuditoriaPantalla):
    def __init__(self, ctx, ventana=None):
        super().__init__(ctx, "T", ventana)
