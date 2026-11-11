import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('sigaaLic', {
  estado: () => ipcRenderer.invoke('lic:estado'),
  activar: (clave: string) => ipcRenderer.invoke('lic:activar', clave),
  continuar: () => ipcRenderer.invoke('lic:continuar'),
  copiar: (texto: string) => ipcRenderer.invoke('lic:copiar', texto),
  cerrar: () => ipcRenderer.invoke('lic:cerrar'),
});
