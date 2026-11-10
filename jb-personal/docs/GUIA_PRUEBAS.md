# JB-Personal — Guía de pruebas con casos reales

Resumen para GitHub; la guía completa (con lista de aceptación) está en `Manual_JB-Personal.docx/.pdf` capítulo 9.

Dataset **ficticio** de **octubre de 2026** (22 días hábiles, sin feriados). Se regenera con `python datos_prueba/generar_dataset.py`.

| Archivo (`datos_prueba/`) | Uso |
|---|---|
| `personal.csv` | 5 servidores: 2 permanentes, 2 eventuales, 1 consultor en línea |
| `biometrico_octubre_2026.csv` / `.dat` / `.xlsx` | Las mismas 408 marcas en 3 formatos |
| `permisos_octubre_2026.csv` | 6 permisos (5 aprobados + 1 pendiente) |
| `cargar_dataset.py` | Carga todo por la API y descarga los reportes (`--url http://127.0.0.1:8765`) |

## Escenarios (jornada 08:00‑12:00 / 14:30‑18:30, tolerancia 10 min, grave > 30 min)
| Servidor | Modalidad / haber | Incidencias |
|---|---|---|
| 1001 Mamani Quispe Juan Carlos | Permanente 6.000 | 06/10 08:12 (12) · 20/10 14:48 (18) · 14/10 omisión de salida |
| 1002 Vargas Rojas María Elena | Permanente 4.500 | 02/10 08:25 (25) · 07/10 08:45 (45 grave) · 15/10 falta |
| 2001 Choque Condori Luis Alberto | Eventual 3.800 | 12‑13/10 licencia médica · 21/10 permiso 08‑10 y llega 10:05 · 28/10 media falta |
| 2002 Flores Apaza Carla Andrea | Eventual 3.500 (alta 01/10) | 09/10 sin goce · 14/10 14:52 (22) · 22/10 omisión de entrada |
| 3001 Salazar Copa Miguel Ángel | Consultor 7.000 (concluye 30/10) | 08/10 y 19/10 justificados con fiscal · 13/10 08:50 (50 grave) · 27/10 permiso pendiente |

## Procedimiento
1. Crear administrador; completar *Configuración*; activar o usar la prueba de 30 días.
2. *Personal → Importar* `personal.csv` (5 creados). *Marcaciones → Importar* el `.dat` (408 nuevas); el `.csv` después: 0 nuevas / 408 duplicadas.
3. Registrar los 6 permisos. *Reportes* → octubre 2026 (se recalculan solos).

## Resultados esperados (calculados a mano)
| Servidor | Faltas | Min. | Días desc. | Ganado | AFP | Desc. asist. | **Líquido** |
|---|---|---|---|---|---|---|---|
| 1001 Mamani | 0 | 30 | 0 | 6.000,00 | 762,60 | 0,00 | **5.237,40** |
| 1002 Vargas | 1 | 70 | 2,5 | 4.500,00 | 571,95 | 375,00 | **3.553,05** |
| 2001 Choque | 0,5 | 0 | 1 | 3.800,00 | 482,98 | 126,67 | **3.190,35** |
| 2002 Flores | 0 | 22 | 1 | 3.500,00 | 444,85 | 116,67 | **2.938,48** |
| 3001 Salazar | 1 | 50 | 2 | 7.000,00 | 0,00 | 466,66 | **6.533,34** |
| **Total** | | | | **24.800,00** | **2.262,38** | **1.085,00** | **21.452,62** |

**Reportes:** (1) informe `.docx`: 5 servidores / 110 días-hombre, regular 94 días (85,45 %), atrasos 4 (172 min), licencias 2 / 3 días, faltas 3 / 2,5 días; (2) Nuevo personal: Flores; (3) Desvinculados: Salazar (30/10, conclusión de contrato); (4) Planilla de sueldos con **los 5 empleados**: Permanentes 10.500,00 / 8.790,45, Eventuales 7.300,00 / 6.128,83, Consultores 7.000,00 / 6.533,34, total 24.800,00 / 21.452,62; (5) detallado: 154 filas de detalle, 16 imputaciones; (6a) consolidado `.txt` UTF‑8 (5 filas, tabulador) y (6b) **`.xlsx` plano** (fila 1 = 10 títulos + 5 filas, sin formato).

## Estructuras de reloj (marcaciones)
| Archivo | Esperado |
|---|---|
| ZKTeco ATTLOG `.dat` | Autodetectado, 408 marcas |
| CSV con `Employee ID, Name, Authentication Date and Time` / `Person ID, Name, Time` / `No; Nombre; Fecha/Hora` | Autodetectado |
| `Cod|Dia|E1|S1|E2|S2` (cabeceras desconocidas) | Requiere *Analizar estructura*: «varias horas por fila», ID = col 1, fecha = col 2, horas = col 3‑6, cabecera = fila 1 → perfil guardado |
| Excel con título, hoja «Resumen» y hoja «Marcaciones» (cabecera fila 3) | Detecta hoja y fila |

## Pruebas negativas y de control
Permiso de consultor sin fiscal → rechazado · reimportar el mismo archivo → rechazado · mes sin personal → error claro · personal cargado **después** de procesar → la planilla lo incluye · periodo cerrado → bloqueado · `UPDATE`/`DELETE` de la bitácora o `UPDATE` de marcas → rechazado por la base · respaldo alterado/hash/contraseña incorrectos → no restaura · código de activación de otro equipo/vencido/alterado → rechazado · prueba vencida → escrituras y reportes con error 402, consultas y respaldos funcionan · usuario CONSULTA → 403 · nombre `=HYPERLINK(...)` → texto en Excel.

Automáticas: `cd backend && python -m pytest tests -q` → **86 pruebas** (SQLite y PostgreSQL 16).
