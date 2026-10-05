import 'reflect-metadata';
import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { NestExpressApplication } from '@nestjs/platform-express';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import cookieParser from 'cookie-parser';
import helmet from 'helmet';
import { AppModule } from './app.module';

export async function configurar(app: NestExpressApplication) {
  app.set('trust proxy', 1);
  app.use(helmet());
  app.use(cookieParser());
  app.setGlobalPrefix('api');
  app.enableCors({ origin: (process.env.FRONTEND_ORIGIN ?? 'http://localhost:3000').split(','), credentials: true });
  app.useGlobalPipes(new ValidationPipe({ whitelist: true, forbidNonWhitelisted: true, transform: true }));
}

async function bootstrap() {
  const app = await NestFactory.create<NestExpressApplication>(AppModule);
  await configurar(app);
  // Swagger solo fuera de producción, o si se habilita explícitamente con SWAGGER_ENABLED=true.
  if (process.env.NODE_ENV !== 'production' || process.env.SWAGGER_ENABLED === 'true') {
    const doc = SwaggerModule.createDocument(app, new DocumentBuilder().setTitle('SABSMUNI-ANPE API').setDescription('Gestión y documentación de contrataciones ANPE (NB-SABS D.S. 0181)').setVersion('1.0').addCookieAuth('access_token').addBearerAuth().build());
    SwaggerModule.setup('api/docs', app, doc);
  }
  await app.listen(Number(process.env.PORT ?? 4000), '0.0.0.0');
}
if (require.main === module) bootstrap();
