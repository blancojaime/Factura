import { useRef, useState } from 'react';
import { bajarArchivo, get, subirArchivo, XLSX_TIPO } from './api';
import { DataTable, Modal, useAction, useLoad } from './ui';

interface Estructura { titulo: string; claveUnica: string[]; columnas: { encabezado: string; obligatorio: boolean; tipo: string; ejemplo: string | number }[]; reglas: string[] }

/** Ventana de importación desde Excel: muestra la estructura, descarga la plantilla y carga el archivo. */
export default function ImportarExcel({ base, titulo, onClose, onDone }: { base: string; titulo: string; onClose: () => void; onDone: () => void }) {
  const { data: est } = useLoad<Estructura>(() => get(`${base}/estructura`), [base]);
  const [run, busy] = useAction();
  const [res, setRes] = useState<any>();
  const ref = useRef<HTMLInputElement>(null);
  const subir = (f?: File) => f && run(async () => {
    const r = await subirArchivo(base, f, XLSX_TIPO);
    setRes(r);
    if (r.importado) onDone();
  });
  return (
    <Modal wide title={`Importar desde Excel — ${titulo}`} onClose={onClose} footer={<button onClick={onClose}>Cerrar</button>}>
      <p className="muted">Estructura del libro de Excel (la <b>fila 1</b> son los encabezados; los datos empiezan en la fila 2):</p>
      <DataTable rows={est?.columnas ?? []} cols={[{ key: 'encabezado', header: 'Encabezado (columna)' }, { key: 'obligatorio', header: 'Obligatorio', render: (r) => (r.obligatorio ? 'Sí' : 'No') }, { key: 'tipo', header: 'Tipo de dato' }, { key: 'ejemplo', header: 'Ejemplo' }]} />
      <ul style={{ margin: '8px 0 10px 18px' }}>{(est?.reglas ?? []).map((r) => <li key={r}>{r}</li>)}</ul>
      <div className="row">
        <button onClick={() => run(() => bajarArchivo(`${base}/plantilla`, `plantilla.xlsx`))}>Descargar plantilla de Excel</button>
        <button className="primary" disabled={busy} onClick={() => ref.current?.click()}>Seleccionar Excel e importar…</button>
        <input ref={ref} type="file" accept=".xlsx" hidden onChange={(e) => { subir(e.target.files?.[0]); e.target.value = ''; }} />
      </div>
      {res && (res.importado
        ? <p className="ok-txt" style={{ marginTop: 10 }}>✔ Importación realizada: {res.creados} creado(s) y {res.actualizados} actualizado(s).</p>
        : <div style={{ marginTop: 10 }}><p className="warn">⚠ No se importó nada: corrija estas filas del Excel y vuelva a cargarlo.</p>
            <DataTable maxHeight="25vh" rows={res.errores} cols={[{ key: 'fila', header: 'Fila', num: true }, { key: 'mensaje', header: 'Problema' }]} /></div>)}
    </Modal>
  );
}
