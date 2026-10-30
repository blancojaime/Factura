"""Copias de seguridad (.cbk = zip con manifiesto SHA-256) y restauración verificada."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime

from . import __version__
from .db import Database
from .sistema import ErrorNegocio, Sistema


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def crear_backup(sis: Sistema, empresa_id: int | None = None, carpeta: str | None = None, incluir_sistema: bool = True, tipo: str = "MANUAL") -> str:
    """Genera un .cbk con copias consistentes (API de backup de SQLite) de las gestiones de una empresa o de todas."""
    carpeta = carpeta or os.path.join(sis.raiz, "backups")
    os.makedirs(carpeta, exist_ok=True)
    empresas = [sis.empresa(empresa_id)] if empresa_id else sis.db.query("SELECT * FROM empresa ORDER BY codigo")
    sello = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre = f"contabol_{empresas[0]['codigo'] if empresa_id else 'TODO'}_{sello}.cbk"
    destino = os.path.join(carpeta, nombre)
    tmp = tempfile.mkdtemp(prefix="cbk_")
    try:
        archivos: dict[str, str] = {}
        meta = {"version": __version__, "fecha": datetime.now().isoformat(timespec="seconds"), "empresas": [], "gestiones": [], "completo": empresa_id is None}
        if incluir_sistema:
            p = os.path.join(tmp, "sistema.db")
            sis.db.backup_to(p)
            archivos["sistema.db"] = p
        for e in empresas:
            meta["empresas"].append(e)
            for g in sis.gestiones(e["id"]):
                meta["gestiones"].append(g)
                ruta = sis.ruta_gestion(g)
                if os.path.exists(ruta):
                    d = Database(ruta)
                    rel = g["archivo"].replace("\\", "/")
                    p = os.path.join(tmp, rel.replace("/", "__"))
                    d.backup_to(p)
                    d.close()
                    archivos[rel] = p
        meta["archivos"] = {rel: {"sha256": _sha256(p), "bytes": os.path.getsize(p)} for rel, p in archivos.items()}
        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for rel, p in archivos.items():
                z.write(p, rel)
            z.writestr("manifest.json", json.dumps(meta, ensure_ascii=False, indent=1))
        mb = round(os.path.getsize(destino) / 1048576, 2)
        sis.db.insert("backup_log", fecha=datetime.now().isoformat(timespec="seconds"), tipo=tipo, archivo=destino, empresa_id=empresa_id,
                      resultado="OK", tamano_mb=mb)
        return destino
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def verificar(ruta: str) -> dict:
    """Valida el .cbk (manifiesto y SHA-256 de cada archivo). Devuelve el manifiesto."""
    if not zipfile.is_zipfile(ruta):
        raise ErrorNegocio("El archivo no es una copia de seguridad válida de ContaBol.")
    with zipfile.ZipFile(ruta) as z:
        if "manifest.json" not in z.namelist():
            raise ErrorNegocio("La copia no contiene manifiesto.")
        meta = json.loads(z.read("manifest.json").decode("utf-8"))
        for rel, info in meta["archivos"].items():
            if rel not in z.namelist():
                raise ErrorNegocio(f"Falta el archivo {rel} dentro de la copia.")
            h = hashlib.sha256(z.read(rel)).hexdigest()
            if h != info["sha256"]:
                raise ErrorNegocio(f"La copia está dañada: falla la verificación de {rel}.")
    return meta


def restaurar(sis: Sistema, ruta: str, usuario: dict) -> dict:
    """Restaura empresas/gestiones de un .cbk. Antes crea una copia de seguridad de seguridad del estado actual."""
    if not usuario["es_admin"]:
        raise ErrorNegocio("Solo el administrador puede restaurar copias de seguridad.")
    meta = verificar(ruta)
    sis.db.checkpoint()
    previa = None
    if meta["empresas"] and sis.db.scalar("SELECT COUNT(*) FROM empresa", (), 0):
        previa = crear_backup(sis, None, tipo="PRE-RESTAURACION")
    n_ges = 0
    with zipfile.ZipFile(ruta) as z:
        with sis.db.tx():
            for e in meta["empresas"]:
                ex = sis.db.one("SELECT id FROM empresa WHERE codigo=?", (e["codigo"],))
                vals = {k: v for k, v in e.items() if k != "id"}
                if ex:
                    sis.db.update("empresa", ex["id"], **{k: v for k, v in vals.items() if k != "codigo"})
                    eid = ex["id"]
                else:
                    eid = sis.db.insert("empresa", **vals)
                for g in [x for x in meta["gestiones"] if x["empresa_id"] == e["id"]]:
                    destino = os.path.join(sis.raiz, g["archivo"])
                    os.makedirs(os.path.dirname(destino), exist_ok=True)
                    for suf in ("", "-wal", "-shm"):
                        if os.path.exists(destino + suf):
                            os.remove(destino + suf)
                    with z.open(g["archivo"].replace("\\", "/")) as src, open(destino, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    gx = sis.db.one("SELECT id FROM gestion WHERE empresa_id=? AND anio=?", (eid, g["anio"]))
                    gv = {k: v for k, v in g.items() if k not in ("id", "empresa_id")}
                    if gx:
                        sis.db.update("gestion", gx["id"], **gv)
                    else:
                        sis.db.insert("gestion", empresa_id=eid, **gv)
                    n_ges += 1
    sis.auditar(usuario, None, None, "Backup", "RESTAURAR", os.path.basename(ruta))
    return {"empresas": len(meta["empresas"]), "gestiones": n_ges, "copia_previa": previa, "fecha_copia": meta["fecha"]}


def limpiar_antiguos(sis: Sistema, conservar: int = 15) -> int:
    carpeta = os.path.join(sis.raiz, "backups")
    arch = sorted((f for f in os.listdir(carpeta) if f.endswith(".cbk") and "PRE" not in f), reverse=True)
    n = 0
    for f in arch[conservar:]:
        try:
            os.remove(os.path.join(carpeta, f))
            n += 1
        except OSError:
            pass
    return n
