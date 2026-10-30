"""Normativa laboral, impositiva y contable boliviana con vigencia por fechas (editable por el administrador).

Los valores por defecto reflejan la normativa vigente a octubre de 2026. DEBEN verificarse periódicamente
contra la Gaceta Oficial / SIN / MTEPS; cada parámetro indica su fuente y puede cambiarse con nueva vigencia.
"""
from __future__ import annotations

import json
from datetime import date

from .db import Database
from .util import to_date

# (clave, vigente_desde, valor, descripción, fuente)
DEFECTOS: list[tuple[str, str, str, str, str]] = [
    ("SMN", "2023-01-01", "2362", "Salario mínimo nacional (Bs)", "DS 4849"),
    ("SMN", "2024-01-01", "2500", "Salario mínimo nacional (Bs)", "DS 5110 (2024)"),
    ("SMN", "2025-01-01", "2750", "Salario mínimo nacional (Bs)", "DS 5383 (2025)"),
    ("SMN", "2026-01-01", "3300", "Salario mínimo nacional (Bs)", "DS 5516 (2026)"),
    ("IVA_PCT", "1990-01-01", "13", "Alícuota del IVA (%)", "Ley 843"),
    ("IT_PCT", "1990-01-01", "3", "Alícuota del IT (%)", "Ley 843"),
    ("IUE_PCT", "2005-01-01", "25", "Alícuota del IUE (%)", "Ley 843, art. 50"),
    ("IUE_BE_PCT", "2005-01-01", "12.5", "IUE beneficiarios del exterior (%)", "Ley 843, art. 51"),
    ("RCIVA_PCT", "1990-01-01", "13", "Alícuota RC-IVA (%)", "Ley 843"),
    ("RCIVA_MIN_SMN", "2000-01-01", "4", "RC-IVA dependientes: ingreso no imponible (n.º de SMN)", "DS 21531"),
    ("RCIVA_CRED_SMN", "2000-01-01", "2", "RC-IVA: 13% sobre n.º de SMN como crédito por facturas presuntas", "DS 21531"),
    ("ITF_PCT", "2026-01-01", "0", "ITF (%): derogación aprobada en 2026; verificar vigencia", "Ley 1717/2026 (verificar)"),
    ("AFP_VEJEZ", "2000-01-01", "10", "Aporte laboral: cotización mensual (%)", "Ley 065"),
    ("AFP_RIESGO_COMUN", "2000-01-01", "1.71", "Aporte laboral: prima de riesgo común (%)", "Ley 065"),
    ("AFP_COMISION", "2000-01-01", "0.5", "Aporte laboral: comisión Gestora (%)", "Ley 065"),
    ("AFP_SOLIDARIO", "2000-01-01", "0.5", "Aporte laboral: aporte solidario del asegurado (%)", "Ley 065"),
    ("PAT_CNS", "2000-01-01", "10", "Aporte patronal: Caja de Salud (%)", "Código de Seguridad Social"),
    ("PAT_RIESGO_PROF", "2000-01-01", "1.71", "Aporte patronal: riesgo profesional (%)", "Ley 065"),
    ("PAT_VIVIENDA", "2000-01-01", "2", "Aporte patronal: Pro-Vivienda (%)", "DS 29272"),
    ("PAT_SOLIDARIO", "2000-01-01", "3", "Aporte patronal solidario (%)", "Ley 065"),
    ("PAT_SOLIDARIO", "2024-12-01", "3.5", "Aporte patronal solidario (%)", "Ley 1582 / DS 5280"),
    ("PAT_INFOCAL", "2000-01-01", "0", "Aporte patronal INFOCAL (%): habilitar si corresponde a la empresa", "Verificar aplicabilidad"),
    ("ANS_T1_MONTO", "2011-01-01", "13000", "ANS: tramo 1, total ganado desde (Bs)", "Ley 065"),
    ("ANS_T1_PCT", "2011-01-01", "1", "ANS: tramo 1 (%)", "Ley 065"),
    ("ANS_T2_MONTO", "2011-01-01", "25000", "ANS: tramo 2, total ganado desde (Bs)", "Ley 065"),
    ("ANS_T2_PCT", "2011-01-01", "5", "ANS: tramo 2 (%)", "Ley 065"),
    ("ANS_T3_MONTO", "2011-01-01", "35000", "ANS: tramo 3, total ganado desde (Bs)", "Ley 065"),
    ("ANS_T3_PCT", "2011-01-01", "10", "ANS: tramo 3 (%)", "Ley 065"),
    ("ANS_T1_PCT", "2024-12-01", "1.15", "ANS: tramo 1 (%)", "Ley 1582 / DS 5280"),
    ("ANS_T2_PCT", "2024-12-01", "5.74", "ANS: tramo 2 (%)", "Ley 1582 / DS 5280"),
    ("ANS_T3_PCT", "2024-12-01", "11.48", "ANS: tramo 3 (%)", "Ley 1582 / DS 5280"),
    ("BONO_ANTIG_BASE_SMN", "1990-01-01", "3", "Bono de antigüedad: base en n.º de SMN", "DS 21137"),
    ("BONO_ANTIG_ESCALA", "1990-01-01",
     json.dumps([[2, 5, 5], [5, 8, 11], [8, 11, 18], [11, 15, 26], [15, 20, 34], [20, 25, 42], [25, 999, 50]]),
     "Escala: [años desde, años hasta, %]", "DS 21137"),
    ("AGUINALDO_MESES_MIN", "1990-01-01", "3", "Aguinaldo: meses mínimos de antigüedad", "DS 1960"),
    ("SEGUNDO_AGUINALDO", "2000-01-01", "0", "Doble aguinaldo 'Esfuerzo por Bolivia' (1=sí): solo si crece PIB ≥ 4,5%", "DS 1802"),
    ("DIAS_MES_LABORAL", "1990-01-01", "30", "Días del mes para sueldos", "LGT"),
    ("HORAS_DIA", "1990-01-01", "8", "Horas por jornada diaria", "LGT"),
    ("RECARGO_HEXTRA_PCT", "1990-01-01", "100", "Recargo por hora extra (%)", "LGT art. 55"),
    ("RECARGO_NOCTURNO_PCT", "1990-01-01", "25", "Recargo nocturno (%)", "LGT art. 46"),
    ("RECARGO_DOMINICAL_PCT", "1990-01-01", "100", "Recargo por trabajo en domingo/feriado (%)", "LGT art. 56"),
    ("VACACION_ESCALA", "1990-01-01", json.dumps([[1, 5, 15], [5, 10, 20], [10, 999, 30]]),
     "Vacaciones: [años desde, hasta, días]", "LGT art. 44"),
    ("INDEM_MESES_POR_ANIO", "1990-01-01", "1", "Indemnización: sueldos por año de servicio", "LGT art. 13"),
    ("DESAHUCIO_MESES", "1990-01-01", "3", "Desahucio: meses de sueldo", "LGT art. 12"),
    ("AJUSTE_INFLACION_CONTABLE", "2020-12-10", "0",
     "Ajuste por inflación con UFV (NC 3): suspendido contablemente desde 10/12/2020 (CTNAC 03/2020); el SIN mantiene UFV para efectos tributarios",
     "CTNAC 03/2020; DS 24051 art. 38"),
    ("DEPRECIACION_ACTUALIZA_UFV", "1990-01-01", "0", "Actualizar activos fijos con UFV (efectos tributarios)", "DS 24051"),
]

# Grupos de activos fijos (DS 24051 art. 22): nombre, años de vida útil, % anual, cuentas
GRUPOS_ACTIVO = [
    ("Edificaciones", 40, 2.5, "1.2.1.01.002", "1.2.1.02.002", "5.3.1.04.002"),
    ("Muebles y Enseres", 10, 10, "1.2.1.01.003", "1.2.1.02.003", "5.3.1.04.003"),
    ("Equipo de Oficina", 8, 12.5, "1.2.1.01.004", "1.2.1.02.004", "5.3.1.04.004"),
    ("Equipo de Computación", 4, 25, "1.2.1.01.005", "1.2.1.02.005", "5.3.1.04.005"),
    ("Vehículos", 5, 20, "1.2.1.01.006", "1.2.1.02.006", "5.3.1.04.006"),
    ("Maquinaria y Equipo", 8, 12.5, "1.2.1.01.007", "1.2.1.02.007", "5.3.1.04.007"),
    ("Herramientas", 4, 25, "1.2.1.01.008", "1.2.1.02.008", "5.3.1.04.008"),
    ("Instalaciones", 8, 12.5, "1.2.1.01.009", "1.2.1.02.009", "5.3.1.04.009"),
]


class Normativa:
    """Acceso a los parámetros normativos vigentes a una fecha."""

    def __init__(self, db: Database):
        self.db = db
        self._cache: dict[str, list[tuple[str, str]]] = {}
        self.recargar()

    def recargar(self) -> None:
        self._cache = {}
        for r in self.db.query("SELECT clave, vigente_desde, valor FROM normativa ORDER BY clave, vigente_desde"):
            self._cache.setdefault(r["clave"], []).append((r["vigente_desde"], r["valor"]))

    def raw(self, clave: str, fecha: date | str | None = None) -> str:
        fecha_s = (to_date(fecha) or date.today()).isoformat()
        vigente = None
        for desde, valor in self._cache.get(clave, []):
            if desde <= fecha_s:
                vigente = valor
        if vigente is None:
            lista = self._cache.get(clave)
            if not lista:
                raise KeyError(f"Parámetro normativo no definido: {clave}")
            vigente = lista[0][1]
        return vigente

    def num(self, clave: str, fecha=None) -> float:
        return float(self.raw(clave, fecha))

    def json(self, clave: str, fecha=None):
        return json.loads(self.raw(clave, fecha))

    def listar(self) -> list[dict]:
        return self.db.query("SELECT * FROM normativa ORDER BY clave, vigente_desde")

    def guardar(self, clave: str, vigente_desde: str, valor: str, descripcion: str = "", fuente: str = "") -> None:
        self.db.execute(
            "INSERT INTO normativa (clave, vigente_desde, valor, descripcion, fuente) VALUES (?,?,?,?,?) "
            "ON CONFLICT(clave, vigente_desde) DO UPDATE SET valor=excluded.valor, descripcion=excluded.descripcion, fuente=excluded.fuente",
            (clave, vigente_desde, valor, descripcion, fuente))
        self.recargar()

    # atajos
    def smn(self, fecha=None) -> float:
        return self.num("SMN", fecha)


def sembrar_normativa(db: Database) -> None:
    for clave, desde, valor, desc, fuente in DEFECTOS:
        db.execute("INSERT OR IGNORE INTO normativa (clave, vigente_desde, valor, descripcion, fuente) VALUES (?,?,?,?,?)",
                   (clave, desde, valor, desc, fuente))
