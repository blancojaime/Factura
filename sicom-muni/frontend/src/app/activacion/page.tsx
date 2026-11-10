"use client";

import { FileText } from "lucide-react";
import PanelLicencia from "@/components/PanelLicencia";
import { Button } from "@/components/ui";

/** Pantalla publica de activacion: se muestra cuando termina la prueba o la licencia vence. */
export default function ActivacionPage() {
  return (
    <main className="min-h-screen bg-slate-50">
      <header className="bg-brand-700 px-4 py-3 text-white">
        <div className="mx-auto flex max-w-3xl items-center gap-2 font-semibold"><FileText className="h-5 w-5" aria-hidden /> SICOM-MUNI — Activación de la licencia</div>
      </header>
      <div className="mx-auto max-w-3xl space-y-4 p-4">
        <PanelLicencia alActivar={() => setTimeout(() => window.location.assign("/login/"), 1200)} />
        <div className="text-center"><Button variant="outline" onClick={() => window.location.assign("/login/")}>Ir al inicio de sesión</Button></div>
      </div>
    </main>
  );
}
