import { Body, Controller, Get, Headers, HttpCode, Post, Req, Res } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { Throttle } from '@nestjs/throttler';
import { IsEmail, IsString, MaxLength, MinLength } from 'class-validator';
import { Request, Response } from 'express';
import { COOKIE_REFRESH, Ctx, CtxActual, IpCliente, Public } from '../../common/auth';
import { AuthService } from './auth.service';

class LoginDto {
  @IsEmail() email!: string;
  @IsString() @MinLength(1) @MaxLength(200) password!: string;
}

@ApiTags('Autenticación')
@Controller()
export class AuthController {
  constructor(private readonly auth: AuthService) {}

  /** Inicia sesión: access token (15 min) y refresh token (7 días) en cookies HTTP-only. */
  @Public() @Throttle({ default: { limit: Number(process.env.LOGIN_RATE_LIMIT ?? 10), ttl: 60_000 } }) @Post('auth/login') @HttpCode(200)
  login(@Body() dto: LoginDto, @IpCliente() ip: string, @Headers('user-agent') ua: string, @Res({ passthrough: true }) res: Response) {
    return this.auth.login(dto.email, dto.password, ip, ua, res);
  }

  @Public() @Throttle({ default: { limit: 30, ttl: 60_000 } }) @Post('auth/refresh') @HttpCode(200)
  refresh(@Req() req: Request, @IpCliente() ip: string, @Headers('user-agent') ua: string, @Res({ passthrough: true }) res: Response) {
    return this.auth.refrescar(req.cookies?.[COOKIE_REFRESH], ip, ua, res);
  }

  @Public() @Post('auth/logout') @HttpCode(200)
  logout(@Req() req: Request, @IpCliente() ip: string, @Res({ passthrough: true }) res: Response) {
    return this.auth.logout(req.cookies?.[COOKIE_REFRESH], (req as Request & { user?: { sub: string } }).user?.sub, ip, res);
  }

  @Public() @Get('health')
  health() { return { ok: true }; }

  @Get('auth/me')
  me(@CtxActual() ctx: Ctx) { return { id: ctx.userId, email: ctx.email, rol: ctx.rol }; }
}
