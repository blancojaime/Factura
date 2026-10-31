"""Genera los manuales (PDF + DOCX) con valores calculados por el propio sistema. Uso: python docs/build_docs.py"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
os.environ["SIIM_HOME"] = tempfile.mkdtemp()

import mdrender
from siim.calc.deuda import DeudaParams, calcular_deuda
from siim.core import demo, security, seed
from siim.core.db import Database
from siim.core.paths import db_path
from siim.reports import catalogo
from siim.reports.engine import fmt_num as f2
from siim.services import liquidacion as L, otros, padron
from siim.services import recaudacion as R
from siim.services.base import Ctx
from siim.ui.mantenimiento import GRUPOS, TABLAS
from decimal import Decimal as X
from datetime import date

OUT = HERE / "salida"
OUT.mkdir(exist_ok=True)
IMG = HERE / "img"


def f0(x):
    return f"{float(x):,.0f}".replace(",", ".")


def permisos_md():
    perms = {"padron.ver": "Ver padrón", "padron.editar": "Altas/modif. F-019/F-027", "padron.baja": "Bajas F-035", "liq.ejecutar": "Liquidar", "liq.masiva": "Liquidación masiva", "rec.cobrar": "Cobrar", "rec.anular": "Anular pagos / fecha distinta",
             "otros.fuc": "FUC", "otros.anular": "Anular FUC", "mant.ver": "Ver mantenimiento", "mant.editar": "Editar tablas", "reportes": "Reportes", "fiscal": "Inspecciones", "plan.crear": "Planes de pago", "util.backup": "Respaldos"}
    rows = ["| Permiso | " + " | ".join(security.ROLES) + " |", "|---|" + "---|" * len(security.ROLES)]
    for k, v in perms.items():
        rows.append(f"| {v} | " + " | ".join("✔" if ("*" in security.ROLES[r] or k in security.ROLES[r]) else "—" for r in security.ROLES) + " |")
    return "\n".join(rows) + "\n\nSólo el ADMINISTRADOR gestiona usuarios, restaura respaldos y carga datos de demostración."


def reportes_md():
    rows = ["| Grupo | Reporte | Parámetros |", "|---|---|---|"]
    for r in catalogo.CATALOGO.values():
        rows.append(f"| {r['grupo']} | {r['titulo']} | " + (", ".join(p["label"] for p in r["params"]) or "—") + " |")
    return "\n".join(rows) + f"\n\nTotal: **{len(catalogo.CATALOGO)} reportes** (todos con salida PDF y Excel)."


def tablas_md():
    rows = ["| Grupo | Tabla |", "|---|---|"]
    for g, ks in GRUPOS:
        for k in ks:
            rows.append(f"| {g} | {TABLAS[k]['titulo']} |")
    return "\n".join(rows)


def manual_implementacion():
    md = (HERE / "manual_implementacion.md").read_text(encoding="utf-8")
    md = md.replace("{{PERMISOS}}", permisos_md()).replace("{{REPORTES}}", reportes_md()).replace("{{TABLAS}}", tablas_md())
    # capturas ilustrativas
    md = md.replace("## 6.2 Datos globales", "![Parámetros globales](img/mant_parametros.png){w=165}\n\n## 6.2 Datos globales")
    md = md.replace("# 7. Operación", "![Empadronamiento: padrón de contribuyentes](img/padron.png){w=165}\n\n# 7. Operación")
    md = md.replace("# 8. Seguridad y respaldos", "![Reporte de proyección de patentes](img/reportes.png){w=165}\n\n# 8. Seguridad y respaldos")
    md = md.replace("# 9. Solución de problemas", "![Utilitarios: copias de seguridad](img/backups.png){w=165}\n\n# 9. Solución de problemas")
    md = md.replace("# 5. Activación y licenciamiento (método externo)", "![Pantalla de activación](img/activacion.png){w=140}\n\n# 5. Activación y licenciamiento (método externo)")
    return md


# ------------------------------------------------------------------------------------------------------------------------
def pruebas():
    db = Database(db_path())
    seed.seed_base(db)
    demo.cargar_cotizaciones_demo(db)
    security.create_user(db, "admin", "Administrador", "ADMINISTRADOR", "Clave2026x")
    ctx = Ctx(db, security.login(db, "admin", "Clave2026x"))
    I = demo.cargar_padron_demo(ctx)
    pre = lambda r, k, g=2004, **kw: L.preliquidar(ctx, r, I[k], g, **kw)
    perez, lopez, cab, rural, fid, bene = (pre("IPBI", k) for k in ("inm_perez", "inm_lopez", "inm_cab", "inm_rural", "inm_fideos", "inm_bene"))
    vp, vl, vf, vm = (pre("IPVA", k) for k in ("veh_perez", "veh_lopez", "veh_fideos", "veh_moto"))
    pf = {k: pre("PAF", k) for k in ("act_farm", "act_tienda", "act_ferr", "act_fideos", "act_hotel")}
    pub = pre("PUB", "pub")
    sim = {}
    for m in ("TOPE_ZONA_SUP", "PUA", "CATEGORIA"):
        db.set_param("patente_modalidad", m)
        sim[m] = pre("PAF", "act_farm")["neto"]
    db.set_param("patente_modalidad", "TOPE_ZONA_SUP")
    d = lambda k: perez["detalle"] if k == "p" else None
    # pagos
    lid_p = L.guardar_liquidacion(ctx, perez)
    liq = db.one("SELECT * FROM liquidaciones WHERE id=?", (lid_p,))
    dp1 = L.deuda_a_fecha(db, liq, "2005-03-31")
    dp2 = L.deuda_a_fecha(db, liq, "2005-04-25")
    dp3 = L.deuda_a_fecha(db, liq, "2005-06-30")
    lid_l = L.liquidar(ctx, "IPBI", I["inm_lopez"], 2004)
    ll = db.one("SELECT * FROM liquidaciones WHERE id=?", (lid_l,))
    dl_mora = L.deuda_a_fecha(db, ll, "2005-06-30")
    # cuotas
    lid_c = L.liquidar(ctx, "PAF", I["act_ferr"], 2004, "CUOTAS")
    lc = db.one("SELECT * FROM liquidaciones WHERE id=?", (lid_c,))
    qs = db.all("SELECT * FROM liq_cuotas WHERE liq_id=? ORDER BY nro", (lid_c,))
    c1 = L.deuda_a_fecha(db, lc, "2005-03-31", qs[0]["id"])
    c2 = L.deuda_a_fecha(db, lc, "2005-07-31", qs[1]["id"])
    db.update("actividades", {"superficie": 200}, "id=?", (I["act_ferr"],))
    R.cobrar(ctx, lid_c, "2005-03-31", cuota_id=qs[0]["id"])
    rect = L.preliquidar(ctx, "PAF", I["act_ferr"], 2004, "CONTADO", "RECTIFICATORIA")
    # IMT
    lid_i, _ = L.liquidar_imt(ctx, "INM", I["perez"], I["lopez"], I["inm_perez"], "2005-02-10", 400000, 49000)
    imt = db.one("SELECT * FROM liquidaciones WHERE id=?", (lid_i,))
    # plan
    lid_f = L.liquidar(ctx, "IPBI", I["inm_fideos"], 2004)
    plan_id = R.crear_plan(ctx, I["fideos"], [lid_f], 6, fecha="2005-06-30")
    plan = db.one("SELECT * FROM planes_pago WHERE id=?", (plan_id,))
    cuotas = db.all("SELECT * FROM plan_cuotas WHERE plan_id=? ORDER BY nro", (plan_id,))
    # FUC
    fid_ = otros.crear_fuc(ctx, "Juan Quispe", [{"subnivel": "151003.002", "cantidad": 10}, {"subnivel": "153401.002", "cantidad": 3}, {"subnivel": "151003.001", "cantidad": 1}])
    fuc = db.one("SELECT * FROM fuc WHERE id=?", (fid_,))
    # deuda del documento
    P = lambda persona, modo="SIIM_PDF": DeudaParams(r=X("0.1082"), persona=persona, modo_df_ufv=modo)
    e1n = calcular_deuda(1000, date(2002, 1, 15), date(2005, 4, 21), None, X("1.10293"), P("N"), usd_fv=X("6.86"), usd_26=X("7.49"), ufv_26=X("1.00815"))
    e1j = calcular_deuda(1000, date(2002, 1, 15), date(2005, 4, 21), None, X("1.10293"), P("J"), usd_fv=X("6.86"), usd_26=X("7.49"), ufv_26=X("1.00815"))
    e2n = calcular_deuda(1000, date(2004, 12, 31), date(2005, 4, 21), X("1.08593"), X("1.10293"), P("N"))
    e2j = calcular_deuda(1000, date(2004, 12, 31), date(2005, 4, 21), X("1.08593"), X("1.10293"), P("J"))
    e2d = calcular_deuda(1000, date(2004, 12, 31), date(2005, 4, 21), X("1.08593"), X("1.10293"), P("N", "DIVISION"))
    pd = perez["detalle"]
    n_tests = 0
    ok = "☐"
    md = f"""# 1. Cómo usar este manual

Este manual contiene **ejercicios completos con datos de ejemplo y resultados esperados**, para capacitar al personal y para realizar la **prueba de aceptación** del sistema. Todos los importes de este documento fueron **calculados por el propio SIIM 2026** al generar el manual, con las tablas de ejemplo de la gestión 2004 de la Guía de Implementación del SIIM, por lo que deben coincidir exactamente con lo que usted verá en pantalla.

> **Aviso.** Las tablas de la gestión 2004 y los contribuyentes de demostración son **ficticios y sólo para capacitación**. No los utilice para cobrar. Realice estos ejercicios en un equipo o instalación de práctica, nunca en la base de producción.

## 1.1 Preparar el ambiente de práctica

1. Instale SIIM 2026 en un equipo de capacitación (o use una instalación nueva).
2. En el primer arranque cree el administrador (por ejemplo usuario `admin`, clave `Clave2026x`).
3. Entre a **Utilitarios ▸ Base de datos ▸ Cargar datos de demostración**. Se cargan 6 contribuyentes, 6 inmuebles, 4 vehículos, 5 actividades, 1 anuncio, las cotizaciones del año 2005 y las tablas de la gestión 2004.
4. Como las cotizaciones de demostración son del año 2005, en los ejercicios **cambie la fecha de pago** a la indicada (el campo *Fecha de pago* de Recaudación). El administrador puede registrar pagos con fecha distinta a hoy.

![Pantalla de ingreso](img/login.png){{w=120}}

## 1.2 Contribuyentes de demostración

| PMC | Contribuyente | Bienes y actividades |
|---|---|---|
| {I['perez']} | Pérez Vedia Fernando (natural) | Casa zona A (250 m² terreno, 180 m² construidos, 1995), vagoneta Toyota 2001, ferretería, hotel (cesó 30/06/2004) |
| {I['lopez']} | López Gómez Roberto (natural) | Casa zona B (300 m², 120 m², 2001), automóvil Suzuki 1998 de dos puertas, tienda de barrio (inicio 01/07/2004) |
| {I['caballero']} | Caballero Gutiérrez Fausto (natural) | Terreno zona C (500 m², inclinado), inmueble rural (Bs 150.000) |
| {I['fideos']} | Fábrica de Fideos CONSUELO S.R.L. (jurídica) | Casa/fábrica zona B (800 m², 600 m²), camión Volvo, actividad industrial |
| {I['farmacia']} | Mamani Quispe Rosa (natural) | Farmacia La Salud (45 m², zona 1), motocicleta Honda 250 cc, letrero luminoso |
| {I['bene']} | Vargas Ríos Anselmo (benemérito) | Casa zona D (200 m², 80 m², 1970) |

## 1.3 Formato de cada ejercicio

Cada ejercicio indica **Objetivo, Datos, Pasos, Resultado esperado** y una casilla de verificación ☐ para marcar cuando el resultado en pantalla coincida. Un ejercicio se considera aprobado cuando todos los importes coinciden al centavo.

---pagina---

# 2. Ejercicios de empadronamiento

## Ejercicio 1 – Alta de un contribuyente (F-019)

**Objetivo:** registrar una persona natural y comprobar que el sistema controla los datos mínimos.

**Datos:** Apellido paterno *Rojas*, materno *Apaza*, nombre *Luis*, CI *7654321* expedido LP, zona A, calle Sucre N.º 10. Formulario F-019 N.º de orden *0001*.

1. *Empadronamiento (PMC)* ▸ **Nuevo contribuyente (F-019)**; escriba la fecha y el N.º de orden y presione Aceptar.
2. Llene primero **sin dirección** (deje *Calle* vacía) y presione **Guardar datos (F10)**. Resultado: el registro queda **INCOMPLETO** y las pestañas de inmuebles/vehículos/actividades permanecen deshabilitadas; el sistema indica «Falta: dirección (calle)».
3. Complete la calle y guarde otra vez.

**Resultado esperado:** estado **ACTIVO**; el PMC asignado es **{I['bene'] + 1}** (correlativo desde 10 000 001); se habilitan las pestañas de bienes. En *Reportes ▸ Control de empadronamiento* aparece el formulario F-019.

☐ Aprobado

![Datos del contribuyente (F-027)](img/contribuyente.png){{w=150}}

## Ejercicio 2 – Registro de un inmueble y de una actividad

**Datos del inmueble:** casa, zona B, material de vía *LOSETA*, terreno 150 m², luz sí, agua sí, alcantarillado no, teléfono no, calidad *ECONOMICA*, 60 m² construidos, año 2010.
**Datos de la actividad:** tipo *14 Comercio en general*, categoría *03 Ferreterías*, nombre *Ferretería Rojas*, inicio 15/01/2020, 30 m², zona 2.

**Resultado esperado:** en el diálogo de inmueble los campos de construcción se habilitan sólo para *CASA/DEPARTAMENTO*; para *TERRENO* se deshabilitan; para *RURAL* sólo se pide el valor declarado. En la actividad, la categoría depende del tipo elegido.

☐ Aprobado

![Diálogo de inmueble](img/dlg_inmueble.png){{w=150}}

## Ejercicio 3 – Búsqueda multiacceso (F6)

Busque *LOPE* en **Apellido/nombre**; debe aparecer *López Gómez Roberto*. Busque la placa *1234-ABC*; debe aparecer *Pérez Vedia Fernando*. Busque el documento *1023456029*; debe aparecer la Fábrica de Fideos.

☐ Aprobado

## Ejercicio 4 – Baja de una actividad (F-035)

En la actividad *Hotel Plaza* de Pérez, use **Dar de baja bienes (F-035)**; indique fecha 30/06/2004 y motivo «cierre». El registro pasa a **INACTIVO**, no se borra, y en la bitácora aparece `F035_BAJA`.

☐ Aprobado

---pagina---

# 3. Ejercicios de liquidación

## Ejercicio 5 – IPBI: casa de Pérez (gestión 2004)

**Objetivo:** verificar el cálculo del Impuesto a la Propiedad de Bienes Inmuebles.

**Pasos:** *Liquidación ▸ Liquidación individual*; Rubro **IPBI**, Gestión **2004**, Original, Al contado; PMC **{I['perez']}**; seleccione la casa; **Calcular**.

| Concepto | Valor esperado |
|---|---|
| Valor por m² (zona A, ASFALTO) | {f2(pd['valor_m2'])} |
| Factor de inclinación (plano) / de servicios (4 servicios) | {f2(pd['f_inclinacion'])} / {f2(pd['f_servicios'])} |
| Valor del terreno = 250 × 75 × 1,00 × 1,00 | {f2(pd['valor_terreno'])} |
| Valor construcción por m² (BUENA) | {f2(pd['valor_const_m2'])} |
| Factor de depreciación (9 años de antigüedad: tramo 6‑10) | {pd['f_depreciacion']:.3f} |
| Valor de la construcción = 180 × 680 × 0,975 | {f2(pd['valor_construccion'])} |
| **Base imponible** | **{f2(perez['base_imponible'])}** |
| Escala: tramo 1, 0,35 % sobre (base − 1) | **Impuesto {f2(perez['neto'])}** |

☐ Aprobado

![Liquidación individual de IPBI](img/liq_ipbi.png){{w=160}}

## Ejercicio 6 – IPBI: otros casos de la gestión 2004

| Caso | Base imponible | Impuesto | Qué demuestra |
|---|---|---|---|
| López (casa, zona B, LOSETA, con luz y agua; sin alcantarillado ni teléfono) | {f2(lopez['base_imponible'])} | {f2(lopez['neto'])} | factor de servicios 0,20 + 0,20 + 0,20 = 0,60 |
| Caballero (terreno inclinado, zona C, RIPIO, sólo luz) | {f2(cab['base_imponible'])} | {f2(cab['neto'])} | factor de inclinación 0,90 y servicios 0,40 |
| Inmueble rural de Caballero (Bs 150.000) | {f2(rural['base_imponible'])} | {f2(rural['neto'])} | alícuota rural 0,20 % |
| Fábrica de Fideos (casa MUY BUENA, 800 m²) | {f2(fid['base_imponible'])} | {f2(fid['neto'])} | **segundo tramo** de la escala: 1.193 + 0,50 % sobre (base − 340.972) |
| Vargas (benemérito, casa económica) | {f2(bene['base_imponible'])} | {f2(bene['neto'])} | exención del benemérito hasta el tope del primer tramo |

☐ Aprobado

## Ejercicio 7 – IPVA

| Vehículo | Base imponible | Impuesto | Cómo se obtiene |
|---|---|---|---|
| Toyota Land Cruiser (vagoneta japonesa, 4.200 cc, doble tracción, año 2001) | {f2(vp['base_imponible'])} | {f2(vp['neto'])} | valor de tabla código 57 JAPÓN = 182.382; +15 % doble tracción; depreciación 3.er año = 0,41; escala tramo 2 (829 + 2 % sobre el excedente de 41.475) |
| Suzuki Swift (1.300 cc, dos puertas, 1998) | {f2(vl['base_imponible'])} | {f2(vl['neto'])} | –15 % por dos puertas; depreciación 6.º año |
| Camión Volvo (4.800 cc, 8 t, chasis cabinado, carrocería estacas, 1999) | {f2(vf['base_imponible'])} | {f2(vf['neto'])} | incremento 0,40 + 0,12 por chasis y carrocería (tramo 5–11 t) |
| Moto Honda 250 cc (2003) | {f2(vm['base_imponible'])} | {f2(vm['neto'])} | tabla de motocicletas, código 52 |

☐ Aprobado

![Liquidación individual de IPVA](img/liq_ipva.png){{w=150}}

---pagina---

# 4. Actividades económicas, tasas y patentes

## Ejercicio 8 – Patente de funcionamiento con tres modalidades

**Datos:** Farmacia La Salud, actividad 14‑05, zona 1, 45 m², inicio 15/03/2001.

| Modalidad (Mantenimiento ▸ Parámetros) | Fórmula | Patente 2004 |
|---|---|---|
| Patente máxima × % zona‑superficie | 4.500 × 70 % (zona 1, rango 31‑50 m² = 70 %) | **{f2(sim['TOPE_ZONA_SUP'])}** |
| Patente Única Anual | 45 m² × Bs 12 (zona 1) | **{f2(sim['PUA'])}** |
| Monto fijo por categoría | tabla de categorías | **{f2(sim['CATEGORIA'])}** |

Compruébelo en **Actividades económicas ▸ Simulador de patente**: ingrese los datos y presione *Simular*; el sistema muestra las tres modalidades a la vez.

☐ Aprobado

![Simulador de patente](img/act_simulador.png){{w=160}}

## Ejercicio 9 – Duodécimas (inicio y cese en la gestión)

- **Tienda Doña Rosa** (12‑01, zona 3, 12 m², inicio 01/07/2004): funcionó **6 de 12 meses**; patente = 600 × 30 % × 6/12 = **{f2(pf['act_tienda']['neto'])}**.
- **Hotel Plaza** (08‑01, zona 1, 400 m², cesó el 30/06/2004): 20.000 × 100 % × 6/12 = **{f2(pf['act_hotel']['neto'])}**.
- **Ferretería El Tornillo** (14‑03, zona 2, 90 m²): 4.000 × 80 % = **{f2(pf['act_ferr']['neto'])}**.
- **Fábrica de fideos** (01‑06, zona 2, 600 m²): 2.500 × 90 % = **{f2(pf['act_fideos']['neto'])}**.

☐ Aprobado

## Ejercicio 10 – Publicidad y propaganda

Letrero luminoso de dos caras de 2,00 m × 1,50 m = 3 m² a Bs 50/m² anual → **{f2(pub['neto'])}**. Pruebe cambiar el tipo a *SIMPLE_2C* (30 Bs/m²) y *MURAL* (10 Bs/m²).

☐ Aprobado

## Ejercicio 11 – Licencia de funcionamiento con QR

1. En **Actividades económicas ▸ Establecimientos y licencias**, seleccione *Farmacia La Salud* y **Emitir / renovar licencia**.
2. Se asigna un número `LF‑AAAA‑000001`, con vigencia de 12 meses. **Imprimir licencia (QR)** genera el PDF con código de verificación.
3. En la pestaña **Verificar licencia** escriba el número y el código impreso: debe responder *AUTÉNTICA*. Cambie un carácter del código: debe responder *NO VÁLIDA*.
4. Liquide la patente 2004 de la farmacia y **no la pague**; con fecha de hoy intente renovar la licencia: el sistema la **bloquea** por patente vencida impaga (el supervisor puede autorizarla).

☐ Aprobado

![Establecimientos y licencias](img/act_licencias.png){{w=160}}

---pagina---

# 5. Recaudación y deuda tributaria

## Ejercicio 12 – Pago al contado con descuento y pago fuera de plazo

**Datos:** IPBI 2004 de Pérez (impuesto **{f2(liq['neto'])}**). Vencimientos de ejemplo cargados: contado hasta 31/03/2005; sin descuento ni accesorios hasta 30/04/2005.

| Fecha de pago | Concepto | Total a pagar |
|---|---|---|
| 31/03/2005 | Contado con 10 % de descuento ({f2(dp1['descuento'])}) | **{f2(dp1['total'])}** |
| 25/04/2005 | Sin descuento y sin accesorios (plazo de gracia) | **{f2(dp2['total'])}** |
| 30/06/2005 | En mora: {dp3['mora']} días; mantenimiento de valor {f2(dp3['mant_valor'])}; intereses {f2(dp3['interes'])}; multa por deberes formales {f2(dp3['multa_df'])} | **{f2(dp3['total'])}** |

**Pasos:** *Liquidación* ▸ emitir la liquidación (se imprime el formulario F‑1980 con QR y código de pago). *Recaudación ▸ Registrar pago*: busque por PMC, elija la liquidación, cambie la *fecha de pago* y observe cómo se recalcula el total. Presione **Registrar pago** y confirme; se imprime el **recibo oficial**.

☐ Aprobado

![Pago al contado](img/cobro_descuento.png){{w=150}}

## Ejercicio 13 – Pago en mora (López, IPBI 2004)

Impuesto **{f2(ll['neto'])}**; pago el 30/06/2005 ({dl_mora['mora']} días de mora, UFV {dl_mora['ufv_fv']} → {dl_mora['ufv_fp']}, r = {dl_mora['r']*100:.2f} %): mantenimiento de valor **{f2(dl_mora['mant_valor'])}**, intereses **{f2(dl_mora['interes'])}**, multa por deberes formales **{f2(dl_mora['multa_df'])}** (mínimo legal de 50 UFV para persona natural × UFV de pago), **total {f2(dl_mora['total'])}**.

☐ Aprobado

![Pago en mora](img/cobro_mora.png){{w=150}}

## Ejercicio 14 – Pago en dos cuotas y rectificatoria

1. Liquide la patente 2004 de la Ferretería El Tornillo (**{f2(pf['act_ferr']['neto'])}**) *En dos cuotas*: se generan 2 cuotas de **{f2(c1['neto'])}** (vencen 31/03/2005 y 30/06/2005).
2. Pague la 1.ª cuota el 31/03/2005: total **{f2(c1['total'])}** (en cuotas no hay descuento). La liquidación pasa a **PARCIAL**.
3. La 2.ª cuota pagada el 31/07/2005 (mora) tiene un total de **{f2(c2['total'])}**.
4. El inspector comprueba que el local mide 200 m² (en vez de 90): corrija la superficie en F‑027 y emita una **Rectificatoria**: la patente sube a 4.000 × 90 % = **{f2(rect['impuesto'])}**, se descuentan los pagos anteriores (**{f2(rect['credito'])}**) y queda un neto de **{f2(rect['neto'])}**.

☐ Aprobado

## Ejercicio 15 – Anulación de un pago

Con rol supervisor/administrador: *Recaudación ▸ Pagos del día* ▸ seleccione un pago ▸ **Anular** con motivo. El pago queda *ANULADO*, la liquidación vuelve a *PENDIENTE* y aparece en el reporte *Pagos anulados*. Un cajero **no** puede anular.

☐ Aprobado

## Ejercicio 16 – Impuesto Municipal a las Transferencias (IMT)

**Datos:** Pérez (vendedor) vende su casa a López (comprador) el 10/02/2005 por Bs 400.000 (US$ 49.000).

1. *Liquidación ▸ Transferencias (IMT)*: elija vendedor y comprador, seleccione la casa, ingrese fecha y montos; **Determinar impuesto**.
2. Base imponible: el mayor entre Bs 400.000 y la base IPBI 2004 ({f2(pd['base_imponible'])}) → **400.000**; impuesto 3 % = **{f2(imt['impuesto'])}**; plazo de pago: 10 días hábiles → **{imt['fecha_venc'][8:]}/{imt['fecha_venc'][5:7]}/{imt['fecha_venc'][:4]}**.
3. Pague el IMT. **Sólo entonces** la casa pasa a nombre de López en el padrón. Si anula el pago, la casa vuelve a Pérez.

☐ Aprobado

## Ejercicio 17 – Plan de pagos

Fábrica de Fideos debe el IPBI 2004 (**{f2(fid['neto'])}**) y paga fuera de plazo. Con fecha 30/06/2005 se crea un plan: deuda con accesorios sin descuento **{f2(plan['deuda_total'])}**, cuota inicial 10 % (**{f2(plan['cuota_inicial'])}**), 6 cuotas mensuales con interés anual de 10,82 %. Cuota mensual: **{f2(cuotas[1]['monto'])}**. El sistema impide un segundo plan para el mismo contribuyente.

☐ Aprobado

---pagina---

# 6. Otros ingresos: FUC

## Ejercicio 18 – Formulario Único de Caja

**Datos:** Juan Quispe paga 10 legalizaciones de fotocopias (Bs 2 c/u), 3 días de sentaje en feria (Bs 15 c/día) y 1 certificado de solvencia municipal (Bs 15).

*Otros ingresos ▸ FUC*: escriba el nombre, agregue los tres subniveles con su cantidad y presione **Guardar y recaudar**. **Total esperado: Bs {f2(fuc['total'])}** (20 + 45 + 15). Verifique en *Control de transacciones* que el estado sea RECAUDADO; pruebe *Anular* (con motivo) y *Borrar* (sólo borradores).

☐ Aprobado

![Formulario Único de Caja](img/fuc.png){{w=160}}

---pagina---

# 7. Cálculo de la Deuda Tributaria (Apuntes SIIM)

## Ejercicio 19 – Ejemplos del documento oficial

En **Deuda tributaria** ingrese los datos. Para reproducir el documento, seleccione *TO × UFV (como en los Apuntes SIIM)*.

**Ejemplo 1 (deuda anterior al 26/12/2002):** TO = Bs 1.000; vencimiento 15/01/2002; pago 21/04/2005; dólar 6,86 (vencimiento) y 7,49 (26/12/2002); UFV 1,00815 (26/12/2002) y 1,10293 (pago); r = 10,82 %.

| Componente | Persona natural | Persona jurídica |
|---|---|---|
| Mora | {e1n.mora} días | {e1j.mora} días |
| Mantenimiento de valor | {f0(e1n.mv)} | {f0(e1j.mv)} |
| TO + Mv | {f0(e1n.to_mv)} | {f0(e1j.to_mv)} |
| Intereses | {f0(e1n.interes)} | {f0(e1j.interes)} |
| Multa deberes formales (UFV → Bs) | {f0(e1n.multa_ufv)} → {f0(e1n.multa_bs)} | {f0(e1j.multa_ufv)} → {f0(e1j.multa_bs)} |
| **Deuda tributaria** | **{f0(e1n.total)}** | **{f0(e1j.total)}** |

> El documento oficial muestra 1.662 para la persona natural, pero la suma de sus propios componentes (1.194 + 515 + 121) es 1.830. SIIM 2026 calcula 1.830. La persona jurídica coincide (1.974).

**Ejemplo 2 (deuda posterior):** TO = Bs 1.000; vencimiento 31/12/2004; pago 21/04/2005; UFV 1,08593 → 1,10293; r = 10,82 %.

| Componente | Natural | Jurídica |
|---|---|---|
| Mora | {e2n.mora} días | {e2j.mora} días |
| Mantenimiento de valor | {f0(e2n.mv)} | {f0(e2j.mv)} |
| Intereses | {f0(e2n.interes)} | {f0(e2j.interes)} |
| Multa (Bs) | {f0(e2n.multa_bs)} | {f0(e2j.multa_bs)} |
| **Deuda tributaria** | **{f0(e2n.total)}** (el documento redondea 1.170) | **{f0(e2j.total)}** (1.315) |

Con la opción **TO ÷ UFV** (definición legal) la multa de la persona natural del Ejemplo 2 es {f0(e2d.multa_ufv)} UFV ({f0(e2d.multa_bs)} Bs) y el total {f0(e2d.total)}.

☐ Aprobado

![Calculadora de deuda tributaria](img/deuda.png){{w=160}}

---pagina---

# 8. Reportes, respaldos, licencia y seguridad

## Ejercicio 20 – Reportes en PDF y Excel

Genere desde *Reportes* y exporte a Excel: Listado de contribuyentes ({len(padron.buscar(db, '', 'nombre'))} registros), Listado de actividades económicas, Control de empadronamiento, Recaudación diaria (fecha 31/03/2005 y 30/06/2005), Cuenta corriente de Pérez, Reporte SINCOM (01/01/2005–31/12/2005), Proyección de patentes 2004, Contribuyentes en mora IPBI 2004. Verifique que el Excel tenga los totales con fórmula `SUM`.

☐ Aprobado

## Ejercicio 21 – Copia de seguridad y restauración

1. *Utilitarios ▸ Copias de seguridad ▸ Crear respaldo ahora*, etiqueta «prueba», contraseña *Resp2026*.
2. Seleccione el respaldo ▸ **Verificar**: debe informar «Respaldo íntegro (SHA‑256 verificado)».
3. Registre un contribuyente nuevo (será el dato «extra»).
4. **Restaurar seleccionado** (pide la contraseña, crea antes un respaldo `antes-de-restaurar`). El sistema se cierra; al reabrir, el contribuyente «extra» **ya no existe**.
5. Pruebe una contraseña incorrecta: «Contraseña incorrecta o archivo dañado».
6. Copie el respaldo a un USB (*Copiar a USB / red*).

☐ Aprobado

![Respaldos](img/backups.png){{w=150}}

## Ejercicio 22 – Activación de licencia (con la herramienta externa)

1. En **Utilitarios ▸ Licencia / activación** copie el *código de instalación* (formato `XXXX-XXXX-XXXX-XXXX`).
2. En el equipo del proveedor: `python tools/licencias.py emitir --codigo <código> --cliente "GAM Prueba" --dias 365`.
3. Cargue el archivo `.siimlic`: el sistema indica «Licenciado a GAM Prueba (vence …)».
4. Edite un carácter del archivo y cárguelo: «La licencia no es válida o fue alterada».
5. Intente usar la misma licencia en otra PC: «emitida para otro equipo».

☐ Aprobado

## Ejercicio 23 – Seguridad y roles

1. Cree un usuario `caja1` con rol CAJERO. Ingrese con él: no debe ver *Mantenimiento* ni *Utilitarios*, y no puede anular pagos ni registrar pagos con otra fecha.
2. Falle 5 veces la contraseña: la cuenta se bloquea 15 minutos.
3. Restablezca la clave desde el administrador: el usuario debe cambiarla al ingresar.
4. Deje el sistema inactivo hasta el tiempo configurado: solicita la contraseña nuevamente.
5. *Utilitarios ▸ Base de datos ▸ Verificar integridad*: «Cadena de bitácora: CORRECTA».

☐ Aprobado

---pagina---

# 9. Plan de capacitación sugerido (3 días)

| Día | Horario | Tema | Ejercicios |
|---|---|---|---|
| 1 | Mañana | Marco tributario municipal, PMC, uso del sistema, ingreso y seguridad | 1–4 |
| 1 | Tarde | Parámetros, cotizaciones, tablas de IPBI e IPVA | 5–7 |
| 2 | Mañana | Actividades económicas, patentes, licencias, publicidad | 8–11 |
| 2 | Tarde | Liquidación, recaudación, mora, cuotas, rectificatoria | 12–15 |
| 3 | Mañana | IMT, plan de pagos, FUC, deuda tributaria | 16–19 |
| 3 | Tarde | Reportes, respaldos, licencia, seguridad y evaluación final | 20–23 |

Perfiles: *Empadronadores* (ejercicios 1‑4, 8‑11), *Liquidadores* (5‑10, 12‑17), *Cajeros* (12‑15, 18, 20), *Supervisores* (todos), *Administrador del sistema* (21‑23 y capítulos de implementación).

# 10. Evaluación final (con respuestas)

| N.º | Pregunta | Respuesta |
|---|---|---|
| 1 | ¿Qué estado tiene un contribuyente sin dirección? | INCOMPLETO; no permite registrar bienes ni liquidar |
| 2 | ¿Cómo se obtiene el factor de servicios? | 0,20 base + 0,20 por cada servicio (luz, agua, alcantarillado, teléfono) |
| 3 | ¿Qué pasa si el pago se hace después del plazo de gracia? | Se calcula la Deuda Tributaria: mantenimiento de valor + intereses + multa por deberes formales |
| 4 | ¿Cuándo cambia de propietario un inmueble vendido? | Cuando se paga el IMT |
| 5 | ¿Cuántos planes de pago puede tener un contribuyente? | Uno solo vigente (facilidades una sola vez) |
| 6 | ¿Cuál es la fórmula de la patente con tope y zona‑superficie? | PF = PMA × PZS / 100 |
| 7 | ¿Por qué el sistema rechaza liquidar con la UFV desactualizada? | Para no cobrar accesorios erróneos; hay que cargar las cotizaciones |
| 8 | ¿Qué debe hacer antes de restaurar un respaldo? | Nada manual: el sistema crea un respaldo `antes-de-restaurar`; pero debe verificar que el archivo sea el correcto |
| 9 | ¿Qué prueba que la licencia está atada a la PC? | El código de instalación se incluye en la licencia firmada; en otra PC se rechaza |
| 10 | ¿Cómo se detecta que alguien alteró la bitácora? | La cadena de hashes se rompe: *Utilitarios ▸ Base de datos* lo informa |

# 11. Acta de aceptación (modelo)

| Criterio | Resultado | Observaciones |
|---|---|---|
| Ejercicios 1‑23 aprobados | ☐ Sí ☐ No | |
| Importes coinciden con este manual al centavo | ☐ Sí ☐ No | |
| Respaldo creado, verificado y restaurado en otro equipo | ☐ Sí ☐ No | |
| Licencia activada con la herramienta externa | ☐ Sí ☐ No | |
| Personal capacitado (nombres y firmas) | | |

Fecha: ______________   Responsable municipal: ______________________   Proveedor: ______________________
"""
    db.close()
    return md.replace("fid['base_imponible']", "").replace("{fid", "{fid") if False else md


def main():
    # corrección de variable en el cuerpo (fid se usa como 'fid' arriba para Fideos)
    md = manual_implementacion()
    mdrender.to_pdf(md, OUT / "1_Manual_de_Implementacion_SIIM2026.pdf", "Manual de Implementación", "Instalación, activación, puesta en marcha, seguridad y respaldos\nVersión 1.0 · Windows 10/11", HERE)
    mdrender.to_docx(md, OUT / "1_Manual_de_Implementacion_SIIM2026.docx", "Manual de Implementación", HERE)
    md2 = pruebas()
    mdrender.to_pdf(md2, OUT / "2_Manual_de_Pruebas_y_Capacitacion_SIIM2026.pdf", "Manual de Pruebas\ny Capacitación", "23 ejercicios completos con datos y resultados esperados\nPlan de capacitación, evaluación y acta de aceptación", HERE)
    mdrender.to_docx(md2, OUT / "2_Manual_de_Pruebas_y_Capacitacion_SIIM2026.docx", "Manual de Pruebas y Capacitación", HERE)
    print("listo:", [p.name for p in OUT.iterdir()])


if __name__ == "__main__":
    main()
