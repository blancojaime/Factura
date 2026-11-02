#!/usr/bin/env python3
"""Genera los manuales (DOCX + PDF) con las capturas reales. Uso: python3 generar-manuales.py"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from docgen import Manual

AQUI = os.path.dirname(os.path.abspath(__file__)); C = AQUI + "/capturas/"; A = C + "anotadas/"; I = C + "instalador/"
VERSION, FECHA = "1.0.0", "2 de noviembre de 2026"

# ============================================================== MANUAL DE USUARIO
def manual_usuario():
    m = Manual("Manual de Usuario", "Cómo decidir, acompañar y documentar una importación paso a paso", VERSION, FECHA)
    m.contenido(["Qué es y para qué sirve", "Instalación en un clic", "Conociendo la ventana", "Primer paso: cargar el arancel",
        "Crear una importación", "Registrar las mercancías", "Calcular y leer la liquidación", "Decidir: comparar escenarios",
        "Acompañar: ruta crítica y semáforos", "Documentar: legajo y bitácora", "Leer facturas con OCR", "Vehículos e ICE",
        "Preferencias arancelarias", "Contrastar con la DIM real", "Exportar (Excel y expediente)", "Problemas frecuentes y límites"])

    m.h1("1. Qué es y para qué sirve")
    m.p("ComexBol Pro es un asistente de escritorio para Windows que le ayuda en tres cosas durante una **importación a Bolivia**:")
    m.bullets(["**Decidir:** calcula cuánto pagará de tributos, cuánto le cuesta cada unidad puesta en su almacén y cuál oferta (FOB, CIF, DAP…) le conviene.",
               "**Acompañar:** le muestra los 12 pasos de la importación con fechas, responsables y semáforos que avisan cuándo algo se atrasa.",
               "**Documentar:** guarda automáticamente una bitácora de todo lo que ocurre, controla qué documentos faltan y genera el expediente en Excel."])
    m.caja("Importante", "ComexBol Pro es una **herramienta de apoyo**. Las cifras se calculan con el Arancel Aduanero de Importaciones 2026 y los parámetros "
           "tributarios vigentes configurados, pero **la liquidación oficial la determina la Aduana Nacional**. Antes de usarlo en operaciones reales, "
           "contraste el cálculo con 3 importaciones ya despachadas (sección 14) y consulte a su despachante.")

    m.h1("2. Instalación en un clic")
    m.bullets(["Haga doble clic en **ComexBolPro-Setup-1.0.0.exe**. No necesita permisos de administrador ni instalar nada más: el instalador incluye todo lo necesario (incluso el lector de texto OCR).",
               "Si Windows muestra «**Windows protegió su PC**» (SmartScreen), pulse **Más información → Ejecutar de todas formas**. Aparece porque el instalador aún no tiene firma digital comercial.",
               "Espere la barra de progreso (menos de un minuto). Al terminar, la aplicación se abre sola y se crean accesos directos en el Escritorio y en el menú Inicio.",
               "Para desinstalar: **Configuración → Aplicaciones → ComexBol Pro → Desinstalar**. Sus datos no se borran."], num=True)

    m.h1("3. Conociendo la ventana")
    m.figura(A + "01.png", "Ventana principal. Los números se explican en la tabla siguiente.")
    m.tabla([["N.º", "Zona", "Para qué sirve"],
        ["1", "TC USD a Bs", "Tipo de cambio oficial de venta (BCB) del día. **Confírmelo cada vez**: se usa para convertir a bolivianos."],
        ["2", "Botones superiores", "Importar el arancel, exportar el expediente (.md) y exportar a Excel."],
        ["3", "Nueva importación / Operaciones", "Crear una importación y elegir entre las ya registradas."],
        ["4", "Pestañas", "Ítems y documento · Liquidación · Decisión · Contraste con DIM · Ruta crítica · Legajo y bitácora."],
        ["5", "Visor de documento", "Muestra la factura o documento que está leyendo (imagen o primera página del PDF)."],
        ["6", "Formulario de captura", "Donde registra cada mercancía y los costos de la operación."]], [1.2, 4.3, 11.5])
    m.p("En la parte inferior verá la **barra de ruta crítica** (los 12 pasos con su semáforo) y la **barra de estado**, que le confirma cada acción o le explica un problema.")

    m.h1("4. Primer paso: cargar el arancel")
    m.p("Antes de registrar mercancías debe cargar el **Arancel Aduanero de Importaciones 2026**. Sin él, el sistema no puede determinar el gravamen arancelario, "
        "los documentos exigidos ni las mercancías prohibidas, y se lo advertirá en rojo en la pestaña Liquidación.")
    m.bullets(["Pulse **Importar catálogo…** (barra superior).", "Seleccione **los tres archivos del arancel a la vez** (mantenga Ctrl) y pulse Abrir.",
               "La barra de estado indica el resultado. Con el arancel 2026 completo: **8.121 partidas**, 97 capítulos y 229 avisos (filas cuyo detalle no pudo interpretarse con certeza; se informan, nunca se corrigen en silencio)."], num=True)
    m.caja("Una sola vez al año", "El arancel se carga una vez y queda guardado. Repita el paso solo cuando se publique un arancel nuevo; la importación reemplaza el catálogo anterior sin tocar sus operaciones.", "E3F4EA")

    m.h1("5. Crear una importación")
    m.bullets(["En **Nueva importación**, escriba el número de carpeta (por ejemplo IMP-2026-001) y elija el **Incoterm** pactado con su proveedor.",
               "Pulse **Crear**."], num=True)
    m.figura(C + "02-nueva-importacion.png", "Número de carpeta escrito; Incoterm FOB seleccionado.")
    m.figura(A + "03.png", "Importación creada: aparece en la lista (1), se dibuja la ruta crítica con sus 12 pasos (2) y la barra de estado lo confirma (3).")
    m.p("El **Incoterm** define qué ya está incluido en el precio de la factura. El sistema lo usa para sumar solo lo que falta (flete, seguro…) y obtener el **valor en aduana (CIF)**:")
    m.tabla([["Incoterm", "El precio de factura ya incluye", "Usted debe agregar"],
        ["EXW", "Nada", "Gastos de origen, flete y seguro"], ["FCA, FAS, FOB", "Entrega en origen", "Flete y seguro"],
        ["CFR, CPT", "Flete", "Seguro"], ["CIF, CIP", "Flete y seguro", "Nada"],
        ["DAP, DPU, DDP", "Todo hasta destino", "Nada; **reste** lo posterior a la frontera"]], [3.5, 6.5, 7])

    m.h1("6. Registrar las mercancías")
    m.p("En la pestaña **Ítems y documento**, complete el formulario de captura y pulse **Agregar ítem**. Repita por cada mercancía distinta.")
    m.figura(A + "04.png", "Formulario completo para el Caso 1 (tablets).")
    m.tabla([["N.º", "Campo", "Qué escribir"],
        ["1", "Partida NANDINA, Descripción, Valor factura, Peso bruto", "La partida de 10 dígitos (con o sin puntos). Valor total de la factura en USD. Peso bruto en kg."],
        ["2", "Flete / Seguro", "Fletes y seguro internacionales en USD, **solo si su Incoterm no los incluye**. Si los incluye (p. ej. CIF), déjelos en 0: el sistema se lo avisará si los escribe."],
        ["3", "Antigüedad / ICE %", "Solo vehículos: años de antigüedad (0 = nuevo). El ICE % se escribe a mano únicamente cuando el arancel no trae la tasa (por ejemplo bebidas)."],
        ["4", "Acuerdo / desgrav. %", "Solo si tiene Certificado de Origen (sección 13)."],
        ["5", "Botones", "**Agregar ítem** guarda la mercancía. **Calcular (F5)** liquida la operación."]], [1.2, 5.3, 10.5])
    m.figura(C + "05-item-agregado.png", "Ítem agregado: aparece en la lista con la alícuota tomada del arancel (10 %).")
    m.caja("Lo que hace el arancel por usted", "Al agregar el ítem, el sistema busca la partida y completa el **gravamen arancelario (GA)**; si la mercancía está **prohibida** la rechaza; "
           "si exige un **permiso previo** (SENASAG, AGEMED, IBMETRO…) lo agrega al legajo como documento faltante; y si está sujeta a **ICE** lo avisa.", "E3F4EA")

    m.h1("7. Calcular y leer la liquidación")
    m.p("Pulse **Calcular (F5)** y abra la pestaña **Liquidación**.")
    m.figura(C + "06-liquidacion.png", "Liquidación del Caso 1: FOB USD 40.000, flete USD 1.800, seguro USD 150, TC 6,96.")
    m.tabla([["Concepto", "Qué significa", "Cifra del ejemplo (Bs)"],
        ["Valor FOB", "Valor de la factura convertido a bolivianos", "278.400,00"], ["(+) Adiciones", "Flete + seguro (+ otros) que su Incoterm no incluía", "13.572,00"],
        ["(-) Deducciones", "Costos posteriores a la frontera incluidos en el precio (DAP/DDP)", "0,00"], ["**CIF aduana**", "Base de todos los tributos", "**291.972,00**"],
        ["Gravamen arancelario", "CIF × alícuota del arancel (10 %)", "29.197,20"], ["ICE / IEHD", "Impuestos especiales (vehículos, alcoholes, combustibles)", "0,00"],
        ["IVA", "14,94 % sobre (CIF + GA + ICE + IEHD)", "47.982,68"], ["**TOTAL TRIBUTOS**", "Suma que se paga en el banco", "**77.179,88**"]], [3.5, 9.5, 4])
    m.p("A la derecha aparecen los **avisos**. En el ejemplo: «FOB desde Bs 50.000: complete el respaldo bancario» — desde ese monto la ley (D.S. 772) exige acreditar el pago por una entidad financiera.")

    m.h1("8. Decidir: comparar escenarios")
    m.p("¿Le conviene la oferta FOB, la CIF o la DAP? La pestaña **Decisión** calcula el **costo unitario puesto en su almacén** y su **margen** para cada oferta.")
    m.bullets(["Arriba escriba: **Unidades** a importar, **Gastos locales** en Bs (transporte interno, almacenaje…), **Precio de mercado con IVA** por unidad y su **Margen objetivo** (%).",
               "Pulse **Agregar escenario** una vez por oferta y complete: nombre, Incoterm, valor total de la oferta, flete, seguro y, si es DAP/DDP, lo que cuesta después de la frontera.",
               "Pulse **Comparar**."], num=True)
    m.figura(C + "10-escenarios.png", "Tres ofertas cargadas (la última fila está resaltada porque se estaba editando).")
    m.figura(A + "11.png", "Resultado. (1) datos generales, (2) ofertas, (3) comparación ordenada por costo unitario; la mejor aparece en verde.")
    m.tabla([["Escenario", "CIF Bs", "Tributos Bs", "Costo unitario Bs", "Margen", "Veredicto"],
        ["FOB + flete propio", "291.972,00", "77.179,88", "**1.628,35**", "34,3 %", "Viable"], ["CIF del proveedor", "292.320,00", "77.271,87", "1.630,26", "34,2 %", "Viable"],
        ["DAP del proveedor", "297.888,00", "78.743,71", "1.660,88", "33,0 %", "Viable"]], [4, 2.6, 2.7, 3.2, 2, 2.5])
    m.p("**Veredicto:** *Viable* si el margen alcanza el objetivo, *Ajustado* si es positivo pero menor, *No viable* si es negativo. El precio de mercado se compara **sin IVA**, porque el IVA pagado en la importación se recupera como crédito fiscal.")

    m.h1("9. Acompañar: ruta crítica y semáforos")
    m.p("La pestaña **Ruta crítica** lista los 12 pasos de la importación, desde verificar la mercancía hasta el retiro con pase de salida. Las fechas se calculan automáticamente a partir del día de creación.")
    m.figura(A + "07.png", "Ruta crítica. (1) semáforo de cada etapa, (2) botón para marcar la etapa cumplida.")
    m.tabla([["Color", "Estado", "Significado"], ["Gris", "Pendiente", "Aún no corresponde iniciar"], ["Azul", "En curso", "Ya empezó y está dentro de plazo"],
        ["Amarillo", "Alerta", "Faltan 2 días o menos para su fecha de fin"], ["Verde", "Cumplida", "Registrada como terminada"], ["Rojo", "Vencida", "Pasó su fecha de fin sin cumplirse"]], [3, 3.5, 10.5])
    m.p("Cuando una etapa termine, pulse **Marcar cumplida**. El sistema registra la fecha real y anota en la bitácora si hubo retraso. La columna «Crítica» indica las etapas que, si se atrasan, atrasan toda la importación.")
    m.figura(C + "08-etapa-cumplida.png", "Primera etapa cumplida: pasa a verde y la barra inferior se actualiza.")
    m.caja("Plazos orientativos", "Las duraciones de cada etapa son estimaciones editables, **no plazos legales**. Los plazos oficiales (vigencia de la DIM, almacenaje, etc.) deben verificarse en la normativa vigente.")

    m.h1("10. Documentar: legajo y bitácora")
    m.figura(C + "09-legajo-bitacora.png", "A la izquierda, los documentos exigidos y cuáles faltan; a la derecha, la bitácora automática.")
    m.p("El **legajo** muestra qué documentos exige su operación (factura, embarque, lista de empaque, seguro, respaldo bancario, certificado de origen, permisos previos…) con **OK** o **FALTA**. "
        "La **bitácora** registra con fecha y hora cada ítem agregado, cada liquidación (con su versión), cada etapa cumplida y cada documento leído: es la memoria del proceso.")

    m.h1("11. Leer facturas con OCR")
    m.p("Si tiene la factura escaneada o en PDF, el sistema puede leerla y **proponer** los datos. Usted siempre revisa y confirma: el OCR puede equivocarse con dígitos.")
    m.bullets(["Con la operación seleccionada, pulse **Abrir y leer con OCR** y elija la imagen (JPG, PNG) o el PDF.",
               "El documento aparece a la izquierda y, a la derecha, la **propuesta** con la confianza de cada dato (Alta / Media / Baja).",
               "Corrija lo que sea necesario y pulse **Confirmar datos**."], num=True)
    m.figura(A + "14.png", "Factura leída: (1) documento, (2) datos propuestos con su confianza, (3) botón de confirmación.")
    m.figura(C + "15-ocr-corregido.png", "Aquí se corrigió a propósito el valor total (10500) antes de confirmar.")
    m.figura(C + "16-ocr-confirmado.png", "Datos confirmados: el valor y el peso pasan al formulario de captura. Complete la partida y la descripción y agregue el ítem.")
    m.figura(C + "17-legajo-con-factura.png", "El legajo ya marca la factura como OK y la bitácora registra lo confirmado por usted.")

    m.h1("12. Vehículos e ICE")
    m.p("Para vehículos, indique los **años de antigüedad**. El sistema toma del arancel (Apéndice I) la tasa del **Impuesto a los Consumos Específicos** correspondiente.")
    m.figura(C + "18-vehiculo-formulario.png", "Tractor de carretera usado (partida 8701.21.00.00), antigüedad 3 años.")
    m.figura(C + "19-vehiculo-avisos-ice.png", "Aviso: «ICE 30 % (Apéndice I, antigüedad 3 años)».")
    m.figura(C + "20-vehiculo-liquidacion.png", "Liquidación con ICE: CIF 157.992,00 · GA 7.899,60 · ICE 49.767,48 · IVA 32.219,47 · total 89.886,55.")
    m.caja("Cuando el arancel no trae la tasa", "En 227 partidas de vehículos las tasas no son legibles en el documento fuente: el sistema se lo indica y usted escribe el **ICE %** a mano. "
           "Lo mismo ocurre con bebidas alcohólicas y con el IEHD de combustibles. **El sistema nunca inventa una tasa.**")

    m.h1("13. Preferencias arancelarias")
    m.p("Si su proveedor le entrega un **Certificado de Origen**, puede aplicar la preferencia de un acuerdo comercial. En **Acuerdo / desgrav. %** elija el acuerdo (CAN, ACE 22 Chile, ACE 36 Mercosur, ACE 47, ACE 66 México, VEN) y deje la desgravación en 0: el sistema toma el porcentaje del arancel.")
    m.figura(C + "21-preferencia-formulario.png", "Reproductor de raza pura (0101.21.00.00) con acuerdo CAN.")
    m.figura(C + "22-preferencia-avisos.png", "El sistema muestra las preferencias del arancel por columna, aplica 100 % para CAN y exige el Certificado de Origen en el legajo.")
    m.bullets(["En el arancel 2026 casi todo tiene 100 % de preferencia; las excepciones son **México 0 %** (por ejemplo aceites en bruto) y **Chile 50 %** (por ejemplo mayonesa).",
               "Si usted declara un porcentaje distinto al del arancel, el sistema lo advierte.",
               "La desgravación **no** es automática: depende de las reglas de origen y de su certificado. Verifíquelo con su despachante."])

    m.h1("14. Contrastar con la DIM real")
    m.p("Esta pestaña le permite **probar que el sistema calcula igual que la Aduana**. Es la comprobación más importante antes de usarlo en serio.")
    m.bullets(["Registre en el sistema una importación **ya despachada**, con los mismos valores, flete, seguro y tipo de cambio de esa fecha, y pulse Calcular.",
               "Abra **Contraste con DIM** y escriba los tributos que la Aduana liquidó en la DIM (GA, ICE, IEHD, IVA).", "Pulse **Contrastar**."], num=True)
    m.figura(A + "12.png", "Cálculo igual al de la DIM: todas las filas «OK».")
    m.figura(C + "13-contraste-diferencia.png", "Con un IVA distinto (47.990) el sistema marca REVISAR y muestra la diferencia de 7,32 Bs.")
    m.p("Si hay diferencias, revise el tipo de cambio, el valor de flete y seguro, y consulte con su despachante: puede deberse a un parámetro tributario (IVA efectivo, base del ICE, redondeo) que deba ajustarse. Cada contraste queda en la bitácora.")

    m.h1("15. Exportar (Excel y expediente)")
    m.bullets(["**Excel…** crea un libro con cinco hojas: Resumen, Ítems, Liquidación, Ruta crítica y Bitácora. Los totales son fórmulas, por lo que se recalculan si usted modifica un valor.",
               "**Expediente (.md)…** crea un documento de texto con el resumen, las mercancías, la liquidación vigente, la ruta, el legajo y la bitácora completa; puede abrirlo con Word o imprimirlo a PDF."])

    m.h1("16. Problemas frecuentes y límites")
    m.tabla([["Situación", "Qué hacer"],
        ["«El arancel NO está cargado»", "Use Importar catálogo… con los 3 archivos del arancel (sección 4)."],
        ["«La partida … no existe en el arancel cargado»", "Revise el código de 10 dígitos; el sistema no calcula un GA sin respaldo."],
        ["«…figura como mercancía prohibida»", "La partida está prohibida (tipo P en el arancel). No se puede importar."],
        ["La lectura OCR falla con un PDF", "Los PDF se leen con el componente incluido. Si el archivo está dañado o protegido, conviértalo a imagen."],
        ["Un mensaje de error inesperado", "Sus datos están guardados. El detalle queda en %LocalAppData%\\ComexBolPro\\errores.log; envíelo a soporte."],
        ["Perdí mis datos / cambio de PC", "Copie el archivo %LocalAppData%\\ComexBolPro\\comex.db: es la copia de seguridad completa."]], [6.5, 10.5])
    m.h3("Lo que todavía no hace")
    m.bullets(["No genera el formulario SUMA ni transmite nada a la Aduana: es un apoyo de cálculo y control.",
               "Las preferencias de 204 partidas no pueden asignarse a una columna con certeza: el sistema muestra los porcentajes impresos y usted verifica.",
               "Los escenarios de la pestaña Decisión no se guardan al cerrar la aplicación.",
               "No cubre exportaciones (DEX/CEDEIM) ni almacenaje en pantalla; existen en el código pero aún no tienen pantalla."])
    m.p("Las capturas de este manual son **reales**, tomadas de la aplicación en ejecución en un entorno de pruebas; en su Windows la tipografía puede verse levemente distinta.", italic=True)
    ruta = AQUI + "/Manual-de-Usuario"; m.guardar(ruta + ".docx"); return ruta

# ============================================================== MANUAL DE INSTALACIÓN, IMPLEMENTACIÓN Y PRUEBAS
def manual_implementacion():
    m = Manual("Manual de Instalación y Pruebas", "Instalación, puesta en marcha, verificación y manual de pruebas con ejemplos completos", VERSION, FECHA)
    m.contenido(["Requisitos", "Instalación en un clic", "Instalación para varios equipos", "Datos, respaldos y actualización", "Carga del arancel",
        "Pruebas automáticas", "Manual de pruebas (casos con cifras esperadas)", "Pruebas de aceptación", "Parámetros que debe validar un despachante",
        "Construcción del instalador (equipo técnico)", "Hallazgos de la primera ejecución real", "Limitaciones conocidas", "Registro de hallazgos"])

    m.h1("1. Requisitos")
    m.tabla([["Elemento", "Requisito"], ["Sistema operativo", "Windows 10 u 11, 64 bits"], ["Espacio en disco", "≈ 450 MB (incluye .NET, OCR y manuales)"],
        ["Memoria", "4 GB recomendados"], ["Permisos", "Usuario normal (no requiere administrador)"],
        ["Software adicional", "Ninguno: .NET, Tesseract (OCR con español) y Poppler (PDF) vienen dentro del instalador"],
        ["Internet", "No necesario para operar"]], [5, 12])

    m.h1("2. Instalación en un clic")
    m.bullets(["Copie **ComexBolPro-Setup-1.0.0.exe** al equipo y haga doble clic.",
               "Si aparece SmartScreen («Windows protegió su PC»): **Más información → Ejecutar de todas formas**. Es normal: el instalador no tiene firma digital comercial (la firma requiere un certificado de pago; se recomienda adquirirlo antes de distribuir ampliamente).",
               "Espere la barra de progreso; al finalizar la aplicación se abre sola.",
               "Se crean: carpeta de programa en `%LocalAppData%\\Programs\\ComexBolPro`, accesos directos en el Escritorio y en Inicio → ComexBol Pro (incluye «Manual del usuario» y «Desinstalar»)."], num=True)
    for f, t in (("01-progreso.png", "Instalador en curso (pantalla única con barra de progreso)."), ("02-terminado.png", "Instalación completada.")):
        m.figura(I + f, t, 13)
    m.h1("3. Instalación para varios equipos")
    m.bullets(["**Silenciosa** (sin pantallas): `ComexBolPro-Setup-1.0.0.exe /S`", "**Desinstalación silenciosa:** `\"%LocalAppData%\\Programs\\ComexBolPro\\Desinstalar.exe\" /S`",
               "Para instalar en una carpeta distinta: `ComexBolPro-Setup-1.0.0.exe /S /D=C:\\Ruta\\ComexBolPro` (la ruta va al final y sin comillas).",
               "Cada usuario de Windows tiene su propia base de datos; para compartir información entre equipos copie el archivo `comex.db` (sección 4)."])

    m.h1("4. Datos, respaldos y actualización")
    m.tabla([["Qué", "Dónde"], ["Base de datos (operaciones, bitácora, liquidaciones, arancel)", "`%LocalAppData%\\ComexBolPro\\comex.db`"],
        ["Registro de errores inesperados", "`%LocalAppData%\\ComexBolPro\\errores.log`"], ["Programa", "`%LocalAppData%\\Programs\\ComexBolPro`"]], [8.5, 8.5])
    m.bullets(["**Respaldo:** cierre la aplicación y copie `comex.db`. Esa única copia contiene todo.", "**Actualizar:** ejecute el instalador nuevo; reemplaza el programa y conserva sus datos.",
               "**Desinstalar** no borra `comex.db`. Para eliminar todo, borre también `%LocalAppData%\\ComexBolPro`.",
               "Los documentos (facturas escaneadas) **no** se copian a la base: se guarda su ubicación y su huella SHA-256. Conserve una carpeta por embarque."])
    m.caja("Cambios de versión", "Todavía no hay migraciones automáticas de la base: ante un cambio de estructura, exporte sus expedientes a Excel y recree la base.")

    m.h1("5. Carga del arancel")
    m.bullets(["Abra ComexBol Pro → **Importar catálogo…** → seleccione **los 3 archivos `.md`** del Arancel 2026 a la vez (Ctrl+clic).",
               "Resultado esperado con los archivos del arancel oficial 2026: **8.121 partidas**, 97 capítulos, **7.917** con preferencias asignadas por columna y **229 avisos**.",
               "Los 229 avisos incluyen 227 filas del Apéndice ICE (vehículos) cuyas tasas no son legibles: el ICE se ingresa a mano en esos casos."], num=True)
    m.tabla([["Dato del arancel", "Estado"], ["Código, descripción, GA, unidad", "Leídos de la tabla"], ["Documento adicional (AP, C, C*, DJ…), entidad, disposición legal", "Leídos"],
        ["Mercancía prohibida (tipo P)", "Detectada: el sistema bloquea la partida"], ["Marca ICE / IEHD", "Detectada (la tasa de IEHD no viene en el arancel)"],
        ["ICE de vehículos por antigüedad (Apéndice I)", "Solo filas con las 6 tasas legibles"],
        ["Preferencias (CAN/ACE36/47/VEN, ACE 22 Chile y Protocolo, ACE 66 México)", "Asignadas por columna; contraste con el PDF: 89 de 89 filas verificadas coinciden"]], [9, 8])
    m.p("**Verificación recomendada:** revise por muestreo 20–30 partidas de su interés contra el arancel impreso (prueba P-02).")

    m.h1("6. Pruebas automáticas")
    m.p("El código incluye pruebas automáticas que se ejecutan en una consola (equipo técnico):")
    m.code("for t in tests/*/; do (cd $t && dotnet test); done")
    m.tabla([["Proyecto", "Pruebas", "Cubre"], ["ComexBol.Core", "25", "Liquidación, Incoterms, ruta crítica, lectura del arancel"], ["ComexBol.Data", "23", "Base de datos, catálogo, preferencias, casos del manual"],
        ["ComexBol.Documentos", "9", "OCR real (Tesseract), PDF (Poppler), Excel"], ["ComexBol.Presentation", "11", "Lógica de la ventana, regresiones halladas en uso real"], ["**Total**", "**68**", ""]], [5, 2.5, 9.5])
    m.p("Con el arancel completo: `COMEXBOL_ARANCEL_DIR=<carpeta con los 3 .md> dotnet test` (PowerShell: `$env:COMEXBOL_ARANCEL_DIR=\"C:\\arancel\"`). El caso 9 verifica 8.121 partidas y 7.917 con preferencias asignadas.")

    m.h1("7. Manual de pruebas")
    m.p("Convenciones: TC = 6,96 Bs/USD (dato de prueba; use el oficial). Las cifras se muestran con formato boliviano. **Cada cifra de estos casos fue obtenida ejecutando la aplicación real** y está además fijada en una prueba automática. "
        "**Preparación común:** abra la aplicación, verifique TC = 6,96 e importe el arancel (sección 5).")
    m.h2("Caso 1 — Tablets, Incoterm FOB")
    m.p("**Datos:** 200 tablets con IMEI, partida **8471.30.00.10**, valor USD 40.000, peso 800 kg, flete USD 1.800, seguro USD 150.")
    m.bullets(["Carpeta `IMP-2026-001`, Incoterm **FOB** → Crear.", "Partida `8471.30.00.10`, Descripción `Tablets con IMEI`, Valor `40000`, Peso `800`, Flete `1800`, Seguro `150` → **Agregar ítem** → **Calcular (F5)**."], num=True)
    m.figura(C + "06-liquidacion.png", "Resultado esperado del Caso 1.")
    m.tabla([["Concepto", "Esperado (Bs)"], ["Valor FOB", "278.400,00"], ["Adiciones", "13.572,00"], ["CIF aduana", "**291.972,00**"], ["Gravamen arancelario (10 %)", "29.197,20"],
        ["IVA", "47.982,68"], ["**Total tributos**", "**77.179,88**"]], [9, 6])
    m.p("Aviso esperado: «FOB desde Bs 50.000: complete el respaldo bancario». Pestaña Legajo: Factura, Embarque, Lista de empaque, Seguro, Respaldo bancario y Factura de flete en **FALTA**.")
    m.h2("Caso 2 — ¿FOB, CIF o DAP? (decisión)")
    m.p("Pestaña **Decisión**: Unidades 200, Gastos locales 4500, Precio de mercado 2800, Margen objetivo 15; escenarios FOB 40000 (flete 1800, seguro 150), CIF 42000 y DAP 44000 (deducción post-frontera 1200).")
    m.figura(C + "11-decision-resultados.png", "Resultado esperado del Caso 2.")
    m.tabla([["Escenario", "CIF Bs", "Tributos Bs", "Costo unit. Bs", "Margen"], ["FOB + flete propio", "291.972,00", "77.179,88", "1.628,35", "34,3 %"],
        ["CIF del proveedor", "292.320,00", "77.271,87", "1.630,26", "34,2 %"], ["DAP del proveedor", "297.888,00", "78.743,71", "1.660,88", "33,0 %"]], [4.5, 3, 3, 3.3, 3.2])
    m.h2("Caso 3 — Animales vivos, CFR (permiso sanitario)")
    m.p("Partida **0101.21.00.00**, valor USD 25.000, peso 3.000 kg, seguro USD 250, Incoterm **CFR** (el flete va en el precio; no lo digite). "
        "Esperado: CIF **175.740,00**; GA 5 % **8.787,00**; IVA **27.568,33**; total **36.355,33**. Aviso: documento adicional C* — SENASAG (Ley 830); el legajo exige la autorización previa.")
    m.h2("Caso 4 — Tractor usado con ICE por antigüedad")
    m.p("Partida **8701.21.00.00**, valor USD 20.000, peso 4.000 kg, **antigüedad 3 años**, FOB, flete USD 2.500, seguro USD 200.")
    m.figura(C + "20-vehiculo-liquidacion.png", "Resultado esperado del Caso 4.")
    m.p("Esperado: CIF **157.992,00**; GA 5 % **7.899,60**; ICE 30 % sobre (CIF+GA) **49.767,48**; IVA **32.219,47**; total **89.886,55**. Con antigüedad 0 el ICE pasa a 15 %.")
    m.h2("Caso 5 — Umbral de bancarización (D.S. 772)")
    m.tabla([["Valor FOB", "Resultado"], ["USD 7.000 (Bs 48.720), partida 8471.30.00.90", "**Sin** aviso de bancarización · tributos Bs 12.878,64"], ["FOB equivalente a Bs 50.000,00", "**Con** aviso · tributos Bs 13.217,00"]], [8, 9])
    m.h2("Caso 6 — Whisky: el ICE no viene en el arancel")
    m.p("Partida **2208.30.00.00**, valor USD 10.000, CIF. GA **40 %**. Avisos: «partida sujeta a ICE… ingrese manualmente» y «documento adicional C — SENASAG». Escriba en *ICE %* la tasa que indique su despachante y verifique que se aplique sobre (CIF+GA). El sistema **no inventa** la tasa.")
    m.h2("Caso 7 — Mercancía prohibida y medicamento")
    m.p("Partida **8703.23.10.10** (vehículo a GLP, tipo **P**): al agregarla el sistema muestra «…figura como mercancía prohibida» y no liquida. Partida **3004.90.10.00**: aviso con **AGEMED** y el legajo exige la autorización.")
    m.h2("Caso 8 — Seguimiento de la ruta")
    m.p("Cree la operación el 02/11/2026: etapa I01 plan 02/11 a 04/11. Márquela cumplida: pasa a verde y la bitácora anota «a tiempo». Con una fecha posterior a un plazo pasa a Vencida (rojo); a 2 días o menos del fin, Alerta (amarillo).")
    m.figura(C + "08-etapa-cumplida.png", "Resultado esperado del Caso 8.")
    m.h2("Caso 9 — Arancel completo")
    m.p("Tras importar: barra de estado «Catálogo: 8121 partidas, 229 avisos/rechazos».")
    m.h2("Caso 10 — OCR de factura (imagen y PDF)")
    m.p("Abra `docs/ejemplos/factura-ejemplo.png` (y repita con `factura-ejemplo.pdf`). Propuesta esperada (puede variar algún dígito):")
    m.tabla([["Campo", "Valor", "Confianza"], ["N.º factura", "INV-88213", "Media"], ["Proveedor", "Shenzhen Tech Co., Ltd", "Alta"], ["Incoterm", "FOB", "Alta"], ["Moneda", "USD", "Media"],
        ["Valor total", "10000", "Media"], ["Peso bruto kg", "1250.5", "Media"]], [5, 8, 4])
    m.figura(A + "14.png", "Resultado esperado del Caso 10.")
    m.p("Corrija el valor a 10500 y confirme: el legajo marca la factura como OK y la bitácora registra «Confirmado por el usuario».")
    m.h2("Caso 11 — Contraste con una DIM")
    m.p("Con el Caso 1 liquidado, pestaña Contraste con DIM: GA `29197,20`, IVA `47982,68` → todas las filas OK. Cambie el IVA a `47990` → la fila IVA y el total marcan REVISAR (diferencia 7,32).")
    m.figura(C + "13-contraste-diferencia.png", "Resultado esperado del Caso 11 con diferencia.")
    m.h2("Caso 12 — Exportar a Excel")
    m.p("**Excel…** → abra el .xlsx: hojas Resumen, Ítems, Liquidación, Ruta crítica y Bitácora. En Liquidación los totales son **fórmulas**. Para el Caso 1: CIF 291.972,00; total tributos 77.179,88.")
    m.h2("Casos 13 a 15 — Preferencias arancelarias")
    m.bullets(["**Caso 13:** partida 0101.21.00.00, acuerdo **CAN**, desgravación 0 → «desgravación 100 % tomada del arancel para CAN. Requiere Certificado de Origen»; GA = 0; el legajo exige el certificado.",
               "**Caso 14:** partida 1507.10.00.00 (aceite en bruto) con **ACE 66 (México)** → el arancel indica **0 %**: no hay desgravación y el GA se cobra completo.",
               "**Caso 15:** partida 2103.90.10.00 (mayonesa) con **ACE 22 (Chile)** → **50 %** (Protocolo VII). Si declara 100 %, el aviso dice «usted declaró 100 % y el arancel indica 50 %».",
               "Sin acuerdo, una desgravación > 0 se rechaza: «Indique el acuerdo comercial que sustenta la desgravación»."])
    m.figura(C + "22-preferencia-avisos.png", "Resultado esperado del Caso 13.")

    m.h1("8. Pruebas de aceptación")
    m.tabla([["#", "Prueba", "Resultado esperado", "Cumple"],
        ["P-01", "Importar los 3 archivos del arancel", "8.121 partidas / 97 capítulos", "☐"], ["P-02", "Contrastar 20 partidas con el arancel impreso", "GA, unidad y documento coinciden", "☐"],
        ["P-03", "Casos 1, 3, 4, 5", "Cifras idénticas a las de este manual", "☐"], ["P-04", "Caso 7", "Prohibida bloqueada; AGEMED exigida", "☐"],
        ["P-05", "Cambiar el TC y recalcular", "La versión 2 queda en bitácora; la 1 se conserva", "☐"], ["P-06", "Cerrar y reabrir la aplicación", "Operaciones, ruta y bitácora persisten", "☐"],
        ["P-07", "Caso 10 con una factura real escaneada", "Propuesta razonable; nada se aplica sin confirmar", "☐"], ["P-08", "Exportar expediente y Excel", ".md con 6 secciones; .xlsx con 5 hojas", "☐"],
        ["P-09", "**Contraste con 3 DIM reales ya despachadas**", "Tributos de la app = tributos pagados (diferencia ≤ redondeo)", "☐"],
        ["P-10", "Casos 2 y 11 en pantalla", "Tablas idénticas a las del manual", "☐"], ["P-11", "Instalación en un PC limpio sin permisos de administrador", "Instala, abre y lee una factura PDF", "☐"]], [1.4, 6.2, 7.2, 2])
    m.caja("La prueba más importante", "**P-09** confirma los supuestos tributarios que ningún dato de prueba puede verificar. Tome 3 importaciones ya liquidadas por la Aduana y repita el cálculo; cualquier diferencia indica un parámetro por corregir (sección 9).")

    m.h1("9. Parámetros que debe validar un despachante")
    m.tabla([["Parámetro", "Valor por defecto"], ["IVA efectivo en aduana", "14,94 %"], ["Base del ICE ad valorem", "(CIF + GA) × tasa"], ["Redondeo", "2 decimales (alternativa: Bs enteros)"],
        ["Umbral de bancarización", "Bs 50.000"], ["Seguro presunto sin póliza", "0 % (solo advierte)"], ["Límite del CEDEIM", "Se exige como dato (sin pantalla aún)"], ["Tipo de cambio", "Se digita en la barra superior"]], [8, 9])

    m.h1("10. Construcción del instalador (equipo técnico)")
    m.p("El instalador se construye con NSIS desde Linux, macOS o Windows. Pasos desde Linux:")
    m.code("installer/construir-instalador.sh")
    m.bullets(["Publica la aplicación autocontenida para win-x64 (`dotnet publish … -r win-x64 --self-contained`).", "Descarga Tesseract 5.3 (Windows) y Poppler 24.08; incluye los idiomas español, inglés y OSD.",
               "Empaqueta todo con `makensis` y genera `dist/ComexBolPro-Setup-<versión>.exe`.",
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
        ["Arancel sin cargar: GA en 0 % sin aviso visible", "Liquidación subestimada", "Aviso permanente en pantalla"]], [6.8, 4.7, 5.5])

    m.h1("12. Limitaciones conocidas")
    m.bullets(["Instalador sin firma digital (SmartScreen avisará). El instalador se verificó solo parcialmente (ver sección 2).",
               "Capturas tomadas en entorno de pruebas; la tipografía en Windows será Segoe UI.", "Sin pantalla para almacenaje, exportación (DEX/CEDEIM), otras monedas ni gastos de origen/hasta frontera.",
               "Preferencias de 204 partidas sin columna asignada; ICE de vehículos solo con 6 tasas legibles; IEHD y bebidas: tasa manual.",
               "Mapeo a casillas SUMA pendiente (requiere el instructivo vigente de la Aduana). Importación directa del arancel en PDF pendiente (hoy se importa el formato Markdown).",
               "Los escenarios de Decisión no se guardan. Sin migraciones automáticas de la base de datos."])

    m.h1("13. Registro de hallazgos")
    m.tabla([["Fecha", "Caso", "Qué pasó", "Esperado", "Captura"], ["", "", "", "", ""], ["", "", "", "", ""], ["", "", "", "", ""], ["", "", "", "", ""]], [2.5, 2, 5.5, 4.5, 2.5])
    ruta = AQUI + "/Manual-de-Instalacion-y-Pruebas"; m.guardar(ruta + ".docx"); return ruta

if __name__ == "__main__":
    for f in (manual_usuario, manual_implementacion):
        r = f(); print("DOCX:", r + ".docx")
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", AQUI, r + ".docx"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("PDF :", r + ".pdf")
