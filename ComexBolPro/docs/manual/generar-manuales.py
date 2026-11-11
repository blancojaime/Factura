#!/usr/bin/env python3
"""Genera los manuales (DOCX + PDF) con las capturas reales. Uso: python3 generar-manuales.py"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from docgen import Manual

AQUI = os.path.dirname(os.path.abspath(__file__)); C = AQUI + "/capturas/"; A = C + "anotadas/"; I = C + "instalador/"
VERSION, FECHA = "1.2.0", "2 de noviembre de 2026"

# ============================================================== MANUAL DE USUARIO
def manual_usuario():
    m = Manual("Manual de Usuario", "COMEX JB: decidir, acompañar y documentar una importación paso a paso", VERSION, FECHA)
    m.contenido(["Qué es y para qué sirve", "Instalación en un clic", "Ingreso al sistema", "Conociendo la ventana", "Arancel: cargar y mantener",
        "Crear y eliminar importaciones", "Registrar mercancías (selector de partida, editar y eliminar)", "Valoración aduanera (DAV)", "Liquidación detallada y costo nacionalizado", "Decidir: comparar escenarios",
        "Despacho aduanero (DIM, canales y descargos)", "Acompañar: ruta crítica y semáforos", "Documentar: legajo y bitácora", "Costos reales", "Leer facturas con OCR", "Contrastar con la DIM real",
        "Configuración (tipos de cambio, UFV, parámetros, perfil, usuarios, respaldo)", "Exportar (Excel, JSON y expediente)", "Problemas frecuentes y límites"])

    m.h1("1. Qué es y para qué sirve")
    m.p("**COMEX JB** es un asistente de escritorio para Windows que le ayuda en tres cosas durante una **importación a Bolivia**:")
    m.bullets(["**Decidir:** calcula cuánto pagará de tributos, cuánto le cuesta cada unidad puesta en su almacén y qué oferta (FOB, CIF, DAP…) le conviene.",
               "**Valorar y liquidar:** guía la declaración del valor (Decisión 571 de la CAN), calcula cada tributo con su fórmula a la vista y llega hasta el costo por unidad puesto en su almacén.",
               "**Acompañar:** le muestra los 12 pasos de la importación con fechas y semáforos, prepara y valida la DIM y le guía según el canal (verde, amarillo, rojo).",
               "**Documentar:** guarda automáticamente una bitácora, controla qué documentos faltan, compara lo proyectado con lo realmente pagado y genera el expediente."])
    m.caja("Importante", "COMEX JB es una **herramienta de apoyo**. Las cifras se calculan con el Arancel Aduanero de Importaciones 2026 y los parámetros "
           "tributarios configurados, pero **la liquidación oficial la determina la Aduana Nacional**. Antes de usarlo en operaciones reales, "
           "contraste el cálculo con 3 importaciones ya despachadas (sección 16) y consulte a su despachante.")

    m.h1("2. Instalación en un clic")
    m.bullets(["Haga doble clic en **ComexJB-Setup-1.2.0.exe**. No necesita permisos de administrador: el instalador incluye todo (también el lector OCR).",
               "Si Windows muestra «**Windows protegió su PC**» (SmartScreen), pulse **Más información → Ejecutar de todas formas**. Aparece porque el instalador aún no tiene firma digital comercial.",
               "Espere la barra de progreso (menos de un minuto). Al terminar, la aplicación se abre sola y se crean accesos directos en el Escritorio y en el menú Inicio.",
               "Si tenía instalada la versión anterior «ComexBol Pro», el instalador la reemplaza y **conserva sus datos** (se copian solos al primer inicio).",
               "Para desinstalar: **Configuración de Windows → Aplicaciones → COMEX JB → Desinstalar**. Sus datos no se borran."], num=True)

    m.h1("3. Ingreso al sistema")
    m.p("COMEX JB pide **usuario y clave** para entrar. La primera vez que se abre, el sistema le pide crear al **administrador**: escriba su nombre completo, un usuario y una clave (mínimo 6 caracteres) dos veces.")
    m.figura(C + "01-primer-uso.png", "Primer uso: pantalla de creación del administrador.", 8)
    m.figura(C + "02-primer-uso-lleno.png", "Datos completos. Al pulsar «Crear administrador e ingresar» se abre el sistema.", 8)
    m.tabla([["Rol", "Qué puede hacer"],
        ["Administrador", "Todo: operaciones, arancel (importar/editar), parámetros tributarios, usuarios, respaldo."],
        ["Operador", "Trabaja con operaciones y consulta el arancel; no cambia parámetros tributarios, no importa el arancel ni administra usuarios."]], [4, 13])
    m.p("Las claves se guardan **cifradas** (PBKDF2-SHA256 con sal); nadie, ni el administrador, puede verlas. Si olvida la clave, otro administrador puede cambiarla en Configuración → Usuarios. "
        "Use **Cerrar sesión** (abajo a la izquierda) al terminar.")

    m.h1("4. Conociendo la ventana")
    m.figura(C + "30-panel.png", "Panel de control con datos de una jornada.")
    m.tabla([["Zona", "Para qué sirve"],
        ["Menú lateral", "**Panel de control**, **Operaciones**, **Arancel**, **Configuración** y **Acerca de**. Abajo, el usuario conectado y «Cerrar sesión»."],
        ["Tarjetas de colores", "Operaciones registradas, etapas en alerta (vencen en 2 días o menos), etapas vencidas, **estado del arancel**, tipo de cambio y UFV vigentes."],
        ["Avisos del sistema", "Le dice qué falta: arancel sin cargar, tipo de cambio sin registrar, perfil del importador incompleto."],
        ["Próximos vencimientos", "Etapas de todas sus operaciones ordenadas por fecha."]], [4, 13])
    m.p("La tarjeta azul **«Arancel cargado»** responde en todo momento a la pregunta: *¿ya está cargado el arancel?* Muestra «No cargado» o «8.132 partidas · versión 2026».")

    m.h1("5. Arancel: cargar y mantener")
    m.p("Abra **Arancel** en el menú. Si todavía no lo cargó, verá una franja **roja**: «El arancel NO está cargado».")
    m.figura(C + "04-arancel-sin-cargar.png", "Arancel sin cargar: franja roja y tabla vacía.")
    m.bullets(["Pulse **Importar arancel (PDF)…** (solo administrador).", "Seleccione **los tres archivos PDF del Arancel 2026 a la vez** (mantenga Ctrl) y pulse Abrir.",
               "La lectura tarda aproximadamente dos minutos; el avance se muestra en pantalla (archivo y página). Al terminar aparece un resumen y, si hubo filas dudosas, su lista."], num=True)
    m.figura(C + "05-arancel-importando.png", "Importando: «Leyendo arancel: archivo 1, página 50…».")
    m.figura(C + "06-arancel-cargado.png", "Arancel cargado: franja verde «8.132 partidas · versión 2026 · 76 prohibidas · 245 con ICE/IEHD · 0 agregadas a mano».")
    m.h3("Tabla para modificar, agregar o eliminar partidas")
    m.p("Después de la primera carga, la tabla le permite **mantener** el arancel sin volver a importarlo:")
    m.bullets(["**Buscar:** escriba parte del código o del nombre del producto (por ejemplo «8471» o «tractor»).",
               "**Modificar:** haga clic en una fila; los datos aparecen en el cuadro de la derecha. Cambie lo necesario y pulse **Guardar**. La fuente de la partida pasa a «(modificada)».",
               "**Agregar:** pulse **Nueva partida**, complete el código de 10 dígitos, la descripción y el gravamen arancelario (GA) y guarde. Se marca como «MANUAL».",
               "**Eliminar:** seleccione la fila y pulse **Eliminar** (pide confirmación)."], num=True)
    m.figura(C + "07-arancel-buscar-editar.png", "Búsqueda por código (8471300010) y edición de la partida en el cuadro derecho.")
    m.caja("Cuidado con las modificaciones", "Cambiar un GA en la tabla afecta a **todos** los cálculos futuros. Registre el motivo (decreto o resolución) fuera del sistema. "
           "Si importa de nuevo el arancel oficial, el catálogo se reemplaza, pero sus operaciones no se tocan.", "FDE8E7")

    m.h1("6. Crear y eliminar importaciones")
    m.bullets(["En **Operaciones**, escriba el **N.º de carpeta** (por ejemplo IMP-2026-001) y elija el **Incoterm** pactado con su proveedor.", "Pulse **Crear importación**."], num=True)
    m.figura(C + "08-nueva-importacion.png", "Importación creada: aparece en la lista, se dibuja la ruta crítica (12 pasos) y la barra inferior lo confirma.")
    m.p("El **Incoterm** define qué ya está incluido en el precio de la factura. El sistema suma solo lo que falta (flete, seguro…) para obtener el **valor en aduana (CIF)**:")
    m.tabla([["Incoterm", "El precio de factura ya incluye", "Usted debe agregar"],
        ["EXW", "Nada", "Gastos de origen, flete y seguro"], ["FCA, FAS, FOB", "Entrega en origen", "Flete y seguro"],
        ["CFR, CPT", "Flete", "Seguro"], ["CIF, CIP", "Flete y seguro", "Nada"],
        ["DAP, DPU, DDP", "Todo hasta destino", "Nada; **reste** lo posterior a la frontera"]], [3.5, 6.5, 7])
    m.h3("Eliminar una operación equivocada")
    m.p("Seleccione la operación en la lista y pulse el botón rojo **Eliminar operación** (abajo del listado). El sistema pide confirmación y borra la operación con **todo su contenido** (ítems, liquidaciones, ruta, costos y bitácora). **No se puede deshacer.**")
    m.figura(C + "32-confirmar-eliminar-operacion.png", "Confirmación antes de eliminar la operación.")
    m.p("Con el cuadro **Buscar** puede filtrar la lista por número de carpeta.")

    m.h1("7. Registrar mercancías (selector de partida, editar y eliminar)")
    m.h3("Elegir la partida y completar la descripción automáticamente")
    m.p("En el cuadro **Partida NANDINA** escriba el **código** o una **palabra del nombre** del producto: aparece una lista con las partidas del arancel, con su gravamen, unidad y el documento exigido. Haga clic en la que corresponda y el sistema completa **el código y la descripción**. El resto de los datos se escribe a mano.")
    m.figura(C + "09-selector-partida.png", "Escribiendo «tablet»: lista de partidas sugeridas.")
    m.figura(C + "10-selector-por-codigo.png", "Escribiendo «84713000»: las partidas que empiezan con ese código.")
    m.p("Si escribe el código completo de 10 dígitos de una partida que existe, la descripción también se completa sola. Puede **editar la descripción** libremente (por ejemplo, para poner el modelo comercial).")
    m.figura(C + "11-formulario-item.png", "Partida elegida (GA 10 %, unidad «u»), descripción automática, y valor, peso y costos digitados.")
    m.tabla([["Campo", "Qué escribir"],
        ["Valor factura (USD), Cantidad, Peso bruto (kg)", "Valor total de la factura de esa mercancía, las **unidades** (sirven para el precio unitario y el costo por unidad) y su peso bruto."],
        ["Antigüedad (años)", "Solo vehículos: 0 = nuevo. Determina la tasa del ICE (Apéndice I del arancel)."],
        ["Marca, Modelo, N.º de serie, País de origen", "Ficha técnica: salen en el JSON para la DMI y en el expediente."],
        ["Acuerdo comercial, Desgravación %", "Solo si tiene Certificado de Origen. Con desgravación 0 se toma la preferencia del arancel para ese acuerdo."],
        ["ICE % (manual)", "Solo si el arancel no trae la tasa (bebidas alcohólicas, tabaco)."],
        ["Flete internacional, Seguro (USD)", "Solo los que su Incoterm **no** incluye. Se conservan al agregar más ítems."]], [6, 11])
    m.p("Pulse **Agregar ítem**. El sistema **valida antes de guardar**: la partida debe tener 10 dígitos y existir en el arancel, la descripción es obligatoria, el valor debe ser mayor que 0, etc. Un ítem inválido no se guarda.")
    m.figura(C + "12-item-agregado.png", "Ítem agregado: aparece en la lista de la izquierda con su GA.")
    m.h3("Editar un ítem")
    m.p("Seleccione el ítem en la lista (o haga doble clic) y pulse **Editar ítem**: sus datos pasan al formulario y el botón cambia a **Guardar cambios del ítem**. Modifique y guarde (o **Limpiar** para cancelar).")
    m.figura(C + "14-editar-item.png", "Editando el ítem 1.")
    m.figura(C + "15-item-editado.png", "Ítem modificado; el sistema recuerda recalcular la liquidación.")
    m.h3("Eliminar un ítem")
    m.p("Seleccione el ítem y pulse **Eliminar ítem**. Se pide confirmación, el ítem se borra, los números se reordenan y la liquidación anterior se conserva en el historial (se recalcula como versión nueva).")
    m.figura(C + "16-confirmar-eliminar-item.png", "Confirmación al eliminar el ítem.")
    m.figura(C + "17-item-eliminado.png", "Ítem eliminado; la bitácora lo registra.")
    m.caja("Lo que hace el arancel por usted", "Al agregar el ítem, el sistema busca la partida y completa el **gravamen arancelario (GA)**; si la mercancía está **prohibida** la rechaza; "
           "si exige un **permiso previo** (SENASAG, AGEMED, IBMETRO…) lo agrega al legajo como documento faltante; y si está sujeta a **ICE** lo avisa.", "E3F4EA")

    m.h1("8. Valoración aduanera (DAV)")
    m.p("La pestaña **Valoración** le ayuda a preparar la **Declaración Andina del Valor (DAV)** bajo la Decisión 571 de la CAN y su Reglamento (Resolución 1684). Trabaja con el **Primer Método: valor de transacción**, que es el precio realmente pagado o por pagar más los ajustes que corresponda. Tiene tres partes.")
    m.h3("1 · Cuestionario de descarte")
    m.p("Responda cinco preguntas. El sistema le dice **al instante** si el valor de transacción sigue siendo aplicable:")
    m.tabla([["Pregunta", "Si responde «Sí»"],
        ["¿Comprador y vendedor están vinculados?", "Si además la vinculación **influyó en el precio**, el primer método no es aplicable. Si no influyó, sigue aplicable, pero debe poder demostrarlo (valores de prueba)."],
        ["¿Hay restricciones a la cesión o utilización de la mercancía?", "No aplicable (salvo restricciones impuestas por ley o limitaciones geográficas)."],
        ["¿El precio depende de condiciones o contraprestaciones que no se pueden valorar?", "No aplicable."],
        ["¿Parte de la reventa o utilización posterior revierte al vendedor?", "Debe declarar el importe en «Reversiones» (se suma al valor); sin importe determinable no procede el valor de transacción."]], [7, 10])
    m.figura(C + "36-valoracion-cuestionario.png", "Cuestionario de descarte: vinculación marcada, sin influencia en el precio.")
    m.caja("Si el primer método no es aplicable", "El sistema muestra una franja **roja** y le indica que corresponde aplicar los métodos secuenciales (valor de mercancías idénticas, similares, deductivo, reconstruido, último recurso). **COMEX JB calcula solo con el primer método**: en ese caso consulte a su despachante.", "FDE8E7")
    m.h3("2 · Ajustes del Art. 8")
    m.p("Anote, en la moneda de la factura, **solo lo que no está incluido en el precio**:")
    m.bullets(["**Adiciones:** comisiones y corretajes (excepto comisión de compra), envases y embalajes, prestaciones o *assists* (matrices, moldes, planos, diseños hechos fuera del país), cánones y derechos de licencia (*royalties*), reversiones al vendedor y otras.",
               "**Deducciones** (solo si están desglosadas en la factura): armado, montaje o asistencia técnica posteriores a la importación; transporte posterior al lugar de importación; derechos e impuestos de Bolivia incluidos en el precio."])
    m.p("Pulse **Guardar valoración**. Luego vuelva a **Calcular (F5)**: las adiciones y deducciones entran al valor en aduana **sin importar el Incoterm**, y aparecen como líneas propias en la liquidación.")
    m.figura(C + "37-valoracion-ajustes.png", "Ajustes del Art. 8: assists USD 500 y royalties USD 1.000.")
    m.figura(C + "39-valoracion-resultado.png", "Resultado del cuestionario: valor de transacción aplicable, con la observación sobre la vinculación.")
    m.h3("3 · Validador previo de precios (riesgo de duda razonable)")
    m.p("Pulse **Validar precios**: el sistema divide el valor de cada ítem entre su **cantidad** y lo compara con la **mediana de sus operaciones anteriores** de la misma partida y moneda. Según la desviación, muestra el riesgo:")
    m.tabla([["Riesgo", "Desviación frente al historial", "Qué hacer"],
        ["Bajo (verde)", "Hasta la mitad de la tolerancia (15 % por defecto)", "Precio coherente con su historial."],
        ["Medio (ámbar)", "Hasta la tolerancia (30 % por defecto)", "Prepare factura, pago bancario y catálogo."],
        ["Alto (rojo)", "Más que la tolerancia", "Riesgo de duda razonable: reúna pruebas (sección 11, descargos)."],
        ["Sin referencia", "No hay operaciones anteriores", "Documente el precio con lista o catálogo del fabricante."]], [3.2, 7, 6.8])
    m.figura(C + "38-valoracion-precios.png", "Validador: el ítem de USD 200 por unidad frente a un historial de USD 150 resulta en riesgo Alto.")
    m.caja("Alcance del validador", "El validador usa **su propio historial** en COMEX JB; no consulta bases referenciales de la Aduana. Cuantas más operaciones registre (con cantidad), más útil será. La tolerancia se ajusta en Configuración.")

    m.h1("9. Liquidación detallada y costo nacionalizado")
    m.p("Pulse **Calcular (F5)** y abra la pestaña **Liquidación**. Ahora tiene cinco bloques, de arriba hacia abajo:")
    m.figura(C + "40-liquidacion-valor.png", "Liquidación del Caso 1 (parte superior): valor en aduana, tributos, avisos y fórmulas.")
    m.tabla([["Bloque", "Qué muestra"],
        ["1 · Determinación del valor en aduana", "Línea por línea: FOB, flete, seguro (o seguro presunto), gastos hasta frontera, ajustes del Art. 8 y deducciones, hasta el **CIF frontera**, que es la base de todos los tributos."],
        ["2 · Tributos a pagar", "FOB, adiciones, deducciones, CIF, Gravamen Arancelario (GA), ICE, IEHD, IVA y **TOTAL TRIBUTOS** en bolivianos. Si registró la UFV, también el CIF en UFV."],
        ["3 · Cómo se calculó", "Las **fórmulas con sus números** para cada tributo y cada ítem, para que usted o su despachante verifiquen el cálculo. Ejemplo: «GA = CIF 291.972,00 × 10% = 29.197,20»."],
        ["4 · Liquidación por ítem", "Tabla con FOB, CIF, GA, ICE, IEHD, IVA y total de **cada ítem**, más la fila TOTAL. Los costos comunes se reparten por valor o por peso (Configuración)."],
        ["5 · Gastos de despacho y costo nacionalizado", "Su costo real por unidad puesto en el almacén (ver abajo)."]], [5, 12])
    m.figura(C + "41-liquidacion-items-costeo.png", "Parte inferior: liquidación por ítem y costeo (aún sin gastos de despacho).")
    m.p("Con la **cantidad** de cada ítem y los gastos locales, el bloque 5 calcula:")
    m.bullets(["**Costo nacionalizado** = CIF + GA + ICE + IEHD + gastos de despacho repartidos (por CIF). El IVA de importación se trata como **crédito fiscal** (no es costo), salvo que en Configuración indique que no lo recupera.",
               "**Factor de importación** = costo nacionalizado ÷ FOB: cuántos bolivianos cuesta poner en su almacén cada boliviano de FOB.",
               "**Costo unitario** por ítem y **flujo de caja requerido** = tributos + gastos de despacho (lo que debe tener disponible).",
               "Gastos que puede anotar (Bs): agencia despachante, almacenaje, transporte interno y otros (por ejemplo el canon ASP-B). **Estimar almacenaje** propone el monto con la tarifa del recinto (Bs por tonelada y día) y los días libres que usted configure; el sistema **no supone tarifas**."])
    m.figura(C + "42-liquidacion-gastos.png", "Gastos de despacho (agencia Bs 3.000, transporte Bs 2.000, 5 días) y costo unitario resultante.")
    m.caja("Base legal y límites", "Los tributos siguen la cascada: **GA** sobre el CIF; **ICE** sobre (CIF + GA); **IEHD** por litro; **IVA** (14,94 % efectivo) sobre (CIF + GA + ICE + IEHD). La tarifa de almacenaje y el ICE de bebidas y tabaco **no vienen en el arancel**: usted los ingresa. La liquidación oficial la determina siempre la Aduana.")

    m.h1("10. Decidir: comparar escenarios")
    m.p("¿Le conviene la oferta FOB, la CIF o la DAP? La pestaña **Decisión** calcula el **costo unitario puesto en su almacén** y su **margen** para cada oferta.")
    m.bullets(["Arriba escriba: **Unidades**, **Gastos locales** en Bs (transporte interno, almacenaje…), **Precio de mercado con IVA** por unidad y **Margen objetivo** (%).",
               "Pulse **Agregar escenario** una vez por oferta y complete en la tabla: nombre, Incoterm, valor de la oferta, flete, seguro y, si es DAP/DDP, lo que cuesta después de la frontera.",
               "Pulse **Comparar**."], num=True)
    m.figura(C + "18-decision-escenarios.png", "Tres ofertas cargadas.")
    m.figura(C + "19-decision-resultados.png", "Resultado: comparación ordenada de menor a mayor costo unitario, con margen y veredicto.")
    m.p("**Veredicto:** *Viable* si el margen alcanza el objetivo, *Ajustado* si es positivo pero menor, *No viable* si es negativo. El precio de mercado se compara **sin IVA**, porque el IVA pagado en la importación se recupera como crédito fiscal. "
        "Con las cifras del Caso 2 del manual de pruebas, los costos unitarios son Bs 1.628,35 (FOB), 1.630,26 (CIF) y 1.660,88 (DAP).")

    m.h1("11. Despacho aduanero (DIM, canales y descargos)")
    m.p("La pestaña **Despacho** prepara la **DIM (Declaración de Importación de Mercancías)** para entregarla a su agencia despachante (o declararla usted, si opera bajo modalidad autorizada) y le acompaña hasta el levante.")
    m.h3("1 · Datos de la DIM")
    m.tabla([["Dato", "Detalle"],
        ["Tipo de despacho", "General, Anticipado, Inmediato, Menor cuantía o Encomienda postal / Courier."],
        ["Régimen aduanero", "10 – Importación a consumo (por defecto), admisión temporal (reexportación o RITEX), depósito de aduana, zona franca."],
        ["Aduana de ingreso y de destino, código de declarante", "Datos críticos del SUMA que la DIM exige."],
        ["Modalidad de transporte", "Cambia las etiquetas: **B/L** (marítimo), **CRT** (carretero), **AWB** (aéreo), **TIF/DTA** (ferroviario); y el manifiesto: MIRA, MIC/DTA, etc."],
        ["Bultos y peso bruto del manifiesto", "Se cotejan con los ítems."],
        ["N.º de DAV y de DIM", "Los de la declaración transmitida."]], [6, 11])
    m.h3("2 · Validación previa")
    m.p("Pulse **Validar la DIM**. El sistema revisa la consistencia y marca cada hallazgo como **ERROR** (corrija antes de declarar), **ALERTA** (revise) u **OK**:")
    m.bullets(["Campos críticos faltantes (aduanas, declarante, modalidad, documento de embarque, bultos).",
               "**Peso bruto de los ítems frente al del manifiesto** (tolerancia 5 % por defecto, configurable).",
               "Que exista la liquidación, que la DAV esté resuelta (cuestionario respondido y valor de transacción aplicable), que no falte el respaldo bancario (D.S. 772) y que el legajo no tenga documentos faltantes.",
               "Si el régimen no es de consumo, advierte que el cálculo de tributos de COMEX JB está hecho para consumo."])
    m.figura(C + "43-despacho-validacion-errores.png", "DIM vacía: la validación lista los datos que faltan.")
    m.figura(C + "44-despacho-datos-validados.png", "DIM completa: el peso de los ítems concuerda con el manifiesto; quedan solo alertas (respaldo bancario, documentos).")
    m.h3("3 · Canal de selectividad")
    m.p("Cuando la Aduana asigne el canal, elíjalo y pulse **Asignar canal y generar lista**. El sistema genera una **lista de control** según el canal y usted va marcando cada tarea (queda en la bitácora):")
    m.tabla([["Canal", "Qué hace la lista"],
        ["Verde", "Levante sin revisión previa: verificar el pago y el refrendo bancario, coordinar el retiro, archivar."],
        ["Amarillo", "Cotejo documental: factura, embarque y lista de empaque contra la DIM; seguro y flete contra la DAV; certificado de origen; autorizaciones previas."],
        ["Rojo", "Inspección física y documental: preparar el acceso, documentos originales, muestras y fichas técnicas (marca, modelo, serie); registrar las observaciones del técnico aduanero; preparar descargos si hay acta."]], [3, 14])
    m.figura(C + "45-despacho-canal-rojo.png", "Canal Rojo asignado: lista de control de la inspección.")
    m.h3("4 · Levante y descargos")
    m.bullets(["**Registrar levante:** anote la fecha en que la Aduana libera la mercancía.",
               "**Generar borrador de descargos:** si la Aduana emite un Acta de Reconocimiento o un Informe de Variación de Valor (duda razonable), el sistema redacta una carta con sus datos (importador, NIT, agencia, N.º de DIM, valor declarado), la observación transcrita y la **lista de pruebas** a adjuntar: factura, contrato u orden de compra, comprobante de pago al exterior (SWIFT, transferencia o carta de crédito), estado de cuenta, lista de precios o catálogo del fabricante, facturas anteriores, póliza y flete."])
    m.caja("Es un borrador", "La plantilla de descargos **no sustituye** al despachante ni a un abogado: revísela y complétela antes de presentarla. Las listas de control resumen buenas prácticas; los procedimientos oficiales los fija la Aduana Nacional.")

    m.h1("12. Acompañar: ruta crítica y semáforos")
    m.p("La pestaña **Ruta** lista los 12 pasos de la importación, desde verificar la mercancía hasta el retiro con pase de salida. Las fechas se calculan a partir del día de creación.")
    m.figura(C + "22-ruta-critica.png", "Ruta crítica: la primera etapa en Alerta; la segunda se marcó «Cumplida» (verde).")
    m.tabla([["Color", "Estado", "Significado"], ["Gris", "Pendiente", "Aún no corresponde iniciar"], ["Azul", "En curso", "Ya empezó y está dentro de plazo"],
        ["Amarillo", "Alerta", "Faltan 2 días o menos para su fecha de fin"], ["Verde", "Cumplida", "Registrada como terminada"], ["Rojo", "Vencida", "Pasó su fecha de fin sin cumplirse"]], [3, 3.5, 10.5])
    m.p("Cuando una etapa termine, pulse **Marcar cumplida**: se registra la fecha real y la bitácora anota si hubo retraso. La columna «Crítica» indica las etapas que, si se atrasan, atrasan toda la importación.")
    m.caja("Plazos orientativos", "Las duraciones de cada etapa son estimaciones, **no plazos legales**. Los plazos oficiales (vigencia de la DIM, almacenaje, etc.) deben verificarse en la normativa vigente.")

    m.h1("13. Documentar: legajo y bitácora")
    m.figura(C + "23-legajo-bitacora.png", "A la izquierda, los documentos exigidos y cuáles faltan; a la derecha, la bitácora automática con el usuario que hizo cada acción.")
    m.p("El **legajo** muestra los documentos que exige su operación (factura, embarque, lista de empaque, seguro, respaldo bancario, certificado de origen, permisos previos…) con **OK** o **FALTA**. "
        "La **bitácora** registra con fecha, hora y **usuario** cada ítem agregado, modificado o eliminado, cada liquidación (con su versión), cada etapa cumplida y cada documento leído: es la memoria del proceso.")

    m.h1("14. Costos reales")
    m.p("La pestaña **Costos** compara **lo proyectado con lo realmente pagado** para conocer el costo exacto de su importación.")
    m.bullets(["Pulse **Cargar proyectado desde la liquidación**: se crean las filas (FOB, flete, seguro, GA, IVA, etc.) con los montos calculados.",
               "En la columna **Real (Bs)** escriba lo que efectivamente pagó (tributos de la DIM, agencia despachante, almacén, transporte).",
               "Use **Agregar costo** para conceptos que no están en la lista y **Guardar hoja** al terminar. La columna **Diferencia** muestra el sobrecosto o el ahorro."], num=True)
    m.figura(C + "21-costos-reales.png", "Hoja de costos: proyectado frente a real.")

    m.h1("15. Leer facturas con OCR")
    m.p("Si tiene la factura escaneada o en PDF, el sistema puede leerla y **proponer** los datos. Usted siempre revisa y confirma: el OCR puede equivocarse con dígitos.")
    m.bullets(["Con la operación seleccionada, en la pestaña Mercancías pulse **Leer factura** y elija la imagen (JPG, PNG) o el PDF.",
               "El documento aparece en el visor y el sistema propone: N.º de factura, proveedor, Incoterm, moneda, valor total y peso, con la **confianza** de cada dato (Alta / Media / Baja).",
               "Corrija lo necesario y pulse **Confirmar datos**: el valor y el peso pasan al formulario de captura; el legajo marca la factura como OK."], num=True)
    m.figura(C + "34-ocr-propuesta.png", "Factura leída con su propuesta de datos.")
    m.figura(C + "35-ocr-confirmado.png", "Datos confirmados y trasladados al formulario.")

    m.h1("16. Contrastar con la DIM real")
    m.p("Esta pestaña le permite **probar que el sistema calcula igual que la Aduana**. Es la comprobación más importante antes de usarlo en serio.")
    m.bullets(["Registre una importación **ya despachada** con los mismos valores, flete, seguro y tipo de cambio de esa fecha, y pulse Calcular.",
               "Abra la pestaña **Contraste** y escriba los tributos que la Aduana liquidó en la DIM (GA, ICE, IEHD, IVA).", "Pulse **Contrastar**."], num=True)
    m.figura(C + "20-contraste.png", "Contraste: cada concepto se marca OK o REVISAR con su diferencia en Bs.")
    m.p("Si hay diferencias, revise el tipo de cambio, el flete y seguro, y los **parámetros tributarios** (Configuración): IVA efectivo, redondeo, base del ICE. Cada contraste queda en la bitácora.")

    m.h1("17. Configuración")
    m.p("El menú **Configuración** concentra el mantenimiento de los datos de referencia. Las pestañas de parámetros y usuarios son solo para administradores.")
    m.h3("Tipos de cambio")
    m.p("Registre el **tipo de cambio oficial de venta (BCB)** por fecha y moneda. El sistema usa el último valor vigente a la fecha de cada operación. Si registra otra vez la misma fecha y moneda, **corrige** el valor; con **Eliminar** borra el registro seleccionado.")
    m.figura(C + "24-config-tipo-cambio.png", "Tipo de cambio USD registrado.")
    m.h3("UFV")
    m.p("Registre el valor de la UFV por fecha (publicado por el BCB). Se usa para expresar el valor en aduana en UFV en la liquidación.")
    m.figura(C + "25-config-ufv.png", "Tabla de UFV y formulario de registro.")
    m.h3("Parámetros tributarios")
    m.p("Valores que cambian por decreto: IVA efectivo en importaciones (14,94 %), umbral de bancarización (Bs 50.000 – D.S. 772), alícuota máxima de GA aceptada, seguro presunto, redondeo (dos decimales o Bs enteros) y reparto del flete y seguro entre ítems (por valor o por peso). **Verifíquelos con su despachante antes de modificarlos**; afectan a todos los cálculos. **Restaurar valores por defecto** los devuelve al estado de fábrica.")
    m.figura(C + "26-config-parametros.png", "Parámetros del cálculo de tributos.")
    m.h3("Perfil del importador")
    m.p("Razón social, NIT, tipo de importador, dirección, contacto y agencia despachante habitual. Se incluye en el expediente y en el JSON para la DMI.")
    m.figura(C + "27-config-perfil.png", "Perfil del importador.")
    m.h3("Usuarios")
    m.p("El administrador crea usuarios (usuario, nombre, clave, rol), cambia claves, **activa o desactiva** cuentas y cambia el rol. Siempre debe quedar al menos **un administrador activo**.")
    m.figura(C + "28-config-usuarios.png", "Administración de usuarios.")
    m.h3("Datos y respaldo")
    m.p("Toda su información está en un único archivo (comex.db). **Crear copia de seguridad…** guarda una copia consistente en la carpeta que elija (por ejemplo un pendrive o la nube); **Abrir la carpeta de datos** la muestra en el Explorador. Haga copias periódicas.")
    m.figura(C + "29-config-respaldo.png", "Respaldo de la base de datos.")

    m.h1("18. Exportar (Excel, JSON y expediente)")
    m.bullets(["**Excel:** libro con las hojas Resumen, Ítems, Liquidación, Ruta crítica y Bitácora. Los totales son fórmulas.",
               "**JSON (SUMA):** archivo estructurado con los datos de la operación (importador, ítems con ficha técnica, valores y liquidación) para **transcribir a la DMI** en el sistema de la Aduana. Aún no transmite nada por sí mismo.",
               "**Expediente:** documento de texto con resumen, mercancías, liquidación vigente, ruta, legajo y bitácora completa."])
    m.figura(C + "31-acerca-de.png", "Acerca de: versión, ubicación de datos y avisos de licencias.")

    m.h1("19. Problemas frecuentes y límites")
    m.tabla([["Situación", "Qué hacer"],
        ["«El arancel NO está cargado»", "Arancel → Importar arancel (PDF)… con los 3 archivos (sección 5)."],
        ["«La partida … no existe en el arancel cargado»", "Revise el código de 10 dígitos o agréguela en Arancel → Nueva partida."],
        ["«…figura como mercancía prohibida»", "La partida está prohibida (tipo P en el arancel). No se puede importar."],
        ["No puedo borrar un ítem u operación", "Seleccione primero la fila y use **Eliminar ítem** / **Eliminar operación**; confirme el aviso."],
        ["La lectura OCR falla con un PDF", "Si el archivo está dañado o protegido, conviértalo a imagen (JPG/PNG)."],
        ["Un mensaje de error inesperado", "Sus datos están guardados. El detalle queda en %LocalAppData%\\ComexJB\\errores.log; envíelo a soporte."],
        ["Perdí mis datos / cambio de PC", "Use Configuración → Datos y respaldo, o copie %LocalAppData%\\ComexJB\\comex.db."]], [6.5, 10.5])
    m.h3("Lo que todavía no hace")
    m.bullets(["No transmite nada a la Aduana ni llena el formulario SUMA por sí mismo: el JSON (incluye DAV y despacho) sirve para transcribir. La correspondencia con las casillas oficiales falta (requiere el instructivo vigente de la ANB).",
               "No elabora borradores de solicitudes de autorización previa (AP), ni actualiza el arancel desde internet.",
               "No incluye aún el archivo probatorio inmutable (PDF/A) ni la conciliación bancario-aduanera automática (módulo de post-despacho): hoy el expediente, la bitácora y el respaldo cubren parte de esa función.",
               "El validador de precios solo usa su historial; no consulta bases referenciales de la Aduana. Las comprobaciones contra el manifiesto se hacen con los datos que usted ingresa (no lee el MIC/DTA).",
               "La tarifa de almacenaje, el canon ASP-B y el ICE de bebidas y tabaco no vienen en el arancel: se ingresan o configuran.",
               "Los escenarios de Decisión no se guardan al cerrar la aplicación; la base de datos no se cifra.",
               "Los roles se aplican en la interfaz de la aplicación (no protegen el archivo de datos frente a quien tenga acceso a la carpeta).",
               "No cubre exportaciones (DEX/CEDEIM) ni almacenaje en pantalla."])
    m.p("Las capturas de este manual son **reales**, tomadas de la aplicación en ejecución en un entorno de pruebas (Wine); en su Windows la tipografía será Segoe UI y los botones de los avisos dirán «Sí/No».", italic=True)
    ruta = AQUI + "/Manual-de-Usuario"; m.guardar(ruta + ".docx"); return ruta

# ============================================================== MANUAL DE INSTALACIÓN, IMPLEMENTACIÓN Y PRUEBAS
def manual_implementacion():
    m = Manual("Manual de Instalación y Pruebas", "Instalación, puesta en marcha, verificación y manual de pruebas con ejemplos completos", VERSION, FECHA)
    m.contenido(["Requisitos", "Instalación en un clic", "Instalación para varios equipos", "Datos, respaldos y actualización", "Carga del arancel",
        "Pruebas automáticas", "Manual de pruebas (casos con cifras esperadas)", "Pruebas de aceptación", "Parámetros que debe validar un despachante",
        "Construcción del instalador (equipo técnico)", "Hallazgos de la primera ejecución real", "Limitaciones conocidas", "Cobertura frente a la solicitud COMEX", "Registro de hallazgos"])

    m.h1("1. Requisitos")
    m.tabla([["Elemento", "Requisito"], ["Sistema operativo", "Windows 10 u 11, 64 bits"], ["Espacio en disco", "≈ 450 MB (incluye .NET, OCR y manuales)"],
        ["Memoria", "4 GB recomendados"], ["Permisos", "Usuario normal (no requiere administrador)"],
        ["Software adicional", "Ninguno: .NET, Tesseract (OCR con español) y Poppler (PDF) vienen dentro del instalador"],
        ["Internet", "No necesario para operar"]], [5, 12])

    m.h1("2. Instalación en un clic")
    m.bullets(["Copie **ComexJB-Setup-1.2.0.exe** al equipo y haga doble clic.",
               "Si aparece SmartScreen («Windows protegió su PC»): **Más información → Ejecutar de todas formas**. Es normal: el instalador no tiene firma digital comercial (la firma requiere un certificado de pago; se recomienda adquirirlo antes de distribuir ampliamente).",
               "Espere la barra de progreso; al finalizar la aplicación se abre sola.",
               "Se crean: carpeta de programa en `%LocalAppData%\\Programs\\ComexJB`, accesos directos en el Escritorio y en Inicio → COMEX JB (incluye «Manual del usuario» y «Desinstalar»)."], num=True)
    for f, t in (("01-progreso.png", "Instalador en curso (pantalla única con barra de progreso)."), ("02-terminado.png", "Instalación completada.")):
        m.figura(I + f, t, 13)
    m.h1("3. Instalación para varios equipos")
    m.bullets(["**Silenciosa** (sin pantallas): `ComexJB-Setup-1.2.0.exe /S`", "**Desinstalación silenciosa:** `\"%LocalAppData%\\Programs\\ComexJB\\Desinstalar.exe\" /S`",
               "Para instalar en una carpeta distinta: `ComexJB-Setup-1.2.0.exe /S /D=C:\\Ruta\\ComexJB` (la ruta va al final y sin comillas).",
               "Cada usuario de Windows tiene su propia base de datos; para compartir información entre equipos copie el archivo `comex.db` (sección 4)."])

    m.h1("4. Datos, respaldos y actualización")
    m.tabla([["Qué", "Dónde"], ["Base de datos (operaciones, bitácora, liquidaciones, arancel)", "`%LocalAppData%\\ComexJB\\comex.db`"],
        ["Registro de errores inesperados", "`%LocalAppData%\\ComexJB\\errores.log`"], ["Programa", "`%LocalAppData%\\Programs\\ComexJB`"]], [8.5, 8.5])
    m.bullets(["**Respaldo:** cierre la aplicación y copie `comex.db`. Esa única copia contiene todo.", "**Actualizar:** ejecute el instalador nuevo; reemplaza el programa y conserva sus datos.",
               "**Desinstalar** no borra `comex.db`. Para eliminar todo, borre también `%LocalAppData%\\ComexJB`.",
               "Los documentos (facturas escaneadas) **no** se copian a la base: se guarda su ubicación y su huella SHA-256. Conserve una carpeta por embarque."])
    m.bullets(["**Venía de «ComexBol Pro» 1.0.0:** el instalador retira esa versión y, al primer inicio, COMEX JB copia automáticamente `%LocalAppData%\\ComexBolPro\\comex.db` a la carpeta nueva `%LocalAppData%\\ComexJB`. La base antigua queda intacta. Los usuarios se crean en el primer ingreso."])
    m.caja("Cambios de versión", "La base añade automáticamente las columnas nuevas al abrir una versión más reciente (no borra datos). Aun así, haga una copia de seguridad antes de actualizar.")

    m.h1("5. Carga del arancel")
    m.bullets(["Abra COMEX JB, ingrese como administrador y vaya a **Arancel → Importar arancel (PDF)…**.",
               "Seleccione los **3 archivos PDF** del Arancel 2026 (también se aceptan los `.md` convertidos, pero el PDF es más exacto).", "La importación tarda unos 2 minutos. Resultado esperado con el arancel oficial 2026: «**8.132 partidas · versión 2026 · 76 prohibidas · 245 con ICE/IEHD**» y **2 avisos** (dos filas del capítulo 98 sin unidad de medida en el original)."], num=True)
    m.tabla([["Dato del arancel", "Estado"], ["Código, descripción, GA, unidad", "Leídos celda por celda del PDF (13 columnas); GA verificado contra una segunda lectura independiente: 8.060 de 8.063 comparables coinciden (las 3 diferencias son errores de la comprobación, no del importador)"],
        ["Documento adicional (AP, C, C*, DJ, CITES…), entidad, disposición legal, despacho en frontera", "Leídos"],
        ["Mercancía prohibida (tipo P)", "Detectada (76 partidas): el sistema bloquea la partida"], ["Marca ICE / IEHD", "Detectada (225 ICE, 20 IEHD); la tasa de IEHD y la de bebidas/tabaco no vienen en el arancel"],
        ["ICE de vehículos por antigüedad (Apéndice I)", "180 partidas con tasas (tablas de 6, 4 y 2 columnas; «≥3 años» reconocido)"],
        ["Preferencias (CAN/ACE36/47/VEN, ACE 22 Chile y Protocolo, ACE 66 México)", "Asignadas por columna para todas las partidas"]], [9, 8])
    m.p("**Verificación recomendada:** revise por muestreo 20–30 partidas de su interés contra el arancel impreso (prueba P-02).")

    m.h1("6. Pruebas automáticas")
    m.p("El código incluye pruebas automáticas que se ejecutan en una consola (equipo técnico):")
    m.code("for t in tests/*/; do (cd $t && dotnet test); done")
    m.tabla([["Proyecto", "Pruebas", "Cubre"], ["ComexBol.Core", "41", "Liquidación, Incoterms, ruta crítica, lectura del arancel (Markdown), valoración (cuestionario, Art. 8, validador de precios), costeo, despacho"], ["ComexBol.Data", "50", "Base de datos, catálogo, ICE por antigüedad, preferencias, usuarios y claves (PBKDF2), configuración, costos reales, edición/eliminación, respaldo"],
        ["ComexBol.Documentos", "15", "OCR real (Tesseract), PDF (Poppler), Excel, lectura del arancel en PDF con páginas reales"], ["ComexBol.Presentation", "30", "Lógica de las pantallas (operaciones, selector de partida, inicio de sesión, configuración, arancel), regresiones halladas en uso real"], ["**Total**", "**136**", ""]], [5, 2.5, 9.5])
    m.p("Con el arancel completo en PDF: `COMEXBOL_ARANCEL_PDF_DIR=<carpeta con los 3 PDF> dotnet test` (PowerShell: `$env:COMEXBOL_ARANCEL_PDF_DIR=\"C:\\arancel\"`). Verifica 8.132 partidas, 97 capítulos, 76 prohibidas y 180 con tasas ICE.")

    m.h1("7. Manual de pruebas")
    m.p("Convenciones: TC = 6,96 Bs/USD (dato de prueba; use el oficial). Las cifras se muestran con formato boliviano. **Cada cifra de estos casos fue obtenida ejecutando la aplicación real** y está además fijada en una prueba automática. "
        "**Preparación común:** abra la aplicación, ingrese (primer uso: cree al administrador), registre en Configuración → Tipos de cambio USD = 6,96 e importe el arancel (sección 5).")
    m.h2("Caso 1 — Tablets, Incoterm FOB")
    m.p("**Datos:** 200 tablets con IMEI, partida **8471.30.00.10**, valor USD 40.000, peso 800 kg, flete USD 1.800, seguro USD 150.")
    m.bullets(["Carpeta `IMP-2026-001`, Incoterm **FOB** → Crear.", "Partida `8471.30.00.10`, Descripción `Tablets con IMEI`, Valor `40000`, Peso `800`, Flete `1800`, Seguro `150` → **Agregar ítem** → **Calcular (F5)**."], num=True)
    m.figura(C + "13-liquidacion.png", "Resultado esperado del Caso 1.")
    m.tabla([["Concepto", "Esperado (Bs)"], ["Valor FOB", "278.400,00"], ["Adiciones", "13.572,00"], ["CIF aduana", "**291.972,00**"], ["Gravamen arancelario (10 %)", "29.197,20"],
        ["IVA", "47.982,68"], ["**Total tributos**", "**77.179,88**"]], [9, 6])
    m.p("Aviso esperado: «FOB desde Bs 50.000: complete el respaldo bancario». Pestaña Legajo: Factura, Embarque, Lista de empaque, Seguro, Respaldo bancario y Factura de flete en **FALTA**.")
    m.h2("Caso 2 — ¿FOB, CIF o DAP? (decisión)")
    m.p("Pestaña **Decisión**: Unidades 200, Gastos locales 4500, Precio de mercado 2800, Margen objetivo 15; escenarios FOB 40000 (flete 1800, seguro 150), CIF 42000 y DAP 44000 (deducción post-frontera 1200).")
    m.figura(C + "19-decision-resultados.png", "Resultado esperado del Caso 2.")
    m.tabla([["Escenario", "CIF Bs", "Tributos Bs", "Costo unit. Bs", "Margen"], ["FOB + flete propio", "291.972,00", "77.179,88", "1.628,35", "34,3 %"],
        ["CIF del proveedor", "292.320,00", "77.271,87", "1.630,26", "34,2 %"], ["DAP del proveedor", "297.888,00", "78.743,71", "1.660,88", "33,0 %"]], [4.5, 3, 3, 3.3, 3.2])
    m.h2("Caso 3 — Animales vivos, CFR (permiso sanitario)")
    m.p("Partida **0101.21.00.00**, valor USD 25.000, peso 3.000 kg, seguro USD 250, Incoterm **CFR** (el flete va en el precio; no lo digite). "
        "Esperado: CIF **175.740,00**; GA 5 % **8.787,00**; IVA **27.568,33**; total **36.355,33**. Aviso: documento adicional C* — SENASAG (Ley 830); el legajo exige la autorización previa.")
    m.h2("Caso 4 — Tractor usado con ICE por antigüedad")
    m.p("Partida **8701.21.00.00**, valor USD 20.000, peso 4.000 kg, **antigüedad 3 años**, FOB, flete USD 2.500, seguro USD 200.")
    m.p("Esperado: CIF **157.992,00**; GA 5 % **7.899,60**; ICE 30 % sobre (CIF+GA) **49.767,48**; IVA **32.219,47**; total **89.886,55**. Con antigüedad 0 el ICE pasa a 15 %.")
    m.h2("Caso 5 — Umbral de bancarización (D.S. 772)")
    m.tabla([["Valor FOB", "Resultado"], ["USD 7.000 (Bs 48.720), partida 8471.30.00.90", "**Sin** aviso de bancarización · tributos Bs 12.878,64"], ["FOB equivalente a Bs 50.000,00", "**Con** aviso · tributos Bs 13.217,00"]], [8, 9])
    m.h2("Caso 6 — Whisky: el ICE no viene en el arancel")
    m.p("Partida **2208.30.00.00**, valor USD 10.000, CIF. GA **40 %**. Avisos: «partida sujeta a ICE… ingrese manualmente» y «documento adicional C — SENASAG». Escriba en *ICE %* la tasa que indique su despachante y verifique que se aplique sobre (CIF+GA). El sistema **no inventa** la tasa.")
    m.h2("Caso 7 — Mercancía prohibida y medicamento")
    m.p("Partida **8703.23.10.10** (vehículo a GLP, tipo **P**): al agregarla el sistema muestra «…figura como mercancía prohibida» y no liquida. Partida **3004.90.10.00**: aviso con **AGEMED** y el legajo exige la autorización.")
    m.h2("Caso 8 — Seguimiento de la ruta")
    m.p("Cree la operación el 02/11/2026: etapa I01 plan 02/11 a 04/11. Márquela cumplida: pasa a verde y la bitácora anota «a tiempo». Con una fecha posterior a un plazo pasa a Vencida (rojo); a 2 días o menos del fin, Alerta (amarillo).")
    m.figura(C + "22-ruta-critica.png", "Resultado esperado del Caso 8 (etapa I02 cumplida).")
    m.h2("Caso 9 — Arancel completo")
    m.p("Tras importar los 3 PDF: barra de estado «Catálogo: 8132 partidas, 2 avisos/rechazos».")
    m.h2("Caso 10 — OCR de factura (imagen y PDF)")
    m.p("Abra `docs/ejemplos/factura-ejemplo.png` (y repita con `factura-ejemplo.pdf`). Propuesta esperada (puede variar algún dígito):")
    m.tabla([["Campo", "Valor", "Confianza"], ["N.º factura", "INV-88213", "Media"], ["Proveedor", "Shenzhen Tech Co., Ltd", "Alta"], ["Incoterm", "FOB", "Alta"], ["Moneda", "USD", "Media"],
        ["Valor total", "10000", "Media"], ["Peso bruto kg", "1250.5", "Media"]], [5, 8, 4])
    m.figura(C + "34-ocr-propuesta.png", "Resultado esperado del Caso 10.")
    m.p("Corrija el valor a 10500 y confirme: el legajo marca la factura como OK y la bitácora registra «Confirmado por el usuario».")
    m.h2("Caso 11 — Contraste con una DIM")
    m.p("Con el Caso 1 liquidado, pestaña Contraste con DIM: GA `29197,20`, IVA `47982,68` → todas las filas OK. Cambie el IVA a `47990` → la fila IVA y el total marcan REVISAR (diferencia 7,32).")
    m.figura(C + "20-contraste.png", "Resultado esperado del Caso 11 con diferencia.")
    m.h2("Caso 12 — Exportar a Excel")
    m.p("**Excel…** → abra el .xlsx: hojas Resumen, Ítems, Liquidación, Ruta crítica y Bitácora. En Liquidación los totales son **fórmulas**. Para el Caso 1: CIF 291.972,00; total tributos 77.179,88.")
    m.h2("Casos 13 a 15 — Preferencias arancelarias")
    m.bullets(["**Caso 13:** partida 0101.21.00.00, acuerdo **CAN**, desgravación 0 → «desgravación 100 % tomada del arancel para CAN. Requiere Certificado de Origen»; GA = 0; el legajo exige el certificado.",
               "**Caso 14:** partida 1507.10.00.00 (aceite en bruto) con **ACE 66 (México)** → el arancel indica **0 %**: no hay desgravación y el GA se cobra completo.",
               "**Caso 15:** partida 2103.90.10.00 (mayonesa) con **ACE 22 (Chile)** → **50 %** (Protocolo VII). Si declara 100 %, el aviso dice «usted declaró 100 % y el arancel indica 50 %».",
               "Sin acuerdo, una desgravación > 0 se rechaza: «Indique el acuerdo comercial que sustenta la desgravación»."])

    m.h2("Caso 16 — Ingreso con usuario y clave")
    m.p("Primer uso: cree el administrador (nombre, usuario, clave de 6 o más caracteres, repetida). Cierre sesión y vuelva a ingresar. Esperado: con clave errónea el sistema lo rechaza («Usuario o clave incorrectos»); con la correcta abre el Panel de control. En Configuración → Usuarios cree un **Operador**: al ingresar con él, las pestañas de parámetros y usuarios no aparecen y «Importar arancel» no está disponible.")
    m.figura(C + "28-config-usuarios.png", "Resultado esperado del Caso 16 (administración de usuarios).")
    m.h2("Caso 17 — Selector de partida y descripción automática")
    m.p("En Operaciones, cree `IMP-2026-001`. En «Partida NANDINA» escriba `84713000`: aparecen **8471300010** y **8471300090** con GA 10 %. Haga clic en la primera. Esperado: el código se completa, la descripción se llena sola («Máquinas automáticas para tratamiento o procesamiento de datos…») y aparece «GA 10 % · Unidad: u».")
    m.figura(C + "10-selector-por-codigo.png", "Resultado esperado del Caso 17.")
    m.h2("Caso 18 — Editar y eliminar ítems y operaciones (el problema que bloqueaba el trabajo)")
    m.bullets(["Agregue el ítem del Caso 1. Seleccione la fila → **Editar ítem** → cambie el valor a 41000 → **Guardar cambios del ítem**. Esperado: «Ítem 1 modificado»; la lista muestra 41.000,00.",
               "Intente agregar un ítem con partida `1234` (incompleta): el sistema responde «La partida NANDINA debe tener 10 dígitos» y **no lo guarda**; la liquidación sigue funcionando.",
               "Seleccione el ítem → **Eliminar ítem** → confirme. Esperado: la lista queda vacía y la bitácora registra «Ítem eliminado».",
               "Seleccione la operación → **Eliminar operación** → confirme. Esperado: desaparece de la lista junto con su ruta, ítems y costos."], num=True)
    m.figura(C + "16-confirmar-eliminar-item.png", "Resultado esperado del Caso 18: confirmación antes de borrar.")
    m.h2("Caso 19 — Mantenimiento del arancel")
    m.p("Arancel → buscar `8471300010` → seleccione la fila → cambie el GA a 5 → **Guardar**. Esperado: la fila muestra 5 % y su fuente termina en «(modificada)»; una liquidación nueva usa 5 %. **Nueva partida:** código `9999999999`, descripción «Prueba», GA 10 → aparece con fuente MANUAL; **Eliminar** la quita. Vuelva a dejar el GA original.")
    m.figura(C + "07-arancel-buscar-editar.png", "Resultado esperado del Caso 19.")
    m.h2("Caso 20 — Configuración: tipo de cambio, UFV, parámetros y respaldo")
    m.bullets(["Tipos de cambio: registre USD 6,96 con la fecha de hoy. Esperado: en Operaciones la caja «TC USD a Bs» propone 6,96 y la leyenda dice «TC registrado al …».",
               "UFV: registre un valor para la fecha de hoy; la liquidación muestra el valor en aduana en UFV.",
               "Parámetros: cambie el redondeo a «Bs enteros», recalcule el Caso 1 (los tributos pasan a enteros) y use **Restaurar valores por defecto**.",
               "Datos y respaldo: **Crear copia de seguridad…** genera un archivo .db que puede abrirse como copia completa."], num=True)
    m.figura(C + "26-config-parametros.png", "Resultado esperado del Caso 20 (parámetros).")

    m.h2("Caso 21 — Ajustes del Art. 8 (royalties y assists)")
    m.p("Con el Caso 1 (200 tablets, cantidad 200), en **Valoración** responda el cuestionario sin marcar nada y anote **Prestaciones (assists) 500** y **Cánones (royalties) 1000** (USD) → **Guardar valoración** → en Mercancías **Calcular (F5)**.")
    m.p("Esperado: la liquidación incluye la línea «(+) Ajustes del Art. 8» de Bs 10.440,00; CIF **302.412,00**; GA 10 % **30.241,20**; IVA **49.698,39**; total **79.939,59**. El flete y el seguro siguen sumándose por el Incoterm.")
    m.figura(C + "37-valoracion-ajustes.png", "Resultado esperado del Caso 21 (ajustes cargados).")
    m.h2("Caso 22 — Cuestionario de descarte")
    m.bullets(["Marque «vinculados» y «la vinculación influyó en el precio» → **Guardar valoración**. Esperado: franja **roja** «Valor de transacción NO aplicable: use métodos secuenciales» y la observación sobre los métodos 2.º a 6.º.",
               "Desmarque «influyó»: franja **verde** «APLICABLE» y la observación de que debe documentar valores de prueba.",
               "Marque «reversión al vendedor» sin importe en Reversiones: aparece la observación de declarar el importe."], num=True)
    m.figura(C + "36-valoracion-cuestionario.png", "Resultado esperado del Caso 22.")
    m.h2("Caso 23 — Validador de precios (historial propio)")
    m.p("Cree `IMP-2025-099` con la misma partida (8471.30.00.10), valor USD 30.000 y **cantidad 200** (USD 150 por unidad). En `IMP-2026-001` (USD 40.000, cantidad 200 = USD 200 por unidad) pulse **Validar precios**. Esperado: mediana histórica 150,00; desviación **+33,3 %**; riesgo **Alto** (rojo), con el mensaje de preparar factura, pago bancario y catálogo. Con un ítem sin cantidad: «Indique la cantidad…».")
    m.figura(C + "38-valoracion-precios.png", "Resultado esperado del Caso 23.")
    m.h2("Caso 24 — Liquidación detallada y costo nacionalizado")
    m.p("Con el Caso 1 (cantidad 200), abra **Liquidación**. Esperado: bloque 1 con FOB 278.400,00 + flete 12.528,00 + seguro 1.044,00 = CIF 291.972,00; bloque 3 con «GA = CIF 291.972,00 × 10% = 29.197,20» e «IVA = 14,94% × (…) = 47.982,68»; bloque 4 con TOTAL 77.179,88. Sin gastos de despacho el costeo da costo Bs **321.169,20**, factor **1,1536**, costo unitario **1.605,85**.")
    m.p("Anote agencia **3.000** y transporte **2.000** (Bs) → **Guardar gastos**. Esperado: costo **326.169,20**, factor **1,1716**, costo unitario **1.630,85** y flujo de caja requerido **Bs 82.179,88** (77.179,88 + 5.000). El IVA (47.982,68) se informa como crédito fiscal.")
    m.figura(C + "42-liquidacion-gastos.png", "Resultado esperado del Caso 24.")
    m.p("**Almacenaje:** sin tarifa configurada, «Estimar almacenaje» responde «Configure la tarifa…». Con tarifa 5 Bs/t·día, 4 días libres y 10 días en almacén sobre 800 kg: (10 − 4) × 0,8 × 5 = **Bs 24,00**.")
    m.h2("Caso 25 — Validación de la DIM")
    m.bullets(["Sin datos: **Validar la DIM** marca ERROR en aduana de ingreso, aduana de destino, declarante, modalidad, documento de embarque y bultos.",
               "Complete: Tambo Quemado → La Paz, ADA-0123, modalidad Carretero (las etiquetas pasan a «N.º de CRT» y «N.º de MIC/DTA»), CRT-77123, 40 bultos, peso manifiesto 810 kg (ítems: 800 kg), DAV-2026-55. Esperado: «Peso bruto de los ítems … concuerda con el manifiesto»; sin errores.",
               "Cambie el peso del manifiesto a 1.200 kg: ERROR «difiere 33,3 %».",
               "Con FOB desde Bs 50.000 y sin comprobante de pago: ALERTA «Falta el respaldo bancario (D.S. 772)»."], num=True)
    m.figura(C + "44-despacho-datos-validados.png", "Resultado esperado del Caso 25.")
    m.h2("Caso 26 — Canal de selectividad, levante y descargos")
    m.bullets(["Elija **Amarillo** → «Asignar canal y generar lista»: 7 tareas (cotejo de factura, embarque, seguro y flete, certificado de origen, autorizaciones previas…). Marque una: queda en la bitácora.",
               "Cambie a **Rojo**: la lista se reemplaza por 7 tareas de inspección (incluye «preparar descargos»). Con **Verde**: 4 tareas. Con «Sin asignar»: lista vacía.",
               "**Registrar levante** con fecha 20/11/2026: «Levante registrado el 20/11/2026».",
               "**Generar borrador de descargos…** → guarde el .txt: contiene su razón social y NIT (Configuración → Perfil), el N.º de DIM, el valor declarado y 8 pruebas numeradas."], num=True)
    m.figura(C + "45-despacho-canal-rojo.png", "Resultado esperado del Caso 26 (canal Rojo).")

    m.h1("8. Pruebas de aceptación")
    m.tabla([["#", "Prueba", "Resultado esperado", "Cumple"],
        ["P-01", "Importar los 3 archivos del arancel", "8.132 partidas / 97 capítulos", "☐"], ["P-02", "Contrastar 20 partidas con el arancel impreso", "GA, unidad y documento coinciden", "☐"],
        ["P-03", "Casos 1, 3, 4, 5", "Cifras idénticas a las de este manual", "☐"], ["P-04", "Caso 7", "Prohibida bloqueada; AGEMED exigida", "☐"],
        ["P-05", "Cambiar el TC y recalcular", "La versión 2 queda en bitácora; la 1 se conserva", "☐"], ["P-06", "Cerrar y reabrir la aplicación", "Operaciones, ruta y bitácora persisten", "☐"],
        ["P-07", "Caso 10 con una factura real escaneada", "Propuesta razonable; nada se aplica sin confirmar", "☐"], ["P-08", "Exportar expediente y Excel", ".md con 6 secciones; .xlsx con 5 hojas", "☐"],
        ["P-09", "**Contraste con 3 DIM reales ya despachadas**", "Tributos de la app = tributos pagados (diferencia ≤ redondeo)", "☐"],
        ["P-10", "Casos 2 y 11 en pantalla", "Tablas idénticas a las del manual", "☐"], ["P-11", "Instalación en un PC limpio sin permisos de administrador", "Instala, abre y lee una factura PDF", "☐"],
        ["P-12", "Casos 16 y 17", "Ingreso con roles; selector de partida completa la descripción", "☐"], ["P-13", "Caso 18", "Editar y eliminar ítems y operaciones sin errores", "☐"],
        ["P-14", "Casos 19 y 20", "Arancel y configuración se mantienen desde pantalla", "☐"], ["P-15", "Actualizar sobre «ComexBol Pro» 1.0.0", "Instala COMEX JB y conserva las operaciones anteriores", "☐"],
        ["P-16", "Casos 21 a 23", "Ajustes del Art. 8, cuestionario y validador con las cifras del manual", "☐"], ["P-17", "Caso 24", "Costeo y flujo de caja idénticos a los del manual", "☐"],
        ["P-18", "Casos 25 y 26", "DIM validada; canales, levante y descargos funcionan", "☐"]], [1.4, 6.2, 7.2, 2])
    m.caja("La prueba más importante", "**P-09** confirma los supuestos tributarios que ningún dato de prueba puede verificar. Tome 3 importaciones ya liquidadas por la Aduana y repita el cálculo; cualquier diferencia indica un parámetro por corregir (sección 9).")

    m.h1("9. Parámetros que debe validar un despachante")
    m.tabla([["Parámetro", "Valor por defecto"], ["IVA efectivo en aduana", "14,94 %"], ["Base del ICE ad valorem", "(CIF + GA) × tasa"], ["Redondeo", "2 decimales (alternativa: Bs enteros)"],
        ["Umbral de bancarización", "Bs 50.000"], ["Seguro presunto sin póliza", "0 % (solo advierte)"], ["Tarifa de almacenaje / días libres", "0 (no se estima hasta que la configure con la tarifa de su recinto)"], ["Tolerancia de precio / de peso", "30 % frente al historial / 5 % frente al manifiesto"], ["IVA como crédito fiscal", "Sí (no entra al costo)"], ["Límite del CEDEIM", "Se exige como dato (sin pantalla aún)"], ["Tipo de cambio", "Se digita en la barra superior"]], [8, 9])

    m.h1("10. Construcción del instalador (equipo técnico)")
    m.p("El instalador se construye con NSIS desde Linux, macOS o Windows. Pasos desde Linux:")
    m.code("installer/construir-instalador.sh")
    m.bullets(["Publica la aplicación autocontenida para win-x64 (`dotnet publish … -r win-x64 --self-contained`).", "Descarga Tesseract 5.3 (Windows) y Poppler 24.08; incluye los idiomas español, inglés y OSD.",
               "Empaqueta todo con `makensis` y genera `dist/ComexJB-Setup-<versión>.exe`.",
               "Requiere: SDK .NET 8 oficial (incluye el componente Windows Desktop), `nsis`, `p7zip-full`, `curl`, `unzip`.",
               "**Licencias:** Tesseract (Apache 2.0) y Poppler (GPL) se redistribuyen sin modificar; conserve sus avisos de licencia en la carpeta `ocr`."])

    m.h1("11. Hallazgos de la primera ejecución real")
    m.p("Al ejecutar por primera vez la aplicación compilada (no solo las pruebas automáticas) se detectaron y corrigieron estos problemas. Se incluyen porque ilustran por qué **la prueba P-09 y la prueba en un PC real son indispensables**:")
    m.tabla([["Hallazgo", "Impacto", "Corrección"],
        ["«Agregar ítem» borraba el flete y el seguro recién digitados", "Liquidación con CIF menor al real", "Se guardan antes de refrescar; prueba de regresión"],
        ["«Confirmar datos» tras el OCR fallaba (referencia nula)", "No se podía confirmar", "Se conserva el identificador antes de recargar la lista; prueba que simula la deselección de WPF"],
        ["Números interpretados con configuración de EE. UU.", "En Windows boliviano «29197,20» se leería como 2.919.720", "La aplicación fija la cultura es-BO"],
        ["Cierre al mostrar la liquidación en equipos sin la fuente Consolas; símbolos (✔ ✖ ●) dependientes de fuentes", "Cierre inesperado", "Texto simple y fuente estándar"],
        ["Mensaje de Decisión visible en Contraste; nombres técnicos en el legajo; botón cortado", "Confusión", "Mensajes separados, nombres legibles, columna ensanchada"],
        ["Llamada de nota «( * )» del arancel leída como documento exigido", "Aviso falso de permiso en vehículos", "Se ignora; prueba con la partida real"],
        ["Arancel sin cargar: GA en 0 % sin aviso visible", "Liquidación subestimada", "Aviso permanente en pantalla y tarjeta «Arancel cargado» en el Panel"],
        ["Un ítem con partida inválida se guardaba y luego impedía «Calcular»; no había forma de borrarlo ni editarlo (hallazgo del usuario con la versión 1.0.0)", "Operación bloqueada", "Se valida antes de guardar; se agregan Editar/Eliminar ítem y Eliminar operación; pruebas de regresión"],
        ["Con el navegador de fuentes de Wine, la aplicación se cerraba al usar una fuente inexistente; el PBKDF2 del sistema no existe en Wine", "Cierres solo en el entorno de pruebas", "Fuente Segoe UI explícita y PBKDF2-SHA256 propio, verificado idéntico a la implementación de .NET"],
        ["El arancel convertido a Markdown leía mal el GA de 17 partidas (p. ej. «Para rayos X»: 10 % leído como 0 %) y perdía 11 partidas", "Gravamen subestimado en esas partidas", "Se lee directamente el PDF oficial celda por celda; verificado con una segunda lectura independiente"]], [6.8, 4.7, 5.5])

    m.h1("12. Limitaciones conocidas")
    m.bullets(["Instalador sin firma digital (SmartScreen avisará). La instalación, el arranque automático y la desinstalación se verificaron en Wine, **no en un Windows real**: pruébelos en un PC limpio (P-11).",
               "Capturas tomadas en entorno de pruebas; la tipografía en Windows será Segoe UI.", "Sin pantalla para almacenaje, exportación (DEX/CEDEIM), otras monedas ni gastos de origen/hasta frontera.",
               "ICE de bebidas alcohólicas, tabaco y el IEHD: tasa manual (no figuran en el arancel). Si el vehículo excede la antigüedad que prevé la tabla no se asigna tasa.",
               "El JSON para la DMI no está mapeado a las casillas oficiales SUMA (requiere el instructivo vigente de la Aduana); los roles se aplican solo en la interfaz; el arancel «PAR 12 %» citado en consultas no figura en ninguna columna del arancel 2026 y no se implementó. El importador está calibrado con el diseño de tablas del Arancel 2026; un arancel de otro año con otro diseño podría requerir ajustes (el sistema informa las páginas que no reconoce).",
               "Los escenarios de Decisión no se guardan. Sin migraciones automáticas de la base de datos."])

    m.h1("13. Cobertura frente a la solicitud COMEX")
    m.p("Se comparó el sistema con la solicitud de estructura modular (Ley 1990, D.S. 25870, SUMA, Decisión 571 de la CAN). Estado de cada módulo en la versión 1.2.0:")
    m.tabla([["Módulo solicitado", "Cubierto", "Parcial o pendiente"],
        ["1. Maestro de operaciones y carpetas digitales", "Carpeta por operación, tipo de despacho (general, anticipado, inmediato, menor cuantía, courier), legajo con documentos exigidos (factura, embarque, seguro, flete, empaque, certificados de origen, autorizaciones), ruta con semáforos, bitácora con usuario.", "El documento de embarque se controla por modalidad en la DIM; el legajo lista el documento de forma genérica. No hay línea de tiempo de hitos automáticos del manifiesto (se registran a mano)."],
        ["2. Clasificación y autorizaciones previas", "Selector NANDINA por código o texto, GA visible, alertas de AP según el tipo de documento del arancel, bloqueo de mercancías prohibidas, mantenimiento de partidas.", "La búsqueda es sobre la descripción del arancel (no por marca, modelo o composición química). Sin gestor ni borradores de solicitudes de AP."],
        ["3. Valoración aduanera y DAV", "Cuestionario de descarte, ajustes del Art. 8 (adiciones y deducciones), desglose de flete y seguro, seguro presunto configurable, validador de precios contra el historial propio, JSON con la valoración.", "Solo el Primer Método; sin base referencial externa de precios; el JSON no está mapeado a las casillas oficiales de la DAV en el SUMA."],
        ["4. Liquidación tributaria", "Base imponible detallada, GA con preferencias, ICE (ad valorem y vehículos por antigüedad), IEHD, IVA, UFV, fórmulas a la vista, liquidación por ítem, prorrateo, factor de importación, costo unitario y flujo de caja, estimación de almacenaje.", "Tarifas de almacén y ASP-B las ingresa el usuario; ICE de bebidas/tabaco manual; ICE de vehículos solo según el Apéndice I (sin cilindrada/combustible propios)."],
        ["5. Despacho y enlace con el SUMA / ADA", "Datos y validación de la DIM (campos críticos, régimen, bultos y peso contra el manifiesto, DAV, bancarización), canales con listas de control, levante, plantilla de descargos.", "Sin transmisión al SUMA ni lectura del MIC/DTA; régimen distinto de consumo sin cálculo propio."],
        ["6. Post-despacho y archivo fiscal", "Bitácora, expediente, Excel y JSON, respaldo de la base, hoja de costos proyectado frente a real.", "Pendiente: archivo probatorio inmutable PDF/A, conciliación bancario-aduanera automática y alertas del plazo de fiscalización."]], [4.2, 7.6, 5.2])
    m.caja("Lectura honesta", "Los módulos 3, 4 y 5 se ampliaron en esta versión. El módulo 6 sigue siendo el menos desarrollado. Todo lo «Cubierto» está probado con pruebas automáticas y en la aplicación en ejecución (Wine), no todavía en un Windows real.")

    m.h1("14. Registro de hallazgos")
    m.tabla([["Fecha", "Caso", "Qué pasó", "Esperado", "Captura"], ["", "", "", "", ""], ["", "", "", "", ""], ["", "", "", "", ""], ["", "", "", "", ""]], [2.5, 2, 5.5, 4.5, 2.5])
    ruta = AQUI + "/Manual-de-Instalacion-y-Pruebas"; m.guardar(ruta + ".docx"); return ruta

if __name__ == "__main__":
    for f in (manual_usuario, manual_implementacion):
        r = f(); print("DOCX:", r + ".docx")
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", AQUI, r + ".docx"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("PDF :", r + ".pdf")
