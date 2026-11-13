#!/usr/bin/env python3
"""SICOM-MUNI — Emisor de Licencias (herramienta EXTERNA del proveedor).

NO se instala en las máquinas de los clientes: solo la usa quien emite las licencias.
  * Sin argumentos abre la ventana (interfaz gráfica).
  * Con argumentos funciona por línea de comandos:
        emisor.py llaves   --salida CARPETA
        emisor.py emitir   --llave llave_privada.pem --entidad "GAM X" --equipo XXXX-XXXX-XXXX-XXXX [--vence 2027-12-31] [--max-usuarios 25] --salida lic.sicomlic
        emisor.py verificar --llave llave_privada.pem ARCHIVO [--equipo XXXX-XXXX-XXXX-XXXX]
La licencia se firma con una llave privada Ed25519 que solo usted conserva; el servidor instalado solo lleva la llave pública.
"""
import argparse
import csv
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# licencia_core.py vive en el backend del sistema; al empaquetar con PyInstaller se incluye con --paths
_AQUI = Path(__file__).resolve().parent
for candidato in (_AQUI / "licencia_core.py", _AQUI.parent.parent / "sicom-muni" / "backend" / "app" / "services" / "licencia_core.py"):
    if candidato.exists():
        sys.path.insert(0, str(candidato.parent))
        break
import licencia_core as core  # noqa: E402

CONFIG_DIR = Path(os.environ.get("APPDATA") or Path.home() / ".config") / "SICOM-Emisor"
CONFIG = CONFIG_DIR / "config.json"
REGISTRO = CONFIG_DIR / "registro_licencias.csv"


# ------------------------------------------------------------------ logica (compartida por la ventana y la consola)
def crear_llaves(carpeta: Path) -> tuple[Path, Path]:
    carpeta.mkdir(parents=True, exist_ok=True)
    priv, pub = core.generar_par_llaves()
    ruta_priv, ruta_pub = carpeta / "llave_privada_SICOM.pem", carpeta / "llave_publica_SICOM.pem"
    if ruta_priv.exists():
        raise FileExistsError(f"Ya existe {ruta_priv}: no se sobrescribe una llave privada")
    ruta_priv.write_bytes(priv)
    try:
        ruta_priv.chmod(0o600)
    except OSError:
        pass
    ruta_pub.write_bytes(pub)
    return ruta_priv, ruta_pub


def registrar(licencia: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    nuevo = not REGISTRO.exists()
    d = licencia["datos"]
    with REGISTRO.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        if nuevo:
            w.writerow(["licencia_id", "entidad", "equipo", "emitida", "vence", "max_usuarios", "observaciones", "registrada"])
        w.writerow([d["licencia_id"], d["entidad"], d["equipo"], d["emitida"], d["vence"] or "sin vencimiento",
                    d["max_usuarios"] or "sin limite", d["observaciones"], datetime.now().isoformat(timespec="seconds")])


def emitir_y_guardar(llave: Path, entidad: str, equipo: str, vence: date | None, max_usuarios: int | None,
                     observaciones: str, salida: Path | None) -> tuple[dict, str]:
    lic = core.emitir(llave.read_bytes(), entidad=entidad, equipo=equipo, vence=vence, max_usuarios=max_usuarios,
                      observaciones=observaciones)
    if salida:
        salida.write_text(json.dumps(lic, ensure_ascii=False, indent=2), encoding="utf-8")
    registrar(lic)
    return lic, core.a_clave(lic)


def describir(lic: dict) -> str:
    d = lic["datos"]
    return (f"Licencia {d['licencia_id']}\nEntidad: {d['entidad']}\nEquipo: {'cualquiera' if d['equipo'] == '*' else d['equipo']}\n"
            f"Emitida: {d['emitida']}\nVence: {d['vence'] or 'sin vencimiento'}\nUsuarios: {d['max_usuarios'] or 'sin límite'}\n"
            f"Observaciones: {d['observaciones'] or '—'}")


def _fecha(texto: str) -> date | None:
    t = texto.strip()
    return date.fromisoformat(t) if t else None


# ------------------------------------------------------------------ consola
def cli(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("llaves", help="crea un par de llaves nuevo")
    p.add_argument("--salida", required=True)
    p = sub.add_parser("emitir", help="emite una licencia firmada")
    p.add_argument("--llave", required=True)
    p.add_argument("--entidad", required=True)
    p.add_argument("--equipo", default="*", help="ID del equipo (XXXX-XXXX-XXXX-XXXX) o * para cualquiera")
    p.add_argument("--vence", default="", help="AAAA-MM-DD (vacío = sin vencimiento)")
    p.add_argument("--max-usuarios", type=int, default=0)
    p.add_argument("--observaciones", default="")
    p.add_argument("--salida", required=True)
    p = sub.add_parser("verificar", help="comprueba una licencia")
    p.add_argument("--llave", required=True, help="llave privada o pública (.pem)")
    p.add_argument("archivo")
    p.add_argument("--equipo", default="")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "llaves":
            priv, pub = crear_llaves(Path(a.salida))
            print(f"Llave PRIVADA (secreta, respáldela): {priv}\nLlave pública (va dentro del instalador): {pub}")
        elif a.cmd == "emitir":
            lic, clave = emitir_y_guardar(Path(a.llave), a.entidad, a.equipo, _fecha(a.vence), a.max_usuarios or None, a.observaciones, Path(a.salida))
            print(describir(lic))
            print(f"\nArchivo: {a.salida}\nClave de activación:\n{clave}")
        else:
            pem = Path(a.llave).read_bytes()
            try:
                pub = core.publica_de(pem)
            except ValueError:
                pub = pem
            r = core.verificar(Path(a.archivo).read_text(encoding="utf-8-sig"), pub, a.equipo or core.id_equipo())
            print(("VÁLIDA: " if r.valida else "NO VÁLIDA: ") + r.mensaje)
            if r.datos:
                print(describir({"datos": r.datos}))
            return 0 if r.valida else 1
    except (ValueError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    return 0


# ------------------------------------------------------------------ ventana
def gui() -> int:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    cfg = {}
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass

    raiz = tk.Tk()
    raiz.title("SICOM-MUNI — Emisor de Licencias")
    raiz.geometry("760x720")
    raiz.minsize(720, 680)
    estilo = ttk.Style()
    estilo.configure("Titulo.TLabel", font=("Segoe UI", 15, "bold"), foreground="#1f4e79")
    estilo.configure("Aviso.TLabel", foreground="#7a1f1f")

    v_llave, v_entidad, v_equipo = tk.StringVar(value=cfg.get("llave", "")), tk.StringVar(), tk.StringVar()
    v_cualquiera, v_vence, v_sin_venc = tk.BooleanVar(), tk.StringVar(value=(date.today() + timedelta(days=365)).isoformat()), tk.BooleanVar()
    v_max, v_obs, v_estado = tk.StringVar(value="0"), tk.StringVar(), tk.StringVar(value="Seleccione su llave privada para comenzar.")

    def guardar_cfg():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps({"llave": v_llave.get()}), encoding="utf-8")

    def abrir_llave():
        f = filedialog.askopenfilename(title="Llave privada", filetypes=[("Llave PEM", "*.pem"), ("Todos", "*.*")])
        if f:
            try:
                core.cargar_privada(Path(f).read_bytes())
            except Exception:  # noqa: BLE001
                messagebox.showerror("Llave inválida", "El archivo no es una llave privada de SICOM-MUNI.")
                return
            v_llave.set(f)
            guardar_cfg()
            v_estado.set("Llave cargada. Complete los datos y pulse «Emitir licencia».")

    def nuevas_llaves():
        c = filedialog.askdirectory(title="Carpeta donde guardar las llaves nuevas")
        if not c:
            return
        if not messagebox.askyesno("Llaves nuevas", "Las licencias emitidas con una llave NUEVA solo funcionan con instaladores compilados con su llave pública.\n¿Crear las llaves?"):
            return
        try:
            priv, pub = crear_llaves(Path(c))
        except (OSError, FileExistsError) as e:
            messagebox.showerror("No se crearon", str(e))
            return
        v_llave.set(str(priv))
        guardar_cfg()
        messagebox.showinfo("Llaves creadas", f"Llave PRIVADA (secreta, respáldela):\n{priv}\n\nLlave pública (para el instalador):\n{pub}")

    def emitir():
        try:
            if not v_llave.get():
                raise ValueError("Seleccione la llave privada")
            equipo = "*" if v_cualquiera.get() else v_equipo.get()
            vence = None if v_sin_venc.get() else _fecha(v_vence.get())
            if not v_sin_venc.get() and vence is None:
                raise ValueError("Indique la fecha de vencimiento (AAAA-MM-DD) o marque «Sin vencimiento»")
            maximo = int(v_max.get() or 0)
            nombre = f"licencia_{''.join(c for c in v_entidad.get() if c.isalnum())[:20] or 'cliente'}_{equipo.replace('*', 'cualquiera')}.sicomlic"
            destino = filedialog.asksaveasfilename(title="Guardar licencia", initialfile=nombre, defaultextension=".sicomlic",
                                                   filetypes=[("Licencia SICOM-MUNI", "*.sicomlic")])
            if not destino:
                return
            lic, clave = emitir_y_guardar(Path(v_llave.get()), v_entidad.get(), equipo, vence, maximo or None, v_obs.get(), Path(destino))
        except ValueError as e:
            messagebox.showerror("Revise los datos", str(e))
            return
        except OSError as e:
            messagebox.showerror("No se pudo guardar", str(e))
            return
        salida.delete("1.0", "end")
        salida.insert("1.0", clave)
        v_estado.set(f"Licencia {lic['datos']['licencia_id']} emitida y registrada. Envíe el archivo (o la clave) al cliente.")

    def copiar():
        raiz.clipboard_clear()
        raiz.clipboard_append(salida.get("1.0", "end").strip())
        v_estado.set("Clave copiada al portapapeles.")

    def verificar():
        f = filedialog.askopenfilename(title="Licencia a verificar", filetypes=[("Licencia", "*.sicomlic *.json *.txt"), ("Todos", "*.*")])
        if not f or not v_llave.get():
            if not v_llave.get():
                messagebox.showwarning("Falta la llave", "Seleccione primero la llave privada (de ella se deriva la pública).")
            return
        pub = core.publica_de(Path(v_llave.get()).read_bytes())
        r = core.verificar(Path(f).read_text(encoding="utf-8-sig"), pub, "")
        mensaje = ("VÁLIDA\n\n" if r.valida or r.codigo == "EQUIPO" else "NO VÁLIDA: " + r.mensaje + "\n\n")
        if r.datos:
            mensaje += describir({"datos": r.datos})
        messagebox.showinfo("Verificación", mensaje)

    m = ttk.Frame(raiz, padding=14)
    m.pack(fill="both", expand=True)
    ttk.Label(m, text="Emisor de Licencias SICOM-MUNI", style="Titulo.TLabel").pack(anchor="w")
    ttk.Label(m, text="Herramienta del proveedor: no la instale en las máquinas de los clientes.", style="Aviso.TLabel").pack(anchor="w", pady=(0, 10))

    g1 = ttk.LabelFrame(m, text="1. Llave privada (secreta)", padding=8)
    g1.pack(fill="x")
    ttk.Entry(g1, textvariable=v_llave, state="readonly").pack(side="left", fill="x", expand=True)
    ttk.Button(g1, text="Abrir…", command=abrir_llave).pack(side="left", padx=4)
    ttk.Button(g1, text="Crear llaves nuevas…", command=nuevas_llaves).pack(side="left")

    g2 = ttk.LabelFrame(m, text="2. Datos de la licencia", padding=8)
    g2.pack(fill="x", pady=8)
    g2.columnconfigure(1, weight=1)
    ttk.Label(g2, text="Entidad / cliente:").grid(row=0, column=0, sticky="w", pady=3)
    ttk.Entry(g2, textvariable=v_entidad).grid(row=0, column=1, columnspan=2, sticky="ew", pady=3)
    ttk.Label(g2, text="ID del equipo:").grid(row=1, column=0, sticky="w", pady=3)
    ttk.Entry(g2, textvariable=v_equipo).grid(row=1, column=1, sticky="ew", pady=3)
    ttk.Checkbutton(g2, text="Cualquier equipo (*)", variable=v_cualquiera).grid(row=1, column=2, padx=6)
    ttk.Label(g2, text="Vence (AAAA-MM-DD):").grid(row=2, column=0, sticky="w", pady=3)
    ttk.Entry(g2, textvariable=v_vence, width=14).grid(row=2, column=1, sticky="w", pady=3)
    ttk.Checkbutton(g2, text="Sin vencimiento", variable=v_sin_venc).grid(row=2, column=2, padx=6)
    ttk.Label(g2, text="Máx. usuarios (0 = sin límite):").grid(row=3, column=0, sticky="w", pady=3)
    ttk.Spinbox(g2, from_=0, to=100000, textvariable=v_max, width=10).grid(row=3, column=1, sticky="w", pady=3)
    ttk.Label(g2, text="Observaciones:").grid(row=4, column=0, sticky="w", pady=3)
    ttk.Entry(g2, textvariable=v_obs).grid(row=4, column=1, columnspan=2, sticky="ew", pady=3)

    botones = ttk.Frame(m)
    botones.pack(fill="x")
    ttk.Button(botones, text="Emitir licencia", command=emitir).pack(side="left")
    ttk.Button(botones, text="Verificar una licencia…", command=verificar).pack(side="left", padx=6)
    ttk.Button(botones, text="Abrir carpeta del registro", command=lambda: (CONFIG_DIR.mkdir(parents=True, exist_ok=True), os.startfile(CONFIG_DIR) if hasattr(os, "startfile") else None)).pack(side="right")

    g3 = ttk.LabelFrame(m, text="3. Clave de activación (alternativa al archivo)", padding=8)
    g3.pack(fill="both", expand=True, pady=8)
    salida = tk.Text(g3, height=8, wrap="char", font=("Consolas", 9))
    salida.pack(fill="both", expand=True)
    ttk.Button(g3, text="Copiar clave", command=copiar).pack(anchor="e", pady=(6, 0))
    ttk.Label(m, textvariable=v_estado, foreground="#1f4e79").pack(anchor="w")
    raiz.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]) if len(sys.argv) > 1 else gui())
