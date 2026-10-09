"use client";

import { FileText } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { Alert, Button, Card, CardBody, Field, Input } from "@/components/ui";
import { mensajeError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { user, cargando, entrar } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    if (!cargando && user) router.replace("/");
  }, [cargando, user, router]);

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setError("");
    setEnviando(true);
    try {
      await entrar(username.trim(), password);
      router.replace("/");
    } catch (err) {
      setError(mensajeError(err));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-b from-brand-700 to-brand-900 p-4">
      <div className="w-full max-w-sm space-y-4">
        <div className="text-center text-white">
          <FileText className="mx-auto h-10 w-10" aria-hidden />
          <h1 className="mt-2 text-2xl font-bold">SICOM-MUNI</h1>
          <p className="text-sm text-brand-100">Sistema Integrado de Contratación Menor Municipal</p>
        </div>
        <Card>
          <CardBody>
            <form onSubmit={enviar} className="space-y-4" aria-label="Inicio de sesión">
              <Field label="Usuario">
                <Input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required autoFocus />
              </Field>
              <Field label="Contraseña">
                <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
              </Field>
              {error && <Alert tipo="error">{error}</Alert>}
              <Button type="submit" cargando={enviando} className="w-full">Ingresar</Button>
            </form>
          </CardBody>
        </Card>
        <p className="text-center text-xs text-brand-100">Acceso restringido a personal autorizado. Las acciones se auditan.</p>
      </div>
    </main>
  );
}
