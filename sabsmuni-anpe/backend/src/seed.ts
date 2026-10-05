/**
 * Datos iniciales. Idempotente: puede ejecutarse en cada despliegue.
 *  - Producción: solo crea roles, configuración mínima y UN administrador (requiere SEED_ADMIN_PASSWORD).
 *  - Desarrollo/demo: crea además un usuario por rol (contraseña SEED_DEMO_PASSWORD) y datos de ejemplo.
 * Los catálogos CHB y de partidas son EJEMPLOS: cargue los oficiales vigentes desde el panel de administración.
 */
import { NombreRol, PrismaClient } from '@prisma/client';
import * as bcrypt from 'bcryptjs';
import { MARCAS_BASE } from './domain/especificaciones';

const prisma = new PrismaClient();

const ROLES: Record<NombreRol, string> = {
  UNIDAD_SOLICITANTE: 'Formula solicitudes, especificaciones técnicas/TdR, cómputos métricos y justificaciones CHB.',
  RESPONSABLE_PRESUPUESTO: 'Certifica el presupuesto, valida partidas y emite la plantilla del Preventivo C-31 SIGEP.',
  RESPONSABLE_CONTRATACIONES: 'Elabora el DBC, verifica el Formulario V-1, evalúa propuestas y genera cuadros comparativos (incluye Comisión de Calificación).',
  AUTORIDAD_RPA: 'Aprueba el DBC, adjudica o declara desierto y firma contratos u órdenes.',
  ADMINISTRADOR_SISTEMA: 'Gestiona usuarios, configuración institucional, catálogos y respaldos.',
};

async function main() {
  const produccion = process.env.NODE_ENV === 'production';
  for (const [nombre, descripcion] of Object.entries(ROLES))
    await prisma.rol.upsert({ where: { nombre: nombre as NombreRol }, create: { nombre: nombre as NombreRol, descripcion }, update: { descripcion } });
  const rol = async (n: NombreRol) => (await prisma.rol.findUniqueOrThrow({ where: { nombre: n } })).id;

  await prisma.configInstitucional.upsert({
    where: { id: 1 }, update: {},
    create: { id: 1, nombreGam: process.env.GAM_NOMBRE ?? 'Gobierno Autónomo Municipal de Demostración', nit: '1000000000', da: '040', ue: '001', ciudad: 'Cochabamba', departamento: 'Cochabamba', direccion: 'Plaza Principal s/n', rpaNombre: 'Alcalde/sa Municipal (configurar)', rpaCargo: 'Máxima Autoridad Ejecutiva - RPA' },
  });

  const adminPass = process.env.SEED_ADMIN_PASSWORD;
  if (produccion && !adminPass) throw new Error('En producción defina SEED_ADMIN_PASSWORD para crear el administrador inicial.');
  const demoPass = process.env.SEED_DEMO_PASSWORD ?? 'Anpe2026Demo';
  const usuarios: { email: string; nombre: string; cargo: string; unidad: string; rol: NombreRol; password: string }[] = [
    { email: process.env.SEED_ADMIN_EMAIL ?? 'admin@gam.bo', nombre: 'Administrador del Sistema', cargo: 'Administrador', unidad: 'Sistemas', rol: 'ADMINISTRADOR_SISTEMA', password: adminPass ?? demoPass },
  ];
  if (!produccion)
    usuarios.push(
      { email: 'solicitante@gam.bo', nombre: 'Carla Mamani (Obras Públicas)', cargo: 'Jefa de Obras Públicas', unidad: 'Dirección de Obras Públicas', rol: 'UNIDAD_SOLICITANTE', password: demoPass },
      { email: 'presupuesto@gam.bo', nombre: 'Luis Quispe', cargo: 'Responsable de Presupuesto', unidad: 'Dirección Financiera', rol: 'RESPONSABLE_PRESUPUESTO', password: demoPass },
      { email: 'contrataciones@gam.bo', nombre: 'Ana Rojas', cargo: 'Responsable de Contrataciones', unidad: 'Unidad de Contrataciones', rol: 'RESPONSABLE_CONTRATACIONES', password: demoPass },
      { email: 'rpa@gam.bo', nombre: 'Mario Vargas', cargo: 'Máxima Autoridad Ejecutiva - RPA', unidad: 'Despacho', rol: 'AUTORIDAD_RPA', password: demoPass },
    );
  for (const u of usuarios) {
    const { password, rol: r, ...datos } = u;
    await prisma.usuario.upsert({ where: { email: u.email }, update: {}, create: { ...datos, rolId: await rol(r), passwordHash: await bcrypt.hash(password, 12) } });
  }

  for (const m of MARCAS_BASE) await prisma.marcaRegistrada.upsert({ where: { nombre: m }, create: { nombre: m }, update: {} });

  if (!produccion) {
    const partidas = [
      ['22500', 'Mantenimiento y reparación de inmuebles y equipos', 'Servicios no personales'], ['25100', 'Consultorías por producto', 'Servicios no personales'],
      ['34200', 'Productos de minerales no metálicos (cemento, cal, yeso)', 'Materiales y suministros'], ['39500', 'Útiles y materiales eléctricos', 'Materiales y suministros'],
      ['43100', 'Construcciones y mejoras de bienes públicos de dominio privado', 'Activos reales'], ['43200', 'Maquinaria y equipo de oficina', 'Activos reales'],
    ];
    for (const [codigo, descripcion, grupo] of partidas) await prisma.catalogoPartida.upsert({ where: { codigo }, create: { codigo, descripcion, grupo }, update: {} });
    const chb = [
      ['30111505', 'Cemento Portland (EJEMPLO – reemplazar por catálogo CHB oficial)', 'Productor nacional A'],
      ['30111505', 'Cemento Portland (EJEMPLO – reemplazar por catálogo CHB oficial)', 'Productor nacional B'],
      ['30121700', 'Ladrillo cerámico (EJEMPLO)', 'Productor nacional C'],
    ];
    for (const [codigoUnspsc, descripcion, productor] of chb)
      await prisma.catalogoChb.upsert({ where: { codigoUnspsc_productor: { codigoUnspsc, productor } }, create: { codigoUnspsc, descripcion, productor }, update: {} });
  }
  console.log(`Seed completado (${produccion ? 'producción' : 'desarrollo'}). Usuarios: ${usuarios.map((u) => u.email).join(', ')}`);
}

main().catch((e) => { console.error(e); process.exit(1); }).finally(() => prisma.$disconnect());
