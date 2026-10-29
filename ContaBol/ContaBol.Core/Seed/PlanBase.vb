Namespace Seed

    ''' <summary>
    ''' Plan de cuentas modelo para empresas comerciales / de costos en Bolivia (PCGA / NC), estructura 1.1.1.01.001.
    ''' Formato por línea: código;nombre;indicadores   U=moneda extranjera, A=ajustable por UFV, B=cuenta bancaria,
    ''' F/V=costo fijo/variable, -=cuenta regularizadora (naturaleza inversa), P=presupuestable.
    ''' </summary>
    Public Module PlanBase

        Public ReadOnly Lineas As String() = {
"1;ACTIVO",
"1.1;ACTIVO CORRIENTE",
"1.1.1;DISPONIBLE",
"1.1.1.01;Caja",
"1.1.1.01.001;Caja Moneda Nacional",
"1.1.1.01.002;Caja Moneda Extranjera;U",
"1.1.1.01.003;Caja Chica (Fondo Fijo)",
"1.1.1.02;Bancos Moneda Nacional",
"1.1.1.02.001;Banco Unión S.A. Cta. Cte. M/N;B",
"1.1.1.02.002;Banco Nacional de Bolivia S.A. Cta. Cte. M/N;B",
"1.1.1.02.003;Banco Mercantil Santa Cruz S.A. Cta. Cte. M/N;B",
"1.1.1.02.004;Banco de Crédito de Bolivia S.A. Cta. Cte. M/N;B",
"1.1.1.02.005;Banco BISA S.A. Cta. Cte. M/N;B",
"1.1.1.03;Bancos Moneda Extranjera",
"1.1.1.03.001;Banco Unión S.A. Cta. Cte. M/E;BU",
"1.1.1.03.002;Banco Nacional de Bolivia S.A. Cta. Cte. M/E;BU",
"1.1.1.04;Cajas de Ahorro",
"1.1.1.04.001;Caja de Ahorro Moneda Nacional;B",
"1.1.1.04.002;Caja de Ahorro Moneda Extranjera;BU",
"1.1.2;EXIGIBLE",
"1.1.2.01;Cuentas por Cobrar Comerciales",
"1.1.2.01.001;Clientes Moneda Nacional",
"1.1.2.01.002;Clientes Moneda Extranjera;U",
"1.1.2.01.003;Documentos por Cobrar",
"1.1.2.02;Anticipos Entregados",
"1.1.2.02.001;Anticipos a Proveedores",
"1.1.2.02.002;Anticipos de Sueldos al Personal",
"1.1.2.02.003;Anticipos a Rendir Cuenta",
"1.1.2.03;Impuestos por Recuperar",
"1.1.2.03.001;Crédito Fiscal IVA",
"1.1.2.03.002;Crédito Fiscal IVA por Compensar",
"1.1.2.03.003;IUE Pagado por Anticipado (compensable con IT)",
"1.1.2.03.004;Retenciones IUE / IT a Favor",
"1.1.2.04;Otras Cuentas por Cobrar",
"1.1.2.04.001;Cuentas por Cobrar a Empleados",
"1.1.2.04.002;Deudores Varios",
"1.1.2.05;Previsiones del Activo Exigible",
"1.1.2.05.001;Previsión para Cuentas Incobrables;-",
"1.1.3;REALIZABLE (INVENTARIOS)",
"1.1.3.01;Mercaderías",
"1.1.3.01.001;Inventario de Mercaderías;A",
"1.1.3.01.002;Mercaderías en Tránsito;A",
"1.1.3.02;Inventarios de Producción",
"1.1.3.02.001;Materia Prima;A",
"1.1.3.02.002;Productos en Proceso;A",
"1.1.3.02.003;Productos Terminados;A",
"1.1.3.02.004;Materiales y Suministros;A",
"1.1.4;DIFERIDO",
"1.1.4.01;Gastos Pagados por Anticipado",
"1.1.4.01.001;Seguros Pagados por Anticipado",
"1.1.4.01.002;Alquileres Pagados por Anticipado",
"1.1.4.01.003;Otros Gastos Pagados por Anticipado",
"1.2;ACTIVO NO CORRIENTE",
"1.2.1;ACTIVO FIJO",
"1.2.1.01;Activos Fijos",
"1.2.1.01.001;Terrenos;A",
"1.2.1.01.002;Edificios;A",
"1.2.1.01.003;Muebles y Enseres;A",
"1.2.1.01.004;Equipo de Oficina;A",
"1.2.1.01.005;Equipo de Computación;A",
"1.2.1.01.006;Vehículos;A",
"1.2.1.01.007;Maquinaria y Equipo;A",
"1.2.1.01.008;Herramientas;A",
"1.2.1.01.009;Instalaciones;A",
"1.2.1.01.010;Obras en Construcción;A",
"1.2.1.02;Depreciación Acumulada",
"1.2.1.02.002;Depreciación Acumulada Edificios;A-",
"1.2.1.02.003;Depreciación Acumulada Muebles y Enseres;A-",
"1.2.1.02.004;Depreciación Acumulada Equipo de Oficina;A-",
"1.2.1.02.005;Depreciación Acumulada Equipo de Computación;A-",
"1.2.1.02.006;Depreciación Acumulada Vehículos;A-",
"1.2.1.02.007;Depreciación Acumulada Maquinaria y Equipo;A-",
"1.2.1.02.008;Depreciación Acumulada Herramientas;A-",
"1.2.1.02.009;Depreciación Acumulada Instalaciones;A-",
"1.2.2;ACTIVO INTANGIBLE",
"1.2.2.01;Intangibles",
"1.2.2.01.001;Marcas y Patentes;A",
"1.2.2.01.002;Software y Licencias;A",
"1.2.2.01.003;Amortización Acumulada de Intangibles;A-",
"1.2.3;INVERSIONES PERMANENTES",
"1.2.3.01;Inversiones",
"1.2.3.01.001;Acciones y Participaciones;A",
"2;PASIVO",
"2.1;PASIVO CORRIENTE",
"2.1.1;CUENTAS POR PAGAR COMERCIALES",
"2.1.1.01;Proveedores",
"2.1.1.01.001;Proveedores Moneda Nacional",
"2.1.1.01.002;Proveedores Moneda Extranjera;U",
"2.1.1.01.003;Documentos por Pagar",
"2.1.1.02;Anticipos Recibidos",
"2.1.1.02.001;Anticipos de Clientes",
"2.1.1.03;Otras Cuentas por Pagar",
"2.1.1.03.001;Acreedores Varios",
"2.1.2;OBLIGACIONES FISCALES",
"2.1.2.01;Impuestos por Pagar",
"2.1.2.01.001;Débito Fiscal IVA",
"2.1.2.01.002;Impuesto a las Transacciones (IT) por Pagar",
"2.1.2.01.003;Impuesto a las Utilidades de las Empresas (IUE) por Pagar",
"2.1.2.01.004;Retenciones IUE por Pagar",
"2.1.2.01.005;Retenciones IT por Pagar",
"2.1.2.01.006;RC-IVA Retenido a Dependientes por Pagar",
"2.1.2.01.007;RC-IVA Retenido a Terceros por Pagar",
"2.1.3;OBLIGACIONES SOCIALES Y LABORALES",
"2.1.3.01;Sueldos y Aportes por Pagar",
"2.1.3.01.001;Sueldos y Salarios por Pagar",
"2.1.3.01.002;AFP Aportes Laborales por Pagar",
"2.1.3.01.003;AFP Aportes Patronales por Pagar",
"2.1.3.01.004;CNS Aporte Patronal por Pagar",
"2.1.3.01.005;Aporte Patronal Pro-Vivienda por Pagar",
"2.1.3.01.006;Aporte Patronal Solidario por Pagar",
"2.1.3.02;Provisiones Laborales",
"2.1.3.02.001;Provisión para Aguinaldos;A",
"2.1.3.02.002;Provisión para Primas;A",
"2.1.3.02.003;Provisión para Vacaciones;A",
"2.1.4;OBLIGACIONES FINANCIERAS",
"2.1.4.01;Préstamos de Corto Plazo",
"2.1.4.01.001;Préstamos Bancarios Corto Plazo M/N",
"2.1.4.01.002;Préstamos Bancarios Corto Plazo M/E;U",
"2.1.4.01.003;Intereses por Pagar",
"2.2;PASIVO NO CORRIENTE",
"2.2.1;OBLIGACIONES A LARGO PLAZO",
"2.2.1.01;Préstamos de Largo Plazo",
"2.2.1.01.001;Préstamos Bancarios Largo Plazo M/N",
"2.2.1.01.002;Préstamos Bancarios Largo Plazo M/E;U",
"2.2.1.02;Previsiones",
"2.2.1.02.001;Previsión para Indemnizaciones;A",
"2.2.1.02.002;Otras Previsiones",
"3;PATRIMONIO",
"3.1;CAPITAL Y RESERVAS",
"3.1.1;CAPITAL",
"3.1.1.01;Capital Social",
"3.1.1.01.001;Capital Social;A",
"3.1.1.01.002;Aportes por Capitalizar;A",
"3.1.1.01.003;Ajuste de Capital;A",
"3.1.2;RESERVAS",
"3.1.2.01;Reservas",
"3.1.2.01.001;Reserva Legal;A",
"3.1.2.01.002;Ajuste de Reservas Patrimoniales;A",
"3.1.2.01.003;Reserva por Revalúo Técnico de Activos Fijos;A",
"3.2;RESULTADOS",
"3.2.1;RESULTADOS",
"3.2.1.01;Resultados",
"3.2.1.01.001;Resultados Acumulados;A",
"3.2.1.01.002;Resultado de la Gestión",
"4;INGRESOS",
"4.1;INGRESOS OPERATIVOS",
"4.1.1;VENTAS",
"4.1.1.01;Ventas",
"4.1.1.01.001;Ventas de Mercaderías",
"4.1.1.01.002;Ventas de Productos Terminados",
"4.1.1.01.003;Ventas de Servicios",
"4.1.1.02;Rebajas y Devoluciones",
"4.1.1.02.001;Descuentos y Rebajas sobre Ventas;-",
"4.1.1.02.002;Devoluciones sobre Ventas;-",
"4.2;OTROS INGRESOS",
"4.2.1;INGRESOS NO OPERATIVOS",
"4.2.1.01;Otros Ingresos",
"4.2.1.01.001;Ingresos Financieros (Intereses Ganados)",
"4.2.1.01.002;Alquileres Percibidos",
"4.2.1.01.003;Otros Ingresos y Recargos en Ventas",
"4.2.1.01.004;Diferencia de Cambio (Ingreso)",
"4.2.1.01.005;Ajuste por Inflación y Tenencia de Bienes (Ingreso)",
"4.2.1.01.006;Mantenimiento de Valor (Ingreso)",
"4.2.1.01.007;Descuentos Obtenidos en Compras",
"4.2.1.01.008;Sobrantes de Caja",
"5;COSTOS Y GASTOS",
"5.1;COSTO DE VENTAS",
"5.1.1;COSTO DE VENTAS",
"5.1.1.01;Costo de Ventas",
"5.1.1.01.001;Costo de Mercaderías Vendidas;V",
"5.1.1.01.002;Costo de Productos Vendidos;V",
"5.1.1.01.003;Costo de Servicios Prestados;V",
"5.2;COSTOS DE PRODUCCIÓN",
"5.2.1;COSTOS DE PRODUCCIÓN",
"5.2.1.01;Costos de Producción",
"5.2.1.01.001;Materia Prima Consumida;V",
"5.2.1.01.002;Mano de Obra Directa;V",
"5.2.1.01.003;Costos Indirectos de Fabricación;F",
"5.3;GASTOS DE ADMINISTRACIÓN",
"5.3.1;GASTOS DE ADMINISTRACIÓN",
"5.3.1.01;Remuneraciones y Cargas Sociales",
"5.3.1.01.001;Sueldos y Salarios;F",
"5.3.1.01.002;Bono de Antigüedad;F",
"5.3.1.01.003;Horas Extras;F",
"5.3.1.01.004;Aguinaldos;F",
"5.3.1.01.005;Primas;F",
"5.3.1.01.006;Indemnizaciones y Desahucios;F",
"5.3.1.01.007;Vacaciones;F",
"5.3.1.01.008;Aporte Patronal Caja Nacional de Salud;F",
"5.3.1.01.009;Aporte Patronal Riesgo Profesional;F",
"5.3.1.01.010;Aporte Patronal Pro-Vivienda;F",
"5.3.1.01.011;Aporte Patronal Solidario;F",
"5.3.1.01.012;Otros Bonos y Beneficios;F",
"5.3.1.01.013;Capacitación al Personal;F",
"5.3.1.02;Servicios y Suministros",
"5.3.1.02.001;Energía Eléctrica;F",
"5.3.1.02.002;Agua Potable;F",
"5.3.1.02.003;Teléfono e Internet;F",
"5.3.1.02.004;Alquileres;F",
"5.3.1.02.005;Honorarios Profesionales;F",
"5.3.1.02.006;Servicios de Seguridad y Limpieza;F",
"5.3.1.02.007;Seguros;F",
"5.3.1.02.008;Mantenimiento y Reparaciones;F",
"5.3.1.02.009;Gastos de Viaje y Movilidad;V",
"5.3.1.02.010;Material de Escritorio y Oficina;F",
"5.3.1.02.011;Fotocopias e Impresiones;F",
"5.3.1.02.012;Gastos Legales y Notariales;F",
"5.3.1.02.013;Suscripciones y Afiliaciones;F",
"5.3.1.02.014;Gastos Generales;F",
"5.3.1.03;Impuestos y Tasas",
"5.3.1.03.001;Impuesto a las Transacciones (IT);F",
"5.3.1.03.002;Impuesto a las Utilidades de las Empresas (IUE);F",
"5.3.1.03.003;Impuesto a la Propiedad de Bienes;F",
"5.3.1.03.004;Patentes y Tasas Municipales;F",
"5.3.1.03.005;Multas y Recargos (No Deducibles);F",
"5.3.1.04;Depreciaciones y Amortizaciones",
"5.3.1.04.002;Depreciación de Edificios;F",
"5.3.1.04.003;Depreciación de Muebles y Enseres;F",
"5.3.1.04.004;Depreciación de Equipo de Oficina;F",
"5.3.1.04.005;Depreciación de Equipo de Computación;F",
"5.3.1.04.006;Depreciación de Vehículos;F",
"5.3.1.04.007;Depreciación de Maquinaria y Equipo;F",
"5.3.1.04.008;Depreciación de Herramientas;F",
"5.3.1.04.009;Depreciación de Instalaciones;F",
"5.3.1.04.010;Amortización de Intangibles;F",
"5.3.1.05;Previsiones",
"5.3.1.05.001;Previsión para Cuentas Incobrables;F",
"5.3.1.05.002;Pérdida por Cuentas Incobrables;F",
"5.4;GASTOS DE COMERCIALIZACIÓN",
"5.4.1;GASTOS DE COMERCIALIZACIÓN",
"5.4.1.01;Gastos de Venta",
"5.4.1.01.001;Publicidad y Propaganda;V",
"5.4.1.01.002;Comisiones sobre Ventas;V",
"5.4.1.01.003;Fletes y Transportes;V",
"5.4.1.01.004;Gastos de Embalaje;V",
"5.4.1.01.005;Mermas y Pérdidas de Inventario;V",
"5.4.1.01.006;Recargos en Compras;V",
"5.5;GASTOS FINANCIEROS",
"5.5.1;GASTOS FINANCIEROS",
"5.5.1.01;Gastos Financieros",
"5.5.1.01.001;Intereses Pagados;F",
"5.5.1.01.002;Comisiones y Gastos Bancarios;F",
"5.5.1.01.003;Diferencia de Cambio (Gasto);F",
"5.5.1.01.004;Ajuste por Inflación y Tenencia de Bienes (Gasto);F",
"5.5.1.01.005;Mantenimiento de Valor (Gasto);F",
"5.6;OTROS GASTOS",
"5.6.1;OTROS GASTOS",
"5.6.1.01;Otros Gastos",
"5.6.1.01.001;Pérdidas por Faltantes;F",
"5.6.1.01.002;Baja de Activos Fijos;F",
"5.6.1.01.003;Gastos de Gestiones Anteriores;F",
"5.6.1.01.004;Gastos No Deducibles;F",
"6;CUENTAS DE ORDEN DEUDORAS",
"6.1;CUENTAS DE ORDEN",
"6.1.1;CUENTAS DE ORDEN DEUDORAS",
"6.1.1.01;Cuentas de Orden",
"6.1.1.01.001;Mercaderías Recibidas en Consignación",
"6.1.1.01.002;Garantías Entregadas",
"7;CUENTAS DE ORDEN ACREEDORAS",
"7.1;CUENTAS DE ORDEN",
"7.1.1;CUENTAS DE ORDEN ACREEDORAS",
"7.1.1.01;Cuentas de Orden",
"7.1.1.01.001;Responsabilidad por Mercaderías en Consignación",
"7.1.1.01.002;Garantías Recibidas"
        }

        ''' <summary>Valores por defecto de los parámetros (cuentas por código).</summary>
        Public Function ParametrosPorDefecto() As Dictionary(Of String, String)
            Dim p As New Dictionary(Of String, String)
            p("IVA_PCT") = "13"
            p("IT_PCT") = "3"
            p("IT_SIN_FACTURA") = "1"
            p("DESC_REC_EN_BASE") = "1"
            p("NIVEL_IMPRESION") = "5"
            p("CONTROL_PRESUPUESTO") = "0"
            p("STOCK_NEGATIVO") = "0"
            p("TC_DEFECTO") = "6.96"
            p("SMN") = "2500"
            p("CTA_CAJA") = "1.1.1.01.001"
            p("CTA_CF_IVA") = "1.1.2.03.001"
            p("CTA_DF_IVA") = "2.1.2.01.001"
            p("CTA_IT_GASTO") = "5.3.1.03.001"
            p("CTA_IT_PAGAR") = "2.1.2.01.002"
            p("CTA_CXC") = "1.1.2.01.001"
            p("CTA_CXP") = "2.1.1.01.001"
            p("CTA_ANT_CLI") = "2.1.1.02.001"
            p("CTA_ANT_PROV") = "1.1.2.02.001"
            p("CTA_INVENT") = "1.1.3.01.001"
            p("CTA_VENTAS") = "4.1.1.01.001"
            p("CTA_COSTO_VTA") = "5.1.1.01.001"
            p("CTA_DESC_VEN") = "4.1.1.02.001"
            p("CTA_REC_VEN") = "4.2.1.01.003"
            p("CTA_DESC_COMP") = "4.2.1.01.007"
            p("CTA_REC_COMP") = "5.4.1.01.006"
            p("CTA_MERMAS") = "5.4.1.01.005"
            p("CTA_AJUSTE_ING") = "4.2.1.01.005"
            p("CTA_AJUSTE_EGR") = "5.5.1.01.004"
            p("CTA_DIFCAMBIO_ING") = "4.2.1.01.004"
            p("CTA_DIFCAMBIO_EGR") = "5.5.1.01.003"
            p("CTA_RESULTADO") = "3.2.1.01.002"
            p("CTA_RESULT_ACUM") = "3.2.1.01.001"
            p("CTA_MP") = "1.1.3.02.001"
            p("CTA_PT") = "1.1.3.02.003"
            p("CTA_MOD") = "5.2.1.01.002"
            p("CTA_CIF") = "5.2.1.01.003"
            p("CTA_AJUSTE_AF") = "4.2.1.01.005"
            p("CTA_SUELDOS") = "5.3.1.01.001"
            p("CTA_BONO_ANTIG") = "5.3.1.01.002"
            p("CTA_HEXTRAS") = "5.3.1.01.003"
            p("CTA_OTROS_BONOS") = "5.3.1.01.012"
            p("CTA_SUELDOS_PAGAR") = "2.1.3.01.001"
            p("CTA_AFP_LAB_PAGAR") = "2.1.3.01.002"
            p("CTA_AFP_PAT_PAGAR") = "2.1.3.01.003"
            p("CTA_CNS_PAGAR") = "2.1.3.01.004"
            p("CTA_VIVIENDA_PAGAR") = "2.1.3.01.005"
            p("CTA_SOLIDARIO_PAGAR") = "2.1.3.01.006"
            p("CTA_RCIVA_PAGAR") = "2.1.2.01.006"
            p("CTA_ANTICIPO_PERS") = "1.1.2.02.002"
            p("CTA_GASTO_CNS") = "5.3.1.01.008"
            p("CTA_GASTO_RIESGO") = "5.3.1.01.009"
            p("CTA_GASTO_VIVIENDA") = "5.3.1.01.010"
            p("CTA_GASTO_SOLIDARIO") = "5.3.1.01.011"
            p("CTA_GASTO_AGUINALDO") = "5.3.1.01.004"
            p("CTA_PROV_AGUINALDO") = "2.1.3.02.001"
            p("CTA_GASTO_INDEM") = "5.3.1.01.006"
            p("CTA_PROV_INDEM") = "2.2.1.02.001"
            ' Planillas: porcentajes de aportes (editables, verificar vigencia)
            p("PL_AFP_VEJEZ") = "10"
            p("PL_AFP_RIESGO") = "1.71"
            p("PL_AFP_COMISION") = "0.5"
            p("PL_AFP_SOLIDARIO") = "0.5"
            p("PL_PAT_CNS") = "10"
            p("PL_PAT_RIESGO") = "1.71"
            p("PL_PAT_VIVIENDA") = "2"
            p("PL_PAT_SOLIDARIO") = "3"
            p("PL_RCIVA_PCT") = "13"
            p("PL_RCIVA_MIN_SMN") = "4"
            p("PL_RCIVA_CRED_SMN") = "2"
            p("PL_ANS_T1") = "13000"
            p("PL_ANS_T2") = "25000"
            p("PL_ANS_T3") = "35000"
            p("PL_DIAS_MES") = "30"
            Return p
        End Function

        ''' <summary>Grupos de activos fijos según D.S. 24051 (nombre, vida útil en años, % depreciación, cuenta activo, dep. acum., gasto).</summary>
        Public ReadOnly GruposActivo As String() = {
            "Edificios;40;2.5;1.2.1.01.002;1.2.1.02.002;5.3.1.04.002",
            "Muebles y Enseres;10;10;1.2.1.01.003;1.2.1.02.003;5.3.1.04.003",
            "Equipo de Oficina;8;12.5;1.2.1.01.004;1.2.1.02.004;5.3.1.04.004",
            "Equipo de Computación;4;25;1.2.1.01.005;1.2.1.02.005;5.3.1.04.005",
            "Vehículos;5;20;1.2.1.01.006;1.2.1.02.006;5.3.1.04.006",
            "Maquinaria y Equipo;8;12.5;1.2.1.01.007;1.2.1.02.007;5.3.1.04.007",
            "Herramientas;4;25;1.2.1.01.008;1.2.1.02.008;5.3.1.04.008",
            "Instalaciones;8;12.5;1.2.1.01.009;1.2.1.02.009;5.3.1.04.009"
        }

    End Module

End Namespace
