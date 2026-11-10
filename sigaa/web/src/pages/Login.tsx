import { useState } from 'react';
import { useAuth } from '../auth';
import { Field, useAction } from '../ui';

export default function Login() {
  const { login } = useAuth();
  const [u, setU] = useState('');
  const [c, setC] = useState('');
  const [run, busy] = useAction();
  return (
    <div className="login">
      <form className="box" onSubmit={(e) => { e.preventDefault(); run(() => login(u, c)); }}>
        <img className="logo-jb" src="/logo-jb.jpg" alt="JB · Jaime Blanco, Consultor Administrativo Financiero" />
        <h1>SIGAA</h1>
        <p>Sistema Integrado de Gestión de Almacenes, Combustible y Activos Fijos</p>
        <div className="grid" style={{ gridTemplateColumns: '1fr' }}>
          <Field label="Usuario"><input value={u} onChange={(e) => setU(e.target.value)} autoFocus autoComplete="username" /></Field>
          <Field label="Clave"><input type="password" value={c} onChange={(e) => setC(e.target.value)} autoComplete="current-password" /></Field>
        </div>
        <div style={{ marginTop: 16 }}><button className="primary" style={{ width: '100%', justifyContent: 'center' }} disabled={busy || !u || !c}>Ingresar</button></div>
      </form>
    </div>
  );
}
