'use client';
import { Landmark } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Field, Input } from '@/components/ui/form';
import { api } from '@/lib/api';

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(false);

  async function entrar(e: React.FormEvent) {
    e.preventDefault();
    setCargando(true); setError('');
    try { await api('/auth/login', { body: { email, password } }); router.replace('/procesos'); }
    catch (err) { setError((err as Error).message); }
    finally { setCargando(false); }
  }
  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center text-center">
          <Landmark className="h-9 w-9 text-primary" />
          <CardTitle className="text-xl">SABSMUNI-ANPE</CardTitle>
          <CardDescription>Contrataciones estatales · modalidad ANPE</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={entrar} className="flex flex-col gap-3">
            <Field label="Correo institucional"><Input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
            <Field label="Contraseña"><Input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
            {error && <Alert tipo="error">{error}</Alert>}
            <Button type="submit" disabled={cargando}>{cargando ? 'Ingresando…' : 'Ingresar'}</Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
