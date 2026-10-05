import { Global, Module } from '@nestjs/common';
import { APP_GUARD, APP_INTERCEPTOR } from '@nestjs/core';
import { JwtModule } from '@nestjs/jwt';
import { ThrottlerGuard, ThrottlerModule } from '@nestjs/throttler';
import { AuditService } from './common/audit.service';
import { JwtAuthGuard, RolesGuard } from './common/auth';
import { CalendarioProvider } from './common/calendario.provider';
import { DecimalInterceptor } from './common/decimal.interceptor';
import { PrismaService } from './common/prisma.service';
import { ProcesoRepo } from './common/proceso.repo';
import { StorageService } from './common/storage.service';
import { AdminController } from './modules/admin/admin.controller';
import { AuthController } from './modules/auth/auth.controller';
import { AuthService } from './modules/auth/auth.service';
import { DocumentosController } from './modules/documentos/documentos.controller';
import { DocumentosService } from './modules/documentos/documentos.service';
import { ExpedienteService } from './modules/documentos/expediente.service';
import { ContratosService } from './modules/procesos/contratos.service';
import { CronogramaService } from './modules/procesos/cronograma.service';
import { FlujoService } from './modules/procesos/flujo.service';
import { PresupuestoService } from './modules/procesos/presupuesto.service';
import { ProcesosController } from './modules/procesos/procesos.controller';
import { ProcesosService } from './modules/procesos/procesos.service';
import { PropuestasService } from './modules/procesos/propuestas.service';
import { RequerimientoService } from './modules/procesos/requerimiento.service';
import { PdfService } from './pdf/pdf.service';

export const jwtSecret = (): string => {
  const s = process.env.JWT_SECRET;
  if (!s || s.length < 32) {
    if (process.env.NODE_ENV === 'production') throw new Error('JWT_SECRET debe definirse con al menos 32 caracteres en producción.');
    return 'dev-only-secret-dev-only-secret-dev-only-secret';
  }
  return s;
};

@Global()
@Module({
  imports: [
    JwtModule.register({ global: true, secret: jwtSecret(), signOptions: { expiresIn: '15m', algorithm: 'HS256' }, verifyOptions: { algorithms: ['HS256'] } }),
    ThrottlerModule.forRoot([{ ttl: 60_000, limit: 300 }]),
  ],
  controllers: [AuthController, AdminController, ProcesosController, DocumentosController],
  providers: [
    PrismaService, AuditService, StorageService, CalendarioProvider, ProcesoRepo, PdfService, AuthService,
    DocumentosService, ExpedienteService, ProcesosService, RequerimientoService, CronogramaService, PresupuestoService, PropuestasService, ContratosService, FlujoService,
    { provide: APP_GUARD, useClass: ThrottlerGuard }, { provide: APP_GUARD, useClass: JwtAuthGuard }, { provide: APP_GUARD, useClass: RolesGuard },
    { provide: APP_INTERCEPTOR, useClass: DecimalInterceptor },
  ],
})
export class AppModule {}
