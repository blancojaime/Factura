---
title: "CONTA JB 2.3 — Manual de Activación de la Licencia"
subtitle: "Solicitud de activación y códigos de activación: uso para el cliente y para el proveedor"
lang: es
---

# 1. Qué es la activación

CONTA JB se puede usar **30 días en modo de prueba** desde el primer ingreso. Para seguir usándolo debe **activarse** con un código que solo el proveedor puede emitir. El proceso tiene dos códigos:

| Código | Quién lo genera | Para qué sirve |
|---|---|---|
| **Código de solicitud** (`JB-XXXX-XXXX-XXXX-XXXX-XXXX`) | CONTA JB, en el equipo del cliente | Identifica **ese equipo**. El cliente se lo envía al proveedor |
| **Código de activación** (cadena larga de letras y números) | El proveedor, con su clave privada | Activa **solo ese equipo**, por un plazo (por ejemplo 1 año) o de forma perpetua |

**Cómo funciona por dentro (resumen técnico).** El código de activación es una **firma digital** (Ed25519) del código de solicitud y de la fecha de vencimiento. El programa solo contiene la clave **pública**: puede *comprobar* la firma pero no *fabricar* códigos. Un código emitido para un equipo **no sirve en otro**, y si se altera un solo carácter es rechazado.

![Flujo de activación](img/flujo_activacion.png){width=100%}

# 2. Guía para el cliente (usuario del sistema)

## 2.1 Primer ingreso: modo de prueba

Al abrir CONTA JB por primera vez aparece la pantalla de **Activación**. Muestra:

- el estado («Modo de prueba: quedan 30 días»);
- su **código de solicitud**, con el botón **Copiar**;
- un recuadro para pegar el **código de activación**.

![Pantalla de activación](img/70_activacion.png){width=80%}

Pulse **Continuar en modo de prueba** para trabajar normalmente. Cada vez que abra el programa durante la prueba verá esta pantalla con los días que restan.

## 2.2 Solicitar la activación

1. En la pantalla de activación pulse **Copiar** (o, con el programa abierto, menú **Ayuda > Activación de la licencia…**).
2. Pegue el código en un correo o mensaje de WhatsApp a su proveedor, indicando el nombre de la empresa y el plazo deseado.
3. Espere el **código de activación**.

> El código de solicitud depende del equipo (identificador de Windows). **No cambia** al reinstalar CONTA JB ni al actualizarlo; **sí cambia** si se formatea el equipo o se pasa el programa a otra computadora (en ese caso solicite una nueva activación).

## 2.3 Aplicar el código de activación

1. Abra **Ayuda > Activación de la licencia…** (o la pantalla de inicio).
2. **Pegue** el código recibido en el recuadro. No importa si tiene espacios, saltos de línea o minúsculas.
3. Pulse **Activar**.

**Resultado esperado:** mensaje «¡CONTA JB quedó activado!» y el estado cambia a *Licencia perpetua* o *Licencia vigente hasta el dd/mm/aaaa*. Ya no volverá a aparecer la pantalla al iniciar.

## 2.4 Mensajes y qué hacer

| Mensaje | Causa | Qué hacer |
|---|---|---|
| «El código de activación no corresponde a este equipo o no es auténtico» | El código es de otro equipo, está mal copiado o fue alterado | Verifique que envió el código de solicitud **de este equipo**; copie el código completo otra vez |
| «El código de activación está incompleto o es incorrecto» | Faltan caracteres al pegar | Copie desde el primer hasta el último carácter |
| «El código de activación tiene caracteres no válidos» | Se pegó texto que no es el código | Pegue solo el código |
| «La licencia venció el dd/mm/aaaa» | Terminó el plazo de la licencia | Solicite renovación con el mismo código de solicitud |
| «El período de prueba terminó» | Pasaron 30 días sin activar | Solicite la activación; los datos **no se pierden** |
| «La fecha del equipo es anterior a la del último uso» | Se retrasó el reloj de Windows | Corrija la fecha y hora del equipo |

> **Sus datos están seguros.** Aunque la prueba o la licencia venza, **no se borra ni se bloquea la información**: solo se pide activar para volver a entrar. Puede activar y recuperar el acceso en cualquier momento.

## 2.5 Renovación y cambio de equipo

- **Renovación:** envíe de nuevo su código de solicitud (es el mismo) y reciba un código con nueva fecha. Péguelo en *Activación de la licencia…*.
- **Cambio de computadora:** instale CONTA JB en la nueva, copie sus datos con una **copia de seguridad** (*Administración > Copias de seguridad*) y solicite una nueva activación con el código de solicitud del equipo nuevo.

# 3. Guía para el proveedor (quien emite los códigos)

## 3.1 Qué necesita

- El archivo de **clave privada**: `clave_privada_contajb.pem`.
- El **código de solicitud** que le envía el cliente.
- Un usuario **administrador** de CONTA JB (la opción solo aparece para administradores).

> **La clave privada es lo más importante.** Quien la tenga puede emitir licencias. Guárdela **fuera de los equipos de los clientes** (por ejemplo, en una memoria USB y en una copia en un lugar seguro). **No** la suba a GitHub, no la envíe por correo y no la incluya en el instalador. Si la pierde no podrá emitir códigos para las instalaciones existentes; si se filtra, deberá generarse un par de claves nuevo y una nueva versión del programa (ver 3.4).

## 3.2 Emitir un código de activación

1. Abra CONTA JB con un usuario administrador.
2. Menú **Ayuda > Emitir código de activación (proveedor)…**.
3. En **Archivo de clave privada** pulse **Examinar…** y elija `clave_privada_contajb.pem`.
4. Pegue el **código de solicitud** del cliente.
5. Elija el plazo: marque **Licencia perpetua** o desmárquela y fije la fecha de **vencimiento** (por ejemplo, dentro de un año).
6. Pulse **Generar código**, luego **Copiar código** y envíelo al cliente.

![Emisión del código de activación](img/71_emision_codigo.png){width=80%}

**Recomendación de control:** lleve un registro (Excel) con: cliente, fecha, código de solicitud, plazo y vencimiento.

## 3.3 Verificar un código antes de enviarlo

El propio sistema valida la forma del código de solicitud (22 caracteres con prefijo JB) y rechaza fechas inválidas. Si lo desea, pida al cliente que envíe una captura del mensaje de éxito tras activar.

## 3.4 Generar un par de claves nuevo (casos excepcionales)

Solo si la clave privada se perdió o se filtró. Un técnico con Python ejecuta:

```
python -c "from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey as K; from cryptography.hazmat.primitives import serialization as S; k=K.generate(); open('clave_privada_contajb.pem','wb').write(k.private_bytes(S.Encoding.PEM,S.PrivateFormat.PKCS8,S.NoEncryption())); print(k.public_key().public_bytes(S.Encoding.Raw,S.PublicFormat.Raw).hex())"
```

El texto impreso (clave **pública**) se coloca en `contabol/licencia.py` (`CLAVE_PUBLICA_HEX`) y se publica una nueva versión; los clientes deberán actualizar y volver a activar.

# 4. Preguntas frecuentes

| Pregunta | Respuesta |
|---|---|
| ¿Puede el cliente generar sus propios códigos? | No: el programa no contiene la clave privada |
| ¿Sirve el mismo código en dos computadoras? | No: cada código está firmado para un código de solicitud |
| ¿Qué pasa si reinstalo o actualizo? | Se mantiene la activación (los datos están en `%LOCALAPPDATA%\ContaJB`) |
| ¿Qué pasa si borro la carpeta de datos? | Se pierde también la activación y la información: restaure su copia de seguridad |
| ¿Funciona sin Internet? | Sí, la activación es totalmente **sin conexión** |
| ¿Se puede ampliar el plazo antes de que venza? | Sí: aplique un nuevo código; reemplaza al anterior |
| ¿Y si el reloj de Windows se atrasa? | El sistema lo detecta y pide corregir la fecha |

# 5. Lista de verificación de la activación

| Nº | Prueba | Esperado |
|---|---|---|
| ☐ 1 | Abrir CONTA JB recién instalado | Pantalla de activación con «quedan 30 días» y un código `JB-…` |
| ☐ 2 | **Copiar** el código de solicitud y pegarlo en el Bloc de notas | Se pega con el formato `JB-XXXX-XXXX-XXXX-XXXX-XXXX` |
| ☐ 3 | **Continuar en modo de prueba** | Entra al sistema |
| ☐ 4 | Pegar un texto cualquiera y pulsar **Activar** | Mensaje de código incorrecto; sigue en prueba |
| ☐ 5 | (Proveedor) Emitir un código perpetuo con el código de solicitud del paso 2 | Se genera un código largo |
| ☐ 6 | Pegar el código en **Ayuda > Activación de la licencia…** y **Activar** | «¡CONTA JB quedó activado!» · «Licencia perpetua» |
| ☐ 7 | Cerrar y volver a abrir | Ya no aparece la pantalla de activación |
| ☐ 8 | (Proveedor) Emitir un código con vencimiento y aplicarlo | «Licencia vigente hasta el …» |
| ☐ 9 | Aplicar un código emitido para **otra** solicitud | «No corresponde a este equipo o no es auténtico» |
