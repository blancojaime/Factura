"""Modelo de reporte independiente del formato: una misma definición se exporta a pantalla, PDF y Excel."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Col:
    titulo: str
    ancho: float = 1.0            # peso relativo
    tipo: str = "txt"             # txt, money, num, int, pct, date
    decimales: int = 2


@dataclass
class Fila:
    valores: list
    estilo: str = ""              # '', titulo, grupo, subtotal, total
    nivel: int = 0                # sangría del primer texto


@dataclass
class Tabla:
    cols: list[Col]
    filas: list[Fila] = field(default_factory=list)
    titulo: str = ""
    sin_encabezado: bool = False

    def add(self, *valores, estilo: str = "", nivel: int = 0) -> "Tabla":
        self.filas.append(Fila(list(valores), estilo, nivel))
        return self


@dataclass
class Texto:
    texto: str
    estilo: str = ""              # '', titulo, nota


@dataclass
class ReporteDef:
    titulo: str
    subtitulo: str = ""
    periodo: str = ""
    moneda: str = "Expresado en Bolivianos"
    empresa: str = ""
    nit: str = ""
    direccion: str = ""
    gestion: str = ""
    usuario: str = ""
    orientacion: str = "V"        # V vertical, H horizontal
    firmas: list[str] = field(default_factory=list)
    bloques: list = field(default_factory=list)
    notas: list[str] = field(default_factory=list)
    emitido: str = field(default_factory=lambda: datetime.now().strftime("%d/%m/%Y %H:%M"))
    nombre_archivo: str = ""

    def tabla(self, cols: list[Col], titulo: str = "", sin_encabezado: bool = False) -> Tabla:
        t = Tabla(cols, titulo=titulo, sin_encabezado=sin_encabezado)
        self.bloques.append(t)
        return t

    def texto(self, texto: str, estilo: str = "") -> None:
        self.bloques.append(Texto(texto, estilo))

    @property
    def tablas(self) -> list[Tabla]:
        return [b for b in self.bloques if isinstance(b, Tabla)]

    @property
    def total_filas(self) -> int:
        return sum(len(t.filas) for t in self.tablas)


def base(ctx, titulo: str, periodo: str = "", subtitulo: str = "", moneda: str = "BS", horizontal: bool = False, firmas: bool = True) -> ReporteDef:
    e = ctx.empresa
    return ReporteDef(
        titulo=titulo, subtitulo=subtitulo, periodo=periodo,
        moneda="Expresado en Bolivianos" if moneda.upper() in ("BS", "BOB") else "Expresado en Dólares Estadounidenses",
        empresa=e["razon_social"], nit=e.get("nit") or "", direccion=", ".join(x for x in (e.get("direccion"), e.get("ciudad")) if x),
        gestion=f"Gestión {ctx.gestion['anio']}", usuario=ctx.usuario["login"], orientacion="H" if horizontal else "V",
        firmas=["Contador", "Representante Legal"] if firmas else [])
