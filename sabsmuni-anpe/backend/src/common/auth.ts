import { CanActivate, createParamDecorator, ExecutionContext, ForbiddenException, Injectable, SetMetadata, UnauthorizedException } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { JwtService } from '@nestjs/jwt';
import { Request } from 'express';
import { Rol } from '../domain/flujo';

export interface UsuarioToken { sub: string; email: string; nombre: string; rol: Rol }
export interface Ctx { userId: string; email: string; rol: Rol; ip: string }

export const IS_PUBLIC = 'isPublic';
export const Public = () => SetMetadata(IS_PUBLIC, true);
export const ROLES_KEY = 'roles';
export const Roles = (...roles: Rol[]) => SetMetadata(ROLES_KEY, roles);

export const COOKIE_ACCESS = 'access_token';
export const COOKIE_REFRESH = 'refresh_token';

export const clienteIp = (req: Request): string => req.ip || req.socket?.remoteAddress || 'desconocida';

/** Contexto de usuario autenticado (id, rol, IP) para auditoría y reglas de negocio. */
export const CtxActual = createParamDecorator((_: unknown, ec: ExecutionContext): Ctx => {
  const req = ec.switchToHttp().getRequest<Request & { user: UsuarioToken }>();
  return { userId: req.user.sub, email: req.user.email, rol: req.user.rol, ip: clienteIp(req) };
});
export const IpCliente = createParamDecorator((_: unknown, ec: ExecutionContext) => clienteIp(ec.switchToHttp().getRequest<Request>()));

@Injectable()
export class JwtAuthGuard implements CanActivate {
  constructor(private readonly jwt: JwtService, private readonly reflector: Reflector) {}
  async canActivate(ec: ExecutionContext): Promise<boolean> {
    if (this.reflector.getAllAndOverride<boolean>(IS_PUBLIC, [ec.getHandler(), ec.getClass()])) return true;
    const req = ec.switchToHttp().getRequest<Request & { user?: UsuarioToken }>();
    const bearer = req.headers.authorization?.startsWith('Bearer ') ? req.headers.authorization.slice(7) : undefined;
    const token = req.cookies?.[COOKIE_ACCESS] ?? bearer;
    if (!token) throw new UnauthorizedException('Sesión no iniciada.');
    try {
      req.user = await this.jwt.verifyAsync<UsuarioToken>(token);
      return true;
    } catch {
      throw new UnauthorizedException('Sesión expirada o inválida.');
    }
  }
}

@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private readonly reflector: Reflector) {}
  canActivate(ec: ExecutionContext): boolean {
    const roles = this.reflector.getAllAndOverride<Rol[]>(ROLES_KEY, [ec.getHandler(), ec.getClass()]);
    if (!roles?.length) return true;
    const user = ec.switchToHttp().getRequest<{ user?: UsuarioToken }>().user;
    if (!user || !roles.includes(user.rol)) throw new ForbiddenException(`Su rol no está autorizado para esta operación (requiere: ${roles.join(' / ')}).`);
    return true;
  }
}
