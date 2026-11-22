#!/usr/bin/env python3
"""Plan de complementación de COMEX JB a partir del manual de procedimientos de importación de maquinaria (DOCX + PDF)."""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from docgen import Manual

AQUI = os.path.dirname(os.path.abspath(__file__)); C = AQUI + "/capturas/"
VERSION, FECHA = "1.3.0", "22 de noviembre de 2026"

def plan():
    m = Manual("Plan de Complementación", "Del manual de procedimientos de importación de maquinaria a nuevas capacidades de COMEX JB", VERSION, FECHA)
    m.contenido(["Resumen ejecutivo", "Lo que dice el manual (comprensión)", "Verificación en fuentes oficiales", "Diagnóstico: manual frente a COMEX JB",
                 "Plan de módulos: implementados en la versión 1.3.0", "Plan de módulos: próximas versiones", "Cómo responde COMEX JB a los cuatro objetivos", "Riesgos, supuestos y límites", "Fuentes consultadas"])

    m.h1("1. Resumen ejecutivo")
    m.p("El manual del usuario («Manual de Procedimientos de Importación de Maquinaria a Bolivia, gestión 2026») describe, con el caso de **hornos a gas para pizzas importados a El Alto**, el camino completo de una importación: formalización, compra, logística, despacho y puesta en tienda. Trae además un compendio normativo, un simulador de costos y una lista de control del expediente.")
    m.p("Se leyó el manual hoja por hoja, se **contrastó con fuentes oficiales y especializadas** y se comparó con COMEX JB 1.2.0. El resultado más importante:")
    m.bullets(["**Dos decretos de 2026 cambian el cálculo del Gravamen Arancelario (GA).** El D.S. 5646 (vigente desde el 6/07/2026) reduce 5 puntos las alícuotas **y cambia la base imponible del GA**: ya no es el CIF completo, sino el valor de transacción + carga y descarga + **10 % del transporte y seguro** hasta la frontera. El D.S. 5516 da GA 0 % a cierta maquinaria **solo hasta el 31/12/2026**, una fecha que el manual no menciona. COMEX JB 1.2.0 calculaba el GA sobre el CIF completo y sin fechas de vigencia: **la liquidación habría quedado sobrestimada** para despachos posteriores al 6 de julio.",
               "El manual aporta **11 pasos** y **12 controles** que la aplicación no tenía como guía operativa.",
               "El manual exige distinguir **importador habitual y no habitual** (tope USD 2.000 por despacho y USD 4.000 por año para el no habitual) y COMEX JB no lo validaba.",
               "El simulador del manual compara **con y sin beneficio arancelario**; COMEX JB comparaba solo Incoterms."], num=False)
    m.p("La versión **1.3.0** incorpora cinco módulos que cierran esas brechas (sección 5). Las siguientes versiones (sección 6) completan DAM y plazos, Parte de Recepción, pago, archivo probatorio, catálogo de beneficios y análisis de conveniencia financiera ampliado.")

    m.h1("2. Lo que dice el manual (comprensión)")
    m.tabla([["Hoja", "Contenido", "Idea fuerza"],
        ["1 · Resumen y normativa", "Ficha del proyecto (hornos 8417.20 en El Alto), 7 normas aplicables: Ley 1990 y D.S. 25870 (RLGA), Ley 843, D.S. 5516, D.S. 5646, Reglamento de Operadores, acuerdos CAN/ACE y arts. 117–119 RLGA.", "El GA 0 % no exime del IVA 14,94 %. Importador Habitual con NIT Régimen General y SEPREC. Hornos a gas nuevos no requieren AP."],
        ["2 · Manual de procedimientos", "11 pasos en 5 fases: formalización (P-01 y P-02), compra (P-03 y P-04), logística (P-05 y P-06), despacho (P-07 a P-10) y tienda (P-11), con responsables, documentos, plazos, normativa y consejos.", "Clasificar y validar beneficios ANTES de pagar; guardar el SWIFT; no pasar de 20 días con la DAM; exhibir la DIM en la tienda."],
        ["3 · Simulador", "Lote de 4 modelos de horno; flete, seguro y gastos prorrateados por valor; CIF, GA 0 %, IVA y costo puesto en tienda; comparación GA 0 % frente a 10 %.", "El ahorro del beneficio es GA + su IVA asociado; el IVA se recupera como crédito fiscal."],
        ["4 · Checklist", "12 verificaciones de expediente con entidad emisora, obligatoriedad y criterio de aprobación.", "Un expediente completo respalda legalmente la mercancía ante controles."]], [3.2, 8.3, 5.5])
    m.h3("El caso del manual, recalculado")
    m.p("El motor de COMEX JB reproduce el simulador de la hoja 3: lote de 4 hornos (FOB USD 8.080, flete USD 1.450, seguro USD 180, TC 6,96) → CIF **USD 9.710** (Bs 67.581,60), GA 0 % por D.S. 5516 y IVA **USD 1.450,67**. Con GA 10 % «sin beneficio» el simulador da GA USD 971 y total de tributos USD 2.566,74 (esta cifra la reproduce una prueba automática de COMEX JB).")
    m.caja("Observación sobre el Arancel 2026 cargado", "En el Arancel Aduanero 2026 que usa COMEX JB, las subpartidas de hornos industriales no eléctricos (8417.10, 8417.20.10, 8417.20.90) **ya aparecen con GA 0 %** (también la mayoría de la maquinaria del capítulo 84). El «0 %» del manual puede estar ya incorporado al arancel; el beneficio del D.S. 5516 sólo cambia el resultado en subpartidas que el arancel aún muestra con GA mayor. Verifique cada subpartida.")

    m.h1("3. Verificación en fuentes oficiales")
    m.p("Se contrastaron las afirmaciones del manual con la Gaceta Oficial (texto de consulta) y fuentes especializadas. Estado: **Confirmado**, **Parcial**, **No verificado** o **Corregir**.")
    m.tabla([["Afirmación del manual", "Estado", "Hallazgo"],
        ["D.S. 5516: GA 0 % para maquinaria de la industria alimenticia", "Parcial", "Confirmado por fuentes especializadas (publicado 13/01/2026; Anexos 3 y 4 por subpartida). **Vigencia hasta el 31/12/2026**: el manual no lo dice. No se obtuvo el texto íntegro de los Anexos."],
        ["D.S. 5646: «reducción general temporal de 5 puntos» al GA", "Corregir", "Texto de consulta de la Gaceta leído: reduce 5 puntos (40→35, …, 10→5, 5→0) hasta el 31/12/2027, vigente desde el 06/07/2026, **y modifica el art. 20 del RLGA: base del GA = valor de transacción + carga y descarga + 10 % del transporte y seguro hasta la frontera** (aéreo: flete = 10 % de lo pagado). El manual y su simulador calculan el GA sobre el CIF completo."],
        ["Mercancías con un D.S. de GA temporal vigente", "Confirmado", "Disposición transitoria del D.S. 5646: conservan su alícuota hasta el vencimiento si es inferior; luego se ajustan a la tabla del D.S. 5646."],
        ["IVA importaciones 14,94 % sobre CIF + GA", "Parcial", "Coherente con la Ley 843 y con fuentes; el D.S. 5646 no modifica el IVA (el texto solo habla del GA). Hay un D.S. 5709 citado por una fuente que fija GA e IVA en 0 % para un anexo de bienes: **por verificar** su alcance, porque cambiaría el crédito fiscal."],
        ["Importador no habitual: USD 2.000 por despacho y USD 4.000 por año", "Confirmado (fuentes secundarias)", "Coincide con el despacho de menor cuantía (FOB ≤ USD 2.000) y el tope anual de la modalidad no presencial. Para ser **habitual**: Padrón de Operadores (F-171) y garantía mínima de 2.000 UFV (el manual no la menciona)."],
        ["DAM: registrar antes del arribo; plazo máximo 20 días", "No verificado", "La DAM existe (RD 01-013-17, modificada por RD 01-022-19). No se encontró el plazo de 20 días en fuentes oficiales."],
        ["Pago de tributos en 3 días hábiles de validada la DIM", "Parcial", "El RLGA fija 3 días contados desde el día hábil siguiente a la aceptación (según el texto citado por una fuente); verificar el cómputo exacto."],
        ["Canales Verde / Amarillo / Rojo", "Confirmado", "D.S. 2295 (2015): verde = levante inmediato con control posterior; rojo = reconocimiento físico y documental (máx. 3 horas desde la asignación del técnico y no más del 10 % mensual)."],
        ["DAV integrada en el SUMA", "Confirmado", "La Aduana integró la DAV al SUMA (reglamento de llenado: RD 01-033-21)."],
        ["Seguro «2 % referencial, Art. 20 RLGA»", "No verificado", "El art. 20 RLGA trata la base del GA; no se halló un porcentaje presunto de seguro de 2 %. En COMEX JB es un parámetro configurable (por defecto 0 %)."],
        ["Hornos a gas nuevos no requieren autorización previa", "Parcial", "Coherente con el arancel cargado (sin tipo de documento para 8417.20); verifique el cilindro de GLP y los gases controlados."]], [5.2, 2.8, 9])
    m.caja("Importante", "Las fuentes especializadas (estudios jurídicos, portales tributarios) son secundarias: **el texto oficial prevalece**. Antes de una operación real, confirme con su despachante y en la Gaceta Oficial / Aduana Nacional. El plazo de la DAM y los Anexos del D.S. 5516 quedan pendientes de verificación.", "FDE8E7")

    m.h1("4. Diagnóstico: manual frente a COMEX JB")
    m.tabla([["Necesidad (manual / usuario)", "Estado en 1.2.0", "Brecha", "Respuesta"],
        ["GA según la norma vigente a la fecha de la DIM", "GA sobre CIF, sin vigencias", "**Crítica**: liquidación errónea desde el 06/07/2026", "Módulo A (1.3.0)"],
        ["Beneficio D.S. 5516 con vencimiento", "No existía", "Alta", "Módulo A (1.3.0)"],
        ["Pasos del procedimiento y control del expediente", "Ruta crítica de 12 etapas, legajo", "Media: faltaba la guía P-01…P-11 y C-01…C-12", "Módulo B (1.3.0)"],
        ["Importador habitual / no habitual", "Perfil sin reglas", "Alta (bloquea el despacho)", "Módulo C (1.3.0)"],
        ["Comparar escenarios (con/sin beneficio, origen, Incoterm)", "Solo Incoterm", "Alta (decisión financiera)", "Módulo D (1.3.0)"],
        ["Fuente de datos para el SUMA", "JSON", "Media: formato de transcripción", "Módulo E (1.3.0)"],
        ["DAM, plazos y alertas", "Etapa genérica en la ruta", "Media", "Módulo F (próxima)"],
        ["Parte de Recepción y discrepancias", "Peso y bultos en la DIM", "Media", "Módulo G (próxima)"],
        ["Pago (RUP) y refrendo bancario", "Aviso de bancarización", "Media", "Módulo H (próxima)"],
        ["Archivo probatorio y conciliación bancario-aduanera", "Expediente .md/Excel", "Media (fiscalización diferida)", "Módulo I (próxima)"],
        ["Catálogo de beneficios por subpartida (Anexos)", "Marca manual por ítem", "Media", "Módulo J (próxima)"],
        ["Rentabilidad: flujo de caja, punto de equilibrio", "Costeo y precio sugerido", "Media", "Módulo K (próxima)"]], [5.2, 3.8, 4.2, 3.8])

    m.h1("5. Plan de módulos: implementados en la versión 1.3.0")
    m.h2("Módulo A · Medidas arancelarias por fecha")
    m.bullets(["Nuevo campo **Fecha de la DIM** en la operación: define qué decretos rigen (se propone la fecha de hoy; sin fecha rige el régimen anterior).",
               "**D.S. 5646:** alícuota −5 puntos (hasta el 31/12/2027) y **nueva base imponible del GA** (valor de transacción + ajustes del Art. 8 + carga y descarga + 10 % del transporte y seguro). El IVA y el ICE siguen sobre el CIF completo.",
               "**D.S. 5516:** casilla «Beneficio D.S. 5516» por ítem (GA 0 % hasta el 31/12/2026), con **aviso de vencimiento** en los 45 días previos y cálculo automático de la alícuota que corresponde después.",
               "Nuevo campo **Carga y descarga** (se suma al CIF y entra completo a la base del GA).",
               "Bloque **Impacto de las medidas arancelarias** en la Liquidación: régimen anterior, con D.S. 5646 y lo aplicado, con el ahorro en Bs."], num=False)
    m.figura(C + "47-liquidacion-regimen-vigente.png", "Liquidación con el régimen vigente: base del GA, alícuota 10 % → 5 % y fórmulas a la vista.")
    m.figura(C + "48-liquidacion-impacto.png", "Impacto de las medidas: Bs 77.179,88 con el régimen anterior frente a Bs 59.698,26 con el D.S. 5646.")
    m.h2("Módulo B · Guía de procedimiento y control del expediente")
    m.bullets(["Los **11 pasos** del manual (P-01 a P-11) con fase, responsables, procedimiento, documentos, plazo, normativa y consejo práctico.",
               "Los **12 controles** del expediente (C-01 a C-12) con emisor, obligatoriedad y criterio.",
               "Avance por operación, nota por paso (queda en la bitácora) y columna **«Sugerido por datos»**: marca los pasos que la información ya cargada respalda (NIT, SWIFT, documentos, DIM, canal, levante, gastos)."], num=False)
    m.figura(C + "51-guia-procedimiento.png", "Pestaña Guía: procedimiento, control del expediente y detalle del paso elegido.")
    m.h2("Módulo C · Habilitación del importador")
    m.p("El perfil indica si el importador es **Habitual** u **Ocasional**. La validación de la DIM verifica, para el ocasional, el tope de **USD 2.000 FOB por despacho** y el acumulado anual de **USD 4.000** (calculado con sus propias operaciones del año) y bloquea con un ERROR indicando que debe registrarse como habitual en el Padrón de Operadores.")
    m.h2("Módulo D · Conveniencia financiera por escenarios")
    m.bullets(["La pestaña Decisión compara ahora **origen y beneficio** además del Incoterm: columnas **Desgravación %** (preferencia con Certificado de Origen, p. ej. proveedor de Brasil o Argentina) y **DS 5516**; muestra el **GA** de cada escenario.",
               "Los escenarios usan la fecha de la DIM, los ajustes del Art. 8 y la carga y descarga de la operación.",
               "El costeo agrega **precio de venta sugerido** (con margen sobre el precio y con IVA de venta 13 %), configurables en Configuración."], num=False)
    m.figura(C + "54-decision-origen-preferencias.png", "Comparación de proveedores: arancel 2026, preferencia del 100 % y beneficio D.S. 5516.")
    m.h2("Módulo E · Hoja de transcripción para el SUMA")
    m.p("El botón **Hoja SUMA** genera un Excel con las hojas **DAV** (importador, transacción, cuestionario, ajustes y valor en aduana), **DIM-General** (declaración, transporte y liquidación) y **DIM-Ítems** (partida, descripción comercial, marca, modelo, serie, cantidades, valores, alícuota aplicada, base del GA y tributos por ítem). Es un borrador de transcripción: la numeración de casillas oficiales depende del instructivo vigente. El JSON de exportación también incluye valoración y despacho.")
    m.figura(C + "50-caso-hornos.png", "Caso del manual (hornos a gas) calculado por COMEX JB.")

    m.h1("6. Plan de módulos: próximas versiones")
    m.tabla([["Módulo", "Alcance", "Prioridad", "Dependencias"],
        ["F · DAM y plazos", "Registro de la DAM, alertas por plazo configurable (el del manual es 20 días: confirmar), alertas de pago a 3 días hábiles de la DIM.", "Alta", "Verificar plazos oficiales"],
        ["G · Parte de Recepción", "Registro del PR, comparación con el MIC/DTA, discrepancias de peso y bultos con observaciones.", "Media", "Módulo F"],
        ["H · Pago y refrendo", "Recibo de pago, banco y fecha; vínculo con la bancarización.", "Media", "—"],
        ["I · Archivo y conciliación", "Paquete probatorio inmutable (PDF/A con metadatos), conciliación valor DIM frente a giros al exterior (SWIFT), alertas del plazo de fiscalización.", "Alta", "—"],
        ["J · Catálogo de beneficios", "Importar los Anexos del D.S. 5516 (y del D.S. 5709 si aplica) por subpartida con su vigencia; asignación automática del beneficio.", "Alta", "Texto oficial de los Anexos"],
        ["K · Rentabilidad", "Flujo de caja por etapas, punto de equilibrio, retorno y sensibilidad al tipo de cambio flotante.", "Media", "—"],
        ["L · Gestor de autorizaciones previas", "Matriz SENASAG, AGEMED, IBNORCA y borradores de solicitud.", "Media", "—"],
        ["M · Capacitación", "Roles por fase y evaluación del checklist para el personal.", "Baja", "Módulo B"]], [3.2, 8.4, 2.1, 3.3])

    m.h1("7. Cómo responde COMEX JB a los cuatro objetivos")
    m.tabla([["Objetivo", "Cómo se cubre en 1.3.0", "Pendiente"],
        ["Dar todos los pasos de la importación", "Guía P-01…P-11 con avance y sugerencias, ruta crítica de 12 etapas con semáforos, validación de la DIM, canales y descargos.", "DAM, Parte de Recepción y pago como módulos propios."],
        ["Responder sobre la conveniencia financiera", "Escenarios por Incoterm, origen, preferencia y beneficio; impacto de decretos; costo nacionalizado, factor, flujo de caja y precio sugerido.", "Rentabilidad avanzada (módulo K)."],
        ["Ser fuente de información para el SUMA", "Hoja SUMA (DAV, DIM general y DIM por ítem) y JSON, con las cifras que respaldan la DIM.", "Mapeo a casillas oficiales (requiere el instructivo vigente)."],
        ["Documentar el proceso", "Bitácora con usuario, legajo, guía con notas, expediente y exportaciones.", "Archivo probatorio PDF/A y conciliación bancaria (módulo I)."]], [4, 8, 5])

    m.h1("8. Riesgos, supuestos y límites")
    m.bullets(["**Base del Arancel:** se asume que el Arancel 2026 cargado es la tabla anterior a los decretos de 2026; la rebaja de 5 puntos se aplica sobre esa alícuota. Si carga un arancel ya modificado, no active la fecha de la DIM posterior al 06/07/2026 sin revisarlo.",
               "**Anexos del D.S. 5516:** COMEX JB no los trae; el usuario marca el beneficio por ítem. Marcar sin respaldo puede subestimar tributos.",
               "**Fuentes secundarias:** varias afirmaciones se apoyan en estudios jurídicos y portales; el texto oficial prevalece.",
               "**Vigencias:** el D.S. 5516 vence el 31/12/2026 y el D.S. 5646 el 31/12/2027; el sistema no conoce decretos posteriores: actualice la tabla de medidas cuando se publiquen.",
               "**Prueba en Windows real:** las pruebas visuales se hicieron en Wine; los cálculos están cubiertos por pruebas automáticas.",
               "COMEX JB es una herramienta de apoyo: **la liquidación oficial la determina la Aduana Nacional**."], num=False)

    m.h1("9. Fuentes consultadas")
    m.bullets(["Texto de consulta del D.S. 5646 (Gaceta Oficial de Bolivia): estaticos.unitel.bo/binrepository/decreto-supremo-5646-de-reduccion-de-impues_101-15983392_20260630180144.pdf",
               "Reproducción del D.S. 5646: pixilegal.com/normativa/decreto-5646-2026-06-29",
               "Ferrere, «Beneficios arancelarios vigentes para 2026»: ferrere.com/es/novedades/beneficios-arancelarios-vigentes-para-2026/",
               "Ferrere, «Arancel e IVA cero para impulsar la producción y la industria» (D.S. 5709): ferrere.com/en/news/arancel-e-iva-cero-para-impulsar-la-produccion-y-la-industria/",
               "Boliviaimpuestos, «Arancel cero 2026» (D.S. 5516): boliviaimpuestos.com/b/8n9",
               "Ferrere, «Modificación de los requisitos para el registro y aceptación de la DAM»: ferrere.com/en/news/bolivia-modificacion-de-los-requisitos-para-el-registro-y-aceptacion-de-la-declaracion-de-adquisicion-de-mercancias-dam/",
               "D.S. 2295 de 2015 (canales de control): lexivox.org/norms/BO-DS-N2295.html",
               "Ley 1990 y D.S. 25870 (Reglamento a la Ley General de Aduanas): lexivox.org/norms/BO-RE-DS25870.html",
               "Aduana Nacional: la DAV en el SUMA (eju.tv/?p=4930048); importador no habitual (boliviaimpuestos.com/b/zM)."], num=False)
    ruta = AQUI + "/Plan-de-Complementacion"; m.guardar(ruta + ".docx"); return ruta

if __name__ == "__main__":
    r = plan(); print("DOCX:", r + ".docx")
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", AQUI, r + ".docx"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("PDF :", r + ".pdf")
