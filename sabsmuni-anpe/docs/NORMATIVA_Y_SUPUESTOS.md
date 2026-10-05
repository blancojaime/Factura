# Normativa aplicada, supuestos y límites

Este documento separa **lo que el requerimiento del proyecto fijó** de **lo que el sistema asumió**, para que la
unidad jurídica y de contrataciones lo valide antes de operar. El software automatiza y verifica; la responsabilidad
del proceso sigue siendo del RPA y del Responsable de Contrataciones.

## A. Parámetros tomados del requerimiento (validar contra la norma vigente)

| Regla | Valor implementado | Dónde se ajusta |
|---|---|---|
| Rango ANPE | Bs 50.001 – Bs 1.000.000 | `domain/cronograma.ts` (`ANPE_MIN/MAX`) |
| Plazo mínimo publicación → apertura (Art. 47 D.S. 0181) | 4 días hábiles hasta Bs 200.000; 8 días hábiles de Bs 200.001 a 1.000.000 | `plazoMinimoDiasHabiles` |
| Días hábiles | Lunes a viernes, excluyendo feriados; el día de publicación **no** se cuenta | `domain/calendario-bolivia.ts` |
| Garantía de cumplimiento | 7 % general · 3,5 % MyPE/APP/OECA | `domain/garantia.ts` |
| Contrato vs. orden | Plazo ≤ 15 días calendario → Orden de Compra/Servicio (Obras siempre Contrato) | `tipoInstrumentoContractual` |
| Márgenes de preferencia | 10 % nacional · 18 % MyPE/APP/OECA · 0 % extranjero | `MARGENES_DEFECTO` o `config_institucional.margenes` |
| Mecanismo de ajuste del margen | Precio de comparación = precio final × (1 − margen); se adjudica por el monto ofertado | `aplicarMargenPreferencia` |
| Subasta electrónica | Solo Obras y Servicios; el precio final no puede superar la oferta inicial | `evaluarPropuestas` |

## B. Supuestos del sistema (no provienen de una norma citada)

1. **Plazos posteriores a la apertura** (evaluación 2 d.h., presentación de documentos 4 d.h., firma 3 d.h.) son valores por defecto
   institucionales, no mínimos legales. Se ajustan en `config_institucional.plazos`.
2. **Calidad, Propuesta Técnica y Costo:** ponderación 70 % técnica / 30 % económica y umbral técnico de 70 puntos. Parametrizable por llamada a `evaluarPropuestas`.
3. **Ofertas sobre el precio referencial:** se admiten con observación (requieren certificación adicional); `rechazarSobrePrecioReferencial` las descalifica.
4. **Desempate:** menor plazo y luego orden de presentación; el sistema avisa (`requiereDesempate`) para que la Comisión lo ratifique según el DBC.
5. **Ítems del Formulario V-1** (`V1-01…V1-06`) son representativos; adáptelos al DBC oficial de su entidad (`V1_ITEMS`).
6. **Feriados:** se calculan los nacionales (incl. Carnaval, Viernes Santo y Corpus Christi). Los departamentales y los decretados ad hoc **deben cargarse** en el catálogo.
7. **Catálogo CHB y partidas del seed son ejemplos.** Cargue los oficiales. La validación CHB compara el código UNSPSC exacto (producto nacional → ficha),
   misma clase de 6 dígitos (alerta de sustituto) o sin coincidencia (insuficiencia técnica); los códigos de servicio (segmento ≥ 70) no se cruzan.
8. **Detector de marcas:** lista base ampliable (`marcas_registradas`); es una ayuda, no sustituye la revisión técnica.
9. **Textos de DBC, contrato, resoluciones y actas** son modelos paramétricos genéricos. Contraste con los modelos oficiales del Órgano Rector
   (SICOES) y con el reglamento específico de la entidad. Las multas se remiten al DBC sin fijar porcentaje.
10. **Formato de campos SIGEP** (dígitos por campo de la estructura programática) es una validación defensiva; ajústela a su clasificador si difiere (`domain/sigep.ts`).

## C. Lo que el sistema NO hace

- **No se integra** con SICOES, SIGEP ni RUPE: la publicación, el registro del C-31 y la verificación de RUPE se hacen en esos sistemas
  (la «Captura SIGEP» prepara y valida los datos para transcribir; el CUCE provisorio se reemplaza por el definitivo).
- **No es firma digital con validez legal** (Ley 164). El SHA-256, el QR y el sello del expediente prueban **integridad y autenticidad del archivo**
  frente a la versión registrada; la firma de los instrumentos sigue siendo la que exija la entidad.
- **No ejecuta la subasta en línea:** registra el precio final resultante de la subasta realizada por el medio que corresponda.
- No sustituye el control interno ni la responsabilidad por la función pública (Ley 1178 SAFCO).

## D. Pistas de auditoría que el sistema deja

Cada operación que modifica datos registra fecha-hora, usuario, IP, acción y estado previo/posterior en una cadena de hashes.
Cada PDF generado queda versionado e inmutable con su SHA-256; el expediente único lleva folio «Fs. n/N» y un sello sobre la lista ordenada de documentos.
