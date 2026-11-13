# Puesta en producción — cómo se trabaja de forma oficial

> Las versiones «de prueba» (Docker en una PC o el modo sin Docker con SQLite) sirven para conocer el sistema.
> **El uso oficial se hace con un servidor central**: el sistema se instala una sola vez y todos los funcionarios entran
> con su navegador (Chrome, Edge…) a una dirección de la entidad, por ejemplo `https://sicom.micomuna.gob.bo`.
> **No se instala nada en cada computador de los usuarios.**

## 1. Modelo de trabajo

```
 PC de funcionarios (solo navegador)  ──HTTPS──►  Servidor SICOM-MUNI  ──►  PostgreSQL + archivos
   solicitante, presupuesto, rpa…                 (administrado por Sistemas)       (con respaldo diario)
```

## 2. Dónde alojarlo (elija una)

| Opción | Cuándo conviene | Observaciones |
|---|---|---|
| **A. Servidor o máquina virtual de la entidad (recomendado)** | Hay sala de servidores o virtualización | Ubuntu Server 22.04/24.04 LTS, 2 CPU, 4 GB RAM, 50 GB de disco como mínimo. Docker funciona sin los problemas de virtualización de las PC con Windows |
| B. Servidor en la nube (VPS) | No hay infraestructura propia | Verifique con asesoría legal si los datos pueden alojarse fuera de la entidad; elija un proveedor con respaldos |
| C. Windows Server | Solo si es obligatorio | Es posible con Docker/WSL2, pero requiere más mantenimiento; no es la opción recomendada |

## 3. Instalación en el servidor (la hace el personal de Sistemas)

1. **Preparar el servidor:** Ubuntu actualizado, usuario administrador, firewall abierto solo para los puertos 80 y 443 (y SSH restringido a la red interna).
2. **Instalar Docker:** `curl -fsSL https://get.docker.com | sh`
3. **Obtener el sistema:** `git clone https://github.com/blancojaime/Factura.git && cd Factura/sicom-muni`
4. **Configurar secretos:** `cp .env.example .env` y editar **todas** las claves con valores largos y aleatorios. Definir `PUBLIC_BASE_URL=https://sicom.su-entidad.gob.bo` y `COOKIE_SECURE=true`.
5. **Levantar:** `docker compose up -d --build` (las migraciones de la base se aplican solas).
6. **Cargar solo los datos base** (no los usuarios demo): crear los usuarios reales desde el menú *Usuarios* con el administrador inicial, o ejecutar `docker compose --profile seed run --rm seed` **una vez**, entrar como `admin`, crear los usuarios reales y **desactivar los usuarios demo**; cambiar de inmediato la clave de `admin`.
7. **HTTPS (obligatorio):** poner un proxy inverso con certificado delante del sistema. Ejemplo con Caddy (obtiene y renueva el certificado automáticamente si el servidor es accesible desde internet; en intranet use el certificado de la CA de la entidad):

   ```
   sicom.su-entidad.gob.bo {
       reverse_proxy 127.0.0.1:3000
   }
   ```
   Publicar el contenedor `frontend` solo en `127.0.0.1:3000` y no exponer PostgreSQL ni MinIO a la red.
8. **Probar** desde otra PC de la red con la dirección oficial y recorrer el Ejemplo 1 del manual.

## 4. Datos que la entidad debe cargar

- **Parámetros del GAM** (menú *Parámetros*): nombre, ciudad, DA, UE, gestión, logotipo.
- **Partidas presupuestarias reales** de la gestión (menú *Presupuesto → Registrar partida*), con la estructura programática vigente.
- **Catálogo CHB oficial** (menú *Catálogo CHB*): los 5 bienes incluidos son ilustrativos.
- **Usuarios reales** con su cargo y rol; una persona por cuenta (no compartir claves).
- **Correo SMTP** (variables `SMTP_*`) si se desea enviar fichas por correo.

## 5. Operación continua

| Tarea | Frecuencia | Cómo |
|---|---|---|
| Respaldo de la base | Diario | `docker compose exec db pg_dump -U sicom sicom > /respaldos/sicom_$(date +%F).sql` programado con `cron`; copiar fuera del servidor |
| Respaldo de archivos PDF | Diario | Copiar el volumen `miniodata` (o `mc mirror`) |
| Prueba de restauración | Trimestral | Restaurar en otro equipo y verificar |
| Actualizaciones del sistema operativo | Mensual | `apt update && apt upgrade` |
| Actualizar SICOM-MUNI | Cuando haya versión | `git pull && docker compose up -d --build` |
| Revisión de auditoría | Mensual | Menú *Auditoría → Verificar integridad* |
| Revisión de usuarios | Trimestral | Desactivar cuentas de personal que ya no corresponde |

## 6. Antes de usarlo oficialmente (lista de control)

- [ ] **Validación normativa** por la asesoría legal: topes, plazos, mínimo de cotizaciones, formularios y márgenes de preferencia (parámetros en *Parámetros del GAM*). Esto **no fue verificado** por el equipo de desarrollo.
- [ ] **Resolución o instructivo interno** que apruebe el uso del sistema y defina quién es el RPA, quién certifica, etc.
- [ ] **Validez de los documentos electrónicos:** confirmar con asesoría legal si los PDF con QR y hash tienen validez como expediente o si deben firmarse (firma digital) / imprimirse y firmarse. El sistema **no incluye firma digital**.
- [ ] **Piloto en paralelo** (1 a 2 meses): tramitar algunas contrataciones en el sistema y por el procedimiento actual para comparar.
- [ ] **Capacitación** de cada rol con el Manual de Usuario.
- [ ] **Revisión de seguridad** por Sistemas o un tercero (clave de administrador, accesos, respaldos, certificados HTTPS).
- [ ] **Responsable técnico** designado y plan de soporte.
- [ ] **Conservación documental:** definir cuánto tiempo y dónde se conservan los PDF y los respaldos según la normativa archivística de la entidad.
- [ ] **Procedimiento de contingencia** si el sistema no está disponible (cómo continuar el trámite y registrar después).

## 7. Qué no hace el sistema (conviene saberlo)

- No se conecta al **SIGEP** ni al **SICOES**: el operador copia/pega el bloque de captura y registra allí los números (C-31, F110, CUCE).
- No incluye **firma digital**, **autenticación de dos factores** ni **recuperación de contraseña por correo** (el administrador restablece las claves).
- No ha pasado una **prueba de penetración** ni de **carga** independiente.
- La **validación legal** de reglas y plazos corresponde a la entidad.
