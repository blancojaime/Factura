"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, login as apiLogin, logout as apiLogout, refrescarSesion } from "./api";
import type { Usuario } from "./tipos";

interface AuthCtx {
  user: Usuario | null;
  cargando: boolean;
  entrar: (u: string, p: string) => Promise<void>;
  salir: () => Promise<void>;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);

  // al abrir la aplicacion se intenta restaurar la sesion con la cookie de refresh
  useEffect(() => {
    let vivo = true;
    (async () => {
      if (await refrescarSesion()) {
        try {
          const me = await api.get<Usuario>("/auth/me");
          if (vivo) setUser(me);
        } catch {
          /* sin sesion */
        }
      }
      if (vivo) setCargando(false);
    })();
    return () => {
      vivo = false;
    };
  }, []);

  const entrar = useCallback(async (u: string, p: string) => {
    await apiLogin(u, p);
    setUser(await api.get<Usuario>("/auth/me"));
  }, []);

  const salir = useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  const valor = useMemo(() => ({ user, cargando, entrar, salir }), [user, cargando, entrar, salir]);
  return <Ctx.Provider value={valor}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth fuera de AuthProvider");
  return c;
}
