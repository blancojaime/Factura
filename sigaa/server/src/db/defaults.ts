/** Parámetros de configuración unificados (valores iniciales tomados de los tres sistemas originales). */
export interface CfgDef {
  clave: string;
  valor: string;
  descripcion: string;
  modulo: 'core' | 'alm' | 'com' | 'af';
}

const c = (modulo: CfgDef['modulo'], clave: string, valor: string, descripcion: string): CfgDef => ({ clave, valor, descripcion, modulo });

export const DEFAULT_CONFIG: CfgDef[] = [
  // Entidad (compartida por los tres módulos)
  c('core', 'Entidad', 'GOBIERNO AUTÓNOMO MUNICIPAL DE CALAMARCA', 'Nombre de la entidad (encabezado de todos los documentos)'),
  c('core', 'Sigla', 'GAMC', 'Sigla de la entidad'),
  c('core', 'NitEntidad', '1234567019', 'NIT de la entidad (facturas de compra directa)'),
  c('core', 'Secretaria', 'SECRETARÍA MUNICIPAL ADMINISTRATIVA Y FINANCIERA', 'Secretaría / Dirección administrativa'),
  c('core', 'Municipio', 'Calamarca', "Se usa en 'Lugar y fecha' de los documentos"),
  c('core', 'Departamento', 'La Paz', 'Departamento'),
  c('core', 'Gestion', '2026', 'Gestión fiscal (reinicia la numeración: CGI-0001/2026)'),
  c('core', 'Logo', '', 'Ruta del logotipo (JPG/PNG) que aparece en los documentos'),
  // Firmantes
  c('core', 'NombreMAE', 'ING. EDGAR NINA CALLISAYA', 'Máxima Autoridad Ejecutiva (firma memorándums y autoriza bajas)'),
  c('core', 'CargoMAE', 'ALCALDE MUNICIPAL', 'Cargo de la MAE'),
  c('core', 'NombreSEC', 'LIC. JUAN CARLOS MAMANI APAZA', 'Secretario/Director Administrativo Financiero (autoriza sobrantes, bajas, reposiciones, vales)'),
  c('core', 'CargoSEC', 'SECRETARIO MUNICIPAL ADMINISTRATIVO Y FINANCIERO', 'Cargo del Secretario/Director Adm. Financiero'),
  c('core', 'NombreJBS', 'LIC. ROSA MARÍA CHOQUE TICONA', 'Jefe de Bienes y Servicios'),
  c('core', 'CargoJBS', 'JEFE DE BIENES Y SERVICIOS', 'Cargo del Jefe de Bienes y Servicios'),
  c('core', 'NombreCON', 'LIC. ELVIRA FLORES CRUZ', 'Responsable de Contabilidad (registro contable, informe semanal de activos)'),
  c('core', 'CargoCON', 'RESPONSABLE DE CONTABILIDAD', 'Cargo del Contador'),
  c('core', 'NombreJUR', 'DR. WILFREDO LAURA CONDORI', 'Responsable Jurídico (informe legal y resolución administrativa)'),
  c('core', 'CargoJUR', 'SECRETARIO MUNICIPAL DE ASUNTOS JURÍDICOS', 'Cargo del Responsable Jurídico'),
  c('core', 'NombreTRA', 'LIC. PATRICIA YUJRA MAMANI', 'Responsable de Transparencia (veedor)'),
  c('core', 'CargoTRA', 'RESPONSABLE DE TRANSPARENCIA', 'Cargo del Responsable de Transparencia'),
  c('core', 'NombreSMG', 'ING. ROSA CONDORI APAZA', 'Secretario(a) Municipal General (programación de maquinaria)'),
  c('core', 'CargoSMG', 'SECRETARIO MUNICIPAL GENERAL', 'Cargo del Secretario Municipal General'),
  c('core', 'NombreContrat', 'LIC. ANA MARÍA FLORES TOLA', 'Responsable de Contrataciones'),
  c('core', 'CargoContrat', 'RESPONSABLE DE CONTRATACIONES', 'Cargo del Responsable de Contrataciones'),
  c('core', 'NombreRAF', 'TÉC. JUAN CARLOS LIMACHI POMA', 'Responsable de Activos Fijos y Almacenes (provisión de combustible, entrega de activos)'),
  c('core', 'CargoRAF', 'RESPONSABLE DE ACTIVOS FIJOS Y ALMACENES', 'Cargo del Responsable de Activos Fijos'),
  // Almacenes
  c('alm', 'UnidadAlm', 'UNIDAD DE BIENES Y SERVICIOS - ALMACENES', 'Unidad responsable del almacén'),
  c('alm', 'NombreALM', 'TÉC. MARIO CONDORI QUISPE', 'Encargado de Almacenes (firma ingresos, salidas e inventarios)'),
  c('alm', 'CargoALM', 'ENCARGADO DE ALMACENES', 'Cargo del Encargado de Almacenes'),
  c('alm', 'DiaPedidoIni', '1', 'Día de inicio de pedidos del mes (Manual 11: del 1 al 25 de cada mes)'),
  c('alm', 'DiaPedidoFin', '25', 'Día de cierre de pedidos del mes'),
  c('alm', 'MaxPedidosMes', '1', 'Pedidos máximos por funcionario al mes (excepciones requieren justificación)'),
  c('alm', 'CantElevada', '50', 'Cantidad considerada elevada: exige Nota Interna de justificación'),
  c('alm', 'DiasVenc', '90', 'Días de alerta antes del vencimiento'),
  c('alm', 'DiasSinMov', '730', 'Días sin movimiento para obsolescencia (dos gestiones)'),
  c('alm', 'DiasAlertaSeg', '30', 'Días de alerta de extintores / seguros'),
  c('alm', 'DiasPublicacion', '15', 'Días hábiles mínimos de publicación SICOES (entrega gratuita y subasta)'),
  c('alm', 'ConteoCiego', 'SI', 'Hoja de conteo sin saldos del sistema (SI/NO)'),
  c('alm', 'SepCodigoAlm', '-', 'Separador del código de ítem: 1-1-0000001'),
  // Activos fijos
  c('af', 'UnidadAF', 'UNIDAD DE ACTIVOS FIJOS', 'Unidad responsable de activos fijos'),
  c('af', 'ValorMinimo', '500', 'Valor mínimo de activo fijo (Bs) — RI-02: bienes menores se alertan en el ingreso'),
  c('af', 'SepCodigo', '-', 'Separador del código de activo: 001-03-03007-01 (15 caracteres, límite VSIAF)'),
  // Combustible
  c('com', 'LITROS_DIA_EJECUTIVO', '16', 'Litros por día hábil (lunes a sábado) para uso ejecutivo — DS 27327 Art. 19'),
  c('com', 'STOCK_MIN_30', '20', 'Stock mínimo de vales de Bs 30 (alerta)'),
  c('com', 'STOCK_MIN_50', '20', 'Stock mínimo de vales de Bs 50 (alerta)'),
  c('com', 'STOCK_MIN_100', '10', 'Stock mínimo de vales de Bs 100 (alerta)'),
  c('com', 'TOLERANCIA_RENDIMIENTO', '0.2', 'Tolerancia del rendimiento real frente al de referencia (0,2 = 20%); fuera de ella el descargo queda Observado'),
  c('com', 'MAX_DESCARGOS_PENDIENTES', '2', 'Descargos vencidos que puede acumular un conductor antes de bloquear nuevas entregas (0 = sin límite)'),
  c('com', 'DIAS_PLAZO_DESCARGO', '3', 'Días después del fin del periodo para presentar el descargo (Anexo 3)'),
  c('com', 'PLANILLA_AL_EMITIR', 'SI', 'SI = al emitir vales se genera la planilla de descargo del conductor'),
  c('com', 'CORTES_VALE', '30,50,100', 'Cortes de vale disponibles (Bs)'),
];
