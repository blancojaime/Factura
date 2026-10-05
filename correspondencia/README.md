# Sistema de Correspondencia Digital (municipio rural)

Sistema web de correspondencia interna y externa inspirado en el **CODICE** (Ministerio de Desarrollo Productivo y Economía Plural, Bolivia), diseñado para funcionar con recursos mínimos:

* **PHP 8.1+ puro** (sin frameworks, sin Composer) y **MariaDB / MySQL** — corre en un hosting compartido económico o un VPS pequeño.
* Sin proceso de compilación. Gráficos (Chart.js) y editor (Quill) se cargan desde CDN; si no hay CDN el sistema sigue funcionando (el editor cae a un cuadro de texto).

## Funciones (equivalentes al CODICE y más)

| Manual CODICE | Aquí |
|---|---|
| Login, cambiar contraseña / datos, información de usuario | `auth`, `usuario` |
| Inicio: bandeja, documentos, estadísticas, usuarios dependientes | `dashboard` |
| Bandeja: Entrada (recepción simple y múltiple), Pendientes (semáforo por días), Enviados (cancelar derivación, cuaderno de 6 posiciones), Archivados (carpetas, desarchivar), Agrupados (carátula) | `bandeja` |
| Documentos con NUR y CITE automáticos, asignar NUR existente, adjuntos, imprimir | `documento` |
| Generar respuesta con el mismo NUR | Pendientes → *Generar respuesta* |
| Hojas de ruta, derivación oficial (una vez) + copias, urgente, proveído obligatorio, imprimir | `hoja` |
| Seguimiento por NUR (línea de tiempo, quién la tiene ahora) | `seguimiento` |
| Reportes: pendientes por oficina, recibida, enviada, personalizado | `reporte` (+ exportar CSV) |
| Búsqueda simple y avanzada (restringida a su oficina) | `busqueda` |
| **Nuevo:** ventanilla de correspondencia externa con cargo de recepción | `ventanilla` |
| **Nuevo:** consulta pública del trámite con NUR + código (sin login) | `consulta` |
| **Nuevo:** administración de oficinas, usuarios, roles, tipos de documento; auditoría; respaldo | `admin`, `bin/backup.php` |

Roles: `admin`, `jefe` (reportes de su oficina), `usuario`, `ventanilla`.

## Instalación (hosting compartido)

1. Cree una base de datos MySQL/MariaDB vacía (utf8mb4) y su usuario.
2. Suba la carpeta `correspondencia/` al hosting. Idealmente el *document root* debe apuntar a `correspondencia/public`. Si no se puede, el `.htaccess` de la raíz redirige a `public/` y bloquea `app/`, `config/`, `storage/`, etc.
3. Abra `https://su-dominio/install.php`, complete base de datos, entidad y administrador.
4. **Elimine `public/install.php`** al terminar. Se creó `config/config.php` (no lo comparta) y `storage/installed.lock`.
5. Ingrese como administrador y cree **oficinas** y **usuarios**. Asigne el *jefe inmediato* para ver "usuarios dependientes".

Instalación por consola: `php bin/install.php host base usuario clave "Entidad" SIGLA admin clave_admin`.
Datos de ejemplo (capacitación): `php bin/demo.php` (usuarios `alcalde`, `finanzas`, `obras`, `ventanilla`… clave `Demo12345`).

Requisitos PHP: `pdo_mysql`, `mbstring`, `fileinfo`, `dom` (y `zip` para el respaldo). Se recomienda HTTPS.

## Operación

* **NUR**: `SIGLA/AÑO-00001`, correlativo anual por entidad. **CITE**: `INF/SIGLA/OFICINA Nº 0001/AÑO`, correlativo por tipo, oficina y año. Se asignan dentro de transacciones (sin duplicados).
* **Respaldo diario** (cron): `0 2 * * * php /ruta/correspondencia/bin/backup.php` — guarda los últimos 14 en `storage/backups/` (descárguelos periódicamente a otro equipo).
* Los archivos adjuntos se guardan fuera del acceso web (`storage/uploads`) y se sirven solo a usuarios con acceso a la hoja de ruta.
* Configuración opcional en `config/config.php`: `max_upload_mb`, `dias_alerta_amarillo`, `dias_alerta_rojo`, `debug`.

## Seguridad

Contraseñas con `password_hash`; sesión HttpOnly/SameSite; token CSRF en todo POST; consultas preparadas; salida escapada; HTML del editor saneado por lista blanca; validación de tipo/tamaño de archivos con nombre aleatorio; bloqueo temporal tras intentos fallidos; auditoría de acciones; cabeceras de seguridad (CSP, X-Frame-Options).

## Pruebas

```
DB_USER=... DB_PASS=... php tests/flujo.php        # reglas de negocio (recrea la BD corr_test)
BASE=http://127.0.0.1:8080 node tests/e2e.js        # navegador (Playwright) contra un servidor en marcha
```

Servidor local de desarrollo: `php -S 127.0.0.1:8080 -t public`.

## Limitaciones conocidas / siguientes pasos

* Las certificaciones POA/Presupuestarias del manual (pasajes y viáticos) son específicas del Ministerio y no se incluyen.
* PDF vía impresión del navegador ("Guardar como PDF"); se puede integrar Dompdf si se requiere generación en servidor.
* Notificaciones por correo y firma digital: no incluidas en esta versión.
