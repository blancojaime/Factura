// Emisión de claves de activación de SIGAA Escritorio (firma Ed25519). Uso interno del proveedor: la clave PRIVADA no se publica.
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

export const PREFIJO = 'SIGAA1-';

export function crearPar(dirPrivada, rutaPublica) {
  const { publicKey, privateKey } = crypto.generateKeyPairSync('ed25519');
  fs.mkdirSync(dirPrivada, { recursive: true });
  const priv = path.join(dirPrivada, 'clave_privada.pem');
  if (fs.existsSync(priv)) throw new Error('Ya existe un par de claves. No se sobrescribe para no invalidar las licencias emitidas.');
  fs.writeFileSync(priv, privateKey.export({ type: 'pkcs8', format: 'pem' }), { mode: 0o600 });
  fs.mkdirSync(path.dirname(rutaPublica), { recursive: true });
  fs.writeFileSync(rutaPublica, publicKey.export({ type: 'spki', format: 'pem' }));
  return { priv, pub: rutaPublica };
}

/** equipo: ID del equipo (XXXX-XXXX-XXXX-XXXX) o '*' para cualquier equipo. vence: 'AAAA-MM-DD' o '' (perpetua). */
export function emitirClave(clavePrivadaPem, { entidad, equipo = '*', vence = '', tipo, hoy = new Date().toISOString().slice(0, 10) }) {
  if (!String(entidad || '').trim()) throw new Error('Indique el nombre de la entidad.');
  if (equipo !== '*' && !/^[0-9A-F]{4}(-[0-9A-F]{4}){3}$/i.test(equipo)) throw new Error('El ID del equipo debe tener el formato XXXX-XXXX-XXXX-XXXX (o * para cualquier equipo).');
  if (vence && !/^\d{4}-\d{2}-\d{2}$/.test(vence)) throw new Error('El vencimiento debe ser AAAA-MM-DD o quedar vacío (perpetua).');
  const datos = { v: 1, n: String(entidad).trim(), m: equipo === '*' ? '*' : equipo.toUpperCase(), e: vence, t: tipo || (vence ? 'ANUAL' : 'PERPETUA'), i: hoy };
  const payload = Buffer.from(JSON.stringify(datos));
  const firma = crypto.sign(null, payload, crypto.createPrivateKey(clavePrivadaPem));
  return { clave: PREFIJO + payload.toString('base64url') + '.' + firma.toString('base64url'), datos };
}
