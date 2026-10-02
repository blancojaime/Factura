import { useEffect, useState } from 'react';
import { NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { useAuth } from './auth';
import { useAction, useUi, Field } from './ui';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Catalogos from './pages/Catalogos';
import Reportes from './pages/Reportes';
import Admin from './pages/Admin';
import { AlmCatalogo, AlmExistencias, AlmIngresos, AlmSalidas, AlmInventarios, AlmBajas, AlmTransferencias, AlmReposicion, AlmSeguridad, AlmCierre } from './pages/almacenes';
import { ComTablero, ComRecepcion, ComEmitir, ComDescargo, ComMovimientos, ComTurriles, ComViajes, ComConciliacion, ComCronograma, ComVales } from './pages/combustible';
import { AfIngresos, AfCodificar, AfFichas, AfSolicitudes, AfAsignar, AfMovimientos, AfEtiquetas, AfConsulta } from './pages/activos';

const NAV: { grupo: string; mod?: string; items: [string, string][] }[] = [
  { grupo: 'General', items: [['/', 'Tablero general']] },
  { grupo: 'Almacenes', mod: 'alm', items: [['/almacenes/catalogo', 'Catálogo de ítems'], ['/almacenes/existencias', 'Existencias y kardex'], ['/almacenes/ingresos', 'Ingresos (CGI)'], ['/almacenes/salidas', 'Salidas (vales)'], ['/almacenes/inventarios', 'Inventario físico'], ['/almacenes/bajas', 'Bajas'], ['/almacenes/transferencias', 'Transferencias'], ['/almacenes/reposicion', 'Reposición'], ['/almacenes/seguridad', 'Seguridad e higiene'], ['/almacenes/cierre', 'Cierre de gestión']] },
  { grupo: 'Combustible', mod: 'com', items: [['/combustible/tablero', 'Tablero de control'], ['/combustible/recepcion', 'Recepción de vales'], ['/combustible/emitir', 'Emitir vales'], ['/combustible/descargo', 'Descargo de vales'], ['/combustible/movimientos', 'Devolución / baja de vales'], ['/combustible/turriles', 'Turriles'], ['/combustible/viajes', 'Viajes y fondos en avance'], ['/combustible/conciliacion', 'Conciliación'], ['/combustible/cronograma', 'Cronograma'], ['/combustible/vales', 'Registro de vales']] },
  { grupo: 'Activos fijos', mod: 'af', items: [['/activos/ingresos', 'Ingreso a almacén'], ['/activos/codificar', 'Codificación'], ['/activos/fichas', 'Fichas técnicas'], ['/activos/solicitudes', 'Solicitudes'], ['/activos/asignar', 'Asignación y entrega'], ['/activos/movimientos', 'Devolución / transferencia / baja'], ['/activos/etiquetas', 'Etiquetas (stickers)'], ['/activos/consulta', 'Consulta y kardex']] },
  { grupo: 'Información', items: [['/reportes', 'Reportes y documentos']] },
  { grupo: 'Administración', items: [['/catalogos', 'Catálogos y bases de datos'], ['/admin', 'Configuración y usuarios']] },
];

function CambiarClave() {
  const { cambiarClave, logout, usuario } = useAuth();
  const [run, busy] = useAction();
  const [a, setA] = useState('');
  const [n, setN] = useState('');
  const [n2, setN2] = useState('');
  const ui = useUi();
  return (
    <div className="login"><div className="box">
      <h1>Cambie su clave</h1><p>{usuario?.nombre ? `${usuario.nombre}: ` : ''}por seguridad debe definir una clave personal (mínimo 8 caracteres, con letras y números).</p>
      <div className="grid" style={{ gridTemplateColumns: '1fr' }}>
        <Field label="Clave actual"><input type="password" value={a} onChange={(e) => setA(e.target.value)} autoFocus /></Field>
        <Field label="Clave nueva"><input type="password" value={n} onChange={(e) => setN(e.target.value)} /></Field>
        <Field label="Repita la clave nueva"><input type="password" value={n2} onChange={(e) => setN2(e.target.value)} /></Field>
      </div>
      <div className="row" style={{ marginTop: 14, justifyContent: 'space-between' }}>
        <button onClick={logout}>Salir</button>
        <button className="primary" disabled={busy} onClick={() => (n !== n2 ? ui.error('Las claves nuevas no coinciden.') : run(() => cambiarClave(a, n), 'Clave actualizada.'))}>Guardar clave</button>
      </div>
    </div></div>
  );
}

function Shell() {
  const { usuario, logout, gestion, puede } = useAuth();
  const [open, setOpen] = useState(false);
  const [tema, setTema] = useState(() => localStorage.getItem('sigaa.tema') || '');
  const loc = useLocation();
  useEffect(() => setOpen(false), [loc.pathname]);
  useEffect(() => {
    if (tema) document.documentElement.setAttribute('data-theme', tema);
    else document.documentElement.removeAttribute('data-theme');
    localStorage.setItem('sigaa.tema', tema);
  }, [tema]);
  return (
    <div className="app">
      <aside className={'side' + (open ? ' open' : '')}>
        <div className="brand"><svg width="34" height="34" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#2d5a94" /><path d="M14 24l18-10 18 10v18L32 52 14 42z" fill="none" stroke="#fff" strokeWidth="4" strokeLinejoin="round" /><path d="M14 24l18 10 18-10M32 34v18" fill="none" stroke="#9fc6f5" strokeWidth="4" strokeLinejoin="round" /></svg><div><b>SIGAA</b><small>Almacenes · Combustible<br />Activos Fijos</small></div></div>
        {NAV.map((g) => (
          <div key={g.grupo}>
            <h4>{g.grupo}{g.mod && !puede(g.mod as any) ? ' (solo lectura)' : ''}</h4>
            {g.items.map(([to, label]) => <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => (isActive ? 'active' : '')}>{label}</NavLink>)}
          </div>
        ))}
      </aside>
      <div className="main">
        <header className="top no-print">
          <button className="menu-btn" onClick={() => setOpen(!open)} aria-label="Menú">☰</button>
          <div className="muted">Gestión <b>{gestion}</b></div>
          <div className="who">
            <button className="sm" onClick={() => setTema(tema === 'dark' ? 'light' : 'dark')} title="Cambiar tema">{tema === 'dark' ? '☀' : '☾'}</button>
            <span>{usuario?.nombre} · <small>{usuario?.roles.join(', ')}</small></span>
            <button className="sm" onClick={logout}>Salir</button>
          </div>
        </header>
        <main className="content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/almacenes/catalogo" element={<AlmCatalogo />} />
            <Route path="/almacenes/existencias" element={<AlmExistencias />} />
            <Route path="/almacenes/ingresos" element={<AlmIngresos />} />
            <Route path="/almacenes/salidas" element={<AlmSalidas />} />
            <Route path="/almacenes/inventarios" element={<AlmInventarios />} />
            <Route path="/almacenes/bajas" element={<AlmBajas />} />
            <Route path="/almacenes/transferencias" element={<AlmTransferencias />} />
            <Route path="/almacenes/reposicion" element={<AlmReposicion />} />
            <Route path="/almacenes/seguridad" element={<AlmSeguridad />} />
            <Route path="/almacenes/cierre" element={<AlmCierre />} />
            <Route path="/combustible/tablero" element={<ComTablero />} />
            <Route path="/combustible/recepcion" element={<ComRecepcion />} />
            <Route path="/combustible/emitir" element={<ComEmitir />} />
            <Route path="/combustible/descargo" element={<ComDescargo />} />
            <Route path="/combustible/movimientos" element={<ComMovimientos />} />
            <Route path="/combustible/turriles" element={<ComTurriles />} />
            <Route path="/combustible/viajes" element={<ComViajes />} />
            <Route path="/combustible/conciliacion" element={<ComConciliacion />} />
            <Route path="/combustible/cronograma" element={<ComCronograma />} />
            <Route path="/combustible/vales" element={<ComVales />} />
            <Route path="/activos/ingresos" element={<AfIngresos />} />
            <Route path="/activos/codificar" element={<AfCodificar />} />
            <Route path="/activos/fichas" element={<AfFichas />} />
            <Route path="/activos/solicitudes" element={<AfSolicitudes />} />
            <Route path="/activos/asignar" element={<AfAsignar />} />
            <Route path="/activos/movimientos" element={<AfMovimientos />} />
            <Route path="/activos/etiquetas" element={<AfEtiquetas />} />
            <Route path="/activos/consulta" element={<AfConsulta />} />
            <Route path="/reportes" element={<Reportes />} />
            <Route path="/catalogos" element={<Catalogos />} />
            <Route path="/admin" element={<Admin />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  const { usuario, cargando, debeCambiar } = useAuth();
  if (cargando) return <div className="login"><div className="box">Cargando…</div></div>;
  if (debeCambiar) return <CambiarClave />;
  if (!usuario) return <Login />;
  return <Shell />;
}
