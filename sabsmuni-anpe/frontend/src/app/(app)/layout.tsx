'use client';
import { FileText, Landmark, LogOut, ShieldCheck } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { SessionContext } from '@/components/session';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';
import { ROL_ETIQUETA, Usuario } from '@/lib/types';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<Usuario | null>(null);
  useEffect(() => { api<Usuario>('/auth/me').then(setUser).catch(() => router.replace('/login')); }, [router]);
  if (!user) return <div className="p-8 text-sm text-muted-foreground">Cargando sesión…</div>;
  const salir = async () => { await api('/auth/logout', { method: 'POST' }); router.replace('/login'); };
  return (
    <SessionContext.Provider value={user}>
      <header className="sticky top-0 z-10 border-b bg-card/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4">
          <Link href="/procesos" className="flex items-center gap-2 font-semibold text-primary"><Landmark className="h-5 w-5" />SABSMUNI-ANPE</Link>
          <nav className="flex items-center gap-1 text-sm">
            <Link className="rounded-md px-2 py-1 hover:bg-accent" href="/procesos"><FileText className="mr-1 inline h-4 w-4" />Procesos</Link>
            {(user.rol === 'ADMINISTRADOR_SISTEMA' || user.rol === 'AUTORIDAD_RPA') && <Link className="rounded-md px-2 py-1 hover:bg-accent" href="/admin"><ShieldCheck className="mr-1 inline h-4 w-4" />Administración</Link>}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm">
            <span className="hidden text-muted-foreground sm:inline">{user.email}</span>
            <Badge variant="secondary">{ROL_ETIQUETA[user.rol]}</Badge>
            <Button variant="ghost" size="icon" aria-label="Cerrar sesión" onClick={salir}><LogOut className="h-4 w-4" /></Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl p-4">{children}</main>
    </SessionContext.Provider>
  );
}
