"""Bloque de captura SIGEP para el comprobante C-31:
   DA | UE | PROGRAMA | PROYECTO | ACTIVIDAD | FTE | ORG | PARTIDA | IMPORTE
Se genera una linea por partida a partir de los preventivos (o del presupuesto previsto, antes de certificar).
"""
from collections import OrderedDict
from decimal import Decimal

ENCABEZADO = ["DA", "UE", "PROGRAMA", "PROYECTO", "ACTIVIDAD", "FTE", "ORG", "PARTIDA", "IMPORTE"]


def construir(params: dict[str, str], lineas: list[tuple]) -> dict:
    """lineas: [(partida: PartidaPresupuestaria, importe: Decimal)] -> agrupa por partida."""
    acumulado: "OrderedDict[str, tuple]" = OrderedDict()
    for partida, importe in lineas:
        k = str(partida.id)
        if k in acumulado:
            acumulado[k] = (partida, acumulado[k][1] + Decimal(importe))
        else:
            acumulado[k] = (partida, Decimal(importe))
    filas = []
    for partida, importe in acumulado.values():
        filas.append([params.get("da", ""), params.get("ue", ""), partida.programa, partida.proyecto,
                      partida.actividad, partida.fuente, partida.organismo, partida.codigo_partida,
                      f"{Decimal(importe):.2f}"])
    total = sum((Decimal(f[-1]) for f in filas), Decimal("0"))
    return {
        "encabezado": ENCABEZADO,
        "filas": filas,
        "texto_pipe": "\n".join(" | ".join(f) for f in filas),
        "texto_tsv": "\n".join("\t".join(f) for f in filas),
        "total": f"{total:.2f}",
    }
