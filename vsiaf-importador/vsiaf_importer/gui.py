"""Ventana principal del Importador Excel → VSIAF (Tkinter, incluido en Python para Windows)."""
from __future__ import annotations

import datetime as dt
import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from . import __version__, service
from .excelio import as_date
from .importer import ERROR, WARN, ImportAbort, Options, Result
from .vsiafdb import VsiafInstallError, detect_installation, vsiaf_running

APP_TITLE = f"Importador Excel → VSIAF  v{__version__}"


def _settings_path() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    d = os.path.join(base, "ImportadorVSIAF")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "settings.json")


def _open_file(path: str) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:  # pragma: no cover
        messagebox.showerror(APP_TITLE, f"No se pudo abrir el archivo:\n{path}\n\n{e}")


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1020x720")
        self.minsize(900, 620)
        self.q: "queue.Queue[tuple]" = queue.Queue()
        self.report_path: Optional[str] = None
        self.busy = False
        self.settings = self._load_settings()
        self._build()
        self.after(100, self._poll)
        self.after(200, self._autodetect)

    # ------------------------------------------------------------------ ajustes
    def _load_settings(self) -> dict:
        try:
            with open(_settings_path(), encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}

    def _save_settings(self) -> None:
        self.settings.update(vsiaf=self.v_vsiaf.get(), excel=self.v_excel.get(), user=self.v_user.get(),
                             unit=self.v_unit.get())
        try:
            with open(_settings_path(), "w", encoding="utf-8") as fh:
                json.dump(self.settings, fh, ensure_ascii=False, indent=1)
        except Exception:
            pass

    # ------------------------------------------------------------------ interfaz
    def _build(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("vista" if sys.platform == "win32" else "clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 15, "bold"), foreground="#1F3864")
        style.configure("Big.TButton", font=("Segoe UI", 10, "bold"), padding=8)
        pad = dict(padx=10, pady=4)

        ttk.Label(self, text="Importador Excel → VSIAF 2.0", style="Title.TLabel").pack(anchor="w", padx=10, pady=(10, 0))
        ttk.Label(self, text="Carga activos fijos, revalúos, transferencias y bajas desde una hoja Excel a la base de datos del VSIAF.",
                  foreground="#555").pack(anchor="w", padx=10)

        f1 = ttk.LabelFrame(self, text=" 1. Instalación del VSIAF ")
        f1.pack(fill="x", **pad)
        self.v_vsiaf = tk.StringVar(value=self.settings.get("vsiaf", ""))
        ttk.Entry(f1, textvariable=self.v_vsiaf).grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        ttk.Button(f1, text="Examinar…", command=self._pick_vsiaf).grid(row=0, column=1, padx=3)
        ttk.Button(f1, text="Detectar", command=self._autodetect).grid(row=0, column=2, padx=3)
        ttk.Button(f1, text="Leer", command=self._load_install).grid(row=0, column=3, padx=(3, 6))
        self.v_info = tk.StringVar(value="(seleccione la carpeta donde está instalado el VSIAF, normalmente C:\\vsiaf)")
        ttk.Label(f1, textvariable=self.v_info, foreground="#1F3864", wraplength=900, justify="left").grid(
            row=1, column=0, columnspan=4, sticky="w", padx=6, pady=(0, 6))
        f1.columnconfigure(0, weight=1)

        f2 = ttk.LabelFrame(self, text=" 2. Libro Excel de importación ")
        f2.pack(fill="x", **pad)
        self.v_excel = tk.StringVar(value=self.settings.get("excel", ""))
        ttk.Entry(f2, textvariable=self.v_excel).grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        ttk.Button(f2, text="Examinar…", command=self._pick_excel).grid(row=0, column=1, padx=3)
        ttk.Button(f2, text="Crear plantilla…", command=self._make_template).grid(row=0, column=2, padx=(3, 6))
        f2.columnconfigure(0, weight=1)

        f3 = ttk.LabelFrame(self, text=" 3. Opciones ")
        f3.pack(fill="x", **pad)
        ttk.Label(f3, text="Unidad por defecto:").grid(row=0, column=0, sticky="e", padx=6, pady=4)
        self.v_unit = tk.StringVar(value=self.settings.get("unit", ""))
        self.cb_unit = ttk.Combobox(f3, textvariable=self.v_unit, width=34, state="normal")
        self.cb_unit.grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(f3, text="Usuario (queda en los registros):").grid(row=0, column=2, sticky="e", padx=6)
        self.v_user = tk.StringVar(value=self.settings.get("user", "admin"))
        ttk.Entry(f3, textvariable=self.v_user, width=10).grid(row=0, column=3, sticky="w")
        ttk.Label(f3, text="Fecha de cálculo (vista previa):").grid(row=1, column=0, sticky="e", padx=6, pady=4)
        self.v_calc = tk.StringVar(value=dt.date.today().strftime("%d/%m/%Y"))
        ttk.Entry(f3, textvariable=self.v_calc, width=12).grid(row=1, column=1, sticky="w", padx=4)
        ttk.Label(f3, text="Estado de activos sin dato:").grid(row=1, column=2, sticky="e", padx=6)
        self.v_state = tk.StringVar(value="ELABORADO")
        ttk.Combobox(f3, textvariable=self.v_state, values=["ELABORADO", "APROBADO"], width=12,
                     state="readonly").grid(row=1, column=3, sticky="w")
        self.v_backup = tk.BooleanVar(value=True)
        self.v_onlyvalid = tk.BooleanVar(value=False)
        ttk.Checkbutton(f3, text="Crear respaldo automático antes de importar (recomendado)",
                        variable=self.v_backup).grid(row=2, column=0, columnspan=3, sticky="w", padx=6)
        ttk.Checkbutton(f3, text="Importar solo las filas válidas (si no, un error cancela toda la importación)",
                        variable=self.v_onlyvalid).grid(row=3, column=0, columnspan=4, sticky="w", padx=6, pady=(0, 4))

        fb = ttk.Frame(self)
        fb.pack(fill="x", padx=10, pady=6)
        self.b_val = ttk.Button(fb, text="① Validar (no escribe nada)", style="Big.TButton",
                                command=lambda: self._start(False))
        self.b_val.pack(side="left")
        self.b_imp = ttk.Button(fb, text="② Importar al VSIAF", style="Big.TButton", command=lambda: self._start(True))
        self.b_imp.pack(side="left", padx=8)
        self.b_rep = ttk.Button(fb, text="Abrir informe", command=self._open_report, state="disabled")
        self.b_rep.pack(side="left", padx=8)
        ttk.Button(fb, text="Salir", command=self.destroy).pack(side="right")
        self.pb = ttk.Progressbar(self, mode="indeterminate")
        self.pb.pack(fill="x", padx=10)

        self.v_status = tk.StringVar(value="Listo.")
        ttk.Label(self, textvariable=self.v_status, relief="sunken", anchor="w").pack(fill="x", side="bottom")

        ff = ttk.LabelFrame(self, text=" Resultado ")
        ff.pack(fill="both", expand=True, **pad)
        self.v_sum = tk.StringVar(value="Sin ejecutar.")
        ttk.Label(ff, textvariable=self.v_sum, font=("Segoe UI", 10, "bold"), wraplength=960,
                  justify="left").pack(anchor="w", padx=6, pady=4)
        cols = ("nivel", "hoja", "fila", "columna", "mensaje")
        self.tree = ttk.Treeview(ff, columns=cols, show="headings", height=10)
        for c, w in zip(cols, (70, 120, 50, 150, 600)):
            self.tree.heading(c, text=c.capitalize())
            self.tree.column(c, width=w, anchor="w", stretch=(c == "mensaje"))
        self.tree.tag_configure(ERROR, background="#F8CBAD")
        self.tree.tag_configure(WARN, background="#FFF2CC")
        sb = ttk.Scrollbar(ff, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=(0, 6))
        sb.pack(side="right", fill="y", pady=(0, 6), padx=(0, 6))

    # ------------------------------------------------------------------ acciones de selección
    def _pick_vsiaf(self) -> None:
        d = filedialog.askdirectory(title="Carpeta de instalación del VSIAF (contiene vsiaf.exe y dbfs)")
        if d:
            self.v_vsiaf.set(os.path.normpath(d))
            self._load_install()

    def _autodetect(self) -> None:
        if not self.v_vsiaf.get():
            d = detect_installation()
            if d:
                self.v_vsiaf.set(d)
        if self.v_vsiaf.get():
            self._load_install()

    def _load_install(self) -> None:
        path = self.v_vsiaf.get().strip()
        if not path:
            return
        try:
            db, ufv = service.open_db(path)
            units = db.unidades()
            self.cb_unit["values"] = [f"{u['unidad']} — {u['descripcion']}" for u in units]
            if not self.v_unit.get() and len(units) == 1:
                self.v_unit.set(self.cb_unit["values"][0])
            if not self.v_user.get() or self.v_user.get() == "admin":
                self.v_user.set(db.usuario_por_defecto)
            stale = ""
            if ufv.last_change and (dt.date.today() - ufv.last_change).days > 75:
                stale = f"  ⚠ UFV sin variación desde {ufv.last_change:%d/%m/%Y}: actualice las UFV."
            self.v_info.set(f"Entidad {db.entidad} — {db.entidad_nombre}  |  {len(units)} unidad(es)  |  "
                            f"UFV hasta {ufv.last:%d/%m/%Y}{stale}"
                            + ("  |  ⛔ GESTIÓN CERRADA" if db.gestion_cerrada() else ""))
            self.v_status.set("Instalación leída correctamente.")
        except (VsiafInstallError, Exception) as e:
            self.v_info.set(f"⛔ {e}")

    def _pick_excel(self) -> None:
        f = filedialog.askopenfilename(title="Libro Excel de importación",
                                       filetypes=[("Excel", "*.xlsx *.xlsm"), ("Todos", "*.*")])
        if f:
            self.v_excel.set(os.path.normpath(f))

    def _make_template(self) -> None:
        ej = messagebox.askyesnocancel(APP_TITLE, "¿Incluir filas de EJEMPLO en la plantilla?\n\n"
                                       "Sí = con ejemplos (para practicar en una base de prueba)\n"
                                       "No = plantilla vacía (para sus datos reales)")
        if ej is None:
            return
        f = filedialog.asksaveasfilename(title="Guardar plantilla", defaultextension=".xlsx",
                                         initialfile="plantilla_importacion_vsiaf.xlsx",
                                         filetypes=[("Excel", "*.xlsx")])
        if not f:
            return
        try:
            service.create_template(f, self.v_vsiaf.get().strip() or None, ej)
            self.v_excel.set(os.path.normpath(f))
            if messagebox.askyesno(APP_TITLE, "Plantilla creada.\n¿Abrirla en Excel ahora?"):
                _open_file(f)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"No se pudo crear la plantilla:\n{e}")

    def _open_report(self) -> None:
        if self.report_path and os.path.exists(self.report_path):
            _open_file(self.report_path)

    # ------------------------------------------------------------------ ejecución
    def _unit_code(self) -> str:
        return self.v_unit.get().split("—")[0].strip()

    def _make_options(self) -> Optional[Options]:
        d = as_date(self.v_calc.get().strip()) if self.v_calc.get().strip() else dt.date.today()
        user = self.v_user.get().strip()[:8] or "admin"
        return Options(default_unit=self._unit_code(), user=user, calc_date=d, default_state=self.v_state.get(),
                       only_valid=self.v_onlyvalid.get(), make_backup=self.v_backup.get())

    def _start(self, apply: bool) -> None:
        if self.busy:
            return
        vs, xl = self.v_vsiaf.get().strip(), self.v_excel.get().strip()
        if not vs or not os.path.isdir(vs):
            messagebox.showwarning(APP_TITLE, "Seleccione la carpeta de instalación del VSIAF.")
            return
        if not xl or not os.path.isfile(xl):
            messagebox.showwarning(APP_TITLE, "Seleccione el libro Excel a importar.")
            return
        try:
            opt = self._make_options()
        except ValueError as e:
            messagebox.showwarning(APP_TITLE, f"Fecha de cálculo no válida: {e}")
            return
        if apply:
            if vsiaf_running():
                messagebox.showerror(APP_TITLE, "El VSIAF está abierto. Ciérrelo antes de importar.")
                return
            if not messagebox.askyesno(
                    APP_TITLE, "Se va a ESCRIBIR en la base de datos del VSIAF.\n\n"
                    + ("• Se creará un respaldo automático (carpeta backups).\n" if opt.make_backup else
                       "• ⚠ SIN respaldo automático.\n")
                    + "• El VSIAF debe estar cerrado.\n\n¿Continuar?", icon="warning"):
                return
        self._save_settings()
        self.busy = True
        self.pb.start(12)
        for b in (self.b_val, self.b_imp):
            b.state(["disabled"])
        self.tree.delete(*self.tree.get_children())
        self.v_sum.set("Procesando…")
        threading.Thread(target=self._worker, args=(vs, xl, opt, apply), daemon=True).start()

    def _worker(self, vs: str, xl: str, opt: Options, apply: bool) -> None:
        try:
            res, path = service.run(vs, xl, opt, apply, log=lambda m: self.q.put(("log", m)))
            self.q.put(("done", res, path, apply, None))
        except ImportAbort as e:
            self.q.put(("done", getattr(e, "result", None), getattr(e, "report", None), apply, str(e)))
        except Exception as e:  # error inesperado
            import traceback
            self.q.put(("crash", f"{e}\n\n{traceback.format_exc()}"))

    def _poll(self) -> None:
        try:
            while True:
                msg = self.q.get_nowait()
                if msg[0] == "log":
                    self.v_status.set(msg[1])
                elif msg[0] == "done":
                    self._finish(*msg[1:])
                elif msg[0] == "crash":
                    self._idle()
                    self.v_sum.set("Error inesperado.")
                    messagebox.showerror(APP_TITLE, f"Ocurrió un error inesperado:\n\n{msg[1]}")
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _idle(self) -> None:
        self.busy = False
        self.pb.stop()
        for b in (self.b_val, self.b_imp):
            b.state(["!disabled"])

    def _finish(self, res: Optional[Result], path: Optional[str], apply: bool, err: Optional[str]) -> None:
        self._idle()
        self.report_path = path
        self.b_rep.state(["!disabled"] if path else ["disabled"])
        if res is not None:
            for it in res.issues:
                if it.level in (ERROR, WARN):
                    self.tree.insert("", "end", values=(it.level, it.sheet, it.row or "", it.column, it.message),
                                     tags=(it.level,))
            counts = ", ".join(f"{k}: {v}" for k, v in res.counts.items()) or "nada para importar"
            head = ("IMPORTACIÓN TERMINADA" if res.applied else
                    ("NO SE IMPORTÓ" if apply else "VALIDACIÓN TERMINADA"))
            self.v_sum.set(f"{head} — errores: {res.errors}, avisos: {res.warnings} — {counts}")
        if err:
            self.v_status.set("No se importó.")
            messagebox.showerror(APP_TITLE, f"No se importó nada.\n\n{err}")
        elif apply and res is not None and res.applied:
            self.v_status.set("Importación terminada.")
            messagebox.showinfo(
                APP_TITLE, "Importación terminada correctamente.\n\n"
                + (f"Respaldo previo: {res.backup_path}\n\n" if res.backup_path else "")
                + "PASO OBLIGATORIO: abra el VSIAF y ejecute  Administradores → Re-indexar.\n"
                "Después compruebe los totales con el Reporte 6 (Resumen por grupo contable).")
        elif res is not None:
            self.v_status.set("Validación terminada." if not apply else "Terminado.")
            if not apply and res.errors == 0 and res.counts:
                messagebox.showinfo(APP_TITLE, "El libro no tiene errores.\nPuede pulsar «② Importar al VSIAF».")


def run_gui() -> None:
    App().mainloop()


if __name__ == "__main__":
    run_gui()
