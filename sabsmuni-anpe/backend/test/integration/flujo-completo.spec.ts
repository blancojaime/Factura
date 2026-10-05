import { NestExpressApplication } from '@nestjs/platform-express';
import * as fs from 'fs';
import * as path from 'path';
import { PDFDocument, PDFName } from 'pdf-lib';
import request from 'supertest';
import { PrismaService } from '../../src/common/prisma.service';
import { V1_ITEMS } from '../../src/domain/evaluacion';
import { sha256 } from '../../src/domain/integridad';
import { Actores, actores, arrancar, hayBaseDeDatos, ok, paso } from './helpers';

const d = hayBaseDeDatos ? describe : describe.skip;
const V1_OK = Object.fromEntries(V1_ITEMS.map((i) => [i.codigo, true]));
let sufijo = Date.now() % 1_000_000;
const nit = () => String(1_000_000_000 + ++sufijo);

d('Integración: flujo completo ANPE (Nest + PostgreSQL)', () => {
  let app: NestExpressApplication; let A: Actores; let prisma: PrismaService;
  beforeAll(async () => { app = await arrancar(); A = await actores(app); prisma = app.get(PrismaService); }, 120_000);
  afterAll(async () => { await app?.close(); });

  const secciones = (tipo: 'BIENES' | 'OBRAS'): Record<string, string> => tipo === 'BIENES'
    ? { descripcion: 'Suministro de material para el mejoramiento de vías urbanas del municipio.', caracteristicas: 'Resistencia a la compresión mínima de 32,5 MPa a 28 días; fraguado inicial no menor a 45 minutos.', normas: 'Cumple NB 011 y NB 063 vigentes.', entrega: 'Entrega en almacén municipal en un plazo de 10 días calendario, en horario administrativo.', garantia: 'Garantía de calidad de 6 meses con reposición por defectos de fabricación.' }
    : { descripcion: 'Construcción de pavimento rígido en la calle Bolívar, tramo 1, de 450 metros de longitud.', computos: 'Pavimento 2.700 m2; cordón cuneta 900 ml; según planilla de cómputos métricos y planos adjuntos.', especificaciones: 'Hormigón H-25, espesor 18 cm, curado 7 días; medición por m2 ejecutado y aprobado.', plazo: 'Plazo de ejecución de 90 días calendario desde la orden de proceder.', supervision: 'Supervisión a cargo de la Dirección de Obras Públicas; recepción provisional y definitiva.' };

  /** Recorre BORRADOR → PUBLICADO con las reglas de cada rol. */
  async function hastaEvaluacion(opc: { objeto: string; tipo: 'BIENES' | 'OBRAS' | 'SERVICIOS'; metodo?: string; items: object[]; partida: string; total: number; plazo: number; secciones: Record<string, string> }) {
    const id = ok(await A.us.post('/api/procesos').send({ objetoContratacion: opc.objeto, tipoObjeto: opc.tipo, metodoSeleccion: opc.metodo ?? 'PRECIO_EVALUADO_MAS_BAJO', plazoEjecucionDias: opc.plazo })).body.id as string;
    for (const it of opc.items) ok(await A.us.post(`/api/procesos/${id}/items`).send(it));
    ok(await A.us.put(`/api/procesos/${id}/requerimiento`).send({ secciones: opc.secciones }));
    const val = ok(await A.us.post(`/api/procesos/${id}/requerimiento/validar`)).body;
    return { id, val };
  }
  async function certificarYPublicar(id: string, partida: string, total: number, fechaPub: string) {
    ok(await paso(A.us, id, 'REQUERIMIENTO_VALIDADO'));
    ok(await A.rp.put(`/api/procesos/${id}/presupuesto`).send({ c31PreventivoNumero: '000123', lineas: [{ da: '40', ue: '1', programa: '1', proyecto: '1', actividadObra: '1', fuente: '20', organismo: '210', partida, importe: total }] }));
    ok(await paso(A.rp, id, 'PRESUPUESTO_CERTIFICADO'));
    ok(await A.rc.put(`/api/procesos/${id}/cronograma`).send({ fechaPublicacion: fechaPub }));
    ok(await paso(A.rc, id, 'DBC_ELABORADO'));
    ok(await paso(A.rpa, id, 'DBC_APROBADO'));
    ok(await paso(A.rc, id, 'PUBLICADO'));
    ok(await paso(A.rc, id, 'EVALUACION'));
  }

  it('Caso exitoso OBRAS: del borrador a la liquidación, con subasta, márgenes, contrato 7%/3,5% y expediente foliado', async () => {
    const { id, val } = await hastaEvaluacion({
      objeto: 'Construcción de pavimento rígido calle Bolívar tramo 1', tipo: 'OBRAS', plazo: 90, partida: '43100', total: 450_000, secciones: secciones('OBRAS'),
      items: [{ codigoUnspsc: '72141000', partidaGasto: '43100', descripcionTecnica: 'Pavimento rígido de hormigón H-25, e=18 cm', unidadMedida: 'm2', cantidad: 2700, precioUnitario: 150 }, { codigoUnspsc: '72141000', partidaGasto: '43100', descripcionTecnica: 'Cordón cuneta de hormigón simple', unidadMedida: 'ml', cantidad: 900, precioUnitario: 50 }],
    });
    expect(val.valido).toBe(true);
    expect(val.requiereJustificacionChb).toBe(false);

    // RBAC: el RC no puede validar el requerimiento ni el solicitante certificar presupuesto
    expect((await A.rc.post(`/api/procesos/${id}/requerimiento/validar`)).status).toBe(403);
    expect((await A.us.put(`/api/procesos/${id}/presupuesto`).send({ lineas: [] })).status).toBe(403);
    // Bloqueo por salto de estados
    expect((await paso(A.rpa, id, 'ADJUDICADO')).status).toBe(409);
    ok(await paso(A.us, id, 'REQUERIMIENTO_VALIDADO'));

    // Presupuesto descuadrado → no se puede certificar
    ok(await A.rp.put(`/api/procesos/${id}/presupuesto`).send({ lineas: [{ da: '40', ue: '1', programa: '1', proyecto: '1', actividadObra: '1', fuente: '20', organismo: '210', partida: '43100', importe: 449_999.99 }] }));
    const malo = await paso(A.rp, id, 'PRESUPUESTO_CERTIFICADO');
    expect(malo.status).toBe(409);
    expect(JSON.stringify(malo.body)).toMatch(/no cuadra/);
    const sigep = ok(await A.rp.get(`/api/procesos/${id}/sigep`)).body;
    expect(sigep.validacion.valido).toBe(false);
    ok(await A.rp.put(`/api/procesos/${id}/presupuesto`).send({ c31PreventivoNumero: '000123', lineas: [{ da: '40', ue: '1', programa: '1', proyecto: '1', actividadObra: '1', fuente: '20', organismo: '210', partida: '43100', importe: 450_000 }] }));
    const sigepOk = ok(await A.rp.get(`/api/procesos/${id}/sigep`)).body;
    expect(sigepOk.validacion.valido).toBe(true);
    expect(sigepOk.bloque).toContain('43100\t450000.00');
    expect(sigepOk.glosa).toMatch(/^PREVENTIVO PARA LA CONTRATACION DE CONSTRUCCION DE PAVIMENTO/);
    ok(await paso(A.rp, id, 'PRESUPUESTO_CERTIFICADO'));

    // Cronograma: 450.000 → 8 días hábiles; apertura anticipada se rechaza
    const corto = await A.rc.put(`/api/procesos/${id}/cronograma`).send({ fechaPublicacion: '2026-11-09', fechaApertura: '2026-11-13' });
    expect(corto.status).toBe(400);
    expect(JSON.stringify(corto.body)).toMatch(/mínimo según Art\. 47/);
    expect((await A.rc.put(`/api/procesos/${id}/cronograma`).send({ fechaPublicacion: '2026-11-07' })).status).toBe(400); // sábado
    const cr = ok(await A.rc.put(`/api/procesos/${id}/cronograma`).send({ fechaPublicacion: '2026-11-09' })).body;
    expect(cr.plazoMinimoDiasHabiles).toBe(8);
    expect(cr.cronograma.fechaApertura).toBe('2026-11-19'); // 10,11,12,13,16,17,18,19
    ok(await paso(A.rc, id, 'DBC_ELABORADO'));
    expect((await paso(A.rc, id, 'DBC_APROBADO')).status).toBe(409); // solo el RPA aprueba el DBC
    ok(await paso(A.rpa, id, 'DBC_APROBADO'));
    ok(await paso(A.rc, id, 'PUBLICADO'));
    ok(await paso(A.rc, id, 'EVALUACION'));

    // Propuestas + V-1 + subasta
    const pA = ok(await A.rc.post(`/api/procesos/${id}/propuestas`).send({ nitProveedor: nit(), razonSocial: 'Constructora Andina SRL', categoria: 'NACIONAL_GENERAL', montoOfertado: 440_000, montoSubasta: 430_000, plazoDias: 85 })).body;
    const pB = ok(await A.rc.post(`/api/procesos/${id}/propuestas`).send({ nitProveedor: nit(), razonSocial: 'MyPE Construcciones Valle', categoria: 'MYPE_APP_OECA', montoOfertado: 445_000, montoSubasta: 440_000, plazoDias: 90 })).body;
    const pC = ok(await A.rc.post(`/api/procesos/${id}/propuestas`).send({ nitProveedor: nit(), razonSocial: 'Viales del Sur SA', categoria: 'NACIONAL_GENERAL', montoOfertado: 400_000, plazoDias: 80 })).body;
    expect((await A.rc.post(`/api/procesos/${id}/propuestas`).send({ nitProveedor: pA.nitProveedor, razonSocial: 'Duplicada SRL', categoria: 'NACIONAL_GENERAL', montoOfertado: 1000, plazoDias: 5 })).status).toBe(409);
    expect((await A.rc.post(`/api/procesos/${id}/propuestas`).send({ nitProveedor: nit(), razonSocial: 'Subasta inválida', categoria: 'NACIONAL_GENERAL', montoOfertado: 400_000, montoSubasta: 410_000, plazoDias: 5 })).status).toBe(400);
    ok(await A.rc.put(`/api/procesos/${id}/propuestas/${pA.id}/v1`).send({ v1: V1_OK }));
    ok(await A.rc.put(`/api/procesos/${id}/propuestas/${pB.id}/v1`).send({ v1: V1_OK }));
    ok(await A.rc.put(`/api/procesos/${id}/propuestas/${pC.id}/v1`).send({ v1: { ...V1_OK, 'V1-03': false } })); // sin RUPE → no califica
    const ev = ok(await A.rc.post(`/api/procesos/${id}/evaluacion`)).body;
    // B: 440.000 con 18% → 360.800 ; A: 430.000 con 10% → 387.000 ; C descalificada aunque es la más barata
    expect(ev.recomendadaId).toBe(pB.id);
    expect(ev.filas.map((f: { razonSocial: string; precioComparacion: number }) => [f.razonSocial, f.precioComparacion])).toEqual([['MyPE Construcciones Valle', 360_800], ['Constructora Andina SRL', 387_000], ['Viales del Sur SA', 360_000]]);
    expect(ev.filas[2].estado).toBe('NO_CALIFICA');
    ok(await paso(A.rc, id, 'RECOMENDACION_EMITIDA'));
    const tiposTrasEvaluar = (await A.rc.get(`/api/procesos/${id}/documentos`)).body.map((x: { tipoDocumento: string }) => x.tipoDocumento);
    expect(tiposTrasEvaluar).toEqual(expect.arrayContaining(['INFORME_V1', 'CUADRO_COMPARATIVO', 'INFORME_EVALUACION']));

    // Adjudicar a otra propuesta exige fundamento
    expect((await paso(A.rpa, id, 'ADJUDICADO', { propuestaId: pA.id })).status).toBe(400);
    ok(await paso(A.rpa, id, 'ADJUDICADO'));

    // Contrato: MyPE → garantía 3,5% de 440.000 = 15.400; plazo 90 d → CONTRATO
    expect((await A.rc.post(`/api/procesos/${id}/contrato`).send({ fechaFirma: '2026-12-05' })).status).toBe(400); // sábado
    const sim = ok(await A.rc.get(`/api/procesos/${id}/contrato/simular`)).body;
    expect(sim).toMatchObject({ tipo: 'CONTRATO', monto: 440_000, garantia: { porcentaje: 3.5, monto: 15_400 } });
    const c = ok(await A.rpa.post(`/api/procesos/${id}/contrato`).send({ fechaFirma: '2026-12-01', garantiaInstrumento: 'Boleta de Garantía', polizaNumero: 'BG-2026-0456', polizaEntidad: 'Banco Nacional', polizaVigenciaHasta: '2027-04-30' })).body;
    expect(c.tipo).toBe('CONTRATO');
    ok(await paso(A.rpa, id, 'CONTRATO_FORMALIZADO'));
    expect((await paso(A.rc, id, 'RECEPCION')).status).toBe(409); // falta acta
    ok(await A.rc.post(`/api/procesos/${id}/recepcion`).send({ fechaRecepcion: '2027-03-10', observacion: 'Conforme' }));
    ok(await paso(A.rc, id, 'RECEPCION'));
    ok(await paso(A.rc, id, 'LIQUIDADO'));

    // Expediente único
    const exp = ok(await A.rc.post(`/api/procesos/${id}/expediente`)).body;
    expect(exp.documentos).toBeGreaterThanOrEqual(8);
    const descarga = ok(await A.rc.get(`/api/documentos/${exp.id}/descargar`).buffer(true).parse((res, cb) => { const ch: Buffer[] = []; res.on('data', (x: Buffer) => ch.push(x)); res.on('end', () => cb(null, Buffer.concat(ch))); }));
    const pdf = await PDFDocument.load(descarga.body as Buffer);
    expect(pdf.getPageCount()).toBe(exp.folios);
    expect(pdf.catalog.has(PDFName.of('Outlines'))).toBe(true);
    expect(sha256(descarga.body as Buffer)).toBe(exp.hashSha256);
    // Verificación pública por QR (sin sesión)
    const v = ok(await request(app.getHttpServer()).get(`/api/verificar/${exp.hashExpediente}`)).body;
    expect(v).toMatchObject({ valido: true, tipoDocumento: 'EXPEDIENTE_UNICO' });
    expect(ok(await request(app.getHttpServer()).get(`/api/verificar/${'a'.repeat(64)}`)).body.valido).toBe(false);

    // Manipular un archivo almacenado es detectado
    const doc = await prisma.documentoExpediente.findFirstOrThrow({ where: { procesoId: id, tipoDocumento: 'DBC' } });
    const ruta = path.join(process.env.STORAGE_DIR!, doc.rutaArchivo);
    fs.appendFileSync(ruta, ' ');
    expect((await A.rc.get(`/api/documentos/${doc.id}/descargar`)).status).toBe(500);
    expect((await request(app.getHttpServer()).get(`/api/verificar/${doc.hashSha256}`)).body.valido).toBe(false);

    // Auditoría: cadena de hashes íntegra y con estado previo/posterior
    const integridad = ok(await A.admin.get('/api/auditoria/verificar')).body;
    expect(integridad.integra).toBe(true);
    const logs = ok(await A.rpa.get(`/api/auditoria?entidad=proceso&entidadId=${id}`)).body;
    const t = logs.find((l: { accion: string; estadoPosterior: { estado: string } }) => l.accion === 'TRANSICION_ESTADO' && l.estadoPosterior.estado === 'ADJUDICADO');
    expect(t.estadoPrevio).toEqual({ estado: 'RECOMENDACION_EMITIDA' });
    expect(t.ip).toBeTruthy();
  }, 120_000);

  it('Caso Bienes FUERA de CHB: emite el formulario de insuficiencia técnica, bloquea marcas y genera Orden de Compra (plazo ≤ 15 días)', async () => {
    const itemPC = { codigoUnspsc: '43211500', partidaGasto: '43200', descripcionTecnica: 'Computadora de escritorio, procesador de 8 núcleos, 16 GB de RAM, SSD de 512 GB', unidadMedida: 'pieza', cantidad: 10, precioUnitario: 6000 };
    const sec = { ...secciones('BIENES'), caracteristicas: 'Computadoras marca Dell Optiplex con 16 GB de RAM y SSD de 512 GB.' };
    const id = ok(await A.us.post('/api/procesos').send({ objetoContratacion: 'Adquisición de computadoras de escritorio para oficinas', tipoObjeto: 'BIENES', metodoSeleccion: 'PRECIO_EVALUADO_MAS_BAJO', plazoEjecucionDias: 10 })).body.id as string;
    ok(await A.us.post(`/api/procesos/${id}/items`).send(itemPC));
    ok(await A.us.put(`/api/procesos/${id}/requerimiento`).send({ secciones: sec }));

    // 1) La marca "Dell" sin "o equivalente" bloquea el requerimiento
    const v1 = ok(await A.us.post(`/api/procesos/${id}/requerimiento/validar`)).body;
    expect(v1.valido).toBe(false);
    expect(v1.hallazgos.some((h: { tipo: string; severidad: string }) => h.tipo === 'SIN_EQUIVALENTE' && h.severidad === 'BLOQUEANTE')).toBe(true);
    const bloqueo = await paso(A.us, id, 'REQUERIMIENTO_VALIDADO');
    expect(bloqueo.status).toBe(409);
    expect(JSON.stringify(bloqueo.body)).toMatch(/bloqueantes/);

    // 2) Se corrige: sin producción nacional → formulario de insuficiencia emitido automáticamente
    ok(await A.us.put(`/api/procesos/${id}/requerimiento`).send({ secciones: secciones('BIENES') }));
    const v2 = ok(await A.us.post(`/api/procesos/${id}/requerimiento/validar`)).body;
    expect(v2.valido).toBe(true);
    expect(v2.requiereJustificacionChb).toBe(true);
    expect(v2.chb[0].validacion.resultado).toBe('SIN_PRODUCCION_NACIONAL');
    expect(v2.justificacionDocumentoId).toBeTruthy();
    const docs = ok(await A.us.get(`/api/procesos/${id}/documentos`)).body;
    expect(docs.some((x: { tipoDocumento: string }) => x.tipoDocumento === 'JUSTIFICACION_CHB')).toBe(true);

    await certificarYPublicar(id, '43200', 60_000, '2026-11-09');
    // Bienes: no admite subasta
    const pa = ok(await A.rc.post(`/api/procesos/${id}/propuestas`).send({ nitProveedor: nit(), razonSocial: 'Tecnología Andina SRL', categoria: 'NACIONAL_GENERAL', montoOfertado: 58_000, plazoDias: 8 })).body;
    expect((await A.rc.post(`/api/procesos/${id}/propuestas`).send({ nitProveedor: nit(), razonSocial: 'Con subasta', categoria: 'NACIONAL_GENERAL', montoOfertado: 58_000, montoSubasta: 50_000, plazoDias: 8 })).status).toBe(400);
    ok(await A.rc.put(`/api/procesos/${id}/propuestas/${pa.id}/v1`).send({ v1: V1_OK }));
    const ev = ok(await A.rc.post(`/api/procesos/${id}/evaluacion`)).body;
    expect(ev.recomendadaId).toBe(pa.id);
    ok(await paso(A.rc, id, 'RECOMENDACION_EMITIDA'));
    ok(await paso(A.rpa, id, 'ADJUDICADO'));
    const c = ok(await A.rc.post(`/api/procesos/${id}/contrato`).send({ fechaFirma: '2026-12-01' })).body;
    expect(c).toMatchObject({ tipo: 'ORDEN_COMPRA', monto: 58_000, garantia: { porcentaje: 7, monto: 4_060 } });
    expect(c.documento.tipoDocumento).toBe('ORDEN_COMPRA_SERVICIO');
  }, 120_000);

  it('Caso del manual: lote de cemento para pavimento, Bs 180.000 (CHB cubierto, ficha requerida; 4 días hábiles)', async () => {
    const { id, val } = await hastaEvaluacion({
      objeto: 'Adquisición de lote de cemento para pavimento', tipo: 'BIENES', plazo: 20, partida: '34200', total: 180_000, secciones: secciones('BIENES'),
      items: [{ codigoUnspsc: '30111505', partidaGasto: '34200', descripcionTecnica: 'Cemento Portland tipo IP, bolsa de 50 kg, resistencia ≥ 32,5 MPa', unidadMedida: 'bolsa', cantidad: 3000, precioUnitario: 60 }],
    });
    expect(val.valido).toBe(true);
    expect(val.chb[0].validacion).toMatchObject({ resultado: 'CUBIERTO_POR_CHB', requiereExcepcion: false, requiereFichaChb: true });
    expect(val.requiereJustificacionChb).toBe(false);
    ok(await paso(A.us, id, 'REQUERIMIENTO_VALIDADO'));
    ok(await A.rp.put(`/api/procesos/${id}/presupuesto`).send({ c31PreventivoNumero: '000200', lineas: [{ da: '40', ue: '1', programa: '1', proyecto: '1', actividadObra: '1', fuente: '20', organismo: '210', partida: '34200', importe: 180_000 }] }));
    ok(await paso(A.rp, id, 'PRESUPUESTO_CERTIFICADO'));
    const cr = ok(await A.rc.put(`/api/procesos/${id}/cronograma`).send({ fechaPublicacion: '2026-11-09' })).body;
    expect(cr.plazoMinimoDiasHabiles).toBe(4);
    expect(cr.cronograma.fechaApertura).toBe('2026-11-13');
    ok(await paso(A.rc, id, 'DBC_ELABORADO')); ok(await paso(A.rpa, id, 'DBC_APROBADO')); ok(await paso(A.rc, id, 'PUBLICADO')); ok(await paso(A.rc, id, 'EVALUACION'));
    const p1 = ok(await A.rc.post(`/api/procesos/${id}/propuestas`).send({ nitProveedor: nit(), razonSocial: 'Ferretería Central', categoria: 'NACIONAL_GENERAL', montoOfertado: 175_000, plazoDias: 12 })).body;
    ok(await A.rc.put(`/api/procesos/${id}/propuestas/${p1.id}/v1`).send({ v1: V1_OK }));
    ok(await A.rc.post(`/api/procesos/${id}/evaluacion`));
    // Cambiar una propuesta invalida la evaluación: no se puede recomendar sin recalcular
    ok(await A.rc.patch(`/api/procesos/${id}/propuestas/${p1.id}`).send({ montoOfertado: 170_000 }));
    expect((await paso(A.rc, id, 'RECOMENDACION_EMITIDA')).status).toBe(409);
    ok(await A.rc.post(`/api/procesos/${id}/evaluacion`));
    ok(await paso(A.rc, id, 'RECOMENDACION_EMITIDA'));
    // Declarar desierto exige fundamento; luego se reabre la convocatoria
    expect((await paso(A.rpa, id, 'DESIERTO')).status).toBe(400);
    ok(await paso(A.rpa, id, 'DESIERTO', { observacion: 'Presupuesto reformulado por la unidad solicitante' }));
    ok(await paso(A.rc, id, 'PRESUPUESTO_CERTIFICADO'));
    expect((await A.rc.get(`/api/procesos/${id}/propuestas`)).body.propuestas).toHaveLength(0);
  }, 120_000);

  it('Seguridad: sesión obligatoria, bloqueo de credenciales inválidas y rotación de refresh token', async () => {
    expect((await request(app.getHttpServer()).get('/api/procesos')).status).toBe(401);
    expect((await request(app.getHttpServer()).post('/api/auth/login').send({ email: 'rpa@gam.bo', password: 'incorrecta123' })).status).toBe(401);
    const agente = request.agent(app.getHttpServer());
    const login = ok(await agente.post('/api/auth/login').send({ email: 'rpa@gam.bo', password: 'Anpe2026Demo' }));
    const cookies = (login.headers['set-cookie'] as unknown as string[]).join(';');
    expect(cookies).toMatch(/access_token=.*HttpOnly/i);
    expect(cookies).toMatch(/refresh_token=.*HttpOnly/i);
    const refreshViejo = /refresh_token=([^;]+)/.exec(cookies)![1];
    ok(await agente.post('/api/auth/refresh'));
    // Reutilizar el refresh token ya rotado revoca la sesión
    const reuso = await request(app.getHttpServer()).post('/api/auth/refresh').set('Cookie', `refresh_token=${refreshViejo}`);
    expect(reuso.status).toBe(401);
    expect((await A.us.get('/api/usuarios')).status).toBe(403);
    expect((await A.admin.get('/api/usuarios')).status).toBe(200);
  }, 60_000);
});
