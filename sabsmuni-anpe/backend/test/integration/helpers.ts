import { Test } from '@nestjs/testing';
import { NestExpressApplication } from '@nestjs/platform-express';
import { execSync } from 'child_process';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import request from 'supertest';
import TestAgent from 'supertest/lib/agent';
import { AppModule } from '../../src/app.module';
import { configurar } from '../../src/main';

export const hayBaseDeDatos = !!process.env.DATABASE_URL;
export const PASSWORD = 'Anpe2026Demo';

export async function arrancar() {
  process.env.STORAGE_DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'anpe-storage-'));
  process.env.PUBLIC_URL = 'http://localhost:3000';
  execSync('npx prisma migrate deploy', { stdio: 'pipe', env: process.env });
  execSync('npx ts-node src/seed.ts', { stdio: 'pipe', env: { ...process.env, NODE_ENV: 'development' } });
  const mod = await Test.createTestingModule({ imports: [AppModule] }).compile();
  const app = mod.createNestApplication<NestExpressApplication>();
  await configurar(app);
  await app.init();
  return app;
}

export type Agente = TestAgent;
export async function sesion(app: NestExpressApplication, email: string): Promise<Agente> {
  const a = request.agent(app.getHttpServer());
  const r = await a.post('/api/auth/login').send({ email, password: PASSWORD });
  if (r.status !== 200) throw new Error(`Login falló para ${email}: ${r.status} ${JSON.stringify(r.body)}`);
  return a;
}

export interface Actores { us: Agente; rp: Agente; rc: Agente; rpa: Agente; admin: Agente }
export async function actores(app: NestExpressApplication): Promise<Actores> {
  return {
    us: await sesion(app, 'solicitante@gam.bo'), rp: await sesion(app, 'presupuesto@gam.bo'), rc: await sesion(app, 'contrataciones@gam.bo'),
    rpa: await sesion(app, 'rpa@gam.bo'), admin: await sesion(app, 'admin@gam.bo'),
  };
}

export const ok = <T extends { status: number; body: unknown }>(r: T, esperado = [200, 201]): T => {
  if (!esperado.includes(r.status)) throw new Error(`HTTP ${r.status}: ${JSON.stringify(r.body)}`);
  return r;
};
export const paso = async (a: Agente, id: string, hacia: string, extra: object = {}) => a.post(`/api/procesos/${id}/transicion`).send({ hacia, ...extra });
