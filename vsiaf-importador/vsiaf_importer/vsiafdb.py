"""Acceso a la instalación del VSIAF: ubicación, catálogos y tablas."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unicodedata
from typing import Dict, List, Optional

from .dbf import DbfTable, find_file_ci

REG_KEY = r"SOFTWARE\MEFP\SIAF"          # HKCU: APPinstall, APPDBFS, APPIncEsp, ...
TABLES = ("ACTUAL", "REVAL", "BAJAS", "TRASFE", "OFICINA", "RESP", "AUXILIAR", "UNIDADADMIN")


def norm(s: object) -> str:
    """Normaliza texto para comparar: sin acentos, mayúsculas, espacios simples."""
    if s is None:
        return ""
    t = str(s).replace("¥", "Ñ").strip()
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t).upper()


def load_bundled_catalogs() -> dict:
    p = os.path.join(os.path.dirname(__file__), "data", "catalogos.json")
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


# ----------------------------------------------------------------------------- Windows
def _read_registry(value: str) -> Optional[str]:
    if sys.platform != "win32":
        return None
    try:
        import winreg  # type: ignore
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY) as k:
            v, _ = winreg.QueryValueEx(k, value)
            return str(v).strip() or None
    except OSError:
        return None


def registry_incesp_enabled() -> bool:
    """¿Tiene este equipo habilitadas las Incorporaciones Especiales? (solo lectura)

    La habilita la Dirección General de Contabilidad Fiscal mediante una llave con
    vigencia; el importador la respeta y nunca la modifica.
    """
    return _read_registry("APPIncEsp") == "1"


def vsiaf_running() -> bool:
    if sys.platform != "win32":
        return False
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq vsiaf.exe", "/NH"],
                             capture_output=True, text=True, timeout=15,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        return "vsiaf.exe" in out.lower()
    except Exception:
        return False


def detect_installation() -> Optional[str]:
    """Devuelve la carpeta de instalación del VSIAF (la que contiene vsiaf.exe y dbfs)."""
    cands: List[str] = []
    reg = _read_registry("APPinstall")
    if reg:
        cands.append(reg)
    cands += [r"C:\vsiaf", r"D:\vsiaf", os.path.expanduser("~/vsiaf")]
    for c in cands:
        c = c.rstrip("\\/")
        if os.path.isdir(os.path.join(c, "dbfs")) or find_file_ci(c, "dbfs"):
            return c
    return None


class VsiafInstallError(Exception):
    pass


class VsiafDb:
    """Una instalación del VSIAF (carpeta raíz + carpeta ``dbfs``)."""

    def __init__(self, install_dir: str, dbfs_dir: Optional[str] = None):
        self.install_dir = install_dir
        self.dbfs_dir = dbfs_dir or find_file_ci(install_dir, "dbfs") or os.path.join(install_dir, "dbfs")
        if not os.path.isdir(self.dbfs_dir):
            raise VsiafInstallError(f"No se encontró la carpeta de datos (dbfs) en {install_dir}")
        self._tables: Dict[str, DbfTable] = {}
        for t in ("ACTUAL", "CODCONT", "UNIDADADMIN"):
            if not find_file_ci(self.dbfs_dir, t + ".DBF"):
                raise VsiafInstallError(f"Falta la tabla {t}.DBF en {self.dbfs_dir}: no parece una base del VSIAF")
        self.catalogs = load_bundled_catalogs()

    # ------------------------------------------------------------------ tablas
    def table(self, name: str) -> DbfTable:
        key = name.upper()
        if key not in self._tables:
            p = find_file_ci(self.dbfs_dir, key + ".DBF")
            if not p:
                raise VsiafInstallError(f"Falta la tabla {key}.DBF en {self.dbfs_dir}")
            self._tables[key] = DbfTable(p)
        return self._tables[key]

    def dirty_files(self) -> List[str]:
        out: List[str] = []
        for t in TABLES:
            out += self.table(t).files
        return out

    def save_all(self) -> None:
        for t in self._tables.values():
            t.save()

    # ------------------------------------------------------------------ datos de la instalación
    @property
    def entidad(self) -> str:
        for r in self.table("CONFIG").records():
            if r["ENTIDAD"].strip():
                return r["ENTIDAD"].strip()
        raise VsiafInstallError("config.dbf no tiene la entidad: abra el VSIAF y seleccione la entidad primero")

    @property
    def entidad_nombre(self) -> str:
        for r in self.table("CONFIG").records():
            if r["ENTIDAD"].strip():
                return r["DESCENT"].strip()
        return ""

    @property
    def usuario_por_defecto(self) -> str:
        for r in self.table("CONFIG").records():
            if r["USUARIO"].strip() and r["USUARIO"].strip().upper() != "VSIAF":
                return r["USUARIO"].strip()[:8]
        return "admin"

    def gestion_cerrada(self) -> bool:
        p = find_file_ci(os.path.join(self.install_dir, "closeges"), "closeges.dbf")
        if not p:
            return False
        return any(r["NOM_ARCH"].strip().upper() == "ACTUAL" for r in DbfTable(p).records())

    def unidades(self) -> List[dict]:
        return [dict(unidad=r["UNIDAD"].strip(), descripcion=r["DESCRIP"].strip(), ciudad=r["CIUDAD"].strip(),
                     estado=r["ESTADOUNI"]) for r in self.table("UNIDADADMIN").records()
                if r["ENTIDAD"].strip() == self.entidad]

    # ------------------------------------------------------------------ catálogos (BD primero, luego incluidos)
    def grupos(self) -> List[dict]:
        out = []
        for r in self.table("CODCONT").records():
            out.append(dict(codcont=int(r["CODCONT"]), nombre=(r["NOMBRE"] or "").replace("¥", "Ñ"),
                            vida_util=float(r["VIDAUTIL"] or 0), depreciar=bool(r["DEPRECIAR"]),
                            actualizar=bool(r["ACTUALIZAR"])))
        return sorted(out, key=lambda g: g["codcont"])

    def estados(self) -> List[dict]:
        try:
            return [dict(codigo=int(r["CODESTADO"]), nombre=r["NOMESTADO"].strip())
                    for r in self.table("ESTADO").records()]
        except VsiafInstallError:
            return self.catalogs["estados"]

    def motivos_baja(self) -> List[dict]:
        try:
            return [dict(codigo=int(r["CODBAJA"]), nombre=r["DESCBAJA"].strip())
                    for r in self.table("BAJA").records()]
        except VsiafInstallError:
            return self.catalogs["motivos_baja"]

    def organismos(self) -> List[dict]:
        try:
            return [dict(codigo=r["OF"].strip(), nombre=r["DES"].strip(), sigla=r["SIGLA"].strip())
                    for r in self.table("ORGANISMO_FIN").records()]
        except VsiafInstallError:
            return self.catalogs["organismos_financiadores"]

    def departamentos(self) -> List[dict]:
        try:
            return [dict(codigo=int(r["CODIGO"]), nombre=r["DESC"].strip(), sigla=r["SIGLA"].strip())
                    for r in self.table("CLA_DEPTS").records()]
        except VsiafInstallError:
            return self.catalogs["departamentos"]
