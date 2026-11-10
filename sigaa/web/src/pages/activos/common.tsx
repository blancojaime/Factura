import { get } from '../../api';
import { useLoad } from '../../ui';

export interface AfMeta {
  cuentas: any[]; auxiliares: any[]; edificios: any[]; ambientes: any[]; estados: any[]; funcionarios: any[]; unidades: any[]; proveedores: any[]; tipos_ingreso: string[]; config: Record<string, string>;
}
export const useAfMeta = () => useLoad<AfMeta>(() => get('/af/meta'));
export const nroUrl = (n: string) => encodeURIComponent(n);
export const optsCta = (m?: AfMeta) => (m?.cuentas ?? []).map((c) => ({ value: c.id_cta, label: `${String(c.id_cta).padStart(2, '0')} - ${c.cuenta}` }));
export const optsAux = (m: AfMeta | undefined, cta?: number | string) => (m?.auxiliares ?? []).filter((a) => !cta || a.id_cta === Number(cta)).map((a) => ({ value: a.id_aux, label: `${String(a.id_aux).padStart(3, '0')} - ${a.auxiliar}` }));
export const optsEdif = (m?: AfMeta) => (m?.edificios ?? []).map((e) => ({ value: e.cod_edif, label: `${String(e.cod_edif).padStart(3, '0')} - ${e.edificio}` }));
export const optsAmb = (m: AfMeta | undefined, edif?: number | string) => (m?.ambientes ?? []).filter((a) => a.cod_edif === Number(edif)).map((a) => ({ value: a.cod_amb, label: `${String(a.cod_amb).padStart(2, '0')} - ${a.ambiente}` }));
