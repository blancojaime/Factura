import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { activar, DIAS_PRUEBA, estadoLicencia, estadoPrueba, evaluarClave, idEquipo, leerClave } from '../../desktop/src/licencia.js';
// @ts-expect-error módulo .mjs de la herramienta del proveedor
import { crearPar, emitirClave } from '../../tools/licencias/emisor.mjs';

let dir = ''; let pub = ''; let priv = ''; let otraPub = '';
const EQ = 'ABCD-1234-EF56-7890';
beforeAll(() => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), 'lic-'));
  const r = crearPar(path.join(dir, 'privada'), path.join(dir, 'publica.pem'));
  pub = fs.readFileSync(r.pub, 'utf8'); priv = fs.readFileSync(r.priv, 'utf8');
  const o = crearPar(path.join(dir, 'privada2'), path.join(dir, 'publica2.pem'));
  otraPub = fs.readFileSync(o.pub, 'utf8');
});
afterAll(() => fs.rmSync(dir, { recursive: true, force: true }));

describe('Clave de activación', () => {
  it('no se sobrescribe un par de claves existente', () => {
    expect(() => crearPar(path.join(dir, 'privada'), path.join(dir, 'publica.pem'))).toThrow(/Ya existe/);
  });
  it('clave perpetua para cualquier equipo', () => {
    const { clave } = emitirClave(priv, { entidad: 'GAM Demo', equipo: '*' });
    const e = evaluarClave(clave, pub, EQ, '2030-01-01');
    expect(e).toMatchObject({ estado: 'ACTIVA', entidad: 'GAM Demo', vence: '', diasRestantes: null });
  });
  it('clave atada a un equipo: sirve solo en ese equipo', () => {
    const { clave } = emitirClave(priv, { entidad: 'GAM Demo', equipo: EQ });
    expect(evaluarClave(clave, pub, EQ).estado).toBe('ACTIVA');
    expect(evaluarClave(clave, pub, 'ABCD-1234-EF56-0000').estado).toBe('OTRO_EQUIPO');
  });
  it('vencimiento: activa hasta el último día y vencida después', () => {
    const { clave } = emitirClave(priv, { entidad: 'GAM Demo', equipo: '*', vence: '2027-03-31' });
    expect(evaluarClave(clave, pub, EQ, '2027-03-31')).toMatchObject({ estado: 'ACTIVA', diasRestantes: 0 });
    expect(evaluarClave(clave, pub, EQ, '2027-03-01')).toMatchObject({ estado: 'ACTIVA', diasRestantes: 30 });
    expect(evaluarClave(clave, pub, EQ, '2027-04-01').estado).toBe('VENCIDA');
  });
  it('rechaza claves alteradas, de otro proveedor o mal formadas', () => {
    const { clave } = emitirClave(priv, { entidad: 'GAM Demo', equipo: '*', vence: '2027-03-31' });
    const [p, s] = clave.slice(7).split('.');
    const falso = Buffer.from(JSON.stringify({ ...JSON.parse(Buffer.from(p, 'base64url').toString()), e: '2099-12-31' })).toString('base64url');
    expect(evaluarClave('SIGAA1-' + falso + '.' + s, pub, EQ).estado).toBe('INVALIDA');
    expect(evaluarClave(clave, otraPub, EQ).estado).toBe('INVALIDA');
    expect(evaluarClave('hola', pub, EQ).estado).toBe('INVALIDA');
    expect(() => leerClave('SIGAA1-abc', pub)).toThrow(/incompleta/);
    expect(evaluarClave(clave.replace(/(.{40})/g, '$1\n '), pub, EQ).estado).toBe('ACTIVA'); // tolera saltos de línea al pegar
  });
  it('valida los datos al emitir', () => {
    expect(() => emitirClave(priv, { entidad: '' })).toThrow(/entidad/);
    expect(() => emitirClave(priv, { entidad: 'X', equipo: '123' })).toThrow(/ID del equipo/);
    expect(() => emitirClave(priv, { entidad: 'X', vence: '31/12/2027' })).toThrow(/AAAA-MM-DD/);
  });
  it('el ID del equipo tiene formato y es estable', () => {
    expect(idEquipo()).toMatch(/^[0-9A-F]{4}(-[0-9A-F]{4}){3}$/);
    expect(idEquipo()).toBe(idEquipo());
  });
});

describe('Activación y período de prueba', () => {
  it('sin clave: prueba de 30 días, luego termina; no se reinicia borrando nada simple', () => {
    const d = fs.mkdtempSync(path.join(dir, 'p-'));
    expect(estadoLicencia(d, pub, '2026-01-01', EQ)).toMatchObject({ estado: 'PRUEBA', diasRestantes: DIAS_PRUEBA });
    expect(estadoLicencia(d, pub, '2026-01-11', EQ)).toMatchObject({ estado: 'PRUEBA', diasRestantes: DIAS_PRUEBA - 10 });
    expect(estadoLicencia(d, pub, '2026-01-31', EQ).estado).toBe('PRUEBA_TERMINADA');
  });
  it('detecta archivo de prueba alterado y reloj retrocedido', () => {
    const d = fs.mkdtempSync(path.join(dir, 'p-'));
    const f = path.join(d, 'prueba.dat');
    estadoPrueba(f, EQ, '2026-02-01');
    const j = JSON.parse(fs.readFileSync(f, 'utf8')); j.ini = '2026-02-20';
    fs.writeFileSync(f, JSON.stringify(j));
    expect(estadoPrueba(f, EQ, '2026-02-03').estado).toBe('PRUEBA_TERMINADA');
    const d2 = fs.mkdtempSync(path.join(dir, 'p-'));
    const f2 = path.join(d2, 'prueba.dat');
    estadoPrueba(f2, EQ, '2026-03-10');
    expect(estadoPrueba(f2, EQ, '2026-03-01').estado).toBe('PRUEBA_TERMINADA');
  });
  it('activar guarda la clave y la licencia prevalece sobre la prueba; clave mala no se guarda', () => {
    const d = fs.mkdtempSync(path.join(dir, 'a-'));
    expect(() => activar(d, 'SIGAA1-xx.yy', pub, EQ)).toThrow();
    expect(fs.existsSync(path.join(d, 'licencia.key'))).toBe(false);
    const { clave } = emitirClave(priv, { entidad: 'GAM Demo', equipo: EQ });
    expect(activar(d, clave, pub, EQ).estado).toBe('ACTIVA');
    expect(estadoLicencia(d, pub, '2026-06-01', EQ).estado).toBe('ACTIVA');
    // licencia vencida: se informa, no vuelve a la prueba
    const v = fs.mkdtempSync(path.join(dir, 'v-'));
    const { clave: c2 } = emitirClave(priv, { entidad: 'X', equipo: '*', vence: '2026-01-31' });
    activar(v, c2, pub, EQ, '2026-01-01');
    expect(estadoLicencia(v, pub, '2026-02-15', EQ).estado).toBe('VENCIDA');
  });
});
