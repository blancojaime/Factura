"""Contexto de trabajo: empresa + gestión abiertas, usuario, base de datos y servicios."""
from __future__ import annotations

from datetime import date

from .db import Database
from .sistema import ErrorNegocio
from .util import to_date


class Contexto:
    def __init__(self, sistema, usuario: dict, empresa: dict, gestion: dict, db: Database):
        self.sistema = sistema
        self.usuario = usuario
        self.empresa = empresa
        self.gestion = gestion
        self.db = db
        self.normativa = sistema.normativa
        self._param: dict[str, str] | None = None
        self._permisos = sistema.permisos(usuario["id"], empresa["id"])
        self._servicios: dict[str, object] = {}

    # ---- permisos y estado
    def puede(self, opcion: str) -> bool:
        return not opcion or opcion in self._permisos

    def requiere(self, opcion: str) -> None:
        if not self.puede(opcion):
            raise ErrorNegocio("No tiene permiso para realizar esta operación.")

    @property
    def abierta(self) -> bool:
        return self.gestion["estado"] == "A"

    def requiere_abierta(self) -> None:
        if not self.abierta:
            raise ErrorNegocio(f"La gestión {self.gestion['anio']} está cerrada: solo permite consultas y reportes.")

    @property
    def inicio(self) -> date:
        return to_date(self.gestion["fecha_inicio"])

    @property
    def fin(self) -> date:
        return to_date(self.gestion["fecha_fin"])

    def requiere_fecha(self, fecha) -> date:
        f = to_date(fecha)
        if f is None:
            raise ErrorNegocio("La fecha no es válida.")
        if f < self.inicio or f > self.fin:
            raise ErrorNegocio(f"La fecha {f:%d/%m/%Y} está fuera de la gestión ({self.inicio:%d/%m/%Y} al {self.fin:%d/%m/%Y}).")
        return f

    # ---- parámetros de la gestión
    def param(self, clave: str, defecto: str = "") -> str:
        if self._param is None:
            self._param = {r["clave"]: r["valor"] for r in self.db.query("SELECT clave, valor FROM parametro")}
        return self._param.get(clave, defecto)

    def set_param(self, clave: str, valor: str) -> None:
        self.db.execute("INSERT INTO parametro (clave, valor) VALUES (?,?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor", (clave, valor))
        self._param = None

    def params(self) -> dict[str, str]:
        self.param("")
        return dict(self._param or {})

    def pnum(self, clave: str, defecto: float = 0.0) -> float:
        try:
            return float(self.param(clave, str(defecto)))
        except ValueError:
            return defecto

    def cuenta_por_codigo(self, codigo: str) -> dict | None:
        return self.db.one("SELECT * FROM cuenta WHERE codigo=?", (codigo,))

    def cuenta_param(self, clave: str) -> int:
        """Id de la cuenta configurada en el parámetro; error claro si no existe."""
        cod = self.param(clave)
        c = self.cuenta_por_codigo(cod) if cod else None
        if not c:
            raise ErrorNegocio(f"Falta configurar la cuenta '{clave}' en Parámetros (código '{cod}' inexistente en el plan).")
        if not c["es_movimiento"]:
            raise ErrorNegocio(f"La cuenta {c['codigo']} configurada en '{clave}' no es de movimiento.")
        return c["id"]

    # ---- servicios (carga diferida)
    def __getattr__(self, nombre: str):
        if nombre.startswith("_"):
            raise AttributeError(nombre)
        mapa = {
            "cuentas": ("contabol.services.cuentas", "CuentaService"),
            "tc": ("contabol.services.tipocambio", "TipoCambioService"),
            "vouchers": ("contabol.services.comprobantes", "ComprobanteService"),
            "iva": ("contabol.services.iva", "IvaService"),
            "terceros": ("contabol.services.terceros", "TerceroService"),
            "inventario": ("contabol.services.inventario", "InventarioService"),
            "ventas": ("contabol.services.comercial", "VentaService"),
            "compras": ("contabol.services.comercial", "CompraService"),
            "cobros": ("contabol.services.comercial", "CobroPagoService"),
            "activos": ("contabol.services.activos", "ActivoService"),
            "rrhh": ("contabol.services.planillas", "PlanillaService"),
            "produccion": ("contabol.services.produccion", "ProduccionService"),
            "presupuesto": ("contabol.services.presupuesto", "PresupuestoService"),
            "bancos": ("contabol.services.bancos", "BancoService"),
            "libros": ("contabol.services.libros", "LibroService"),
            "estados": ("contabol.services.estados", "EstadosService"),
            "gestiones": ("contabol.services.gestion", "GestionService"),
        }
        if nombre not in mapa:
            raise AttributeError(nombre)
        if nombre not in self._servicios:
            import importlib
            mod, cls = mapa[nombre]
            self._servicios[nombre] = getattr(importlib.import_module(mod), cls)(self)
        return self._servicios[nombre]

    def auditar(self, modulo: str, accion: str, detalle: str = "") -> None:
        self.sistema.auditar(self.usuario, self.empresa["id"], self.gestion["id"], modulo, accion, detalle)

    def cerrar(self) -> None:
        self.db.close()
