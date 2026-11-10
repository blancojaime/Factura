import { createContext, useContext, useState, useCallback, useEffect, useRef, ReactNode } from 'react';
import { fmt2, fmtN, fmtDate } from './api';

// ───────── Avisos (toasts) y diálogos ─────────
interface ToastItem { id: number; texto: string; error?: boolean }
interface DialogReq { tipo: 'confirm' | 'prompt'; titulo?: string; texto: string; defecto?: string; lista?: string[]; resolve: (v: any) => void }
interface Ui {
  ok(t: string): void;
  error(t: string): void;
  confirm(texto: string, o?: { titulo?: string; lista?: string[] }): Promise<boolean>;
  prompt(texto: string, defecto?: string): Promise<string | null>;
}
const UiCtx = createContext<Ui>(null as any);
export const useUi = () => useContext(UiCtx);

export function UiProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [dlg, setDlg] = useState<DialogReq | null>(null);
  const [val, setVal] = useState('');
  const n = useRef(0);
  const push = useCallback((texto: string, error = false) => {
    const id = ++n.current;
    setToasts((t) => [...t, { id, texto, error }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), error ? 9000 : 4000);
  }, []);
  const ui: Ui = {
    ok: (t) => push(t),
    error: (t) => push(t, true),
    confirm: (texto, o) => new Promise((resolve) => { setDlg({ tipo: 'confirm', texto, titulo: o?.titulo, lista: o?.lista, resolve }); }),
    prompt: (texto, defecto = '') => new Promise((resolve) => { setVal(defecto); setDlg({ tipo: 'prompt', texto, defecto, resolve }); }),
  };
  const cerrar = (v: any) => { dlg?.resolve(v); setDlg(null); };
  return (
    <UiCtx.Provider value={ui}>
      {children}
      <div className="toasts">{toasts.map((t) => <div key={t.id} className={'toast' + (t.error ? ' error' : '')}>{t.texto}</div>)}</div>
      {dlg && (
        <div className="modal-bg" onKeyDown={(e) => e.key === 'Escape' && cerrar(dlg.tipo === 'confirm' ? false : null)}>
          <div className="modal" style={{ width: 'min(520px,100%)' }} role="dialog" aria-modal>
            <h2>{dlg.titulo ?? (dlg.tipo === 'confirm' ? 'Confirmar' : 'Ingrese un dato')}</h2>
            <pre className="msg">{dlg.texto}</pre>
            {dlg.lista && <ul style={{ margin: '0 0 8px 18px', padding: 0 }}>{dlg.lista.map((l, i) => <li key={i}>{l}</li>)}</ul>}
            {dlg.tipo === 'prompt' && <input autoFocus value={val} onChange={(e) => setVal(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && cerrar(val)} />}
            <footer>
              <button onClick={() => cerrar(dlg.tipo === 'confirm' ? false : null)}>Cancelar</button>
              <button className="primary" autoFocus={dlg.tipo === 'confirm'} onClick={() => cerrar(dlg.tipo === 'confirm' ? true : val)}>Aceptar</button>
            </footer>
          </div>
        </div>
      )}
    </UiCtx.Provider>
  );
}

/** Ejecuta una acción asíncrona mostrando el error de negocio al usuario. */
export function useAction() {
  const ui = useUi();
  const [busy, setBusy] = useState(false);
  const run = useCallback(async <T,>(fn: () => Promise<T>, okMsg?: string): Promise<T | undefined> => {
    setBusy(true);
    try {
      const r = await fn();
      if (okMsg) ui.ok(okMsg);
      return r;
    } catch (e: any) {
      ui.error(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }, [ui]);
  return [run, busy] as const;
}

/**
 * Para operaciones con advertencias (requieren confirmación): llama a `fn(false)`; si el servidor responde
 * `requiereConfirmacion`, muestra la lista y, si el usuario acepta, repite con `confirmar = true`.
 */
export function useConfirmable() {
  const ui = useUi();
  const [run, busy] = useAction();
  const exec = useCallback(async (fn: (confirmar: boolean) => Promise<any>, okMsg?: (r: any) => string) => {
    return run(async () => {
      let r = await fn(false);
      if (r?.requiereConfirmacion) {
        const resumen = r.resumen ? Object.entries(r.resumen).map(([k, v]) => `${k.replace(/_/g, ' ')}: ${typeof v === 'number' ? fmtN(v) : v}`).join('\n') : '';
        const si = await ui.confirm(`${resumen}${resumen ? '\n\n' : ''}ADVERTENCIAS (puede continuar bajo su responsabilidad):`, { titulo: 'Revise antes de continuar', lista: r.advertencias });
        if (!si) return undefined;
        r = await fn(true);
      }
      if (okMsg && r) ui.ok(okMsg(r));
      return r;
    });
  }, [run, ui]);
  return [exec, busy] as const;
}

/** Carga datos y permite recargar. */
export function useLoad<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | undefined>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const ui = useUi();
  const reload = useCallback(() => {
    setLoading(true);
    return fn().then((d) => { setData(d); setError(''); }).catch((e) => { setError(e.message); ui.error(e.message); }).finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(() => { reload(); }, [reload]);
  return { data, loading, error, reload, setData };
}

// ───────── Estructura ─────────
export const PageHead = ({ title, sub, children }: { title: string; sub?: string; children?: ReactNode }) => (
  <div className="page-head"><div><h1>{title}</h1>{sub && <p>{sub}</p>}</div><div className="row">{children}</div></div>
);
export const Card = ({ title, children, right }: { title?: string; children: ReactNode; right?: ReactNode }) => (
  <section className="card">{(title || right) && <div className="row" style={{ justifyContent: 'space-between', marginBottom: 8 }}>{title && <h2 style={{ margin: 0 }}>{title}</h2>}{right}</div>}{children}</section>
);
export const Kpi = ({ label, value, tone, mod }: { label: string; value: ReactNode; tone?: 'warn' | 'bad'; mod?: 'alm' | 'com' | 'af' }) => (
  <div className={`kpi ${mod ?? ''} ${tone ?? ''}`}><b>{value}</b><span>{label}</span></div>
);
export function Tabs<T extends string>({ value, onChange, items }: { value: T; onChange: (v: T) => void; items: { id: T; label: string }[] }) {
  return <div className="tabs" role="tablist">{items.map((i) => <button key={i.id} role="tab" className={value === i.id ? 'on' : ''} onClick={() => onChange(i.id)}>{i.label}</button>)}</div>;
}
export function Modal({ title, onClose, children, footer, wide }: { title: string; onClose: () => void; children: ReactNode; footer?: ReactNode; wide?: boolean }) {
  return (
    <div className="modal-bg" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={'modal' + (wide ? ' wide' : '')} role="dialog" aria-modal><h2>{title}</h2>{children}<footer>{footer ?? <button onClick={onClose}>Cerrar</button>}</footer></div>
    </div>
  );
}

const TONOS: Record<string, string> = {
  ENTREGADO: 'b-ok', INGRESADO: 'b-ok', CERRADO: 'b-ok', CODIFICADO: 'b-ok', ATENDIDA: 'b-ok', EJECUTADA: 'b-ok', 'BAJA EJECUTADA': 'b-ok', CONCLUIDO: 'b-ok', HECHO: 'b-ok', CUMPLE: 'b-ok', ACTIVO: 'b-ok', Activo: 'b-ok', Conforme: 'b-ok', Descargado: 'b-ok', Utilizado: 'b-ok', Vigente: 'b-ok', CONFORME: 'b-ok', VIGENTE: 'b-ok',
  PEDIDO: 'b-warn', REGISTRADO: 'b-warn', REGISTRADA: 'b-warn', PENDIENTE: 'b-warn', 'EN TRÁMITE': 'b-warn', 'EN CONTEO': 'b-warn', PARCIAL: 'b-warn', 'ATENDIDA PARCIAL': 'b-warn', Observado: 'b-warn', 'En curso': 'b-warn', Entregado: 'b-info', APROBADO: 'b-info', ASIGNADO: 'b-info', Emitido: 'b-info', Disponible: 'b-info', 'EN ALMACEN': 'b-info',
  ANULADO: 'b-bad', RECHAZADO: 'b-bad', BAJA: 'b-bad', 'NO CUMPLE': 'b-bad', 'SIN EXISTENCIA': 'b-bad', INACTIVO: 'b-mute', Anulado: 'b-bad', Vencido: 'b-bad', Extraviado: 'b-bad', VENCIDO: 'b-bad', 'POR VENCER': 'b-warn',
};
export const Badge = ({ v }: { v?: string | null }) => (v ? <span className={'badge ' + (TONOS[v] ?? '')}>{v}</span> : null);

// ───────── Campos ─────────
type Opt = string | { value: string | number; label: string };
const optVal = (o: Opt) => (typeof o === 'string' ? o : o.value);
const optLab = (o: Opt) => (typeof o === 'string' ? o : o.label);

interface FieldProps { label: string; req?: boolean; className?: string; children: ReactNode; hint?: string }
export const Field = ({ label, req, className, children, hint }: FieldProps) => (
  <label className={'f ' + (className ?? '')}><span className={req ? 'req' : ''}>{label}</span>{children}{hint && <small className="muted" style={{ fontWeight: 400 }}>{hint}</small>}</label>
);
interface BaseProps { label: string; req?: boolean; className?: string; disabled?: boolean; hint?: string }
export const TextField = ({ label, value, onChange, req, className, disabled, hint, placeholder, list }: BaseProps & { value: any; onChange: (v: string) => void; placeholder?: string; list?: string }) => (
  <Field label={label} req={req} className={className} hint={hint}><input value={value ?? ''} onChange={(e) => onChange(e.target.value)} disabled={disabled} placeholder={placeholder} list={list} /></Field>
);
export const NumField = ({ label, value, onChange, req, className, disabled, hint, step }: BaseProps & { value: any; onChange: (v: number | null) => void; step?: string }) => (
  <Field label={label} req={req} className={className} hint={hint}><input type="number" step={step ?? 'any'} value={value ?? ''} onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))} disabled={disabled} /></Field>
);
export const DateField = ({ label, value, onChange, req, className, disabled, hint }: BaseProps & { value: any; onChange: (v: string) => void }) => (
  <Field label={label} req={req} className={className} hint={hint}><input type="date" value={value ? String(value).slice(0, 10) : ''} onChange={(e) => onChange(e.target.value)} disabled={disabled} /></Field>
);
export const AreaField = ({ label, value, onChange, req, className, disabled, rows }: BaseProps & { value: any; onChange: (v: string) => void; rows?: number }) => (
  <Field label={label} req={req} className={className}><textarea rows={rows ?? 2} value={value ?? ''} onChange={(e) => onChange(e.target.value)} disabled={disabled} /></Field>
);
export const SelectField = ({ label, value, onChange, options, req, className, disabled, blank = true, hint }: BaseProps & { value: any; onChange: (v: string) => void; options: Opt[]; blank?: boolean }) => (
  <Field label={label} req={req} className={className} hint={hint}>
    <select value={value ?? ''} onChange={(e) => onChange(e.target.value)} disabled={disabled}>
      {blank && <option value="">— seleccione —</option>}
      {options.map((o) => <option key={String(optVal(o))} value={optVal(o)}>{optLab(o)}</option>)}
    </select>
  </Field>
);
export const Datalist = ({ id, options }: { id: string; options: Opt[] }) => <datalist id={id}>{options.map((o) => <option key={String(optVal(o))} value={optVal(o)}>{optLab(o)}</option>)}</datalist>;

// ───────── Tablas ─────────
export interface Col<T> { key: string; header: string; num?: boolean; ctr?: boolean; money?: boolean; date?: boolean; badge?: boolean; render?: (row: T, i: number) => ReactNode; width?: number | string }
export function DataTable<T extends Record<string, any>>({ cols, rows, onRow, selected, empty, foot, maxHeight, rowKey }: { cols: Col<T>[]; rows: T[]; onRow?: (r: T) => void; selected?: (r: T) => boolean; empty?: string; foot?: ReactNode; maxHeight?: string | number; rowKey?: (r: T, i: number) => string | number }) {
  return (
    <div className="table-wrap" style={maxHeight ? { maxHeight } : undefined}>
      <table className="t">
        <thead><tr>{cols.map((c) => <th key={c.key} className={c.num ? 'num' : ''} style={c.width ? { width: c.width } : undefined}>{c.header}</th>)}</tr></thead>
        <tbody>
          {rows.length === 0 && <tr><td colSpan={cols.length} className="empty">{empty ?? 'Sin registros'}</td></tr>}
          {rows.map((r, i) => (
            <tr key={rowKey ? rowKey(r, i) : i} className={(onRow ? 'click ' : '') + (selected?.(r) ? 'sel' : '')} onClick={() => onRow?.(r)}>
              {cols.map((c) => {
                const v = r[c.key];
                const cell = c.render ? c.render(r, i) : c.badge ? <Badge v={v} /> : c.money ? fmt2(v) : c.date ? fmtDate(v) : c.num ? fmtN(v) : v;
                return <td key={c.key} className={(c.num || c.money ? 'num ' : '') + (c.ctr ? 'ctr' : '')}>{cell as ReactNode}</td>;
              })}
            </tr>
          ))}
        </tbody>
        {foot && <tfoot>{foot}</tfoot>}
      </table>
    </div>
  );
}

/** Grilla editable de ítems (líneas de documento). */
export interface GridCol<R> { key: keyof R & string; header: string; type?: 'text' | 'number' | 'date' | 'select' | 'readonly'; options?: Opt[]; list?: string; width?: number | string; num?: boolean; money?: boolean; placeholder?: string }
export function ItemsGrid<R extends Record<string, any>>({ cols, rows, onChange, vacio, disabled, max }: { cols: GridCol<R>[]; rows: R[]; onChange: (rows: R[]) => void; vacio: () => R; disabled?: boolean; max?: number }) {
  const set = (i: number, k: string, v: any) => onChange(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  return (
    <div>
      <div className="table-wrap" style={{ maxHeight: '50vh' }}>
        <table className="t">
          <thead><tr><th style={{ width: 34 }}>#</th>{cols.map((c) => <th key={c.key} className={c.num ? 'num' : ''} style={c.width ? { width: c.width } : undefined}>{c.header}</th>)}<th style={{ width: 34 }} /></tr></thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td className="ctr muted">{i + 1}</td>
                {cols.map((c) => (
                  <td key={c.key} className={c.num ? 'num' : ''}>
                    {c.type === 'readonly' || disabled ? <span>{c.money ? fmt2(r[c.key]) : c.num ? fmtN(r[c.key]) : String(r[c.key] ?? '')}</span>
                      : c.type === 'select' ? <select value={r[c.key] ?? ''} onChange={(e) => set(i, c.key, e.target.value)}><option value="" />{(c.options ?? []).map((o) => <option key={String(optVal(o))} value={optVal(o)}>{optLab(o)}</option>)}</select>
                      : <input type={c.type === 'number' ? 'number' : c.type === 'date' ? 'date' : 'text'} step="any" list={c.list} placeholder={c.placeholder} value={r[c.key] ?? ''} onChange={(e) => set(i, c.key, c.type === 'number' ? (e.target.value === '' ? '' : Number(e.target.value)) : e.target.value)} />}
                  </td>
                ))}
                <td>{!disabled && <button className="sm danger" title="Quitar" onClick={() => onChange(rows.filter((_, j) => j !== i))}>×</button>}</td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={cols.length + 2} className="empty">Agregue líneas con «+ Agregar línea»</td></tr>}
          </tbody>
        </table>
      </div>
      {!disabled && (!max || rows.length < max) && <div style={{ marginTop: 6 }}><button className="sm" onClick={() => onChange([...rows, vacio()])}>+ Agregar línea</button></div>}
    </div>
  );
}

export const money = fmt2;
export const numf = fmtN;
export const Mono = ({ children }: { children: ReactNode }) => <span style={{ fontFamily: 'ui-monospace, Consolas, monospace' }}>{children}</span>;
export const Loading = ({ on }: { on: boolean }) => (on ? <div className="muted" style={{ padding: 8 }}>Cargando…</div> : null);
