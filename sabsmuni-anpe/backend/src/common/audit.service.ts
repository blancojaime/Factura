import { Injectable } from '@nestjs/common';
import { PrismaService } from './prisma.service';
import { Ctx } from './auth';
import { GENESIS, hashRegistroAuditoria, verificarCadena } from '../domain/integridad';

export interface EventoAuditoria {
  ctx?: Pick<Ctx, 'userId' | 'email' | 'ip'> | { userId?: string; email?: string; ip?: string };
  accion: string;
  entidad: string;
  entidadId?: string;
  previo?: unknown;
  posterior?: unknown;
}

const json = <T>(v: T): T | null => (v === undefined ? null : (JSON.parse(JSON.stringify(v)) as T));

/** Payload que se sella en la cadena (reproducible al verificar). */
const payload = (r: { fecha: Date; usuarioId: string | null; ip: string | null; accion: string; entidad: string; entidadId: string | null; estadoPrevio: unknown; estadoPosterior: unknown }) => ({
  fecha: r.fecha.toISOString(), usuarioId: r.usuarioId, ip: r.ip, accion: r.accion, entidad: r.entidad, entidadId: r.entidadId, estadoPrevio: r.estadoPrevio ?? null, estadoPosterior: r.estadoPosterior ?? null,
});

@Injectable()
export class AuditService {
  constructor(private readonly prisma: PrismaService) {}

  async registrar(e: EventoAuditoria): Promise<void> {
    await this.prisma.$transaction(async (tx) => {
      await tx.$executeRaw`SELECT pg_advisory_xact_lock(7001)`; // serializa la cadena
      const ultimo = await tx.logAuditoria.findFirst({ orderBy: { id: 'desc' }, select: { hash: true } });
      const hashPrevio = ultimo?.hash ?? GENESIS;
      const fila = {
        fecha: new Date(), usuarioId: e.ctx?.userId ?? null, ip: e.ctx?.ip ?? null, accion: e.accion, entidad: e.entidad, entidadId: e.entidadId ?? null,
        estadoPrevio: json(e.previo), estadoPosterior: json(e.posterior),
      };
      await tx.logAuditoria.create({
        data: { ...fila, usuarioEmail: e.ctx?.email ?? null, estadoPrevio: fila.estadoPrevio ?? undefined, estadoPosterior: fila.estadoPosterior ?? undefined, hashPrevio, hash: hashRegistroAuditoria(hashPrevio, payload(fila)) },
      });
    });
  }

  async consultar(filtro: { entidad?: string; entidadId?: string; limite?: number }) {
    const filas = await this.prisma.logAuditoria.findMany({ where: { entidad: filtro.entidad, entidadId: filtro.entidadId }, orderBy: { id: 'desc' }, take: Math.min(filtro.limite ?? 100, 500) });
    return filas.map((f) => ({ ...f, id: f.id.toString() }));
  }

  async verificarIntegridad() {
    const filas = await this.prisma.logAuditoria.findMany({ orderBy: { id: 'asc' } });
    const r = verificarCadena(filas, (f) => payload(f));
    return { registros: filas.length, ...r, falloEnId: r.falloEn === null ? null : filas[r.falloEn].id.toString() };
  }
}
