"use client";

import { FileText, LogOut, Menu, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { useAuth } from "@/lib/auth";
import { NAV } from "@/lib/flujo";
import { ROL_LABEL } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Cargando } from "./ui";

export default function Shell({ children }: { children: ReactNode }) {
  const { user, cargando, salir } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [abierto, setAbierto] = useState(false);

  useEffect(() => {
    if (!cargando && !user) router.replace("/login");
  }, [cargando, user, router]);

  useEffect(() => setAbierto(false), [pathname]);

  if (cargando || !user) return <Cargando texto="Verificando sesión…" />;

  const items = NAV.filter((n) => !n.roles || n.roles.includes(user.rol));
  const activo = (href: string) => (href === "/" ? pathname === "/" : pathname === href || (pathname.startsWith(href + "/") && !items.some((o) => o.href !== href && o.href.length > href.length && pathname.startsWith(o.href))));

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-brand-900 bg-brand-700 px-4 text-white">
        <div className="flex items-center gap-3">
          <button className="rounded p-1 hover:bg-brand-600 md:hidden" onClick={() => setAbierto((a) => !a)} aria-label="Menú">
            <Menu className="h-5 w-5" />
          </button>
          <Link href="/" className="flex items-center gap-2 font-semibold">
            <FileText className="h-5 w-5" aria-hidden /> SICOM-MUNI
          </Link>
          <span className="hidden text-xs text-brand-100 sm:inline">Sistema Integrado de Contratación Menor Municipal</span>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <div className="hidden text-right leading-tight sm:block">
            <div className="font-medium">{user.nombre_completo}</div>
            <div className="text-xs text-brand-100">{ROL_LABEL[user.rol]}</div>
          </div>
          <button onClick={async () => { await salir(); router.replace("/login"); }} className="flex items-center gap-1 rounded px-2 py-1 hover:bg-brand-600" aria-label="Cerrar sesión">
            <LogOut className="h-4 w-4" aria-hidden /> <span className="hidden sm:inline">Salir</span>
          </button>
        </div>
      </header>
      <div className="mx-auto flex max-w-[1400px]">
        <nav aria-label="Principal" className={cn("w-56 shrink-0 md:min-h-[calc(100vh-3.5rem)] border-r border-slate-200 bg-white p-3 md:block", abierto ? "block" : "hidden", "max-md:absolute max-md:z-20 max-md:min-h-[calc(100vh-3.5rem)] max-md:shadow-lg")}>
          <ul className="space-y-1">
            {items.map((n) => (
              <li key={n.href}>
                <Link href={n.href} className={cn("block rounded-md px-3 py-2 text-sm font-medium", activo(n.href) ? "bg-brand-50 text-brand-700" : "text-slate-700 hover:bg-slate-100")}>
                  {n.etiqueta}
                </Link>
              </li>
            ))}
          </ul>
          <p className="mt-6 flex items-start gap-1 px-3 text-xs text-slate-400">
            <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden /> Toda acción queda registrada en el Audit Trail.
          </p>
        </nav>
        <main className="min-w-0 flex-1 p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
