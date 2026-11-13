"use client";

import { cva, type VariantProps } from "class-variance-authority";
import { AlertTriangle, CheckCircle2, Info, Loader2, XCircle, X } from "lucide-react";
import {
  forwardRef, useEffect, type ButtonHTMLAttributes, type HTMLAttributes, type InputHTMLAttributes, type ReactNode,
  type SelectHTMLAttributes, type TextareaHTMLAttributes, type TdHTMLAttributes, type ThHTMLAttributes,
} from "react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------- Button
const botonVariantes = cva(
  "inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 whitespace-nowrap",
  {
    variants: {
      variant: {
        primary: "bg-brand-700 text-white hover:bg-brand-600",
        success: "bg-emerald-600 text-white hover:bg-emerald-700",
        danger: "bg-red-600 text-white hover:bg-red-700",
        outline: "border border-slate-300 bg-white text-slate-800 hover:bg-slate-100",
        ghost: "text-slate-700 hover:bg-slate-100",
      },
      size: { sm: "h-8 px-3", md: "h-10 px-4", lg: "h-11 px-6 text-base" },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof botonVariantes> {
  cargando?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant, size, cargando, children, disabled, type = "button", ...p }, ref,
) {
  return (
    <button ref={ref} type={type} disabled={disabled || cargando} className={cn(botonVariantes({ variant, size }), className)} {...p}>
      {cargando && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
      {children}
    </button>
  );
});

// ---------------------------------------------------------------- Card
export function Card({ className, ...p }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-lg border border-slate-200 bg-white shadow-sm", className)} {...p} />;
}
export function CardHeader({ className, ...p }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-5 py-3", className)} {...p} />;
}
export function CardTitle({ className, ...p }: HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn("text-base font-semibold text-brand-900", className)} {...p} />;
}
export function CardBody({ className, ...p }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-5", className)} {...p} />;
}

// ---------------------------------------------------------------- Badge
export function Badge({ className, ...p }: HTMLAttributes<HTMLSpanElement>) {
  return <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset", className)} {...p} />;
}

// ---------------------------------------------------------------- Formularios
const campoBase =
  "block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm placeholder:text-slate-400 disabled:bg-slate-100 disabled:text-slate-500";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input({ className, ...p }, ref) {
  return <input ref={ref} className={cn(campoBase, "h-10", className)} {...p} />;
});
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(function Textarea({ className, ...p }, ref) {
  return <textarea ref={ref} className={cn(campoBase, "min-h-[88px]", className)} {...p} />;
});
export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(function Select({ className, ...p }, ref) {
  return <select ref={ref} className={cn(campoBase, "h-10", className)} {...p} />;
});

export function Field({ label, hint, error, children, className }: {
  label: string; hint?: string; error?: string; children: ReactNode; className?: string;
}) {
  return (
    <label className={cn("block space-y-1", className)}>
      <span className="text-sm font-medium text-slate-700">{label}</span>
      {children}
      {hint && !error && <span className="block text-xs text-slate-500">{hint}</span>}
      {error && <span className="block text-xs text-red-600">{error}</span>}
    </label>
  );
}

// ---------------------------------------------------------------- Alert
const alertaVariantes = {
  info: { c: "border-sky-200 bg-sky-50 text-sky-900", i: Info },
  success: { c: "border-emerald-200 bg-emerald-50 text-emerald-900", i: CheckCircle2 },
  warning: { c: "border-amber-300 bg-amber-50 text-amber-900", i: AlertTriangle },
  error: { c: "border-red-300 bg-red-50 text-red-900", i: XCircle },
} as const;

export function Alert({ tipo = "info", titulo, children, className }: {
  tipo?: keyof typeof alertaVariantes; titulo?: string; children?: ReactNode; className?: string;
}) {
  const { c, i: Icono } = alertaVariantes[tipo];
  return (
    <div role={tipo === "error" ? "alert" : "status"} className={cn("flex gap-3 rounded-md border p-3 text-sm", c, className)}>
      <Icono className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div className="min-w-0 space-y-1">
        {titulo && <p className="font-semibold">{titulo}</p>}
        {children}
      </div>
    </div>
  );
}

export function Cargando({ texto = "Cargando…" }: { texto?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 p-8 text-sm text-slate-500" role="status">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> {texto}
    </div>
  );
}

// ---------------------------------------------------------------- Tabla
export function Tabla({ className, ...p }: HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="overflow-x-auto">
      <table className={cn("w-full border-collapse text-sm", className)} {...p} />
    </div>
  );
}
export function Th({ className, ...p }: ThHTMLAttributes<HTMLTableCellElement>) {
  return <th className={cn("border-b border-slate-200 bg-slate-50 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-600", className)} {...p} />;
}
export function Td({ className, ...p }: TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn("border-b border-slate-100 px-3 py-2 align-top", className)} {...p} />;
}

// ---------------------------------------------------------------- Tabs
export function Tabs<T extends string>({ valor, onCambio, items }: {
  valor: T; onCambio: (v: T) => void; items: { id: T; etiqueta: string; contador?: number }[];
}) {
  return (
    <div role="tablist" className="flex gap-1 overflow-x-auto border-b border-slate-200">
      {items.map((t) => (
        <button
          key={t.id} role="tab" type="button" aria-selected={valor === t.id} onClick={() => onCambio(t.id)}
          className={cn(
            "whitespace-nowrap border-b-2 px-4 py-2 text-sm font-medium",
            valor === t.id ? "border-brand-700 text-brand-700" : "border-transparent text-slate-500 hover:text-slate-800",
          )}
        >
          {t.etiqueta}
          {t.contador !== undefined && <span className="ml-2 rounded-full bg-slate-100 px-2 text-xs text-slate-600">{t.contador}</span>}
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------- Dialog
export function Dialog({ abierto, onCerrar, titulo, children, ancho = "max-w-lg" }: {
  abierto: boolean; onCerrar: () => void; titulo: string; children: ReactNode; ancho?: string;
}) {
  useEffect(() => {
    if (!abierto) return;
    const h = (e: KeyboardEvent) => e.key === "Escape" && onCerrar();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [abierto, onCerrar]);
  if (!abierto) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4" role="dialog" aria-modal="true" aria-label={titulo}>
      <div className={cn("mt-12 w-full rounded-lg bg-white shadow-xl", ancho)}>
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <h3 className="text-base font-semibold text-brand-900">{titulo}</h3>
          <button type="button" onClick={onCerrar} aria-label="Cerrar" className="rounded p-1 text-slate-500 hover:bg-slate-100">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
