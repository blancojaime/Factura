"""Contexto de servicios y utilidades comunes."""
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from ..core import security
from ..calc.deuda import DeudaParams


class ServiceError(Exception):
    """Error de negocio mostrable al usuario."""


@dataclass
class Ctx:
    db: object
    session: object = None      # security.Session o None (procesos internos)

    @property
    def user(self):
        return self.session.usuario if self.session else "sistema"

    def require(self, perm):
        if self.session is not None and not self.session.can(perm):
            raise ServiceError(f"Su rol ({self.session.rol}) no tiene permiso para esta operación ({perm}).")

    def log(self, accion, tabla=None, registro=None, detalle=None):
        security.audit(self.db, self.user, accion, tabla, registro, detalle)


def hoy() -> str:
    return date.today().isoformat()


def ahora() -> str:
    return datetime.now().strftime("%H:%M:%S")


def numero(db, prefijo, fecha=None, ancho=6) -> str:
    anio = (fecha or hoy())[:4]
    return f"{prefijo}-{anio}-{db.next_number(f'{prefijo}{anio}'):0{ancho}d}"


def dv11(digits: str) -> int:
    pesos = [2, 3, 4, 5, 6, 7]
    s = sum(int(c) * pesos[i % 6] for i, c in enumerate(reversed(digits)))
    r = 11 - (s % 11)
    return 0 if r >= 10 else r


def codigo_pago(rubro: str, gestion: int, id_: int) -> str:
    base = f"{gestion % 100:02d}{id_:08d}"
    return f"{rubro[0]}{base}{dv11(base)}"


def deuda_params(db, persona="N", multa_df=True) -> DeudaParams:
    return DeudaParams(
        r=Decimal("0"), persona=persona, multa_df=multa_df, df_pct=Decimal(db.param("df_pct", "10")) / 100,
        df_min_n=Decimal(db.param("persona_df_min_n", "50")), df_min_j=Decimal(db.param("persona_df_min_j", "240")),
        df_max=Decimal(db.param("df_max", "2400")), modo_df_ufv=db.param("modo_df_ufv", "DIVISION"),
        decimales=int(db.param("redondeo_deuda", "0")), sancion_adm=Decimal(db.param("sancion_administrativa", "0")))


def cotizacion(db, fecha, max_atraso=10):
    """(dolar, ufv, exacta). Arrastra la última cotización conocida (fin de semana/feriado) hasta `max_atraso` días."""
    f = str(fecha)[:10]
    r = db.one("SELECT dolar,ufv,fecha FROM cotizaciones WHERE fecha<=? ORDER BY fecha DESC LIMIT 1", (f,))
    if not r:
        raise ServiceError(f"No hay cotización de dólar/UFV cargada para {f} ni fechas anteriores (Mantenimiento ▸ Cotizaciones).")
    if (date.fromisoformat(f) - date.fromisoformat(r["fecha"])).days > max_atraso:
        raise ServiceError(f"La última cotización de dólar/UFV cargada es del {r['fecha']}; cargue las cotizaciones hasta {f} (Mantenimiento ▸ Cotizaciones).")
    return Decimal(str(r["dolar"])), Decimal(str(r["ufv"])), r["fecha"] == f


def tasa_interes(db, fecha) -> Decimal:
    r = db.one("SELECT r FROM tasas_interes WHERE desde<=? ORDER BY desde DESC LIMIT 1", (str(fecha)[:10],))
    if r:
        return Decimal(str(r[0]))
    p = db.param("tasa_interes")
    if p:
        return Decimal(p)
    raise ServiceError("No hay tasa de interés vigente (Mantenimiento ▸ Parámetros ▸ Tasas de interés).")


def row_dict(r):
    return {k: r[k] for k in r.keys()} if r is not None else None


def j(obj):
    return json.dumps(obj, ensure_ascii=False, default=str)
