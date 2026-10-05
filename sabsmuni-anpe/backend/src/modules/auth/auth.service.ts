import { Injectable, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import * as bcrypt from 'bcryptjs';
import { randomBytes } from 'crypto';
import { Response } from 'express';
import { AuditService } from '../../common/audit.service';
import { COOKIE_ACCESS, COOKIE_REFRESH, UsuarioToken } from '../../common/auth';
import { PrismaService } from '../../common/prisma.service';
import { sha256 } from '../../domain/integridad';

const REFRESH_DIAS = 7;
const DUMMY_HASH = bcrypt.hashSync('no-existe', 12); // iguala el tiempo de respuesta cuando el usuario no existe

@Injectable()
export class AuthService {
  constructor(private readonly prisma: PrismaService, private readonly jwt: JwtService, private readonly audit: AuditService) {}

  private cookieBase() {
    return { httpOnly: true, sameSite: 'strict' as const, secure: process.env.NODE_ENV === 'production' && process.env.COOKIE_SECURE !== 'false' };
  }

  private async emitir(u: { id: string; email: string; nombre: string; rol: { nombre: string } }, ip: string, userAgent: string | undefined, res: Response) {
    const refresh = randomBytes(48).toString('base64url');
    await this.prisma.sesion.create({ data: { usuarioId: u.id, refreshHash: sha256(refresh), ip, userAgent: userAgent?.slice(0, 250), expiraEn: new Date(Date.now() + REFRESH_DIAS * 86_400_000) } });
    const payload: UsuarioToken = { sub: u.id, email: u.email, nombre: u.nombre, rol: u.rol.nombre as UsuarioToken['rol'] };
    const access = await this.jwt.signAsync(payload);
    res.cookie(COOKIE_ACCESS, access, { ...this.cookieBase(), maxAge: 15 * 60_000, path: '/' });
    res.cookie(COOKIE_REFRESH, refresh, { ...this.cookieBase(), maxAge: REFRESH_DIAS * 86_400_000, path: '/api/auth' });
    return { id: u.id, email: u.email, nombre: u.nombre, rol: u.rol.nombre };
  }

  async login(email: string, password: string, ip: string, userAgent: string | undefined, res: Response) {
    const u = await this.prisma.usuario.findUnique({ where: { email: email.toLowerCase().trim() }, include: { rol: true } });
    const ok = await bcrypt.compare(password, u?.passwordHash ?? DUMMY_HASH);
    if (!u || !u.activo || !ok) {
      await this.audit.registrar({ ctx: { ip }, accion: 'LOGIN_FALLIDO', entidad: 'sesion', posterior: { email } });
      throw new UnauthorizedException('Credenciales inválidas.');
    }
    const usuario = await this.emitir(u, ip, userAgent, res);
    await this.audit.registrar({ ctx: { userId: u.id, email: u.email, ip }, accion: 'LOGIN_OK', entidad: 'sesion', entidadId: u.id });
    return usuario;
  }

  /** Rotación de refresh tokens con detección de reutilización (posible robo → se revocan todas las sesiones). */
  async refrescar(token: string | undefined, ip: string, userAgent: string | undefined, res: Response) {
    if (!token) throw new UnauthorizedException('Sin sesión.');
    const s = await this.prisma.sesion.findUnique({ where: { refreshHash: sha256(token) }, include: { usuario: { include: { rol: true } } } });
    if (!s) throw new UnauthorizedException('Sesión inválida.');
    if (s.revocadaEn) {
      await this.prisma.sesion.updateMany({ where: { usuarioId: s.usuarioId, revocadaEn: null }, data: { revocadaEn: new Date() } });
      await this.audit.registrar({ ctx: { userId: s.usuarioId, ip }, accion: 'REFRESH_REUTILIZADO', entidad: 'sesion', entidadId: s.id });
      throw new UnauthorizedException('Sesión revocada.');
    }
    if (s.expiraEn < new Date() || !s.usuario.activo) throw new UnauthorizedException('Sesión expirada.');
    await this.prisma.sesion.update({ where: { id: s.id }, data: { revocadaEn: new Date() } });
    return this.emitir(s.usuario, ip, userAgent, res);
  }

  async logout(token: string | undefined, userId: string | undefined, ip: string, res: Response) {
    if (token) await this.prisma.sesion.updateMany({ where: { refreshHash: sha256(token), revocadaEn: null }, data: { revocadaEn: new Date() } });
    res.clearCookie(COOKIE_ACCESS, { ...this.cookieBase(), path: '/' });
    res.clearCookie(COOKIE_REFRESH, { ...this.cookieBase(), path: '/api/auth' });
    if (userId) await this.audit.registrar({ ctx: { userId, ip }, accion: 'LOGOUT', entidad: 'sesion', entidadId: userId });
    return { ok: true };
  }
}
