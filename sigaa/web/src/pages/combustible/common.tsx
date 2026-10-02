import { get } from '../../api';
import { useLoad } from '../../ui';

export interface ComMeta {
  vehiculos: any[]; conductores: any[]; puestos: any[]; contratos: any[]; aperturas: any[]; unidades: any[]; proveedores: any[]; precios: any[]; cortes: number[]; config: Record<string, string>;
}
export const useComMeta = () => useLoad<ComMeta>(() => get('/com/meta'));
export const nroUrl = (n: string) => encodeURIComponent(n);
