import { createContext, useContext, useEffect, useState, ReactNode, useCallback } from 'react';
import { get, post, setToken, getToken, setUnauthorizedHandler } from './api';

export interface Usuario { usuario: string; nombre: string; roles: string[] }
interface AuthState {
  usuario: Usuario | null;
  gestion: number | null;
  debeCambiar: boolean;
  cargando: boolean;
  login(u: string, c: string): Promise<void>;
  logout(): void;
  cambiarClave(actual: string, nueva: string): Promise<void>;
  /** ¿puede escribir en el módulo? */
  puede(m: 'alm' | 'com' | 'af' | 'core'): boolean;
  esAdmin: boolean;
}
const Ctx = createContext<AuthState>(null as any);
export const useAuth = () => useContext(Ctx);

const ROL: Record<string, string> = { alm: 'ALMACEN', com: 'COMBUSTIBLE', af: 'ACTIVOS' };

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [gestion, setGestion] = useState<number | null>(null);
  const [debeCambiar, setDebe] = useState(false);
  const [cargando, setCargando] = useState(true);

  const logout = useCallback(() => {
    setToken('');
    setUsuario(null);
  }, []);
  useEffect(() => setUnauthorizedHandler(logout), [logout]);
  useEffect(() => {
    if (!getToken()) return setCargando(false);
    get('/auth/me')
      .then((r) => { setUsuario(r.usuario); setGestion(r.gestion); })
      .catch((e) => { if (e.extra?.cambiarClave) setDebe(true); else logout(); })
      .finally(() => setCargando(false));
  }, [logout]);

  const value: AuthState = {
    usuario, gestion, debeCambiar, cargando,
    async login(u, c) {
      const r = await post('/auth/login', { usuario: u, clave: c });
      setToken(r.token);
      setUsuario(r.usuario);
      setGestion(r.gestion);
      setDebe(!!r.debeCambiar);
    },
    logout,
    async cambiarClave(actual, nueva) {
      const r = await post('/auth/cambiar-clave', { actual, nueva });
      setToken(r.token);
      setDebe(false);
    },
    puede: (m) => !!usuario && (usuario.roles.includes('ADMIN') || (m !== 'core' && usuario.roles.includes(ROL[m]))),
    esAdmin: !!usuario?.roles.includes('ADMIN'),
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
