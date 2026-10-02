/** Cliente HTTP de SIGAA: token de sesión, manejo uniforme de errores y apertura de PDF/Excel. */
export class ApiError extends Error {
  constructor(message: string, public status: number, public extra?: any) {
    super(message);
  }
}

let token = sessionStorage.getItem('sigaa.token') || '';
export const getToken = () => token;
export const setToken = (t: string) => {
  token = t;
  if (t) sessionStorage.setItem('sigaa.token', t);
  else sessionStorage.removeItem('sigaa.token');
};
let onUnauthorized: () => void = () => {};
export const setUnauthorizedHandler = (f: () => void) => (onUnauthorized = f);

export type Query = Record<string, string | number | boolean | undefined | null>;
const qs = (q?: Query) => {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(q ?? {})) if (v !== undefined && v !== null && v !== '') p.set(k, String(v));
  const s = p.toString();
  return s ? '?' + s : '';
};

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown; query?: Query } = {}): Promise<T> {
  const res = await fetch('/api' + path + qs(opts.query), {
    method: opts.method ?? (opts.body !== undefined ? 'POST' : 'GET'),
    headers: { ...(opts.body !== undefined ? { 'content-type': 'application/json' } : {}), ...(token ? { authorization: `Bearer ${token}` } : {}) },
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  const text = await res.text();
  let data: any = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) {
    if (res.status === 401) onUnauthorized();
    throw new ApiError(data?.error || `Error ${res.status}`, res.status, data);
  }
  return data as T;
}

export const get = <T = any>(path: string, query?: Query) => api<T>(path, { query });
export const post = <T = any>(path: string, body: unknown = {}) => api<T>(path, { method: 'POST', body });
export const put = <T = any>(path: string, body: unknown = {}) => api<T>(path, { method: 'PUT', body });
export const del = <T = any>(path: string) => api<T>(path, { method: 'DELETE' });

/** URL con el token de sesión para abrir PDF/Excel/imágenes en una pestaña nueva. */
export const urlConToken = (path: string, query?: Query) => `/api${path}${qs({ ...query, access_token: token })}`;
export const abrirDocumento = (id: string, ref: string, extra?: Query) => window.open(urlConToken(`/documentos/${id}`, { ref, ...extra }), '_blank');
export const abrirReporte = (id: string, formato: 'pdf' | 'xlsx', params: Query) => window.open(urlConToken(`/reportes/${id}`, { ...params, formato }), '_blank');

export async function subirFoto(codigo: string, n: number, file: File) {
  const res = await fetch(`/api/af/activos/${encodeURIComponent(codigo)}/foto/${n}`, { method: 'PUT', headers: { authorization: `Bearer ${token}`, 'content-type': file.type || 'image/jpeg' }, body: file });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(data.error || 'No se pudo subir la imagen', res.status);
  return data;
}

export const fmt2 = (v: unknown) => (v === null || v === undefined || v === '' ? '' : Number(v).toLocaleString('es-BO', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
export const fmtN = (v: unknown) => (v === null || v === undefined || v === '' ? '' : Number(v).toLocaleString('es-BO', { maximumFractionDigits: 4 }));
export const fmtDate = (s?: string | null) => (s && /^\d{4}-\d{2}-\d{2}/.test(s) ? `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}` : s || '');
export const hoy = () => new Date().toISOString().slice(0, 10);

/** POST que devuelve un PDF (stickers): se abre como blob en una pestaña nueva. */
export async function abrirPdfPost(path: string, body: unknown) {
  const res = await fetch('/api' + path, { method: 'POST', headers: { 'content-type': 'application/json', authorization: `Bearer ${token}` }, body: JSON.stringify(body) });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    throw new ApiError(d.error || `Error ${res.status}`, res.status);
  }
  window.open(URL.createObjectURL(await res.blob()), '_blank');
}
