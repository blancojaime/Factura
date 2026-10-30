import os
import shutil
import sys
import tempfile
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contabol.sistema import Sistema  # noqa: E402


class Entorno:
    def __init__(self, anio=2025, mensual=True):
        self.dir = tempfile.mkdtemp(prefix="contabol_test_")
        self.sis = Sistema(self.dir)
        self.usuario = self.sis.autenticar("admin", "admin")
        self.eid, self.gid = self.sis.crear_empresa(
            {"codigo": "TEST", "razon_social": "Comercial Prueba S.R.L.", "nit": "1020304050", "direccion": "Av. Camacho 123", "ciudad": "La Paz"},
            anio, self.usuario, mensual)
        self.ctx = self.sis.abrir_contexto(self.usuario, self.eid, self.gid)
        self.anio = anio

    def cta(self, codigo):
        c = self.ctx.cuentas.por_codigo(codigo)
        assert c, codigo
        return c["id"]

    def asiento(self, fecha, debe, haber, monto, glosa="prueba", tipo="T"):
        return self.ctx.vouchers.crear({"tipo": tipo, "fecha": fecha, "glosa": glosa, "lineas": [
            {"cuenta_id": self.cta(debe), "debe": monto}, {"cuenta_id": self.cta(haber), "haber": monto}]})

    def saldo(self, codigo, hasta=None):
        return self.ctx.cuentas.saldo(self.cta(codigo), hasta)

    def cerrar(self):
        try:
            self.ctx.cerrar()
            self.sis.close()
        finally:
            shutil.rmtree(self.dir, ignore_errors=True)


@pytest.fixture
def env():
    e = Entorno()
    yield e
    e.cerrar()


CAJA = "1.1.1.01.001"
BANCO = "1.1.1.02.001"
CAPITAL = "3.1.1.01.001"
VENTAS = "4.1.1.01.001"
GASTO_LUZ = "5.3.1.02.001"
