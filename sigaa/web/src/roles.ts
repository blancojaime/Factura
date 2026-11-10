/** Roles del sistema con su color institucional (formal) para distinguirlos en toda la interfaz. */
export interface RolInfo { codigo: string; nombre: string; mod?: 'alm' | 'com' | 'af'; color: string; descripcion: string }

export const ROLES_INFO: RolInfo[] = [
  { codigo: 'ADMIN', nombre: 'Administrador del sistema', color: '#7a1f3d', descripcion: 'Acceso total: configuración, usuarios, bitácora, catálogos y los tres módulos.' },
  { codigo: 'ALMACEN', nombre: 'Administración de Almacenes', mod: 'alm', color: '#1f4e8c', descripcion: 'Registra y modifica en Almacenes: ingresos, salidas, inventarios, bajas, transferencias y cierre.' },
  { codigo: 'COMBUSTIBLE', nombre: 'Administración de Combustible', mod: 'com', color: '#a85a0b', descripcion: 'Registra y modifica en Combustible: recepción, emisión y descargo de vales, turriles, viajes y conciliación.' },
  { codigo: 'ACTIVOS', nombre: 'Administración de Activos Fijos', mod: 'af', color: '#17693f', descripcion: 'Registra y modifica en Activos Fijos: ingresos, codificación, fichas, asignaciones, movimientos y etiquetas.' },
  { codigo: 'CONSULTA', nombre: 'Consulta', color: '#4a5568', descripcion: 'Solo lectura: puede ver información y descargar reportes y documentos; no registra nada.' },
];

export const rolInfo = (codigo: string) => ROLES_INFO.find((r) => r.codigo === codigo);

/** Color principal de un usuario (el de su primer rol, con ADMIN primero). */
export function colorPrincipal(roles: string[]): string {
  for (const r of ROLES_INFO) if (roles.includes(r.codigo)) return r.color;
  return '#4a5568';
}

/** Módulo según la ruta actual (para teñir la pantalla con el color de su rol). */
export function moduloDeRuta(path: string): 'alm' | 'com' | 'af' | '' {
  if (path.startsWith('/almacenes')) return 'alm';
  if (path.startsWith('/combustible')) return 'com';
  if (path.startsWith('/activos')) return 'af';
  return '';
}
