"""Plantillas parametrizables de los módulos de auditoría: marcas, aseveraciones, programas de trabajo, cédulas y modelos de informes.

Las referencias normativas son orientativas y deben verificarse contra la norma vigente (Gaceta Oficial, SIN, CAUB/CTNAC)."""
from __future__ import annotations

MARCAS = [("V", "Verificado / cotejado sin diferencias", "#287846"), ("S", "Sumado (verificación aritmética)", "#1F3A5F"), ("M", "Cotejado con el Libro Mayor", "#2E5E96"),
          ("D", "Cotejado con documentación de respaldo", "#0F7C8A"), ("C", "Confirmado por terceros (circularización)", "#6C4AB6"), ("F", "Verificado mediante inspección física", "#B7791F"),
          ("R", "Recalculado por el auditor", "#2E7D4F"), ("T", "Rastreado hasta el registro contable", "#5B6675"), ("N", "No conforme: ver hallazgo", "#B02424"), ("A", "Con ajuste propuesto", "#C0392B")]

ASEVERACIONES = ["Existencia", "Integridad", "Valuación / asignación", "Derechos y obligaciones", "Presentación y revelación"]

# (índice, título, prefijos de cuenta, naturaleza)
SUMARIAS_F = [("A", "Disponible (caja y bancos)", ["1.1.1"], "D"), ("B", "Exigible (cuentas por cobrar e impuestos por recuperar)", ["1.1.2"], "D"),
              ("C", "Inventarios (mercaderías, materia prima, productos en proceso y terminados)", ["1.1.3"], "D"), ("D", "Gastos pagados por anticipado", ["1.1.4"], "D"),
              ("E", "Activos fijos y depreciación acumulada", ["1.2.1"], "D"), ("F", "Intangibles e inversiones permanentes", ["1.2.2", "1.2.3"], "D"),
              ("AA", "Cuentas por pagar comerciales y anticipos", ["2.1.1"], "C"), ("BB", "Obligaciones fiscales", ["2.1.2"], "C"), ("CC", "Obligaciones sociales y laborales", ["2.1.3"], "C"),
              ("DD", "Obligaciones financieras y previsiones de largo plazo", ["2.1.4", "2.2"], "C"), ("PP", "Patrimonio", ["3"], "C"), ("II", "Ingresos", ["4"], "C"),
              ("GG", "Costos y gastos", ["5"], "D")]
SUMARIAS_T = [("T1", "Débito fiscal IVA", ["2.1.2.01.001"], "C"), ("T2", "Crédito fiscal IVA", ["1.1.2.03.001"], "D"), ("T3", "Impuesto a las Transacciones (IT)", ["2.1.2.01.002", "5.3.1.03.001"], "C"),
              ("T4", "IUE y retenciones", ["2.1.2.01.003", "2.1.2.01.004", "2.1.2.01.005", "5.3.1.03.002"], "C"), ("T5", "RC-IVA y obligaciones sociales", ["2.1.2.01.006", "2.1.2.01.007", "2.1.3.01"], "C"),
              ("T6", "Ventas e ingresos gravados", ["4"], "C"), ("T7", "Costos y gastos deducibles", ["5"], "D")]

# componente -> lista de (procedimiento, aseveración, base normativa)
PROGRAMAS_F = {
    "A": ("Disponibilidades", "Comprobar la existencia, propiedad y adecuada valuación de caja y bancos.", [
        ("Realizar arqueo sorpresivo de caja y fondos fijos y cotejar con el saldo contable.", "Existencia", "NIA 500"),
        ("Obtener confirmaciones bancarias a la fecha de cierre (saldos, créditos, garantías).", "Existencia / Derechos", "NIA 505"),
        ("Revisar las conciliaciones bancarias y los movimientos pendientes posteriores al cierre.", "Integridad", "NIA 330"),
        ("Verificar la valuación en moneda extranjera al tipo de cambio de cierre y su diferencia de cambio.", "Valuación", "NC 6; NIA 540"),
        ("Revisar cheques en tránsito, partidas antiguas y transferencias entre cuentas (corte).", "Integridad", "NIA 330"),
        ("Verificar revelaciones y restricciones sobre el disponible en las Notas a los EEFF.", "Presentación", "NIA 700")]),
    "B": ("Cuentas por cobrar", "Comprobar existencia y cobrabilidad del exigible.", [
        ("Circularizar saldos de clientes significativos (confirmación positiva) y aplicar procedimientos alternativos.", "Existencia", "NIA 505"),
        ("Probar el corte de ventas: facturas y notas de entrega cercanas al cierre.", "Integridad / Corte", "NIA 330"),
        ("Analizar la antigüedad de saldos y evaluar la previsión para cuentas incobrables.", "Valuación", "NIA 540"),
        ("Conciliar el auxiliar de clientes con la cuenta de mayor.", "Integridad", "NIA 500"),
        ("Verificar cobros posteriores a la fecha de cierre.", "Existencia / Valuación", "NIA 500"),
        ("Revisar anticipos, impuestos por recuperar y cuentas con partes relacionadas.", "Derechos", "NIA 550")]),
    "C": ("Inventarios", "Comprobar existencia, propiedad y valuación de inventarios (mercaderías, materia prima, productos en proceso y terminados).", [
        ("Asistir al recuento físico y realizar pruebas de conteo (muestra del sistema al físico y del físico al sistema).", "Existencia / Integridad", "NIA 501"),
        ("Probar el corte documental de entradas y salidas alrededor de la fecha de cierre.", "Integridad / Corte", "NIA 501"),
        ("Recalcular el costo promedio ponderado y el kardex valorado de la muestra.", "Valuación", "NC 8; NIA 540"),
        ("Aplicar la prueba de valor neto de realización (VNR) y evaluar obsolescencia y productos vencidos.", "Valuación", "NC 8; NIA 540"),
        ("Revisar mercadería en tránsito, en consignación y en poder de terceros.", "Derechos", "NIA 501"),
        ("Conciliar el inventario valorado del kardex con la cuenta contable.", "Integridad", "NIA 500")]),
    "E": ("Activos fijos y depreciaciones", "Comprobar existencia, propiedad, valuación y depreciación de bienes de uso.", [
        ("Inspeccionar físicamente una muestra de activos y rastrear a los registros.", "Existencia", "NIA 500"),
        ("Verificar altas del período con facturas y contratos; revisar capitalizaciones.", "Valuación / Derechos", "NIA 500"),
        ("Verificar bajas y ventas y su resultado contable.", "Integridad", "NIA 500"),
        ("Recalcular la depreciación según los coeficientes del D.S. 24051 y contrastar con lo registrado.", "Valuación", "D.S. 24051 art. 22"),
        ("Recalcular la actualización por UFV cuando corresponda (NC 3 / efectos tributarios).", "Valuación", "NC 3; D.S. 24051 art. 38"),
        ("Revisar gravámenes, seguros y revelaciones.", "Presentación", "NIA 700")]),
    "CC": ("Planillas y pasivos laborales", "Comprobar la integridad y exactitud de sueldos, aportes y provisiones sociales.", [
        ("Conciliar planilla de sueldos con el mayor y con las planillas de la Gestora Pública y Cajas de Salud.", "Integridad", "NIA 500"),
        ("Recalcular aportes laborales y patronales con los porcentajes vigentes.", "Valuación", "Ley 065; D.S. 5280"),
        ("Recalcular la provisión de aguinaldo y de indemnización (beneficios sociales).", "Valuación", "NIA 540; D.S. 1960"),
        ("Conciliar la planilla tributaria RC-IVA con los Formularios 110 y las retenciones.", "Integridad", "D.S. 21531"),
        ("Verificar pagos posteriores y pasivos no registrados (búsqueda de pasivos omitidos).", "Integridad", "NIA 500")]),
    "COSTOS": ("Costos de conversión", "Comprobar la asignación de materia prima, mano de obra y costos indirectos a las órdenes de producción.", [
        ("Rastrear una muestra de órdenes de producción: requisiciones de materia prima, horas de mano de obra y CIF aplicado.", "Valuación", "NC 8; NIA 500"),
        ("Recalcular la cuota de aplicación de CIF y analizar variaciones entre CIF real y aplicado.", "Valuación", "NIA 520"),
        ("Probar el corte de producción en proceso y la transferencia a productos terminados.", "Integridad / Corte", "NIA 501"),
        ("Conciliar costo de ventas con los movimientos de kardex.", "Integridad", "NIA 500")]),
    "AA": ("Cuentas por pagar y obligaciones", "Comprobar la integridad de los pasivos.", [
        ("Circularizar proveedores significativos y conciliar estados de cuenta.", "Integridad", "NIA 505"),
        ("Buscar pasivos no registrados: pagos posteriores y facturas recibidas después del cierre.", "Integridad", "NIA 330"),
        ("Verificar obligaciones financieras, intereses devengados y garantías con confirmaciones.", "Derechos y obligaciones", "NIA 505"),
        ("Verificar obligaciones fiscales con las declaraciones juradas presentadas.", "Valuación", "Ley 843")]),
    "PP": ("Patrimonio", "Comprobar capital, reservas y resultados acumulados.", [
        ("Verificar el capital social con escritura constitutiva, testimonios y libro de socios o accionistas.", "Derechos", "Código de Comercio"),
        ("Revisar movimientos del patrimonio del período (aportes, capitalizaciones, distribución de utilidades) y su soporte en actas.", "Presentación", "NIA 500"),
        ("Verificar la reserva legal y el Estado de Evolución del Patrimonio Neto.", "Presentación", "NC 1")]),
    "II": ("Ingresos y gastos", "Comprobar el reconocimiento de ingresos y la adecuada clasificación de costos y gastos.", [
        ("Realizar procedimientos analíticos sustantivos de ingresos (mes a mes, margen bruto).", "Ocurrencia / Integridad", "NIA 520"),
        ("Probar el corte de ingresos y gastos alrededor del cierre.", "Corte", "NIA 330"),
        ("Rastrear una muestra de ventas desde el pedido hasta el cobro y la factura.", "Ocurrencia", "NIA 500"),
        ("Revisar gastos significativos con su documentación y la adecuada imputación al período.", "Valuación / Clasificación", "NIA 500"),
        ("Verificar la partida de ajuste por inflación y diferencia de cambio.", "Valuación", "NC 3; NC 6")]),
}

PROGRAMAS_T = {
    "T1": ("Débito fiscal IVA", "Comprobar que el débito fiscal declarado coincide con las ventas facturadas y el Libro de Ventas.", [
        ("Conciliar el débito fiscal del Libro de Ventas con los Formularios 200 presentados y con el mayor contable.", "Integridad", "Ley 843 art. 4; D.S. 21530"),
        ("Cotejar ventas registradas contra facturas emitidas (secuencia, anuladas, no utilizadas).", "Integridad", "RND de facturación vigente"),
        ("Verificar la correcta determinación de la base imponible (descuentos, bonificaciones, exportaciones).", "Valuación", "D.S. 21530"),
        ("Verificar la facturación en línea: modalidad, CUF y contingencias.", "Cumplimiento", "RND de facturación vigente")]),
    "T2": ("Crédito fiscal IVA", "Comprobar que el crédito fiscal cumple los requisitos de procedencia.", [
        ("Conciliar el crédito fiscal del Libro de Compras con los Formularios 200 y con el mayor.", "Integridad", "Ley 843 art. 8"),
        ("Verificar la vinculación de la compra con la actividad gravada, la validez de la factura y su registro oportuno.", "Derechos", "Ley 843 art. 8; D.S. 21530 art. 8"),
        ("Verificar la bancarización: operaciones de Bs 50.000 o más con medio fehaciente de pago.", "Cumplimiento", "Ley 843; D.S. 27310 art. 37"),
        ("Revisar proporcionalidad del crédito fiscal en operaciones mixtas.", "Valuación", "D.S. 21530")]),
    "T3": ("Impuesto a las Transacciones", "Comprobar la determinación del IT y su compensación con el IUE.", [
        ("Recalcular el IT sobre ingresos brutos y conciliar con los Formularios 400 y el mayor.", "Valuación", "Ley 843 arts. 72-77; D.S. 21532"),
        ("Verificar la compensación del IT con el IUE pagado (PAGO A CUENTA).", "Valuación", "D.S. 24051")]),
    "T4": ("IUE y retenciones", "Comprobar la depuración de gastos y la determinación del IUE.", [
        ("Elaborar la cédula de depuración de gastos (deducibles y no deducibles) y la utilidad imponible.", "Valuación", "Ley 843 arts. 36-54; D.S. 24051 art. 8"),
        ("Verificar gastos sin factura, retenciones asumidas, multas y previsiones no admitidas.", "Valuación", "D.S. 24051"),
        ("Verificar donaciones (límite del 10 % de la utilidad neta imponible).", "Valuación", "D.S. 24051 art. 18"),
        ("Recalcular depreciaciones con los coeficientes legales.", "Valuación", "D.S. 24051 art. 22"),
        ("Revisar retenciones de IUE-BE, IT y RC-IVA practicadas a terceros y su pago.", "Cumplimiento", "Ley 843; D.S. 24051")]),
    "T5": ("RC-IVA y obligaciones sociales", "Comprobar retenciones de dependientes y aportes.", [
        ("Conciliar planilla tributaria RC-IVA (Formulario 110) con retenciones, saldos y Formulario 608.", "Integridad", "D.S. 21531"),
        ("Verificar aportes laborales y patronales con las planillas de la Gestora Pública y Cajas de Salud.", "Cumplimiento", "Ley 065")]),
    "T6": ("Deberes formales e ITC", "Comprobar el cumplimiento de deberes formales y la información tributaria complementaria.", [
        ("Verificar vigencia de NIT, libros contables, Libros de Compras y Ventas y presentación de declaraciones.", "Cumplimiento", "Ley 2492 arts. 70, 162"),
        ("Preparar los anexos de la Información Tributaria Complementaria (ITC) y conciliarlos con los estados financieros.", "Presentación", "RND SIN vigente (ITC)"),
        ("Cuantificar contingencias tributarias (tributo omitido, mantenimiento de valor, intereses y sanciones).", "Valuación", "Ley 2492 arts. 47, 165")]),
}

ANEXOS_ITC = [
    (1, "Detalle de ingresos operativos y otros ingresos"), (2, "Detalle de costos y gastos"), (3, "Conciliación del Débito Fiscal IVA con el Libro de Ventas"),
    (4, "Conciliación del Crédito Fiscal IVA con el Libro de Compras"), (5, "Conciliación del Impuesto a las Transacciones (IT)"), (6, "Depuración de gastos y determinación del IUE"),
    (7, "Detalle de activos fijos y depreciaciones (D.S. 24051)"), (8, "Detalle de inventarios"), (9, "Detalle de cuentas por cobrar"), (10, "Detalle de cuentas por pagar y obligaciones fiscales"),
    (11, "Planilla de sueldos, aportes y retenciones RC-IVA"), (12, "Operaciones sujetas a bancarización (Bs 50.000 o más)"), (13, "Patrimonio y evolución"),
    (14, "Retenciones practicadas a terceros"), (15, "Hallazgos y contingencias tributarias")]

KAM_PLANTILLA = ("Cuestión clave de auditoría: {titulo}. Descripción: {descripcion}. Respuesta de auditoría: {respuesta}.")
