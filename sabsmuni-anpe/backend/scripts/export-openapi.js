// Genera docs/openapi.json a partir de la aplicación compilada (requiere DATABASE_URL accesible).
require('reflect-metadata');
const fs = require('fs');
const path = require('path');
const { NestFactory } = require('@nestjs/core');
const { DocumentBuilder, SwaggerModule } = require('@nestjs/swagger');
const { AppModule } = require('../dist/app.module');
(async () => {
  const app = await NestFactory.create(AppModule, { logger: false });
  const doc = SwaggerModule.createDocument(app, new DocumentBuilder().setTitle('SABSMUNI-ANPE API').setVersion('1.0').addCookieAuth('access_token').build());
  fs.writeFileSync(path.join(__dirname, '../../docs/openapi.json'), JSON.stringify(doc, null, 2));
  await app.close();
  console.log('docs/openapi.json generado:', Object.keys(doc.paths).length, 'rutas');
})();
