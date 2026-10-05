'use client';
import { createContext, useContext } from 'react';
import { Usuario } from '@/lib/types';

export const SessionContext = createContext<Usuario | null>(null);
export const useSession = () => {
  const u = useContext(SessionContext);
  if (!u) throw new Error('Sin sesión');
  return u;
};
