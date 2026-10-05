export class ApiError extends Error {
  constructor(public status: number, message: string, public detalle?: unknown) { super(message); }
}

const mensaje = (b: unknown): string => {
  const o = b as { message?: string | string[]; motivos?: string[] } | null;
  if (o?.motivos?.length) return o.motivos.join(' · ');
  return Array.isArray(o?.message) ? o!.message.join(' · ') : (o?.message ?? 'Error inesperado');
};

let refrescando: Promise<boolean> | null = null;
const refrescar = () => (refrescando ??= fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' }).then((r) => r.ok).finally(() => { refrescando = null; }));

export async function api<T = unknown>(ruta: string, init: { method?: string; body?: unknown; form?: FormData } = {}): Promise<T> {
  const ejecutar = () => fetch('/api' + ruta, {
    method: init.method ?? (init.body || init.form ? 'POST' : 'GET'), credentials: 'include',
    headers: init.form ? undefined : init.body ? { 'Content-Type': 'application/json' } : undefined,
    body: init.form ?? (init.body ? JSON.stringify(init.body) : undefined),
  });
  let r = await ejecutar();
  if (r.status === 401 && !ruta.startsWith('/auth/') && (await refrescar())) r = await ejecutar();
  const texto = await r.text();
  const cuerpo = texto ? JSON.parse(texto) : null;
  if (!r.ok) {
    if (r.status === 401 && typeof window !== 'undefined' && !ruta.startsWith('/auth/') && !location.pathname.startsWith('/login')) location.href = '/login';
    throw new ApiError(r.status, mensaje(cuerpo), cuerpo);
  }
  return cuerpo as T;
}
