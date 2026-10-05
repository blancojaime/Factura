import { Injectable } from '@nestjs/common';
import { Ctx } from '../../common/auth';
import { AuditService } from '../../common/audit.service';
import { PrismaService } from '../../common/prisma.service';
import { ProcesoCompleto, ProcesoRepo } from '../../common/proceso.repo';
import { analizarEspecificacion, Hallazgo, MARCAS_BASE, SECCIONES_REQUERIMIENTO, verificarCompletitud } from '../../domain/especificaciones';
import { validarItemChb, ValidacionChb } from '../../domain/chb';
import { DocumentosService } from '../documentos/documentos.service';

export interface InformeRequerimiento {
  valido: boolean;
  completitud: { completo: boolean; faltantes: string[] };
  hallazgos: (Hallazgo & { origen: string })[];
  chb: { itemId: string; numero: number; codigoUnspsc: string; validacion: ValidacionChb }[];
  requiereJustificacionChb: boolean;
}

@Injectable()
export class RequerimientoService {
  constructor(private readonly prisma: PrismaService, private readonly repo: ProcesoRepo, private readonly audit: AuditService, private readonly docs: DocumentosService) {}

  private async marcas(): Promise<string[]> {
    const extra = await this.prisma.marcaRegistrada.findMany();
    return [...new Set([...MARCAS_BASE, ...extra.map((m) => m.nombre.toLowerCase())])];
  }

  async analizarTexto(texto: string) {
    return analizarEspecificacion(texto, await this.marcas());
  }

  async guardarSecciones(id: string, secciones: Record<string, string>, ctx: Ctx) {
    const p = await this.repo.obtener(id);
    this.repo.exigirEstado(p, ['BORRADOR'], 'editar el requerimiento');
    const claves = new Set(SECCIONES_REQUERIMIENTO[p.tipoObjeto].map((s) => s.clave));
    const limpio = Object.fromEntries(Object.entries(secciones).filter(([k]) => claves.has(k)).map(([k, v]) => [k, String(v).slice(0, 8000)]));
    await this.prisma.procesoAnpe.update({ where: { id }, data: { requerimiento: limpio } });
    await this.audit.registrar({ ctx, accion: 'REQUERIMIENTO_GUARDADO', entidad: 'proceso', entidadId: id, previo: p.requerimiento, posterior: limpio });
    return limpio;
  }

  /** Cálculo puro (sin persistir) usado también como precondición del flujo. */
  async evaluar(p: ProcesoCompleto): Promise<InformeRequerimiento> {
    const marcas = await this.marcas();
    const catalogo = (await this.prisma.catalogoChb.findMany()).map((c) => ({ id: c.id, codigoUnspsc: c.codigoUnspsc, descripcion: c.descripcion, productor: c.productor, vigente: c.vigente }));
    const hallazgos: InformeRequerimiento['hallazgos'] = [];
    const req = (p.requerimiento ?? {}) as Record<string, string>;
    for (const s of SECCIONES_REQUERIMIENTO[p.tipoObjeto]) {
      if (req[s.clave]) analizarEspecificacion(req[s.clave], marcas).hallazgos.forEach((h) => hallazgos.push({ ...h, origen: s.titulo }));
    }
    for (const i of p.items) analizarEspecificacion(i.descripcionTecnica, marcas).hallazgos.forEach((h) => hallazgos.push({ ...h, origen: `Ítem ${i.numero}` }));
    const chb = p.items.map((i) => ({ itemId: i.id, numero: i.numero, codigoUnspsc: i.codigoUnspsc, validacion: validarItemChb(p.tipoObjeto, { codigoUnspsc: i.codigoUnspsc, descripcion: i.descripcionTecnica, incompatibilidadTecnica: i.incompatibilidadTecnica }, catalogo) }));
    const completitud = verificarCompletitud(p.tipoObjeto, req);
    return {
      valido: completitud.completo && !hallazgos.some((h) => h.severidad === 'BLOQUEANTE'), completitud, hallazgos, chb,
      requiereJustificacionChb: chb.some((c) => c.validacion.requiereExcepcion),
    };
  }

  /** Valida ET/TdR + cruce CHB, persiste las banderas por ítem y emite el formulario de insuficiencia si corresponde. */
  async validar(id: string, ctx: Ctx, regenerarJustificacion = true) {
    const p = await this.repo.obtener(id);
    this.repo.exigirEstado(p, ['BORRADOR'], 'validar el requerimiento');
    const informe = await this.evaluar(p);
    for (const c of informe.chb) {
      await this.prisma.itemContratacion.update({ where: { id: c.itemId }, data: { requiereExcepcionChb: c.validacion.requiereExcepcion, resultadoChb: c.validacion.resultado } });
    }
    let justificacion = null;
    if (informe.requiereJustificacionChb) {
      const existe = await this.prisma.documentoExpediente.count({ where: { procesoId: id, tipoDocumento: 'JUSTIFICACION_CHB' } });
      if (!existe || regenerarJustificacion) justificacion = await this.docs.generar(id, 'JUSTIFICACION_CHB', ctx);
    }
    await this.audit.registrar({ ctx, accion: 'REQUERIMIENTO_VALIDADO', entidad: 'proceso', entidadId: id, posterior: { valido: informe.valido, hallazgos: informe.hallazgos.length, excepcionesChb: informe.chb.filter((c) => c.validacion.requiereExcepcion).length } });
    return { ...informe, justificacionDocumentoId: justificacion?.id ?? null };
  }
}
