/* Gestión de Personal y Asistencia Municipal — SPA sin dependencias externas (funciona sin Internet).
   Todo el contenido dinámico se inserta con textContent (sin innerHTML) para evitar XSS. */
"use strict";

const MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
const MOD = { PERMANENTE: "Permanente", EVENTUAL: "Eventual", CONSULTOR_LINEA: "Consultor en Línea" };
const ESTADO = { NORMAL: "Asistencia normal", RETRASO_LEVE: "Retraso leve", RETRASO_GRAVE: "Retraso grave", FALTA_INJUSTIFICADA: "Falta injustificada",
  FALTA_JUSTIFICADA: "Falta justificada", OMISION_MARCACION: "Omisión de marcación", NO_LABORABLE: "No laborable", FERIADO: "Feriado" };
const CAUSALES = { RENUNCIA: "Renuncia", CONCLUSION_CONTRATO: "Conclusión de contrato", DESTITUCION: "Destitución", JUBILACION: "Jubilación",
  FALLECIMIENTO: "Fallecimiento", RESCISION: "Rescisión de contrato", OTRO: "Otro" };

const S = { token: sessionStorage.getItem("tok"), user: null, view: "inicio",
  anio: +(localStorage.getItem("anio") || 0), mes: +(localStorage.getItem("mes") || 0) };
if (!S.anio) { const d = new Date(); d.setMonth(d.getMonth() - 1); S.anio = d.getFullYear(); S.mes = d.getMonth() + 1; }

/* ---------- utilidades DOM ---------- */
function h(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === false || v == null) continue;
    if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (k === "class") e.className = v;
    else if (k === "value") e.value = v;
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat(Infinity)) if (c != null && c !== false) e.append(c.nodeType ? c : document.createTextNode(String(c)));
  return e;
}
const money = (x) => (x == null ? "" : Number(x).toLocaleString("es-BO", { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
const num = (x) => (x == null ? "" : String(+Number(x).toFixed(2)));
const fdate = (s) => (s ? s.slice(8, 10) + "/" + s.slice(5, 7) + "/" + s.slice(0, 4) : "");
function toast(msg, tipo) {
  const t = h("div", { class: tipo || "" }, msg);
  document.getElementById("toast").append(t);
  setTimeout(() => t.remove(), tipo === "err" ? 9000 : 4000);
}
function fmtErr(d) {
  if (!d) return "Error";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => (x.loc ? x.loc.slice(1).join(".") + ": " : "") + x.msg).join("; ");
  return JSON.stringify(d);
}
async function api(path, opt = {}) {
  const o = { method: opt.method || "GET", headers: {} };
  if (S.token) o.headers.Authorization = "Bearer " + S.token;
  if (opt.json !== undefined) { o.headers["Content-Type"] = "application/json"; o.body = JSON.stringify(opt.json); }
  if (opt.form) o.body = opt.form;
  const r = await fetch(path, o);
  if (r.status === 401 && S.token) { logout(); throw new Error("Sesión vencida"); }
  if (!r.ok) {
    let d; try { d = (await r.json()).detail; } catch { d = r.statusText; }
    throw new Error(fmtErr(d));
  }
  if (opt.blob) return r;
  return r.headers.get("content-type")?.includes("json") ? r.json() : r;
}
async function accion(fn, okMsg) {
  try { const r = await fn(); if (okMsg) toast(okMsg, "ok"); return r; } catch (e) { toast(e.message, "err"); }
}
async function descargar(path, nombre) {
  const r = await accion(() => api(path, { blob: true }));
  if (!r) return;
  const b = await r.blob();
  const cd = r.headers.get("content-disposition") || "";
  const fn = (cd.match(/filename="([^"]+)"/) || [])[1] || nombre;
  const a = h("a", { href: URL.createObjectURL(b), download: fn });
  document.body.append(a); a.click(); a.remove();
}
async function verPdf(path) {
  const r = await accion(() => api(path, { blob: true }));
  if (r) window.open(URL.createObjectURL(await r.blob()), "_blank");
}
function campo(label, name, o = {}) {
  let el;
  if (o.opts) el = h("select", { name }, o.opts.map(([v, t]) => h("option", { value: v }, t)));
  else if (o.area) el = h("textarea", { name });
  else el = h("input", { name, type: o.type || "text", step: o.step, min: o.min, max: o.max, maxlength: o.maxlength, required: o.req, placeholder: o.ph, autocomplete: "off" });
  if (o.value !== undefined && o.value !== null) { if (el.type === "checkbox") el.checked = !!o.value; else el.value = o.value; }
  return h("label", { style: o.style }, label, el);
}
function leer(form) {
  const d = {};
  for (const el of form.elements) {
    if (!el.name) continue;
    d[el.name] = el.type === "checkbox" ? el.checked : el.type === "number" && el.value !== "" ? +el.value : el.value;
  }
  return d;
}
function dialogo(titulo, contenido) {
  const dlg = h("dialog", {}, h("h3", { style: "margin-top:0" }, titulo), contenido);
  document.body.append(dlg);
  dlg.addEventListener("close", () => dlg.remove());
  dlg.showModal();
  return dlg;
}
function tabla(cols, filas, opts = {}) {
  return h("div", { class: "scroll" }, h("table", {},
    h("thead", {}, h("tr", {}, cols.map((c) => h("th", { class: c.n ? "n" : "" }, c.t)))),
    h("tbody", {}, filas.length ? filas.map((f) => h("tr", { class: opts.cls ? opts.cls(f) : "" }, cols.map((c) => h("td", { class: c.n ? "n" : "" }, c.f(f)))))
      : h("tr", {}, h("td", { colspan: cols.length, class: "muted" }, "Sin registros")))));
}
function selPeriodo(onchange) {
  const m = h("select", { onchange: () => { S.mes = +m.value; localStorage.setItem("mes", S.mes); onchange(); } },
    MESES.map((n, i) => h("option", { value: i + 1 }, n)));
  m.value = S.mes;
  const a = h("input", { type: "number", min: 2020, max: 2100, value: S.anio, style: "width:90px", onchange: () => { S.anio = +a.value; localStorage.setItem("anio", S.anio); onchange(); } });
  return h("div", { class: "row" }, h("label", {}, "Mes", m), h("label", {}, "Año", a));
}
const puede = () => S.user && (S.user.rol === "ADMIN" || S.user.rol === "RRHH");

/* ---------- autenticación ---------- */
function logout() { sessionStorage.removeItem("tok"); S.token = null; S.user = null; render(); }
async function pantallaLogin() {
  const est = await api("/api/auth/estado").catch(() => ({ inicializado: true }));
  const primera = !est.inicializado;
  const f = h("form", { class: "card login", onsubmit: async (ev) => {
    ev.preventDefault();
    const d = leer(f);
    const r = await accion(() => api(primera ? "/api/auth/setup" : "/api/auth/login", { method: "POST", json: d }));
    if (r) { S.token = r.token; S.user = r.usuario; sessionStorage.setItem("tok", r.token); render(); }
  } },
    h("h2", {}, "Gestión de Personal y Asistencia"),
    h("p", { class: "muted" }, primera ? "Primer ingreso: cree la cuenta de administrador (mínimo 8 caracteres)." : "Ingrese con su usuario."),
    campo("Usuario", "username", { req: true, style: "margin-bottom:8px" }),
    campo("Contraseña", "password", { type: "password", req: true, style: "margin-bottom:8px" }),
    primera ? campo("Nombre completo", "nombre", { style: "margin-bottom:8px" }) : null,
    h("button", { type: "submit" }, primera ? "Crear administrador" : "Ingresar"));
  document.getElementById("app").replaceChildren(f);
}

/* ---------- vistas ---------- */
const VISTAS = [["inicio", "Inicio / Planilla"], ["personal", "Personal"], ["marcas", "Marcaciones"], ["asistencia", "Asistencia diaria"],
  ["permisos", "Permisos y boletas"], ["instructivos", "Instructivos"], ["reportes", "Reportes"], ["config", "Configuración"],
  ["respaldos", "Respaldos", "ADMIN"], ["auditoria", "Auditoría"], ["usuarios", "Usuarios", "ADMIN"]];

async function render() {
  if (!S.token) return pantallaLogin();
  if (!S.user) { S.user = await api("/api/auth/yo").catch(() => null); if (!S.user) return logout(); }
  const main = h("main", {});
  const nav = h("nav", {}, h("h1", {}, "Gestión de Personal y Asistencia Municipal"),
    VISTAS.filter((v) => !v[2] || v[2] === S.user.rol).map(([k, t]) => h("a", { tabindex: 0, class: S.view === k ? "on" : "", onclick: () => { S.view = k; render(); },
      onkeydown: (e) => { if (e.key === "Enter") { S.view = k; render(); } } }, t)),
    h("div", { class: "u" }, S.user.username + " · " + S.user.rol, h("br"), h("a", { style: "padding:0;display:inline;text-decoration:underline", onclick: logout }, "Cerrar sesión")));
  document.getElementById("app").replaceChildren(h("div", { class: "layout" }, nav, main));
  try { main.append(await V[S.view]()); } catch (e) { main.append(h("div", { class: "card" }, "Error: " + e.message)); }
}
const refrescar = () => render();

const V = {};

V.inicio = async () => {
  const [periodos, liq] = await Promise.all([api("/api/periodos"), api(`/api/liquidacion/${S.anio}/${S.mes}`)]);
  const p = periodos.find((x) => x.anio === S.anio && x.mes === S.mes);
  const tot = (k) => liq.reduce((s, x) => s + x[k], 0);
  return h("div", {}, h("h2", {}, "Planilla y control del periodo"),
    h("div", { class: "card row" }, selPeriodo(refrescar),
      h("span", { class: "tag " + (p?.estado === "CERRADO" ? "mal" : p?.procesado_en ? "ok" : "av") }, p ? (p.estado === "CERRADO" ? "CERRADO" : p.procesado_en ? "Procesado" : "Sin procesar") : "Sin procesar"),
      puede() && p?.estado !== "CERRADO" ? h("button", { onclick: async () => { if (await accion(() => api(`/api/periodos/${S.anio}/${S.mes}/procesar`, { method: "POST" }), "Periodo procesado")) refrescar(); } }, "Procesar periodo") : null,
      puede() && p?.procesado_en && p.estado !== "CERRADO" ? h("button", { class: "sec", onclick: async () => { if (confirm("¿Cerrar el periodo? Se bloquearán importaciones, permisos y reproceso.") && await accion(() => api(`/api/periodos/${S.anio}/${S.mes}/cerrar`, { method: "POST" }), "Periodo cerrado")) refrescar(); } }, "Cerrar periodo") : null,
      S.user.rol === "ADMIN" && p?.estado === "CERRADO" ? h("button", { class: "mal", onclick: async () => { const m = prompt("Motivo de la reapertura (queda en la bitácora):"); if (m && await accion(() => api(`/api/periodos/${S.anio}/${S.mes}/reabrir`, { method: "POST", json: { motivo: m } }), "Periodo reabierto")) refrescar(); } }, "Reabrir") : null),
    h("div", { class: "kpis" }, [["Personal", liq.length], ["Faltas (días)", num(tot("faltas"))], ["Min. de retraso", tot("min_retraso")], ["Total ganado Bs", money(tot("total_ganado"))],
      ["Desc. asistencia Bs", money(tot("desc_asistencia"))], ["Líquido Bs", money(tot("liquido_pagable"))]].map(([t, v]) => h("div", { class: "kpi" }, t, h("b", {}, v)))),
    h("h3", {}, "Liquidación individual"),
    tabla([{ t: "Servidor", f: (x) => x.empleado }, { t: "C.I.", f: (x) => x.ci }, { t: "Modalidad", f: (x) => MOD[x.modalidad] },
      { t: "Días lab.", n: 1, f: (x) => num(x.dias_laborables) }, { t: "Faltas", n: 1, f: (x) => num(x.faltas) }, { t: "Min. retraso", n: 1, f: (x) => x.min_retraso },
      { t: "Justif.", n: 1, f: (x) => num(x.dias_justificados) }, { t: "Días desc.", n: 1, f: (x) => num(x.dias_descuento) },
      { t: "Total ganado", n: 1, f: (x) => money(x.total_ganado) }, { t: "Aporte lab.", n: 1, f: (x) => money(x.aporte_laboral) },
      { t: "Desc. asist.", n: 1, f: (x) => money(x.desc_asistencia) }, { t: "Líquido", n: 1, f: (x) => h("b", {}, money(x.liquido_pagable)) },
      { t: "Sanción / obs.", f: (x) => [x.sancion, x.observacion].filter(Boolean).join(" · ") }], liq),
    h("p", { class: "muted" }, "El descuento por día = haber ÷ 30. Falta injustificada = factor configurable (por defecto ×2 planta/eventual, ×1 consultor)."));
};

V.personal = async () => {
  let q = "";
  const cont = h("div", {});
  const cargar = async () => {
    const lista = await api("/api/empleados?q=" + encodeURIComponent(q));
    cont.replaceChildren(tabla([{ t: "Código", f: (e) => e.codigo }, { t: "C.I.", f: (e) => e.ci + (e.complemento ? "-" + e.complemento : "") },
      { t: "Apellidos y nombres", f: (e) => e.apellidos + " " + e.nombres }, { t: "Cargo", f: (e) => e.cargo }, { t: "Unidad", f: (e) => e.unidad },
      { t: "Modalidad", f: (e) => MOD[e.modalidad] || "" }, { t: "Haber/Honorario", n: 1, f: (e) => money(e.haber_basico) }, { t: "Ingreso", f: (e) => fdate(e.fecha_inicio) },
      { t: "Estado", f: (e) => h("span", { class: "tag " + (e.activo ? "ok" : "mal") }, e.activo ? "Activo" : "Inactivo") },
      { t: "", f: (e) => h("button", { class: "sec", onclick: () => formEmpleado(e.id) }, "Ver / editar") }], lista));
  };
  const file = h("input", { type: "file", accept: ".xlsx,.csv,.txt" });
  const out = h("div", { class: "muted" });
  const vista = h("div", {}, h("h2", {}, "Personal y contratos"),
    h("div", { class: "card row" },
      h("label", {}, "Buscar", h("input", { oninput: (e) => { q = e.target.value; clearTimeout(vista._t); vista._t = setTimeout(cargar, 250); } })),
      puede() ? h("button", { onclick: () => formEmpleado(null) }, "Nuevo servidor") : null,
      h("button", { class: "sec", onclick: () => descargar("/api/personal/plantilla", "plantilla_personal.xlsx") }, "Descargar plantilla Excel"),
      puede() ? h("label", {}, "Importación masiva (.xlsx/.csv)", file) : null,
      puede() ? h("button", { onclick: async () => {
        if (!file.files[0]) return toast("Seleccione un archivo", "err");
        const fd = new FormData(); fd.append("archivo", file.files[0]);
        const r = await accion(() => api("/api/personal/importar", { method: "POST", form: fd }));
        if (r) { out.textContent = `Creados: ${r.creados} · Actualizados: ${r.actualizados} · Errores: ${r.errores.length}` + (r.errores.length ? "\n" + r.errores.join("\n") : ""); out.style.whiteSpace = "pre-wrap"; cargar(); }
      } }, "Importar") : null), out, cont);
  await cargar();
  return vista;
};

async function formEmpleado(id) {
  const [unidades, horarios] = await Promise.all([api("/api/unidades"), api("/api/horarios")]);
  const e = id ? await api("/api/empleados/" + id) : null;
  const c = e?.contratos?.slice(-1)[0] || {};
  const f = h("form", { onsubmit: async (ev) => {
    ev.preventDefault();
    const d = leer(f);
    const emp = { codigo: d.codigo, ci: d.ci, complemento: d.complemento, expedido: d.expedido, nombres: d.nombres, apellidos: d.apellidos, cargo: d.cargo,
      unidad: d.unidad, horario_id: d.horario_id ? +d.horario_id : null, nro_cua: d.nro_cua, activo: d.activo };
    const con = { modalidad: d.modalidad, partida: d.partida, haber_basico: d.haber_basico, bono_antiguedad: d.bono_antiguedad || 0, rc_iva: d.rc_iva || 0,
      fecha_inicio: d.fecha_inicio, fecha_fin: d.fecha_fin || null, nro_documento: d.nro_documento };
    const r = await accion(async () => {
      if (!id) return api("/api/empleados", { method: "POST", json: { d: emp, c: con } });
      await api("/api/empleados/" + id, { method: "PUT", json: emp });
      if (c.id) await api("/api/contratos/" + c.id, { method: "PUT", json: con });
      else await api(`/api/empleados/${id}/contratos`, { method: "POST", json: con });
      return true;
    }, "Guardado");
    if (r) { dlg.close(); refrescar(); }
  } },
    h("div", { class: "row" },
      campo("Código reloj", "codigo", { req: true, value: e?.codigo }), campo("C.I.", "ci", { req: true, value: e?.ci }), campo("Compl.", "complemento", { value: e?.complemento, maxlength: 5, style: "width:70px" }),
      campo("Exp.", "expedido", { value: e?.expedido, maxlength: 4, style: "width:70px" }), campo("N° CUA", "nro_cua", { value: e?.nro_cua })),
    h("div", { class: "row" }, campo("Nombres", "nombres", { req: true, value: e?.nombres }), campo("Apellidos", "apellidos", { req: true, value: e?.apellidos }),
      campo("Cargo", "cargo", { value: e?.cargo, style: "min-width:260px" })),
    h("div", { class: "row" },
      h("label", {}, "Unidad organizacional", h("input", { name: "unidad", list: "uns", value: e?.unidad || "" }), h("datalist", { id: "uns" }, unidades.map((u) => h("option", { value: u.nombre })))),
      campo("Horario", "horario_id", { opts: [["", "(Por defecto)"], ...horarios.map((x) => [x.id, x.nombre])], value: e?.horario_id ?? "" }),
      campo("Activo", "activo", { type: "checkbox", value: e ? e.activo : true })),
    h("h3", {}, "Contrato vigente"),
    h("div", { class: "row" },
      campo("Modalidad", "modalidad", { opts: Object.entries(MOD), value: c.modalidad || "PERMANENTE" }), campo("Partida", "partida", { value: c.partida, style: "width:90px" }),
      campo("Haber básico / Honorario Bs", "haber_basico", { type: "number", step: "0.01", min: 0.01, req: true, value: c.haber_basico }),
      campo("Bono antigüedad Bs", "bono_antiguedad", { type: "number", step: "0.01", min: 0, value: c.bono_antiguedad ?? 0 }),
      campo("RC-IVA Bs", "rc_iva", { type: "number", step: "0.01", min: 0, value: c.rc_iva ?? 0 })),
    h("div", { class: "row" }, campo("Fecha de ingreso", "fecha_inicio", { type: "date", req: true, value: c.fecha_inicio }), campo("Fecha fin pactada", "fecha_fin", { type: "date", value: c.fecha_fin }),
      campo("N° memorándum / contrato", "nro_documento", { value: c.nro_documento })),
    h("p", { class: "muted" }, c.fecha_baja ? `Baja: ${fdate(c.fecha_baja)} (${CAUSALES[c.causal_baja] || c.causal_baja})` : ""),
    h("div", { class: "row", style: "margin-top:12px" }, puede() ? h("button", { type: "submit" }, "Guardar") : null,
      puede() && c.id && !c.fecha_baja ? h("button", { type: "button", class: "mal", onclick: async () => {
        const fecha = prompt("Fecha efectiva de la baja (AAAA-MM-DD):"); if (!fecha) return;
        const causal = prompt("Causal: " + Object.keys(CAUSALES).join(", "), "RENUNCIA"); if (!causal) return;
        if (await accion(() => api(`/api/contratos/${c.id}/baja`, { method: "POST", json: { fecha, causal } }), "Baja registrada")) { dlg.close(); refrescar(); }
      } }, "Registrar baja") : null,
      h("button", { type: "button", class: "sec", onclick: () => dlg.close() }, "Cerrar")));
  const dlg = dialogo(e ? "Servidor: " + e.apellidos + " " + e.nombres : "Nuevo servidor", f);
}

V.marcas = async () => {
  const [lotes, nr] = await Promise.all([api("/api/biometrico/lotes"), api(`/api/biometrico/no-reconocidos/${S.anio}/${S.mes}`)]);
  const file = h("input", { type: "file", accept: ".xlsx,.csv,.txt,.dat" });
  const orden = h("select", {}, h("option", { value: "dmy" }, "día/mes/año (Bolivia)"), h("option", { value: "mdy" }, "mes/día/año"));
  const out = h("pre", { class: "muted" });
  return h("div", {}, h("h2", {}, "Marcaciones biométricas"),
    puede() ? h("div", { class: "card row" }, h("label", {}, "Archivo del reloj (ZKTeco .dat/.txt, Anviz/Dahua .csv, Excel)", file), h("label", {}, "Formato de fecha", orden),
      h("button", { onclick: async () => {
        if (!file.files[0]) return toast("Seleccione un archivo", "err");
        const fd = new FormData(); fd.append("archivo", file.files[0]); fd.append("orden_fecha", orden.value);
        const r = await accion(() => api("/api/biometrico/importar", { method: "POST", form: fd }));
        if (r) { out.textContent = `Formato ${r.formato}: leídas ${r.leidas}, nuevas ${r.nuevas}, duplicadas ${r.duplicadas}, rechazadas ${r.rechazadas}\n` + r.detalle_rechazo.join("\n"); toast("Importación terminada", "ok"); setTimeout(refrescar, 3000); }
      } }, "Importar")) : null, out,
    h("p", { class: "muted" }, "Las marcas se guardan tal como las entrega el reloj y NO pueden editarse (inalterabilidad). Los archivos repetidos o las marcas duplicadas se detectan automáticamente. Después de importar, procese el periodo."),
    h("h3", {}, `Identificadores del reloj sin servidor asociado (${MESES[S.mes - 1]} ${S.anio})`), selPeriodo(refrescar),
    tabla([{ t: "ID en el reloj", f: (x) => x.identificador }, { t: "Marcas", n: 1, f: (x) => x.marcas }], nr),
    h("h3", {}, "Lotes importados"),
    tabla([{ t: "#", f: (l) => l.id }, { t: "Archivo", f: (l) => l.archivo }, { t: "Formato", f: (l) => l.formato }, { t: "Fecha", f: (l) => l.fecha.replace("T", " ") },
      { t: "Usuario", f: (l) => l.usuario }, { t: "Leídas", n: 1, f: (l) => l.leidas }, { t: "Nuevas", n: 1, f: (l) => l.nuevas }, { t: "Duplic.", n: 1, f: (l) => l.duplicadas },
      { t: "Rech.", n: 1, f: (l) => l.rechazadas }, { t: "SHA-256", f: (l) => l.sha256.slice(0, 12) + "…" }], lotes));
};

V.asistencia = async () => {
  const emps = await api("/api/empleados");
  const sel = h("select", {}, emps.map((e) => h("option", { value: e.id }, e.apellidos + " " + e.nombres)));
  const cont = h("div", {});
  const cargar = async () => {
    if (!sel.value) return cont.replaceChildren(h("p", { class: "muted" }, "No hay personal registrado"));
    const l = await api(`/api/asistencia/${S.anio}/${S.mes}?empleado_id=${sel.value}`);
    cont.replaceChildren(tabla([{ t: "Fecha", f: (a) => fdate(a.fecha) }, { t: "Marcas", f: (a) => a.marcas }, { t: "Estado", f: (a) => ESTADO[a.estado] || a.estado },
      { t: "Min. retraso", n: 1, f: (a) => a.min_retraso || "" }, { t: "Falta", n: 1, f: (a) => a.falta || "" }, { t: "Justif.", n: 1, f: (a) => a.justificado || "" }, { t: "Observaciones", f: (a) => a.observacion }], l, { cls: (a) => a.estado }));
    if (!l.length) cont.append(h("p", { class: "muted" }, "Periodo sin procesar para este servidor: use Inicio → Procesar periodo."));
  };
  sel.onchange = cargar;
  const v = h("div", {}, h("h2", {}, "Asistencia diaria"), h("div", { class: "card row" }, selPeriodo(() => cargar()), h("label", {}, "Servidor", sel)), cont);
  await cargar();
  return v;
};

V.permisos = async () => {
  const [lista, emps, tipos] = await Promise.all([api(`/api/permisos?anio=${S.anio}&mes=${S.mes}`), api("/api/empleados"), api("/api/permiso-tipos")]);
  return h("div", {}, h("h2", {}, "Permisos, licencias y boletas"),
    h("div", { class: "card row" }, selPeriodo(refrescar), puede() ? h("button", { onclick: () => formPermiso(emps, tipos) }, "Nueva solicitud") : null),
    tabla([{ t: "Boleta", f: (p) => p.nro_boleta }, { t: "Servidor", f: (p) => p.empleado }, { t: "Tipo", f: (p) => p.tipo }, { t: "Desde", f: (p) => fdate(p.fecha_desde) + (p.hora_desde ? " " + p.hora_desde : "") },
      { t: "Hasta", f: (p) => fdate(p.fecha_hasta) + (p.hora_hasta ? " " + p.hora_hasta : "") }, { t: "Goce", f: (p) => (p.con_goce ? "Sí" : "No") },
      { t: "Autoriza", f: (p) => p.autorizado_por }, { t: "Estado", f: (p) => h("span", { class: "tag " + (p.estado === "APROBADO" ? "ok" : p.estado === "PENDIENTE" ? "av" : "mal") }, p.estado) },
      { t: "", f: (p) => h("div", { class: "row" }, h("button", { class: "sec", onclick: () => verPdf(`/api/permisos/${p.id}/boleta.pdf`) }, "Boleta PDF"),
        puede() && p.estado === "PENDIENTE" ? h("button", { onclick: async () => { const a = p.autorizado_por || prompt("Autorizado por (inmediato superior / fiscal de servicio):") || ""; if (await accion(() => api(`/api/permisos/${p.id}/aprobar`, { method: "POST", json: { autorizado_por: a } }), "Aprobado")) refrescar(); } }, "Aprobar") : null,
        puede() && p.estado === "PENDIENTE" ? h("button", { class: "sec", onclick: async () => { if (await accion(() => api(`/api/permisos/${p.id}/rechazar`, { method: "POST" }), "Rechazado")) refrescar(); } }, "Rechazar") : null,
        puede() && p.estado === "APROBADO" ? h("button", { class: "mal", onclick: async () => { if (confirm("¿Anular el permiso?") && await accion(() => api(`/api/permisos/${p.id}/anular`, { method: "POST" }), "Anulado")) refrescar(); } }, "Anular") : null) }], lista));
};
function formPermiso(emps, tipos) {
  const f = h("form", { onsubmit: async (ev) => {
    ev.preventDefault();
    const d = leer(f);
    const body = { empleado_id: +d.empleado_id, tipo_codigo: d.tipo_codigo, fecha_desde: d.fecha_desde, fecha_hasta: d.fecha_hasta || d.fecha_desde, hora_desde: d.hora_desde || null,
      hora_hasta: d.hora_hasta || null, motivo: d.motivo, doc_respaldo: d.doc_respaldo, autorizado_por: d.autorizado_por, gestion_vacacion: d.gestion_vacacion, saldo_vacacion: d.saldo_vacacion, aprobar: d.aprobar };
    const r = await accion(() => api("/api/permisos", { method: "POST", json: body }), "Solicitud registrada");
    if (r) { dlg.close(); verPdf(`/api/permisos/${r.id}/boleta.pdf`); refrescar(); }
  } },
    h("div", { class: "row" }, campo("Servidor", "empleado_id", { opts: emps.map((e) => [e.id, e.apellidos + " " + e.nombres + " (" + (MOD[e.modalidad] || "") + ")"]) }),
      campo("Tipo", "tipo_codigo", { opts: tipos.map((t) => [t.codigo, t.nombre + (t.con_goce ? "" : " (sin goce)")]) })),
    h("div", { class: "row" }, campo("Desde", "fecha_desde", { type: "date", req: true }), campo("Hasta", "fecha_hasta", { type: "date" }),
      campo("Hora desde (vacío = día completo)", "hora_desde", { type: "time" }), campo("Hora hasta", "hora_hasta", { type: "time" })),
    h("div", { class: "row" }, campo("Motivo", "motivo", { style: "min-width:300px" }), campo("Documento de respaldo", "doc_respaldo")),
    h("div", { class: "row" }, campo("Autorizado por (obligatorio para consultores: fiscal de servicio)", "autorizado_por", { style: "min-width:340px" }),
      campo("Gestión vacación", "gestion_vacacion"), campo("Saldo vacación", "saldo_vacacion"), campo("Aprobar de inmediato", "aprobar", { type: "checkbox" })),
    h("div", { class: "row", style: "margin-top:12px" }, h("button", { type: "submit" }, "Registrar"), h("button", { type: "button", class: "sec", onclick: () => dlg.close() }, "Cancelar")));
  const dlg = dialogo("Solicitud de permiso / licencia", f);
}

V.instructivos = async () => {
  const lista = await api("/api/instructivos");
  return h("div", {}, h("h2", {}, "Instructivos y cites oficiales de RR.HH."),
    puede() ? h("div", { class: "card" }, h("button", { onclick: formInstructivo }, "Nuevo instructivo")) : null,
    tabla([{ t: "Cite", f: (i) => i.cite }, { t: "Título", f: (i) => i.titulo }, { t: "Emisión", f: (i) => fdate(i.fecha_emision) }, { t: "Estado", f: (i) => h("span", { class: "tag " + (i.estado === "EMITIDO" ? "ok" : i.estado === "ANULADO" ? "mal" : "av") }, i.estado) },
      { t: "Destinatarios", n: 1, f: (i) => `${i.notificados}/${i.n_destinatarios} notificados` }, { t: "", f: (i) => h("button", { class: "sec", onclick: () => verInstructivo(i.id) }, "Abrir") }], lista));
};
async function formInstructivo() {
  const [unidades, emps] = await Promise.all([api("/api/unidades"), api("/api/empleados")]);
  const multi = (name, opts) => h("label", {}, name, h("select", { multiple: true, size: 5, name: "m_" + name }, opts.map(([v, t]) => h("option", { value: v }, t))));
  const f = h("form", { onsubmit: async (ev) => {
    ev.preventDefault();
    const d = leer(f);
    const sel = (n) => [...f.elements["m_" + n].selectedOptions].map((o) => o.value);
    const body = { titulo: d.titulo, contenido: d.contenido, fecha_emision: d.fecha_emision || null, todos: d.todos, empleados: sel("Personas").map(Number), unidades: sel("Unidades").map(Number),
      modalidades: sel("Modalidades"), cargos: d.cargos.split(",").map((x) => x.trim()).filter(Boolean) };
    const r = await accion(() => api("/api/instructivos", { method: "POST", json: body }), "Instructivo creado");
    if (r) { dlg.close(); refrescar(); }
  } },
    h("div", { class: "row" }, campo("Título / asunto", "titulo", { req: true, style: "min-width:420px" }), campo("Fecha de emisión", "fecha_emision", { type: "date" })),
    campo("Contenido (separe párrafos con una línea en blanco)", "contenido", { area: true, req: true }),
    h("h3", {}, "Destinatarios (se suman los criterios marcados)"),
    h("div", { class: "row" }, campo("Todo el personal activo", "todos", { type: "checkbox" }), multi("Unidades", unidades.map((u) => [u.id, u.nombre])), multi("Modalidades", Object.entries(MOD)),
      multi("Personas", emps.map((e) => [e.id, e.apellidos + " " + e.nombres])), campo("Cargos que contengan (separados por coma)", "cargos")),
    h("div", { class: "row", style: "margin-top:12px" }, h("button", { type: "submit" }, "Crear (BORRADOR)"), h("button", { type: "button", class: "sec", onclick: () => dlg.close() }, "Cancelar")));
  const dlg = dialogo("Nuevo instructivo", f);
}
async function verInstructivo(id) {
  const i = await api("/api/instructivos/" + id);
  const box = h("div", {}, h("p", {}, h("b", {}, i.cite), " — ", i.titulo), h("pre", { style: "white-space:pre-wrap;font:inherit" }, i.contenido),
    h("div", { class: "row" }, h("button", { class: "sec", onclick: () => verPdf(`/api/instructivos/${id}/pdf`) }, "Ver PDF"),
      puede() && i.estado === "BORRADOR" ? h("button", { onclick: async () => { if (await accion(() => api(`/api/instructivos/${id}/emitir`, { method: "POST" }), "Emitido")) { dlg.close(); refrescar(); } } }, "Emitir") : null,
      puede() && i.estado !== "ANULADO" ? h("button", { class: "mal", onclick: async () => { if (confirm("¿Anular? El cite no se reutiliza.") && await accion(() => api(`/api/instructivos/${id}/anular`, { method: "POST" }), "Anulado")) { dlg.close(); refrescar(); } } }, "Anular") : null,
      h("button", { class: "sec", onclick: () => dlg.close() }, "Cerrar")),
    h("h3", {}, "Notificación a destinatarios"),
    tabla([{ t: "Servidor", f: (d) => d.empleado }, { t: "Cargo", f: (d) => d.cargo }, { t: "Estado", f: (d) => d.notificacion },
      { t: "", f: (d) => (puede() && i.estado === "EMITIDO" ? ["NOTIFICADO", "RECIBIDO"].map((n) => h("button", { class: "sec", style: "margin-right:4px", onclick: async () => { if (await accion(() => api(`/api/instructivos/${id}/destinatarios/${d.id}`, { method: "PUT", json: { notificacion: n } }), n)) { dlg.close(); verInstructivo(id); } } }, n.toLowerCase())) : "") }], i.destinatarios));
  const dlg = dialogo("Instructivo " + i.cite + " · " + i.estado, box);
}

V.reportes = async () => {
  const q = `${S.anio}/${S.mes}`, suf = `${S.anio}-${String(S.mes).padStart(2, "0")}`;
  const emitir = h("input", { type: "checkbox" });
  const delim = h("select", {}, h("option", { value: "tab" }, "Tabulador (.txt)"), h("option", { value: "coma" }, "Coma (.csv)"), h("option", { value: "pyc" }, "Punto y coma (.csv)"));
  const bom = h("input", { type: "checkbox" });
  const R = (t, d, path, nombre, extra) => h("div", { class: "card" }, h("b", {}, t), h("p", { class: "muted" }, d), extra || null,
    h("button", { onclick: () => descargar(`/api/reportes/${q}/${path}`, nombre) }, "Descargar"));
  return h("div", {}, h("h2", {}, "Reportes y planillas"), h("div", { class: "card" }, selPeriodo(refrescar), h("p", { class: "muted" }, "El periodo debe estar procesado (Inicio → Procesar periodo).")),
    h("div", { class: "card" }, h("b", {}, "1. Informe de Asistencia de Personal (.docx)"), h("p", { class: "muted" }, "Informe técnico editable (membrete, antecedentes, marco normativo, análisis, cuadro resumen, conclusiones y firmas)."),
      h("label", { style: "flex-direction:row;align-items:center;gap:6px;margin-bottom:8px" }, emitir, "Emitir con N° correlativo oficial (consume número; si no, sale como BORRADOR)"),
      h("button", { onclick: () => descargar(`/api/reportes/${q}/informe.docx?emitir=${emitir.checked}`, `Informe_Asistencia_${suf}.docx`) }, "Descargar")),
    R("2. Planilla de Nuevo Personal (.xlsx)", "Altas del periodo: designación/contrato, partida, vigencia.", "nuevos.xlsx", `Planilla_Nuevo_Personal_${suf}.xlsx`),
    R("3. Planilla de Personal Desvinculado (.xlsx)", "Bajas del periodo con causal y fecha efectiva.", "desvinculados.xlsx", `Planilla_Desvinculados_${suf}.xlsx`),
    R("4. Planilla de Sueldos y Salarios (.xlsx)", "Por modalidad: Permanente, Eventual y Consultores; con descuentos, aportes y líquido pagable.", "planilla.xlsx", `Planilla_Sueldos_${suf}.xlsx`),
    R("5. Reporte detallado de asistencia, faltas y retrasos (.xlsx)", "Resumen institucional, detalle diario por servidor e imputación de faltas/retrasos.", "asistencia.xlsx", `Reporte_Asistencia_${suf}.xlsx`),
    h("div", { class: "card" }, h("b", {}, "6. Consolidado plano para auditoría (UAI / CGE) — UTF-8"), h("p", { class: "muted" }, "Periodo, C.I., código, tipo de contrato, días laborables, asistidos, faltas, minutos de retraso, días justificados e importe de descuentos."),
      h("div", { class: "row" }, h("label", {}, "Delimitador", delim), h("label", { style: "flex-direction:row;align-items:center;gap:6px" }, bom, "Incluir BOM (para Excel antiguo)"),
        h("button", { onclick: () => descargar(`/api/reportes/${q}/auditoria.txt?delimitador=${delim.value}&bom=${bom.checked}`, "consolidado.txt") }, "Descargar"))));
};
V.config = async () => {
  const [ent, hors, escMin, escCant, fer] = await Promise.all([api("/api/entidad"), api("/api/horarios"), api("/api/escala/MINUTOS"), api("/api/escala/CANTIDAD"), api(`/api/feriados?anio=${S.anio}`)]);
  const f = h("form", { class: "card", onsubmit: async (ev) => {
    ev.preventDefault();
    const d = leer(f); delete d.id;
    if (await accion(() => api("/api/entidad", { method: "PUT", json: d }), "Parámetros guardados")) refrescar();
  } }, h("h3", { style: "margin-top:0" }, "Datos institucionales y reglas de cálculo"),
    h("div", { class: "row" }, campo("Nombre de la entidad", "nombre", { value: ent.nombre, style: "min-width:340px" }), campo("Sigla del municipio", "sigla", { value: ent.sigla, style: "width:100px" }), campo("Código SIGEP", "codigo_sigep", { value: ent.codigo_sigep }), campo("Ciudad / localidad", "ciudad", { value: ent.ciudad })),
    h("div", { class: "row" }, campo("Dirección", "direccion", { value: ent.direccion, style: "min-width:320px" }), campo("Prefijo de cites", "prefijo_cite", { value: ent.prefijo_cite }), campo("Reglamento Interno (RIP)", "reglamento_rip", { value: ent.reglamento_rip, style: "min-width:240px" })),
    h("div", { class: "row" }, campo("Máxima Autoridad Ejecutiva", "mae_nombre", { value: ent.mae_nombre }), campo("Cargo MAE", "mae_cargo", { value: ent.mae_cargo }), campo("Responsable de RR.HH.", "rrhh_nombre", { value: ent.rrhh_nombre }), campo("Cargo", "rrhh_cargo", { value: ent.rrhh_cargo })),
    h("div", { class: "row" }, campo("Aprueba el informe", "aprobador_nombre", { value: ent.aprobador_nombre }), campo("Cargo", "aprobador_cargo", { value: ent.aprobador_cargo, style: "min-width:300px" })),
    h("div", { class: "row" }, campo("Escala de sanción por", "escala_modo", { opts: [["MINUTOS", "Minutos acumulados"], ["CANTIDAD", "Cantidad de retrasos"]], value: ent.escala_modo }),
      campo("Factor falta injustificada (planta/eventual)", "factor_falta_planta", { type: "number", step: "0.01", value: ent.factor_falta_planta }), campo("Factor falta (consultor)", "factor_falta_consultor", { type: "number", step: "0.01", value: ent.factor_falta_consultor }),
      campo("Días justificados libres/mes (consultor)", "max_justificados_consultor", { type: "number", step: "0.5", value: ent.max_justificados_consultor })),
    h("div", { class: "row" }, campo("Aporte laboral AFP/Gestora", "tasa_afp", { type: "number", step: "0.0001", value: ent.tasa_afp }), campo("Aporte patronal (informativo)", "tasa_patronal", { type: "number", step: "0.0001", value: ent.tasa_patronal }),
      campo("Superada la tolerancia, contar retraso completo", "tolerancia_cuenta_total", { type: "checkbox", value: ent.tolerancia_cuenta_total }), campo("Contar salida anticipada como retraso", "contar_salida_anticipada", { type: "checkbox", value: ent.contar_salida_anticipada })),
    puede() ? h("button", { type: "submit" }, "Guardar") : null);
  const escalaTabla = (modo, filas) => {
    const area = h("textarea", { style: "min-height:100px" }, filas.map((x) => `${x.desde};${x.hasta ?? ""};${x.dias_descuento};${x.sancion}`).join("\n"));
    return h("div", { class: "card" }, h("h3", { style: "margin-top:0" }, "Escala de sanción por " + (modo === "MINUTOS" ? "minutos acumulados" : "cantidad de retrasos") + (ent.escala_modo === modo ? " (ACTIVA)" : "")),
      h("p", { class: "muted" }, "Una fila por tramo: desde;hasta;días de descuento;sanción  (hasta vacío = sin tope)"), area,
      puede() ? h("button", { onclick: async () => {
        const filas = area.value.split("\n").filter((l) => l.trim()).map((l) => { const [d, hh, dd, ...s] = l.split(";"); return { desde: +d, hasta: hh.trim() === "" ? null : +hh, dias_descuento: +dd, sancion: s.join(";").trim() }; });
        await accion(() => api("/api/escala/" + modo, { method: "PUT", json: filas }), "Escala guardada");
      } }, "Guardar escala") : null);
  };
  const horarios = hors.map((x) => {
    const g = h("form", { class: "card", onsubmit: async (ev) => {
      ev.preventDefault();
      const d = leer(g);
      const turnos = []; for (let i = 1; i <= 4; i++) if (d["e" + i] && d["s" + i]) turnos.push({ nombre: d["n" + i] || "Turno " + i, hora_entrada: d["e" + i], hora_salida: d["s" + i] });
      if (await accion(() => api("/api/horarios/" + x.id, { method: "PUT", json: { nombre: d.nombre, es_defecto: d.es_defecto, activo: true, tolerancia_min: d.tolerancia_min, umbral_grave_min: d.umbral_grave_min, dias_laborables: d.dias_laborables, turnos } }), "Horario guardado")) refrescar();
    } }, h("h3", { style: "margin-top:0" }, "Horario: " + x.nombre + (x.es_defecto ? " (por defecto)" : "")),
      h("div", { class: "row" }, campo("Nombre", "nombre", { value: x.nombre }), campo("Tolerancia (min)", "tolerancia_min", { type: "number", min: 0, value: x.tolerancia_min, style: "width:100px" }),
        campo("Retraso grave > (min)", "umbral_grave_min", { type: "number", min: 1, value: x.umbral_grave_min, style: "width:100px" }), campo("Días laborables (0=lun … 6=dom)", "dias_laborables", { value: x.dias_laborables, style: "width:110px" }),
        campo("Por defecto", "es_defecto", { type: "checkbox", value: x.es_defecto })),
      [1, 2, 3, 4].map((i) => h("div", { class: "row" }, campo("Turno " + i, "n" + i, { value: x.turnos[i - 1]?.nombre || "", style: "width:120px" }), campo("Entrada", "e" + i, { type: "time", value: x.turnos[i - 1]?.hora_entrada }), campo("Salida", "s" + i, { type: "time", value: x.turnos[i - 1]?.hora_salida }))),
      puede() ? h("button", { type: "submit", style: "margin-top:8px" }, "Guardar horario") : null);
    return g;
  });
  const fd = h("input", { type: "date" }), fx = h("input", { placeholder: "Descripción", style: "min-width:240px" });
  return h("div", {}, h("h2", {}, "Configuración institucional"), f, horarios, escalaTabla("MINUTOS", escMin), escalaTabla("CANTIDAD", escCant),
    h("div", { class: "card" }, h("h3", { style: "margin-top:0" }, "Feriados " + S.anio), puede() ? h("div", { class: "row" }, h("label", {}, "Fecha", fd), h("label", {}, "Descripción", fx), h("button", { onclick: async () => { if (await accion(() => api("/api/feriados", { method: "POST", json: { fecha: fd.value, descripcion: fx.value } }), "Guardado")) refrescar(); } }, "Agregar")) : null,
      tabla([{ t: "Fecha", f: (x) => fdate(x.fecha) }, { t: "Descripción", f: (x) => x.descripcion }, { t: "", f: (x) => (puede() ? h("button", { class: "sec", onclick: async () => { if (await accion(() => api("/api/feriados/" + x.fecha, { method: "DELETE" }))) refrescar(); } }, "Quitar") : "") }], fer)));
};

V.respaldos = async () => {
  const lista = await api("/api/backup");
  const pw = h("input", { type: "password", autocomplete: "new-password" }), dest = h("input", { placeholder: "Opcional: ruta local o USB (ej. E:\\Respaldos)", style: "min-width:320px" });
  const fr = h("input", { type: "file" }), hr = h("input", { placeholder: "SHA-256 de referencia", style: "min-width:420px" }), pr = h("input", { type: "password", autocomplete: "off" });
  const out = h("pre", { class: "muted" });
  const enviar = async (ruta, restaurar) => {
    if (!fr.files[0]) return toast("Seleccione el archivo .sql.enc", "err");
    const fd = new FormData(); fd.append("archivo", fr.files[0]); fd.append("sha256", hr.value); fd.append("password", pr.value);
    const r = await accion(() => api(ruta, { method: "POST", form: fd }));
    if (r) { out.textContent = JSON.stringify(r, null, 2); if (restaurar) toast("Restauración completada; vuelva a ingresar", "ok"); }
  };
  return h("div", {}, h("h2", {}, "Respaldos y recuperación"),
    h("div", { class: "card" }, h("h3", { style: "margin-top:0" }, "Crear copia de seguridad cifrada (AES-256-GCM)"),
      h("div", { class: "row" }, h("label", {}, "Contraseña de cifrado (mín. 8; anótela: sin ella no se puede restaurar)", pw), h("label", {}, "Destino", dest),
        h("button", { onclick: async () => { const r = await accion(() => api("/api/backup", { method: "POST", json: { password: pw.value, destino: dest.value } }), "Respaldo creado"); if (r) { out.textContent = JSON.stringify(r, null, 2); setTimeout(refrescar, 4000); } } }, "Crear respaldo"))),
    h("div", { class: "card" }, h("h3", { style: "margin-top:0" }, "Verificar / restaurar"),
      h("div", { class: "row" }, h("label", {}, "Archivo", fr), h("label", {}, "SHA-256 (archivo .sha256)", hr), h("label", {}, "Contraseña", pr),
        h("button", { class: "sec", onclick: () => enviar("/api/backup/verificar") }, "Verificar integridad"),
        h("button", { class: "mal", onclick: () => confirm("Se reemplazarán TODOS los datos actuales por los del respaldo (se guarda una copia previa). ¿Continuar?") && enviar("/api/backup/restaurar", true) }, "Restaurar"))),
    out,
    tabla([{ t: "Fecha", f: (b) => b.ts.replace("T", " ") }, { t: "Archivo", f: (b) => b.archivo }, { t: "Tamaño", n: 1, f: (b) => b.bytes }, { t: "SHA-256", f: (b) => b.sha256 }, { t: "Usuario", f: (b) => b.usuario },
      { t: "", f: (b) => h("button", { class: "sec", onclick: () => descargar(`/api/backup/${b.archivo}/descargar`, b.archivo) }, "Descargar") }], lista));
};

V.auditoria = async () => {
  const lista = await api("/api/auditoria?limite=300");
  const out = h("span", { class: "tag" });
  return h("div", {}, h("h2", {}, "Bitácora de auditoría (encadenada por hash)"),
    h("div", { class: "card row" }, h("button", { onclick: async () => { const r = await accion(() => api("/api/auditoria/verificar")); if (r) { out.textContent = r.ok ? `Cadena íntegra (${r.registros} registros)` : `¡ALTERACIÓN detectada en el registro ${r.primer_error_id}!`; out.className = "tag " + (r.ok ? "ok" : "mal"); } } }, "Verificar integridad de la cadena"), out),
    tabla([{ t: "#", f: (a) => a.id }, { t: "Fecha", f: (a) => a.ts }, { t: "Usuario", f: (a) => a.usuario }, { t: "Acción", f: (a) => a.accion }, { t: "Entidad", f: (a) => a.entidad + " " + a.entidad_id }, { t: "Detalle", f: (a) => a.detalle }, { t: "Hash", f: (a) => a.hash }], lista));
};

V.usuarios = async () => {
  const lista = await api("/api/usuarios");
  return h("div", {}, h("h2", {}, "Usuarios y roles"), h("div", { class: "card" }, h("button", { onclick: formUsuario }, "Nuevo usuario"), h("p", { class: "muted" }, "ADMIN: todo. RRHH: opera personal, asistencia, permisos y reportes. CONSULTA: solo lectura y descargas.")),
    tabla([{ t: "Usuario", f: (u) => u.username }, { t: "Nombre", f: (u) => u.nombre }, { t: "Rol", f: (u) => u.rol }, { t: "Activo", f: (u) => (u.activo ? "Sí" : "No") },
      { t: "", f: (u) => h("button", { class: "sec", onclick: () => formUsuario(u) }, "Editar") }], lista));
};
function formUsuario(u) {
  const f = h("form", { onsubmit: async (ev) => {
    ev.preventDefault();
    const d = leer(f); if (u && !d.password) delete d.password;
    if (await accion(() => api(u ? "/api/usuarios/" + u.id : "/api/usuarios", { method: u ? "PUT" : "POST", json: d }), "Guardado")) { dlg.close(); refrescar(); }
  } }, h("div", { class: "row" }, campo("Usuario", "username", { req: true, value: u?.username }), campo("Nombre", "nombre", { value: u?.nombre }),
    campo("Rol", "rol", { opts: [["RRHH", "RRHH"], ["CONSULTA", "CONSULTA"], ["ADMIN", "ADMIN"]], value: u?.rol || "RRHH" }),
    campo(u ? "Nueva contraseña (opcional)" : "Contraseña (mín. 8)", "password", { type: "password", req: !u }), campo("Activo", "activo", { type: "checkbox", value: u ? u.activo : true })),
    h("div", { class: "row", style: "margin-top:12px" }, h("button", { type: "submit" }, "Guardar"), h("button", { type: "button", class: "sec", onclick: () => dlg.close() }, "Cancelar")));
  const dlg = dialogo(u ? "Editar usuario" : "Nuevo usuario", f);
}

render();
