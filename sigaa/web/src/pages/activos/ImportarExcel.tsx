import { useRef, useState } from 'react';
import { ApiError, bajarArchivo, fmt2, get, getToken, subirArchivo, subirFoto, XLSX_TIPO } from '../../api';
import { useAuth } from '../../auth';
import { Card, DataTable, PageHead, useAction, useLoad } from '../../ui';

interface Resultado { importado: boolean; total: number; creados: { fila: number; codigo: string; fotos: { n: number; archivo: string }[] }[]; errores: { fila: number; mensaje: string }[]; fotosEsperadas: string[] }

/** Importación de activos fijos desde Excel, con una carpeta aparte para las fotografías (columnas foto1, foto2, foto3). */
export default function AfImportarExcel() {
  const { puede } = useAuth();
  const [run, busy] = useAction();
  const { data: est } = useLoad<any>(() => get('/af/importar/estructura'));
  const [excel, setExcel] = useState<File>();
  const [fotos, setFotos] = useState<Map<string, File>>(new Map());
  const [res, setRes] = useState<Resultado>();
  const [subida, setSubida] = useState<{ ok: number; falla: { archivo: string; motivo: string }[]; total: number } | null>(null);
  const refX = useRef<HTMLInputElement>(null);
  const refF = useRef<HTMLInputElement>(null);

  const elegirCarpeta = (lista: FileList | null) => {
    const m = new Map<string, File>();
    for (const f of Array.from(lista ?? [])) m.set(f.name.toLowerCase(), f);
    setFotos(m); setRes(undefined); setSubida(null);
  };
  const faltantes = (res?.fotosEsperadas ?? []).filter((n) => !fotos.has(n.toLowerCase()));
  const enviar = async (confirmar: boolean) => {
    if (!excel) return;
    const r = await subirArchivo<Resultado>(`/af/importar?confirmar=${confirmar ? 1 : 0}`, excel, XLSX_TIPO);
    setRes(r); setSubida(null);
    if (r.importado) {
      const trabajos = r.creados.flatMap((c) => c.fotos.map((f) => ({ codigo: c.codigo, ...f })));
      let ok = 0; const falla: { archivo: string; motivo: string }[] = [];
      for (const t of trabajos) {
        const file = fotos.get(t.archivo.toLowerCase());
        if (!file) { falla.push({ archivo: t.archivo, motivo: 'No está en la carpeta elegida' }); continue; }
        try { await subirFoto(t.codigo, t.n, file); ok++; } catch (e) { falla.push({ archivo: t.archivo, motivo: e instanceof ApiError ? e.message : String(e) }); }
        setSubida({ ok, falla: [...falla], total: trabajos.length });
      }
      setSubida({ ok, falla, total: trabajos.length });
    }
  };
  void getToken; void fmt2;
  return (
    <>
      <PageHead title="Importar activos desde Excel" sub="Cargue un inventario existente: un libro de Excel con los datos y una carpeta aparte con las fotografías" />
      <Card title="1. Estructura del Excel" right={<button onClick={() => run(() => bajarArchivo('/af/importar/plantilla', 'plantilla_activos_fijos.xlsx'))}>Descargar plantilla de Excel</button>}>
        <p className="muted">La fila 1 son los encabezados (no los cambie); desde la fila 2, un activo por fila. Naranja = obligatorio, verde = fotos. La plantilla trae además la hoja CATALOGOS con los valores válidos.</p>
        <DataTable maxHeight="38vh" rows={est?.columnas ?? []} cols={[{ key: 'encabezado', header: 'Columna' }, { key: 'obligatorio', header: 'Oblig.', render: (r) => (r.obligatorio ? 'Sí' : 'No') }, { key: 'tipo', header: 'Qué escribir' }, { key: 'ejemplo', header: 'Ejemplo' }]} />
        <ul style={{ margin: '8px 0 0 18px' }}>{(est?.reglas ?? []).map((r: string) => <li key={r}>{r}</li>)}</ul>
      </Card>
      {puede('af') && (
        <Card title="2. Elija los archivos">
          <div className="row">
            <button onClick={() => refX.current?.click()}>{excel ? `Excel: ${excel.name}` : 'Seleccionar Excel…'}</button>
            <input ref={refX} type="file" accept=".xlsx" hidden onChange={(e) => { setExcel(e.target.files?.[0]); setRes(undefined); setSubida(null); e.target.value = ''; }} />
            <button onClick={() => refF.current?.click()}>{fotos.size ? `Carpeta de fotos: ${fotos.size} archivo(s)` : 'Seleccionar carpeta de fotos…'}</button>
            <input ref={refF} type="file" multiple hidden {...({ webkitdirectory: '', directory: '' } as any)} onChange={(e) => { elegirCarpeta(e.target.files); e.target.value = ''; }} />
          </div>
          <p className="muted">Las fotos son opcionales. Si el Excel nombra fotos, deben estar en la carpeta elegida (JPG, PNG o WEBP, hasta 8 MB cada una).</p>
          <div className="row" style={{ marginTop: 8 }}>
            <button className="primary" disabled={busy || !excel} onClick={() => run(() => enviar(false))}>Validar (no guarda nada)</button>
            <button className="ok" disabled={busy || !excel || !res || res.errores.length > 0 || res.importado} onClick={() => run(() => enviar(true))}>Importar</button>
          </div>
        </Card>
      )}
      {res && (
        <Card title="3. Resultado">
          {res.errores.length > 0 ? (
            <>
              <p className="warn">⚠ No se importó nada: corrija estas filas del Excel y vuelva a validar.</p>
              <DataTable maxHeight="30vh" rows={res.errores} cols={[{ key: 'fila', header: 'Fila', num: true }, { key: 'mensaje', header: 'Problema' }]} />
            </>
          ) : res.importado ? (
            <p className="ok-txt">✔ Se importaron <b>{res.creados.length}</b> activo(s).</p>
          ) : (
            <p className="ok-txt">✔ El Excel está correcto: {res.total} activo(s) listos para importar. Pulse <b>Importar</b>.</p>
          )}
          {res.fotosEsperadas.length > 0 && res.errores.length === 0 && (
            <p className={faltantes.length ? 'warn' : 'ok-txt'}>{faltantes.length ? `⚠ Faltan ${faltantes.length} foto(s) en la carpeta elegida: ${faltantes.slice(0, 8).join(', ')}${faltantes.length > 8 ? '…' : ''}` : `✔ Las ${res.fotosEsperadas.length} foto(s) nombradas están en la carpeta.`}</p>
          )}
          {!res.importado && res.errores.length === 0 && <DataTable maxHeight="30vh" rows={res.creados} cols={[{ key: 'fila', header: 'Fila', num: true }, { key: 'codigo', header: 'Código que tendrá' }, { key: 'f', header: 'Fotos', render: (r) => r.fotos.map((f) => f.archivo).join(', ') }]} />}
          {subida && (
            <p className={subida.falla.length ? 'warn' : 'ok-txt'}>
              Fotografías: {subida.ok} de {subida.total} subidas{subida.falla.length ? `; ${subida.falla.length} con problema: ${subida.falla.slice(0, 5).map((f) => `${f.archivo} (${f.motivo})`).join('; ')}` : ''}.
            </p>
          )}
        </Card>
      )}
    </>
  );
}
