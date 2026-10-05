import { CallHandler, ExecutionContext, Injectable, NestInterceptor, StreamableFile } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import { Observable, map } from 'rxjs';

const convertir = (v: unknown): unknown => {
  if (v === null || v === undefined) return v;
  if (Prisma.Decimal.isDecimal(v)) return Number(v);
  if (typeof v === 'bigint') return v.toString();
  if (v instanceof Date || Buffer.isBuffer(v) || v instanceof StreamableFile) return v;
  if (Array.isArray(v)) return v.map(convertir);
  if (typeof v === 'object') return Object.fromEntries(Object.entries(v as object).map(([k, x]) => [k, convertir(x)]));
  return v;
};

/** Prisma serializa Decimal como string; la API expone números (importes en Bs con 2 decimales). */
@Injectable()
export class DecimalInterceptor implements NestInterceptor {
  intercept(_: ExecutionContext, next: CallHandler): Observable<unknown> {
    return next.handle().pipe(map(convertir));
  }
}
