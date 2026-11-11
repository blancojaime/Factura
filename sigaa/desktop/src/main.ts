/**
 * SIGAA Escritorio: ventana Electron que ejecuta el servidor de SIGAA en el mismo equipo
 * con una base de datos SQLite local (carpeta de datos del usuario) y abre la aplicación web.
 *
 * Datos: <datos del usuario>/SIGAA/sigaa.sqlite  ·  Fotos: <datos del usuario>/SIGAA/fotos
 * Para usar PostgreSQL en vez de SQLite defina la variable de entorno DATABASE_URL antes de abrir la aplicación.
 */
import { app, BrowserWindow, clipboard, dialog, ipcMain, Menu, shell } from 'electron';
import path from 'node:path';
import fs from 'node:fs';
import { activar, AVISO_VENCIMIENTO_DIAS, estadoLicencia, permiteUsar, type Estado } from './licencia';

let ventana: BrowserWindow | null = null;
let servidor: { url: string; close(): Promise<void> } | null = null;

/** Recursos copiados junto a este archivo por scripts/copiar.mjs (dentro del asar al empaquetar). */
function recursos() {
  return { server: path.join(__dirname, 'server', 'start.js'), web: path.join(__dirname, 'web'), seed: path.join(__dirname, 'seed') };
}

const datosDir = () => path.join(app.getPath('userData'), 'SIGAA');

/** Clave pública de licenciamiento (la copia scripts/copiar.mjs desde desktop/licencia/publica.pem). 'SIN_LICENCIA' = compilación de desarrollo sin protección. */
function clavePublica(): string {
  const f = path.join(__dirname, 'licencia-publica.pem');
  return fs.existsSync(f) ? fs.readFileSync(f, 'utf8') : 'SIN_LICENCIA';
}
const sinLicencia = () => clavePublica().trim() === 'SIN_LICENCIA';
const estadoActual = (): Estado => estadoLicencia(datosDir(), clavePublica());

/** Ventana de activación. Resuelve true si el usuario puede continuar (licencia activa o prueba vigente y eligió continuar). */
function ventanaActivacion(modal: boolean): Promise<boolean> {
  return new Promise((resolve) => {
    let resuelto = false;
    const fin = (v: boolean) => { if (!resuelto) { resuelto = true; resolve(v); } };
    const w = new BrowserWindow({ width: 700, height: 640, resizable: false, autoHideMenuBar: true, title: 'Activación de SIGAA', backgroundColor: '#14263f', parent: modal && ventana ? ventana : undefined, modal: modal && !!ventana, webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true, preload: path.join(__dirname, 'preload.js') } });
    w.setMenu(null);
    const quitar = () => { for (const c of ['lic:estado', 'lic:activar', 'lic:continuar', 'lic:copiar', 'lic:cerrar']) ipcMain.removeHandler(c); };
    ipcMain.handle('lic:estado', () => estadoActual());
    ipcMain.handle('lic:activar', (_e, clave: string) => { try { return { estado: activar(datosDir(), String(clave || ''), clavePublica()) }; } catch (e: any) { return { error: e.message }; } });
    ipcMain.handle('lic:continuar', () => { if (permiteUsar(estadoActual())) { fin(true); w.close(); } });
    ipcMain.handle('lic:copiar', (_e, t: string) => { clipboard.writeText(String(t || '')); });
    ipcMain.handle('lic:cerrar', () => { w.close(); });
    w.on('closed', () => { quitar(); fin(false); });
    w.loadFile(path.join(__dirname, 'activacion.html'));
  });
}

/** Comprueba la licencia al iniciar. Devuelve false si no se debe abrir la aplicación. */
async function verificarLicencia(): Promise<boolean> {
  if (sinLicencia()) return true;
  const e = estadoActual();
  if (e.estado === 'ACTIVA') return true;
  return ventanaActivacion(false); // prueba (con botón Continuar) o bloqueo (solo activar)
}

/** Aviso de vencimiento próximo y control periódico mientras la aplicación está abierta. */
function vigilarLicencia() {
  if (sinLicencia()) return;
  const e = estadoActual();
  if (e.estado === 'ACTIVA' && e.diasRestantes !== null && e.diasRestantes <= AVISO_VENCIMIENTO_DIAS && ventana)
    dialog.showMessageBox(ventana, { type: 'warning', title: 'Licencia por vencer', message: `Su licencia vence en ${e.diasRestantes} día(s).`, detail: 'Solicite la renovación al proveedor (menú SIGAA → Licencia).' });
  setInterval(() => {
    if (!permiteUsar(estadoActual())) { dialog.showErrorBox('Licencia vencida', 'La licencia de SIGAA venció. Active una clave nueva para continuar.'); app.quit(); }
  }, 60 * 60 * 1000);
}

/** Reemplaza la base de datos local por una copia de respaldo elegida por el usuario (se guarda antes una copia de la actual). */
async function restaurarCopia() {
  if (process.env.DATABASE_URL) { dialog.showMessageBox(ventana!, { type: 'info', message: 'Esta instalación usa PostgreSQL: restaure la copia con las herramientas de PostgreSQL.' }); return; }
  const r = await dialog.showOpenDialog(ventana!, { title: 'Elija la copia de respaldo (.sqlite)', properties: ['openFile'], filters: [{ name: 'Copia de respaldo SIGAA', extensions: ['sqlite', 'db'] }] });
  if (r.canceled || !r.filePaths[0]) return;
  const origen = r.filePaths[0];
  const cab = Buffer.alloc(16);
  const fd = fs.openSync(origen, 'r'); fs.readSync(fd, cab, 0, 16, 0); fs.closeSync(fd);
  if (cab.toString('latin1', 0, 15) !== 'SQLite format 3') { dialog.showErrorBox('Archivo no válido', 'El archivo elegido no es una base de datos de SIGAA.'); return; }
  const ok = await dialog.showMessageBox(ventana!, { type: 'warning', buttons: ['Cancelar', 'Reemplazar los datos'], defaultId: 0, cancelId: 0, title: 'Restaurar copia de respaldo', message: 'Se REEMPLAZARÁN todos los datos actuales por los de la copia elegida.', detail: 'Antes se guarda una copia de seguridad de los datos actuales en la carpeta "respaldos". SIGAA se reiniciará.' });
  if (ok.response !== 1) return;
  const datos = datosDir();
  const bd = path.join(datos, 'sigaa.sqlite');
  await servidor?.close().catch(() => {});
  servidor = null;
  const resp = path.join(datos, 'respaldos');
  fs.mkdirSync(resp, { recursive: true });
  if (fs.existsSync(bd)) fs.copyFileSync(bd, path.join(resp, `antes-de-restaurar-${new Date().toISOString().replace(/[:T]/g, '-').slice(0, 19)}.sqlite`));
  for (const x of ['-wal', '-shm', '-journal']) fs.rmSync(bd + x, { force: true });
  fs.copyFileSync(origen, bd);
  app.relaunch();
  app.exit(0);
}

async function iniciarServidor() {
  const datos = path.join(app.getPath('userData'), 'SIGAA');
  fs.mkdirSync(datos, { recursive: true });
  const r = recursos();
  if (!fs.existsSync(r.server)) throw new Error(`No se encontró el servidor compilado (${r.server}). Ejecute «npm run build» en la raíz del proyecto.`);
  process.env.SIGAA_SEED_DIR = r.seed;
  const nueva = !fs.existsSync(path.join(datos, 'sigaa.sqlite'));
  // import dinámico: el servidor es ESM y esta aplicación es CommonJS
  const mod: any = await (new Function('p', 'return import(p)') as (p: string) => Promise<any>)(require('node:url').pathToFileURL(r.server).href);
  servidor = await mod.startServer({
    databaseUrl: process.env.DATABASE_URL || `sqlite:${path.join(datos, 'sigaa.sqlite')}`,
    fotosDir: path.join(datos, 'fotos'),
    webDir: r.web,
    port: 0, // puerto libre
    host: '127.0.0.1',
    demo: nueva && process.env.SIGAA_DEMO === '1', // distribución: la base inicia VACÍA (solo catálogos normativos y el administrador); SIGAA_DEMO=1 carga datos de ejemplo
    logger: false,
  });
}

async function crearVentana() {
  ventana = new BrowserWindow({ width: 1440, height: 900, minWidth: 1000, minHeight: 640, title: 'SIGAA', backgroundColor: '#14263f', webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true } });
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    { label: 'SIGAA', submenu: [{ label: 'Abrir carpeta de datos', click: () => shell.openPath(path.join(app.getPath('userData'), 'SIGAA')) }, { label: 'Restaurar copia de respaldo…', click: () => restaurarCopia().catch((e) => dialog.showErrorBox('No se pudo restaurar', String(e?.message || e))) }, ...(sinLicencia() ? [] : [{ label: 'Licencia…', click: () => ventanaActivacion(true) }]), { type: 'separator' }, { role: 'quit', label: 'Salir' }] },
    { label: 'Ver', submenu: [{ role: 'reload', label: 'Recargar' }, { role: 'togglefullscreen', label: 'Pantalla completa' }, { role: 'zoomIn', label: 'Acercar' }, { role: 'zoomOut', label: 'Alejar' }, { role: 'resetZoom', label: 'Zoom normal' }] },
  ]));
  // PDF/Excel/enlaces externos: los PDF se abren en una ventana; lo demás en el navegador del sistema
  ventana.webContents.setWindowOpenHandler(({ url }) => {
    // Los PDF generados en pantalla (stickers con QR, vales) se abren desde un enlace blob: del propio servidor local
    const origen = servidor ? new URL(servidor.url).origin : '';
    if (servidor && (url.startsWith(servidor.url) || url.startsWith(`blob:${origen}`))) return { action: 'allow', overrideBrowserWindowOptions: { width: 1000, height: 800, autoHideMenuBar: true } };
    // Solo enlaces web: nunca archivos locales ni otros protocolos (file:, smb:, ms-…).
    if (/^https?:\/\//i.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });
  await ventana.loadURL(servidor!.url);
}

app.whenReady().then(async () => {
  try {
    if (!(await verificarLicencia())) { app.quit(); return; }
    await iniciarServidor();
    await crearVentana();
    vigilarLicencia();
  } catch (e: any) {
    dialog.showErrorBox('SIGAA no pudo iniciar', String(e?.stack || e));
    app.quit();
  }
});
app.on('window-all-closed', () => app.quit());
app.on('before-quit', async () => {
  await servidor?.close().catch(() => {});
});
