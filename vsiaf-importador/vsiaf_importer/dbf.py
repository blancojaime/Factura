"""Lectura / escritura mínima de tablas Visual FoxPro (.DBF + .FPT).

Solo implementa lo que necesita el VSIAF: agregar registros, modificar campos
de un registro existente y marcar/desmarcar registros como borrados.  NO toca
los índices (.CDX); después de importar hay que ejecutar *Administradores →
Re-indexar* dentro del VSIAF (ver la guía de uso).

Todas las operaciones se hacen en memoria; ``save()`` vuelca el archivo a disco
de una sola vez (escribe a un temporal y reemplaza), de modo que una
importación fallida no deja tablas a medias.
"""
from __future__ import annotations

import datetime as _dt
import os
import struct
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, Iterator, List, Optional

# Byte 29 de la cabecera = "language driver".  El VSIAF usa 0x03 (cp1252) en casi
# todas sus tablas y 0x02 (cp850) en AUXILIAR.DBF.
LANG_ENCODING = {
    0x00: "cp1252", 0x01: "cp437", 0x02: "cp850", 0x03: "cp1252",
    0x04: "mac_roman", 0x64: "cp852", 0x65: "cp866", 0x66: "cp865",
    0x78: "cp950", 0x79: "cp949", 0x7A: "cp936", 0x7B: "cp932",
    0xC8: "cp1250", 0xC9: "cp1251", 0xCA: "cp1254", 0xCB: "cp1253",
}
EOF_MARK = b"\x1a"


class DbfError(Exception):
    pass


@dataclass(frozen=True)
class Field:
    name: str
    type: str
    length: int
    decimals: int
    offset: int  # desplazamiento dentro del registro (el byte 0 es el flag de borrado)


@dataclass
class Record:
    recno: int          # 1-based, igual que RECNO() de FoxPro
    deleted: bool
    values: Dict[str, Any]

    def __getitem__(self, k: str) -> Any:
        return self.values[k.upper()]

    def get(self, k: str, default: Any = None) -> Any:
        return self.values.get(k.upper(), default)


def find_file_ci(folder: str, name: str) -> Optional[str]:
    """Busca ``name`` en ``folder`` sin distinguir mayúsculas (Windows sí, Linux no)."""
    direct = os.path.join(folder, name)
    if os.path.exists(direct):
        return direct
    low = name.lower()
    try:
        for f in os.listdir(folder):
            if f.lower() == low:
                return os.path.join(folder, f)
    except FileNotFoundError:
        pass
    return None


def round_half_up(x: float, nd: int = 2) -> float:
    q = Decimal(1).scaleb(-nd)
    return float(Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP))


class DbfTable:
    def __init__(self, path: str, encoding: Optional[str] = None):
        self.path = path
        with open(path, "rb") as fh:
            self._buf = bytearray(fh.read())
        self._parse_header()
        self.encoding = encoding or LANG_ENCODING.get(self.lang, "cp1252")
        self.memo_path: Optional[str] = None
        self._memo: Optional[bytearray] = None
        if any(f.type in "MGP" for f in self.fields):
            base, _ = os.path.splitext(path)
            for ext in (".FPT", ".fpt", ".Fpt"):
                if os.path.exists(base + ext):
                    self.memo_path = base + ext
                    break
            if self.memo_path is None:
                raise DbfError(f"{os.path.basename(path)}: falta el archivo de memo (.FPT)")
            with open(self.memo_path, "rb") as fh:
                self._memo = bytearray(fh.read())
        self._dirty = False

    # ------------------------------------------------------------------ cabecera
    def _parse_header(self) -> None:
        b = self._buf
        if len(b) < 33:
            raise DbfError(f"{self.path}: archivo DBF demasiado corto")
        self.version = b[0]
        self.nrec = struct.unpack("<I", b[4:8])[0]
        self.hlen, self.rlen = struct.unpack("<HH", b[8:12])
        self.lang = b[29]
        fields: List[Field] = []
        pos, off = 32, 1
        while pos < len(b) and b[pos] != 0x0D:
            d = b[pos:pos + 32]
            name = d[:11].split(b"\0")[0].decode("ascii", "replace").upper()
            ftype = chr(d[11])
            fields.append(Field(name, ftype, d[16], d[17], off))
            off += d[16]
            pos += 32
        if off != self.rlen:
            raise DbfError(f"{self.path}: longitud de registro inconsistente ({off} != {self.rlen})")
        self.fields = fields
        self.field_map = {f.name: f for f in fields}

    @property
    def name(self) -> str:
        return os.path.basename(self.path)

    def __len__(self) -> int:
        return self.nrec

    # ------------------------------------------------------------------ lectura
    def _rec_off(self, recno: int) -> int:
        return self.hlen + (recno - 1) * self.rlen

    def read(self, recno: int) -> Record:
        if not 1 <= recno <= self.nrec:
            raise DbfError(f"{self.name}: registro {recno} fuera de rango")
        off = self._rec_off(recno)
        raw = bytes(self._buf[off:off + self.rlen])
        return Record(recno, raw[0:1] == b"*", {f.name: self._decode(f, raw) for f in self.fields})

    def records(self, include_deleted: bool = False) -> Iterator[Record]:
        for n in range(1, self.nrec + 1):
            rec = self.read(n)
            if rec.deleted and not include_deleted:
                continue
            yield rec

    def _decode(self, f: Field, rec: bytes) -> Any:
        raw = rec[f.offset:f.offset + f.length]
        t = f.type
        if t == "C":
            return raw.decode(self.encoding, "replace").rstrip(" \0")
        if t in "NF":
            s = raw.decode("ascii", "replace").strip()
            if not s or s.strip("*") == "":
                return None
            try:
                return float(s) if (f.decimals or "." in s) else int(s)
            except ValueError:
                return None
        if t == "D":
            s = raw.decode("ascii", "replace").strip()
            if not s:
                return None
            try:
                return _dt.date(int(s[:4]), int(s[4:6]), int(s[6:8]))
            except ValueError:
                return None
        if t == "L":
            c = raw.decode("ascii", "replace").strip().upper()
            return True if c in ("T", "Y") else (False if c in ("F", "N") else None)
        if t == "I":
            return struct.unpack("<i", raw)[0]
        if t == "B":
            return struct.unpack("<d", raw)[0]
        if t == "Y":
            return struct.unpack("<q", raw)[0] / 10000
        if t == "T":
            jd, ms = struct.unpack("<ii", raw)
            if not jd:
                return None
            return _dt.datetime(1, 1, 1) + _dt.timedelta(days=jd - 1721426, milliseconds=ms)
        if t == "M":
            return self._read_memo(self._memo_ptr(f, raw))
        return raw

    # ------------------------------------------------------------------ memo
    def _memo_ptr(self, f: Field, raw: bytes) -> int:
        if f.length == 4:
            return struct.unpack("<I", raw)[0]
        s = raw.decode("ascii", "replace").strip()
        return int(s) if s.isdigit() else 0

    def _memo_blocksize(self) -> int:
        assert self._memo is not None
        return struct.unpack(">H", self._memo[6:8])[0] or 64

    def _read_memo(self, block: int) -> Optional[str]:
        if not block or self._memo is None:
            return None
        o = block * self._memo_blocksize()
        if o + 8 > len(self._memo):
            return None
        _typ, ln = struct.unpack(">II", self._memo[o:o + 8])
        return bytes(self._memo[o + 8:o + 8 + ln]).decode(self.encoding, "replace")

    def _write_memo(self, text: str) -> int:
        assert self._memo is not None
        data = text.encode(self.encoding)
        bs = self._memo_blocksize()
        block = struct.unpack(">I", self._memo[0:4])[0]
        nblocks = (8 + len(data) + bs - 1) // bs
        start = block * bs
        if len(self._memo) < start:
            self._memo.extend(b"\0" * (start - len(self._memo)))
        del self._memo[start:]
        self._memo.extend(struct.pack(">II", 1, len(data)) + data)
        self._memo.extend(b"\0" * (nblocks * bs - 8 - len(data)))
        self._memo[0:4] = struct.pack(">I", block + nblocks)
        return block

    # ------------------------------------------------------------------ codificación
    def _encode(self, f: Field, value: Any) -> bytes:
        t = f.type
        if t == "C":
            s = "" if value is None else str(value)
            b = s.encode(self.encoding, "replace")
            if len(b) > f.length:
                raise DbfError(f"{self.name}.{f.name}: valor demasiado largo ({len(b)} > {f.length})")
            return b.ljust(f.length, b" ")
        if t in "NF":
            if value is None or value == "":
                return b" " * f.length
            if f.decimals:
                s = f"{float(value):.{f.decimals}f}"
            else:
                s = str(int(round(float(value))))
            if len(s) > f.length:
                raise DbfError(f"{self.name}.{f.name}: número fuera de rango ({s})")
            return s.rjust(f.length).encode("ascii")
        if t == "D":
            if not value:
                return b" " * 8
            return value.strftime("%Y%m%d").encode("ascii")
        if t == "L":
            return b"?" if value is None else (b"T" if value else b"F")
        if t == "M":
            if value is None or str(value) == "":
                return b"\0\0\0\0" if f.length == 4 else b" " * f.length
            if self._memo is None:
                raise DbfError(f"{self.name}: la tabla no tiene archivo de memo")
            blk = self._write_memo(str(value))
            return struct.pack("<I", blk) if f.length == 4 else str(blk).rjust(f.length).encode("ascii")
        if t == "I":
            return struct.pack("<i", int(value or 0))
        raise DbfError(f"{self.name}.{f.name}: tipo de campo '{t}' no soportado para escritura")

    def _blank_record(self) -> bytearray:
        rec = bytearray(b" " * self.rlen)
        for f in self.fields:
            if f.type in "NFDC" or f.type == "M":
                continue
            if f.type == "L":
                rec[f.offset] = ord("F")
            elif f.type in "IBYT":
                rec[f.offset:f.offset + f.length] = b"\0" * f.length
        return rec

    # ------------------------------------------------------------------ escritura
    def append(self, values: Dict[str, Any]) -> int:
        rec = self._blank_record()
        for k, v in values.items():
            f = self.field_map.get(k.upper())
            if f is None:
                raise DbfError(f"{self.name}: no existe el campo {k}")
            rec[f.offset:f.offset + f.length] = self._encode(f, v)
        pos = self._rec_off(self.nrec + 1)
        del self._buf[pos:]
        self._buf.extend(rec)
        self._buf.extend(EOF_MARK)
        self.nrec += 1
        self._buf[4:8] = struct.pack("<I", self.nrec)
        self._touch_header()
        self._dirty = True
        return self.nrec

    def update(self, recno: int, values: Dict[str, Any]) -> None:
        if not 1 <= recno <= self.nrec:
            raise DbfError(f"{self.name}: registro {recno} fuera de rango")
        base = self._rec_off(recno)
        for k, v in values.items():
            f = self.field_map.get(k.upper())
            if f is None:
                raise DbfError(f"{self.name}: no existe el campo {k}")
            self._buf[base + f.offset:base + f.offset + f.length] = self._encode(f, v)
        self._touch_header()
        self._dirty = True

    def set_deleted(self, recno: int, deleted: bool = True) -> None:
        self._buf[self._rec_off(recno)] = 0x2A if deleted else 0x20
        self._touch_header()
        self._dirty = True

    def _touch_header(self) -> None:
        # Se respeta la convención que ya usa cada archivo (años desde 1900, o YY).
        today = _dt.date.today()
        y = self._buf[1]
        self._buf[1] = today.year - 1900 if y >= 100 else today.year % 100
        self._buf[2] = today.month
        self._buf[3] = today.day

    # ------------------------------------------------------------------ guardar
    def save(self) -> None:
        if not self._dirty:
            return
        _atomic_write(self.path, bytes(self._buf))
        if self.memo_path and self._memo is not None:
            _atomic_write(self.memo_path, bytes(self._memo))
        self._dirty = False

    @property
    def files(self) -> List[str]:
        out = [self.path]
        if self.memo_path:
            out.append(self.memo_path)
        return out


def _atomic_write(path: str, data: bytes) -> None:
    import stat
    tmp = path + ".vsiaf_imp_tmp"
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    try:                                   # archivos extraídos de un .rar/.zip pueden venir como "solo lectura"
        if not os.access(path, os.W_OK):
            os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
    except OSError:
        pass
    try:
        os.replace(tmp, path)
    except PermissionError as e:
        os.remove(tmp)
        raise DbfError(f"No se pudo escribir {os.path.basename(path)}: está en uso (¿VSIAF abierto?) o sin permisos.") from e


# ---------------------------------------------------------------------- creación (pruebas)
def create_table(path: str, spec: List[tuple], lang: int = 0x03, memo_blocksize: int = 64,
                 version: int = 0xF5) -> None:
    """Crea una tabla vacía.  ``spec`` = [(nombre, tipo, largo, decimales), ...].

    Solo se usa en las pruebas automáticas (para fabricar una BD de ejemplo con la
    misma estructura que el VSIAF) y en el generador de datos de demostración.
    """
    nf = len(spec)
    hlen = 32 + 32 * nf + 1
    rlen = 1 + sum(s[2] for s in spec)
    head = bytearray(32)
    head[0] = version
    today = _dt.date.today()
    head[1:4] = bytes([today.year - 1900, today.month, today.day])
    head[8:10] = struct.pack("<H", hlen)
    head[10:12] = struct.pack("<H", rlen)
    head[29] = lang
    body = bytearray()
    off = 1
    for name, t, ln, dec in spec:
        d = bytearray(32)
        d[:len(name)] = name.encode("ascii")
        d[11] = ord(t)
        d[12:16] = struct.pack("<I", off)
        d[16] = ln
        d[17] = dec
        body += d
        off += ln
    with open(path, "wb") as fh:
        fh.write(bytes(head) + bytes(body) + b"\r" + EOF_MARK)
    if any(s[1] == "M" for s in spec):
        base, _ = os.path.splitext(path)
        nb = 512 // memo_blocksize
        hdr = struct.pack(">I", nb) + b"\0\0" + struct.pack(">H", memo_blocksize)
        with open(base + ".FPT", "wb") as fh:
            fh.write(hdr.ljust(512, b"\0"))
