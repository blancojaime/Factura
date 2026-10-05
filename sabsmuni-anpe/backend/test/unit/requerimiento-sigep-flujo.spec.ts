import { generarJustificacionInsuficiencia, validarItemChb, EntradaChb } from '../../src/domain/chb';
import { analizarEspecificacion, verificarCompletitud } from '../../src/domain/especificaciones';
import { bloqueSigep, construirGlosa, validarPreventivoC31 } from '../../src/domain/sigep';
import { evaluarTransicion, ContextoFlujo, transicionesDesde } from '../../src/domain/flujo';
import { GENESIS, hashExpediente, hashRegistroAuditoria, jsonCanonico, sha256, verificarCadena } from '../../src/domain/integridad';

const catalogo: EntradaChb[] = [{ id: '1', codigoUnspsc: '30111505', descripcion: 'Cemento Portland', productor: 'Productor X', vigente: true }, { id: '2', codigoUnspsc: '30111600', descripcion: 'Mortero', vigente: false }];

describe('Validador CHB (D.S. 4505)', () => {
  it('producto con producción nacional exige ficha CHB', () => {
    const r = validarItemChb('BIENES', { codigoUnspsc: '30111505', descripcion: 'Cemento' }, catalogo);
    expect(r).toMatchObject({ resultado: 'CUBIERTO_POR_CHB', requiereExcepcion: false, requiereFichaChb: true });
  });
  it('incompatibilidad técnica habilita excepción', () => {
    const r = validarItemChb('BIENES', { codigoUnspsc: '30111505', descripcion: 'Cemento', incompatibilidadTecnica: 'Requiere resistencia 52,5 MPa no disponible' }, catalogo);
    expect(r.resultado).toBe('INCOMPATIBLE_CON_CHB');
    expect(r.requiereExcepcion).toBe(true);
  });
  it('misma clase sin coincidencia exacta → similar; sin clase → sin producción nacional', () => {
    expect(validarItemChb('BIENES', { codigoUnspsc: '30111599', descripcion: 'x' }, catalogo).resultado).toBe('SIMILAR_EN_CHB');
    expect(validarItemChb('BIENES', { codigoUnspsc: '43211500', descripcion: 'Computadoras' }, catalogo)).toMatchObject({ resultado: 'SIN_PRODUCCION_NACIONAL', requiereExcepcion: true });
  });
  it('ignora entradas no vigentes y servicios', () => {
    expect(validarItemChb('BIENES', { codigoUnspsc: '30111600', descripcion: 'Mortero' }, catalogo).resultado).toBe('SIN_PRODUCCION_NACIONAL'); // entrada no vigente se ignora
    expect(validarItemChb('SERVICIOS', { codigoUnspsc: '80101500', descripcion: 'Consultoría' }, catalogo).resultado).toBe('NO_APLICA');
  });
  it('códigos de servicio (segmento ≥ 70) no se cruzan con el catálogo, aunque el objeto sea Obras', () => {
    expect(validarItemChb('OBRAS', { codigoUnspsc: '72141000', descripcion: 'Pavimentación' }, catalogo).resultado).toBe('NO_APLICA');
    expect(validarItemChb('OBRAS', { codigoUnspsc: '30111505', descripcion: 'Cemento para obra' }, catalogo).resultado).toBe('CUBIERTO_POR_CHB');
  });
  it('rechaza códigos UNSPSC mal formados', () => {
    expect(() => validarItemChb('BIENES', { codigoUnspsc: '123', descripcion: 'x' }, catalogo)).toThrow(/8 dígitos/);
  });
  it('genera el formulario de insuficiencia solo con ítems en excepción', () => {
    const items = [
      { codigoUnspsc: '30111505', descripcion: 'Cemento', validacion: validarItemChb('BIENES', { codigoUnspsc: '30111505', descripcion: 'Cemento' }, catalogo) },
      { codigoUnspsc: '43211500', descripcion: 'PC', validacion: validarItemChb('BIENES', { codigoUnspsc: '43211500', descripcion: 'PC' }, catalogo) },
    ];
    const j = generarJustificacionInsuficiencia('Equipos', items);
    expect(j.items).toHaveLength(1);
    expect(j.items[0].codigoUnspsc).toBe('43211500');
  });
});

describe('Analizador de especificaciones técnicas', () => {
  it('bloquea marcas sin "o equivalente"', () => {
    const r = analizarEspecificacion('Computadora marca Dell Latitude con 16GB de RAM');
    expect(r.valido).toBe(false);
    expect(r.hallazgos[0]).toMatchObject({ tipo: 'SIN_EQUIVALENTE', severidad: 'BLOQUEANTE' });
  });
  it('degrada a advertencia cuando hay "o equivalente"', () => {
    const r = analizarEspecificacion('Impresora tipo Epson L3250 o equivalente');
    expect(r.valido).toBe(true);
    expect(r.hallazgos[0].severidad).toBe('ADVERTENCIA');
  });
  it('detecta símbolos, patentes y exclusividad', () => {
    const r = analizarEspecificacion('Sistema XPro® patentado, solo el distribuidor oficial');
    const tipos = r.hallazgos.map((h) => h.tipo);
    expect(tipos).toEqual(expect.arrayContaining(['SIMBOLO_REGISTRO', 'PATENTE', 'EXCLUSIVIDAD']));
    expect(r.valido).toBe(false);
  });
  it('no genera falsos positivos por subcadenas ("hp" en "chapa")', () => {
    expect(analizarEspecificacion('Chapa galvanizada de 2 mm, resistencia a tracción mínima 300 MPa').hallazgos).toHaveLength(0);
  });
  it('aprueba especificaciones genéricas y verifica completitud', () => {
    expect(analizarEspecificacion('Cemento Portland tipo IP, resistencia a compresión ≥ 32,5 MPa a 28 días, NB 011').valido).toBe(true);
    expect(verificarCompletitud('BIENES', { descripcion: 'Cemento portland para pavimento rígido de vías urbanas' }).faltantes).toHaveLength(4);
  });
});

describe('Validación C-31 / SIGEP', () => {
  const linea = { da: '40', ue: '1', programa: '1', proyecto: '1', actividadObra: '1', fuente: '20', organismo: '210', partida: '34200', importe: 180_000 };
  const items = [{ partidaGasto: '34200', cantidad: 3000, precioUnitario: 60, precioTotal: 180_000 }];
  it('valida un preventivo balanceado', () => {
    const v = validarPreventivoC31([linea], items, 180_000);
    expect(v.errores).toEqual([]);
    expect(v.valido).toBe(true);
  });
  it('detecta descuadres por total, partida y aritmética de ítem', () => {
    const v = validarPreventivoC31([{ ...linea, importe: 179_999.99 }], [{ ...items[0], precioTotal: 180_000.5 }], 180_000);
    expect(v.valido).toBe(false);
    expect(v.errores.join(' ')).toMatch(/no coincide con el total/);
    expect(v.errores.join(' ')).toMatch(/Partida 34200/);
  });
  it('detecta partidas no certificadas y formatos inválidos', () => {
    const v = validarPreventivoC31([{ ...linea, partida: '342', fuente: 'AB' }], items, 180_000);
    expect(v.errores.join(' ')).toMatch(/Partida "342"/);
    expect(v.errores.join(' ')).toMatch(/Fuente "AB"/);
  });
  it('construye glosa estandarizada y bloque de copia', () => {
    const g = construirGlosa('Adquisición de cemento para pavimento', 'ANPE-2025-0001', 'GAM Demo');
    expect(g).toBe('PREVENTIVO PARA LA CONTRATACION DE ADQUISICION DE CEMENTO PARA PAVIMENTO - ANPE ANPE-2025-0001 - GAM DEMO');
    const b = bloqueSigep([linea], g, '123');
    expect(b).toContain('C-31 PREVENTIVO N° 123');
    expect(b).toContain('34200\t180000.00');
    expect(b).toContain('TOTAL');
  });
});

describe('Flujo de estados y RBAC', () => {
  const ok: ContextoFlujo = { itemsCargados: true, rangoAnpeValido: true, requerimientoValido: true, excepcionesChbJustificadas: true, c31Valido: true, cronogramaValido: true, documentoDbcGenerado: true, evaluacionRealizada: true, hayRecomendacion: true, contratoGenerado: true, actaRecepcionGenerada: true };
  it('permite la transición con rol y precondiciones correctas', () => {
    expect(evaluarTransicion('BORRADOR', 'REQUERIMIENTO_VALIDADO', 'UNIDAD_SOLICITANTE', ok).permitido).toBe(true);
  });
  it('bloquea un precio referencial fuera del rango ANPE desde el requerimiento', () => {
    const r = evaluarTransicion('BORRADOR', 'REQUERIMIENTO_VALIDADO', 'UNIDAD_SOLICITANTE', { ...ok, rangoAnpeValido: false });
    expect(r.permitido).toBe(false);
    expect(r.motivos[0]).toMatch(/50\.001/);
  });
  it('bloquea por rol incorrecto', () => {
    const r = evaluarTransicion('DBC_ELABORADO', 'DBC_APROBADO', 'RESPONSABLE_CONTRATACIONES', ok);
    expect(r.permitido).toBe(false);
    expect(r.motivos[0]).toMatch(/AUTORIDAD_RPA/);
  });
  it('bloquea por precondiciones y las explica', () => {
    const r = evaluarTransicion('REQUERIMIENTO_VALIDADO', 'PRESUPUESTO_CERTIFICADO', 'RESPONSABLE_PRESUPUESTO', { ...ok, c31Valido: false });
    expect(r).toEqual({ permitido: false, motivos: [expect.stringMatching(/no cuadra/)] });
  });
  it('impide saltos de estado y administrador no opera el flujo', () => {
    expect(evaluarTransicion('BORRADOR', 'ADJUDICADO', 'AUTORIDAD_RPA', ok).permitido).toBe(false);
    expect(evaluarTransicion('BORRADOR', 'REQUERIMIENTO_VALIDADO', 'ADMINISTRADOR_SISTEMA', ok).permitido).toBe(false);
  });
  it('solo el RPA cancela y no desde estados terminales', () => {
    expect(evaluarTransicion('PUBLICADO', 'CANCELADO', 'AUTORIDAD_RPA', ok).permitido).toBe(true);
    expect(evaluarTransicion('PUBLICADO', 'CANCELADO', 'RESPONSABLE_CONTRATACIONES', ok).permitido).toBe(false);
    expect(evaluarTransicion('LIQUIDADO', 'CANCELADO', 'AUTORIDAD_RPA', ok).permitido).toBe(false);
    expect(transicionesDesde('LIQUIDADO')).toEqual([]);
  });
});

describe('Integridad criptográfica', () => {
  it('SHA-256 conocido', () => {
    expect(sha256('abc')).toBe('ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
  });
  it('JSON canónico es independiente del orden de claves', () => {
    expect(jsonCanonico({ b: 1, a: [2, { d: 1, c: 2 }] })).toBe(jsonCanonico({ a: [2, { c: 2, d: 1 }], b: 1 }));
  });
  it('la cadena de auditoría detecta manipulación', () => {
    const regs: { hash: string; hashPrevio: string; accion: string }[] = [];
    let prev = GENESIS;
    for (const accion of ['crear', 'editar', 'aprobar']) {
      const hash = hashRegistroAuditoria(prev, { accion });
      regs.push({ hash, hashPrevio: prev, accion });
      prev = hash;
    }
    expect(verificarCadena(regs, (r) => ({ accion: r.accion }))).toEqual({ integra: true, falloEn: null });
    regs[1].accion = 'borrar';
    expect(verificarCadena(regs, (r) => ({ accion: r.accion }))).toEqual({ integra: false, falloEn: 1 });
  });
  it('hash de expediente cambia si cambia cualquier documento', () => {
    const d = [{ orden: 1, tipo: 'DBC', version: 1, hashSha256: 'a' }, { orden: 2, tipo: 'CONTRATO', version: 1, hashSha256: 'b' }];
    const h = hashExpediente(d);
    expect(hashExpediente([...d].reverse())).toBe(h);
    expect(hashExpediente([d[0], { ...d[1], hashSha256: 'c' }])).not.toBe(h);
  });
});
