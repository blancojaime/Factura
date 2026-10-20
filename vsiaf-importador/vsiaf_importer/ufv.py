"""Tabla de índices UFV (la misma que usa el VSIAF).

El VSIAF no guarda las UFV en ``dbfs``: están embebidas dentro de
``tipocambio.app`` (tabla ``TIPCAMB``: DIA, MES, ANO, TC, FEULT, USUAR) y se
renuevan cada mes con el "actualizador de UFV" del Ministerio.  Este módulo
extrae esa tabla directamente del .app para que el importador calcule con
exactamente los mismos índices que el sistema.

Orden de búsqueda: ``tipocambio.app`` → ``dbfs/tipcamb.dbf`` → CSV incluido.
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import re
import struct
from typing import Dict, Optional, Tuple

from .dbf import DbfTable, find_file_ci

# Descriptor de campo "DIA" (N,2,0) al comienzo de la tabla TIPCAMB.
_DIA_FIELD = re.compile(rb"DIA\x00{8}N.{4}\x02\x00", re.S)


class UfvMissing(KeyError):
    """No hay UFV registrada para esa fecha (el VSIAF muestra 'Tipo de cambio NO registrado')."""


class UfvTable:
    def __init__(self, values: Dict[dt.date, float], source: str):
        self._v = values
        self.source = source
        self.first = min(values) if values else None
        self.last = max(values) if values else None

    def __len__(self) -> int:
        return len(self._v)

    def has(self, d: dt.date) -> bool:
        return d in self._v

    def get(self, d: dt.date) -> float:
        try:
            return self._v[d]
        except KeyError:
            raise UfvMissing(f"UFV no registrada para {d:%d/%m/%Y}") from None

    @property
    def last_change(self) -> Optional[dt.date]:
        """Última fecha en que el índice varía (después el valor es plano / proyectado)."""
        if not self._v:
            return None
        days = sorted(self._v)
        for i in range(len(days) - 1, 0, -1):
            if self._v[days[i]] != self._v[days[i - 1]]:
                return days[i]
        return days[0]


def _parse_embedded(data: bytes, start: int) -> Tuple[Dict[dt.date, float], int]:
    hdr = start
    nrec = struct.unpack("<I", data[hdr + 4:hdr + 8])[0]
    hlen, rlen = struct.unpack("<HH", data[hdr + 8:hdr + 12])
    out: Dict[dt.date, float] = {}
    base = hdr + hlen
    for i in range(nrec):
        r = data[base + i * rlen: base + (i + 1) * rlen]
        if len(r) < rlen or r[0:1] == b"*":
            continue
        try:
            d = dt.date(int(r[5:9]), int(r[3:5]), int(r[1:3]))
            out[d] = float(r[9:17])
        except ValueError:
            continue
    return out, nrec


def load_from_app(app_path: str) -> UfvTable:
    with open(app_path, "rb") as fh:
        data = fh.read()
    best: Optional[Dict[dt.date, float]] = None
    for m in _DIA_FIELD.finditer(data):
        start = m.start() - 32
        if start < 0 or data[start] not in (0x03, 0x30, 0x83, 0xF5):
            continue
        try:
            cand, _ = _parse_embedded(data, start)
        except (struct.error, ValueError):
            continue
        if cand and (best is None or (max(cand), len(cand)) > (max(best), len(best))):
            best = cand  # el .app puede traer una copia vieja: se usa la más reciente
    if not best:
        raise ValueError(f"No se encontró la tabla TIPCAMB dentro de {app_path}")
    return UfvTable(best, app_path)


def load_from_dbf(path: str) -> UfvTable:
    t = DbfTable(path)
    vals = {}
    for r in t.records():
        try:
            vals[dt.date(r["ANO"], r["MES"], r["DIA"])] = float(r["TC"])
        except (TypeError, ValueError):
            continue
    return UfvTable(vals, path)


def load_from_csv(path: str) -> UfvTable:
    vals = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            vals[dt.date.fromisoformat(row["fecha"])] = float(row["ufv"])
    return UfvTable(vals, path)


def bundled_csv() -> str:
    return os.path.join(os.path.dirname(__file__), "data", "ufv_embedded.csv")


def load_ufv(vsiaf_dir: Optional[str], dbfs_dir: Optional[str] = None) -> UfvTable:
    """Carga las UFV con el mismo origen que el VSIAF; si no existe, usa el CSV incluido."""
    if vsiaf_dir:
        app = find_file_ci(vsiaf_dir, "tipocambio.app")
        if app:
            try:
                return load_from_app(app)
            except (ValueError, OSError):
                pass
    if dbfs_dir:
        p = find_file_ci(dbfs_dir, "tipcamb.dbf")
        if p:
            try:
                return load_from_dbf(p)
            except Exception:
                pass
    return load_from_csv(bundled_csv())
