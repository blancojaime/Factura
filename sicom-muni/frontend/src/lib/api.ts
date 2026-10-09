// Cliente HTTP: access token en memoria; el refresh token vive en una cookie HTTP-only (no accesible desde JS).
const BASE = "/api/v1";

let accessToken: string | null = null;
let refreshing: Promise<boolean> | null = null;

export function setAccessToken(t: string | null) {
  accessToken = t;
}

export class ApiError extends Error {
  status: number;
  codigo: string;
  errores: string[];
  constructor(status: number, mensaje: string, codigo = "ERROR", errores: string[] = []) {
    super(mensaje);
    this.status = status;
    this.codigo = codigo;
    this.errores = errores;
  }
}

function parseError(status: number, cuerpo: unknown): ApiError {
  const d = (cuerpo as { detail?: unknown } | null)?.detail;
  if (typeof d === "string") return new ApiError(status, d);
  if (Array.isArray(d)) {
    // validacion de Pydantic: [{loc:[...], msg:"..."}]
    const errores = d.map((e: { loc?: unknown[]; msg?: string }) => `${(e.loc ?? []).slice(1).join(".")}: ${e.msg ?? ""}`);
    return new ApiError(status, "Hay datos inválidos en el formulario", "VALIDACION", errores);
  }
  if (d && typeof d === "object") {
    const o = d as { mensaje?: string; codigo?: string; errores?: string[] };
    return new ApiError(status, o.mensaje ?? "Error", o.codigo ?? "ERROR", o.errores ?? []);
  }
  return new ApiError(status, status === 401 ? "Sesión expirada" : "Error inesperado del servidor");
}

export async function refrescarSesion(): Promise<boolean> {
  if (refreshing) return refreshing;
  refreshing = (async () => {
    try {
      const r = await fetch(`${BASE}/auth/refresh`, { method: "POST", credentials: "same-origin" });
      if (!r.ok) {
        accessToken = null;
        return false;
      }
      accessToken = (await r.json()).access_token;
      return true;
    } catch {
      return false;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

async function peticion(path: string, init: RequestInit = {}, reintento = true): Promise<Response> {
  const headers = new Headers(init.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const r = await fetch(`${BASE}${path}`, { ...init, headers, credentials: "same-origin" });
  if (r.status === 401 && reintento && !path.startsWith("/auth/")) {
    if (await refrescarSesion()) return peticion(path, init, false);
  }
  return r;
}

async function json<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await peticion(path, init);
  if (r.status === 204) return undefined as T;
  const cuerpo = await r.json().catch(() => null);
  if (!r.ok) throw parseError(r.status, cuerpo);
  return cuerpo as T;
}

const body = (d: unknown) => (d === undefined ? undefined : JSON.stringify(d));

export const api = {
  get: <T>(p: string) => json<T>(p),
  post: <T>(p: string, d?: unknown) => json<T>(p, { method: "POST", body: body(d) }),
  put: <T>(p: string, d?: unknown) => json<T>(p, { method: "PUT", body: body(d) }),
  patch: <T>(p: string, d?: unknown) => json<T>(p, { method: "PATCH", body: body(d) }),
  del: <T>(p: string) => json<T>(p, { method: "DELETE" }),
  async blob(p: string): Promise<Blob> {
    const r = await peticion(p);
    if (!r.ok) throw parseError(r.status, await r.json().catch(() => null));
    return r.blob();
  },
  /** Publico (sin token): verificacion de autenticidad. */
  async publico<T>(p: string, init?: RequestInit): Promise<T> {
    const r = await fetch(`${BASE}${p}`, init);
    const cuerpo = await r.json().catch(() => null);
    if (!r.ok) throw parseError(r.status, cuerpo);
    return cuerpo as T;
  },
};

export async function login(username: string, password: string): Promise<void> {
  const r = await fetch(`${BASE}/auth/login`, {
    method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const cuerpo = await r.json().catch(() => null);
  if (!r.ok) throw parseError(r.status, cuerpo);
  accessToken = cuerpo.access_token;
}

export async function logout(): Promise<void> {
  await fetch(`${BASE}/auth/logout`, { method: "POST", credentials: "same-origin" }).catch(() => undefined);
  accessToken = null;
}

export function mensajeError(e: unknown): string {
  return e instanceof ApiError ? e.message : "Error de conexión con el servidor";
}
