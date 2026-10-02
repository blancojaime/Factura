/**
 * SIGAA Escritorio: ventana Electron que ejecuta el servidor de SIGAA en el mismo equipo
 * con una base de datos SQLite local (carpeta de datos del usuario) y abre la aplicación web.
 *
 * Datos: <datos del usuario>/SIGAA/sigaa.sqlite  ·  Fotos: <datos del usuario>/SIGAA/fotos
 * Para usar PostgreSQL en vez de SQLite defina la variable de entorno DATABASE_URL antes de abrir la aplicación.
 */
import { app, BrowserWindow, dialog, Menu, shell } from 'electron';
import path from 'node:path';
import fs from 'node:fs';

let ventana: BrowserWindow | null = null;
let servidor: { url: string; close(): Promise<void> } | null = null;

/** Recursos copiados junto a este archivo por scripts/copiar.mjs (dentro del asar al empaquetar). */
function recursos() {
  return { server: path.join(__dirname, 'server', 'start.js'), web: path.join(__dirname, 'web'), seed: path.join(__dirname, 'seed') };
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
    demo: nueva && process.env.SIGAA_DEMO !== '0', // primera ejecución: carga de ejemplo para conocer el sistema
    logger: false,
  });
}

async function crearVentana() {
  ventana = new BrowserWindow({ width: 1440, height: 900, minWidth: 1000, minHeight: 640, title: 'SIGAA', backgroundColor: '#14263f', webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true } });
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    { label: 'SIGAA', submenu: [{ label: 'Abrir carpeta de datos', click: () => shell.openPath(path.join(app.getPath('userData'), 'SIGAA')) }, { type: 'separator' }, { role: 'quit', label: 'Salir' }] },
    { label: 'Ver', submenu: [{ role: 'reload', label: 'Recargar' }, { role: 'togglefullscreen', label: 'Pantalla completa' }, { role: 'zoomIn', label: 'Acercar' }, { role: 'zoomOut', label: 'Alejar' }, { role: 'resetZoom', label: 'Zoom normal' }] },
  ]));
  // PDF/Excel/enlaces externos: los PDF se abren en una ventana; lo demás en el navegador del sistema
  ventana.webContents.setWindowOpenHandler(({ url }) => {
    if (servidor && url.startsWith(servidor.url)) return { action: 'allow', overrideBrowserWindowOptions: { width: 1000, height: 800, autoHideMenuBar: true } };
    shell.openExternal(url);
    return { action: 'deny' };
  });
  await ventana.loadURL(servidor!.url);
}

app.whenReady().then(async () => {
  try {
    await iniciarServidor();
    await crearVentana();
  } catch (e: any) {
    dialog.showErrorBox('SIGAA no pudo iniciar', String(e?.stack || e));
    app.quit();
  }
});
app.on('window-all-closed', () => app.quit());
app.on('before-quit', async () => {
  await servidor?.close().catch(() => {});
});
