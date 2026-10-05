# Guía paso a paso para probar el sistema de correspondencia
*Para personas sin conocimientos de informática. Tiempo estimado: 1 hora para instalar y 1 hora para probar.*

> **Qué vamos a hacer:** instalar en su computadora con Windows un programa gratuito llamado **XAMPP**, que la convierte en un "mini servidor". Con él probará el sistema **sin internet de pago, sin hosting y sin riesgo**: nada de lo que haga se publica. Cuando termine puede borrarlo todo.

---
## PARTE 1 — Descargar el sistema

1. Abra el navegador (Chrome, Edge o Firefox) e ingrese a este enlace:
   `https://github.com/blancojaime/Factura/archive/refs/heads/claude/beautiful-brahmagupta-ajj7co.zip`
   (Si GitHub le pide ingresar, use su cuenta; el archivo es de su repositorio.)
2. Se descargará un archivo **ZIP** (normalmente a la carpeta *Descargas*).
3. Haga **clic derecho** sobre el ZIP → **Extraer todo…** → **Extraer**.
4. Dentro de la carpeta extraída busque la carpeta llamada **`correspondencia`**. Esa es la que necesitamos (la de su alrededor puede ignorarse). Dentro de ella hay otra carpeta `database` que contiene su Excel **Cargos_y_Oficinas_GAM.xlsx**.

## PARTE 2 — Instalar XAMPP (el "mini servidor")

1. Ingrese a **https://www.apachefriends.org** y pulse el botón **Download** para Windows. Se descarga un instalador (`xampp-windows-x64-…-installer.exe`).
2. Haga doble clic en el instalador.
   * Si aparece un aviso amarillo sobre "antivirus" o "Control de cuentas de usuario", pulse **Sí / OK / Next**.
   * Pulse **Next** en todas las pantallas **sin cambiar nada**; la carpeta de instalación debe ser **`C:\xampp`**.
   * Al terminar, deje marcado "Do you want to start the Control Panel now?" y pulse **Finish**.
3. Se abre el **XAMPP Control Panel** (una ventana con una lista de módulos). Si aparece un idioma, elija English o Deutsch, no importa.
4. En la fila **Apache** pulse **Start**. En la fila **MySQL** pulse **Start**.
   * Cuando funcionan, los nombres **Apache** y **MySQL** se ponen **en verde** y aparecen números de puerto (80, 443 y 3306).
   * Si Windows muestra "Permitir acceso" (firewall), pulse **Permitir acceso**.

> ❗ **Si Apache no se pone verde** (aparece en rojo "Port 80 in use"): otro programa usa el puerto. Cierre Skype, Zoom o similares y pulse Start otra vez. Si sigue igual, vea la sección *Problemas frecuentes* al final.

## PARTE 3 — Poner el sistema dentro de XAMPP

1. Abra la carpeta **`correspondencia`** que extrajo en la Parte 1 y verifique que dentro vea carpetas llamadas `app`, `public`, `database`…
2. **Copie** (clic derecho → Copiar) esa carpeta `correspondencia`.
3. Abra el Explorador de archivos y vaya a **`C:\xampp\htdocs`**. Haga clic derecho en un espacio vacío → **Pegar**.
4. Compruebe que exista: `C:\xampp\htdocs\correspondencia\public` .

## PARTE 4 — Instalar el sistema (una sola vez)

1. En el navegador escriba en la barra de direcciones (arriba) exactamente:
   **`http://localhost/correspondencia/public/install.php`** y pulse Enter.
2. Verá el formulario **"Instalación del sistema de correspondencia"**. Llénelo así:

   | Campo | Qué escribir |
   |---|---|
   | Servidor | `localhost` (ya viene) |
   | Nombre de la base | `correspondencia` (ya viene) |
   | Usuario | `root` (ya viene) |
   | Contraseña (de la base) | **déjela vacía** |
   | Nombre de la entidad | Gobierno Autónomo Municipal de … (el nombre de su municipio) |
   | Sigla | La sigla corta, p. ej. `GAMX` (se usará en los números de documento) |
   | Nombre completo (administrador) | Su nombre |
   | Usuario (administrador) | `admin` |
   | Contraseña (administrador) | Invente una de **al menos 8 letras/números** y **anótela en papel** |

3. Pulse **Instalar**. Si todo sale bien, aparece la pantalla de ingreso con el nombre de su entidad.
   * Si aparece un mensaje rojo, léalo: casi siempre dice que **MySQL no está iniciado** (vuelva al XAMPP Control Panel y pulse Start en MySQL).
4. **Ingreso al sistema** (cada vez): `http://localhost/correspondencia/public/`
   Escriba el usuario `admin` y su contraseña → **Ingresar**.

## PARTE 5 — Cargar las oficinas y cargos desde su Excel

1. Ya dentro como administrador, en la barra azul oscura pulse **Administración**.
2. En el menú de la izquierda pulse **Importar cargos (Excel)**.
3. Pulse **Seleccionar archivo** y elija el Excel:
   `…\correspondencia\database\Cargos_y_Oficinas_GAM.xlsx` → pulse **Subir y revisar**.
4. Aparece un **resumen** (todavía no se creó nada). Debe decir:
   * **4 oficinas nuevas** y **46 usuarios nuevos**.
   * Dos avisos amarillos ⚠ indicando que se corrigieron nombres cortados (es normal).
   * Revise la tabla: cada cargo tiene su usuario (`u401`, `u402`, …), su rol y de quién depende.
5. Si está conforme pulse **Confirmar e importar** y acepte el mensaje.
6. Aparece la lista de **Claves temporales** (una por cada usuario).
   * **Muy importante:** pulse **Imprimir** (o **Descargar en Excel**) y guárdela. **Se muestra una sola vez.** Esas claves se las entregará a cada persona.
   * Cuando la tenga guardada pulse **Ya la guardé, borrar del servidor**.

## PARTE 6 — Poner los nombres reales de las personas

1. Administración → **Asignar nombres**.
2. Para la prueba basta escribir el nombre de **5 personas** (deje las demás vacías):
   * `u401` ALCALDE (SA) MUNICIPAL
   * `u402` SECRETARIO MUNICIPAL ADMINISTRATIVO FINANCIERO
   * `u410` JEFE DE UNIDAD DE CONTRATACIONES
   * `u404` SECRETARIO MUNICIPAL DE OBRAS PUBLICAS
   * `u435` RESPONSABLE DE ARCHIVO
   Escriba nombres cualquiera (por ejemplo, de familiares o amigos) → **Guardar nombres**.
3. Más adelante podrá completar el resto, o editar un usuario en **Administración → Usuarios → Editar**.

## PARTE 7 — Ingresar con otra persona (primer ingreso)

Para ver el trabajo "de varias personas" a la vez, use **tres ventanas distintas**:
* Ventana 1: el navegador normal → **Alcalde** (`u401`).
* Ventana 2: **ventana de incógnito** (Chrome: `Ctrl + Shift + N`; Edge: `Ctrl + Shift + P`; Firefox: `Ctrl + Shift + P`) → **Secretario Administrativo** (`u402`).
* Ventana 3: otro navegador (por ejemplo Edge si usa Chrome) → **Responsable de Archivo** (`u435`).

Primer ingreso de cada persona:
1. Entre a `http://localhost/correspondencia/public/`
2. Usuario: por ejemplo `u401`; clave: la **clave temporal** de la lista impresa.
3. El sistema pedirá **cambiar la contraseña** (es normal y es una medida de seguridad):
   escriba la temporal en "actual", y una nueva de 8 o más caracteres (para la prueba puede usar la misma para todos, ej. `Prueba2026`) dos veces → **Cambiar contraseña**.

## PARTE 8 — Escenarios de prueba

Marque ✔ si funcionó o ✘ si no, y anote observaciones.

### Escenario A — Enviar un documento y recibirlo
| # | Quién | Qué hacer | Resultado esperado | ✔/✘ |
|---|---|---|---|---|
| A1 | Alcalde | Menú **Documentos** → **Informe**. En "Seleccionar funcionario" elija al Secretario Administrativo. Referencia: *Solicitud de presupuesto*. Escriba un texto → **Crear documento** | Aparece el documento con un **NUR** (ej. `GAMX/2026-00001`) y un **CITE** (ej. `INF/GAMX/DAM Nº 0001/2026`) | |
| A2 | Alcalde | Pestaña **Adjuntos** → suba un PDF o foto | El archivo aparece en la lista | |
| A3 | Alcalde | Pulse **Derivar**. Elija al Secretario Administrativo, escriba *Remito para su atención* en Proveído, marque **Urgente** → **Derivar oficial**. Luego derive una **copia** al Secretario de Obras | Aparecen las 2 derivaciones en la tabla de abajo | |
| A4 | Alcalde | Menú **Bandeja → Enviados** | Se ven las 2 derivaciones "aún no recibidas" | |
| A5 | Secretario Adm. (ventana 2) | **Bandeja → Entrada** | Ve 1 correspondencia **URGENTE** con el número rojo en el menú | |
| A6 | Secretario Adm. | Pulse **Recepcionar** | Pasa a **Pendientes** | |
| A7 | Alcalde | Actualice **Enviados** | Ya no aparece la derivación oficial (fue recibida), solo la copia | |

### Escenario B — Responder, reenviar y seguimiento
| # | Quién | Qué hacer | Resultado esperado |
|---|---|---|---|
| B1 | Secretario Adm. | En **Pendientes** pulse **Generar respuesta** → **Nota Interna** → destinatario: Alcalde → **Crear documento** | La respuesta usa el **mismo NUR** (aparece ya escrito) |
| B2 | Secretario Adm. | **Derivar** la hoja de ruta al Jefe de Contrataciones (oficial) | Correcto |
| B3 | Cualquiera | Menú **Seguimiento** → **Ver** | Se ve el recorrido: quién la envió, quién la tiene ahora (resaltado en verde) |
| B4 | Alcalde | Escriba en el buscador (arriba a la derecha) una palabra de la referencia, ej. *presupuesto* → **Buscar** | Aparecen los documentos |
| B5 | Alcalde | Abra un documento (clic en el CITE) → **Imprimir / Guardar PDF** | Se abre el documento listo para imprimir |

### Escenario C — Ordenar la correspondencia
| # | Quién | Qué hacer | Resultado esperado |
|---|---|---|---|
| C1 | Jefe de Contrataciones | Cree 2 documentos nuevos y derívelos oficialmente a una misma persona; esa persona los recibe | Aparecen 2 en Pendientes |
| C2 | Esa persona | Marque ambas casillas → **Agrupar** → elija la principal | Solo queda la principal en Pendientes; en **Agrupados** está el detalle |
| C3 | Esa persona | Marque la principal → **Archivar** → escriba carpeta *Correspondencia 2026* | Se ve en **Archivados** dentro de la carpeta; allí puede **Desarchivar** |
| C4 | Alcalde | Derive algo y, **antes de que lo reciban**, en **Enviados** pulse **Cancelar derivación** | La hoja vuelve a sus Pendientes |

### Escenario D — Ventanilla (correspondencia de ciudadanos)
| # | Quién | Qué hacer | Resultado esperado |
|---|---|---|---|
| D1 | Responsable de Archivo (ventana 3) | Menú **Ventanilla → Registrar nueva**. Remitente: *Comunidad Tacopaya*; referencia: *Solicitud de camino*; destinatario: Secretario de Obras → **Registrar y derivar** | Aparece el **cargo de recepción** con NUR y un **código de 6 letras/números** |
| D2 | Cualquiera | En otra ventana abra `http://localhost/correspondencia/public/index.php?r=consulta/index`, escriba el NUR y el código | Muestra en qué oficina está el trámite **sin pedir usuario** |

### Escenario E — Reportes y administración
| # | Quién | Qué hacer | Resultado esperado |
|---|---|---|---|
| E1 | Secretario Adm. | **Reportes → Pendientes oficina** | Gráfico y tabla por funcionario |
| E2 | Secretario Adm. | **Reportes → Correspondencia recibida** → **Generar reporte** → **Exportar CSV** | Descarga un archivo que abre en Excel |
| E3 | Administrador | **Administración → Auditoría** | Lista de quién hizo qué y cuándo |
| E4 | Alcalde | Intente abrir `…/index.php?r=admin/usuarios` | Mensaje "No tiene permiso" |

### Escenario F — Seguridad básica
| # | Qué hacer | Resultado esperado |
|---|---|---|
| F1 | Intente ingresar con una clave equivocada | "Usuario o contraseña incorrectos" |
| F2 | Con una persona que **no participó** (p. ej. un Subalcalde) intente ver un NUR ajeno | "No tiene acceso" |

## PARTE 9 — Si algo falla: cómo avisar
Anote: **(1)** qué escenario y número (ej. "B2"), **(2)** qué hizo, **(3)** qué esperaba y **(4)** qué pasó. Saque una **captura de pantalla** (tecla *Windows + Shift + S*) y envíela. Con eso se puede corregir rápido.

## Problemas frecuentes
* **Apache no inicia (puerto 80 ocupado):** en el XAMPP Control Panel, fila Apache → **Config → httpd.conf**; busque `Listen 80` y cámbielo por `Listen 8080`; guarde, pulse Start y use las direcciones con `:8080`, ej. `http://localhost:8080/correspondencia/public/`.
* **"Access denied" / no conecta a la base:** MySQL no está en verde; pulse Start. La contraseña de la base en XAMPP es **vacía**.
* **Página en blanco o error:** vea `C:\xampp\htdocs\correspondencia\storage\logs\error.log` y envíe su contenido.
* **Olvidé la clave del administrador:** borre la carpeta de datos con el botón **Admin** de MySQL (phpMyAdmin: `http://localhost/phpmyadmin`) → base `correspondencia` → tabla `usuarios` → editar, o repita la instalación borrando la base `correspondencia` y el archivo `correspondencia\config\config.php`.
* **Quiero empezar de cero:** en `http://localhost/phpmyadmin` elimine la base `correspondencia`, borre `config\config.php` y `storage\installed.lock`, y repita la Parte 4.
* **Los gráficos o el editor de textos enriquecido no aparecen:** necesitan internet (usan bibliotecas en línea). Sin internet el sistema funciona igual, pero el texto se escribe en un cuadro simple.

## Cuando la prueba termine: pasar a un servicio real
1. Contrate un hosting con **PHP 8 y MySQL** (cualquier hosting compartido económico).
2. Suba la carpeta `correspondencia` (por el Administrador de archivos de cPanel) e instale con `install.php` usando los datos de base de datos que le dé el hosting.
3. **Borre `public/install.php`** y configure un respaldo diario (ver `README.md`).
