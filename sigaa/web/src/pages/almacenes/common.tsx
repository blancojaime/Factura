import { useMemo } from 'react';
import { get } from '../../api';
import { Datalist, useLoad } from '../../ui';

export interface AlmMeta {
  bodegas: { cod: string; nombre: string }[];
  grupos: { grupo: number; nombre: string }[];
  subgrupos: { grupo: number; subgrupo: number; nombre: string }[];
  unidades_medida: string[];
  partidas: { partida: string; descripcion: string }[];
  causales: { causal: string; grupo: string }[];
  tipos_ingreso: string[];
  tipos_inventario: string[];
  tipos_requerimiento: string[];
  estados_bien: string[];
  criterios_inspeccion: string[];
  config: Record<string, string>;
}
export const useAlmMeta = () => useLoad<AlmMeta>(() => get('/alm/meta'));

/** Ítems del catálogo para selección con búsqueda (datalist "código - descripción"). */
export function useItems(bod?: string) {
  const { data } = useLoad<any[]>(() => get('/alm/catalogo', { estado: 'ACTIVO' }));
  const items = useMemo(() => (data ?? []).filter((i) => !bod || i.cod_bod === bod), [data, bod]);
  const list = useMemo(() => items.map((i) => `${i.codigo} - ${i.descripcion}`), [items]);
  const porCodigo = useMemo(() => new Map(items.map((i) => [i.codigo, i])), [items]);
  return { items, list, porCodigo, listId: 'items-' + (bod || 'all'), Lista: () => <Datalist id={'items-' + (bod || 'all')} options={list} /> };
}
export const codeOf = (s: string) => String(s ?? '').split(' - ')[0].trim();
export const nroUrl = (n: string) => encodeURIComponent(n);
