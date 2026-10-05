import { expect, Page, test } from '@playwright/test';

/**
 * E2E del caso práctico del manual: «Adquisición de lote de cemento para pavimento · Bs 180.000».
 * Requiere el sistema levantado (docker compose up) con los usuarios demo del seed.
 */
const PASS = process.env.E2E_PASSWORD ?? 'Anpe2026Demo';
const ahora = Date.now();
const NIT = String(2_000_000_000 + (ahora % 100_000_000));

async function entrar(page: Page, email: string) {
  await page.context().clearCookies();
  await page.goto('/login');
  await page.getByLabel('Correo institucional').fill(email);
  await page.getByLabel('Contraseña').fill(PASS);
  await page.getByRole('button', { name: 'Ingresar' }).click();
  await expect(page).toHaveURL(/\/procesos$/);
}
const avanzar = async (page: Page, hacia: string) => {
  const b = page.getByTestId(`paso-${hacia}`);
  await expect(b).toBeEnabled();
  await b.click();
};

test('flujo completo ANPE por roles en la interfaz', async ({ page }) => {
  let url = '';

  // ── Unidad solicitante: requerimiento + CHB ──
  await entrar(page, 'solicitante@gam.bo');
  await page.getByRole('button', { name: 'Nueva solicitud' }).click();
  await page.getByPlaceholder('Ej.: Adquisición de lote de cemento para pavimento').fill(`Adquisición de lote de cemento para pavimento ${ahora}`);
  await page.getByRole('button', { name: 'Crear borrador' }).click();
  await expect(page).toHaveURL(/\/procesos\/[0-9a-f-]{36}$/);
  url = page.url();

  await page.getByLabel('UNSPSC (8 díg.)').fill('30111505');
  await page.getByLabel('Partida de gasto').fill('34200');
  await page.getByLabel('Unidad').fill('bolsa');
  await page.getByLabel('Cantidad').fill('3000');
  await page.getByLabel('Precio unitario (Bs)').fill('60');
  await page.getByLabel('Descripción técnica (sin marcas)').fill('Cemento Portland tipo IP en bolsa de 50 kg, resistencia ≥ 32,5 MPa');
  await page.getByRole('button', { name: 'Agregar ítem' }).click();
  await expect(page.getByTestId('total-items')).toContainText('180.000,00');

  // El analizador en vivo bloquea marcas
  const texto = page.getByTestId('seccion-texto');
  await texto.fill('Cemento marca Soboce de 50 kg');
  await expect(page.getByText('Bloqueante:')).toBeVisible();

  const secciones = [
    'Cemento Portland para pavimento rígido de vías urbanas del municipio.',
    'Resistencia a la compresión mínima de 32,5 MPa a 28 días y fraguado inicial mayor a 45 minutos.',
    'Cumple las normas NB 011 y NB 063 vigentes en el país.',
    'Entrega en almacén municipal dentro de 15 días calendario, en horario administrativo.',
    'Garantía de calidad de seis meses con reposición por defectos de fabricación.',
  ];
  for (let i = 0; i < secciones.length; i++) {
    await page.getByRole('button', { name: new RegExp(`^${i + 1}\\.`) }).click();
    await texto.fill(secciones[i]);
  }
  await page.getByTestId('btn-validar').click();
  await expect(page.getByText('Requerimiento sin hallazgos bloqueantes y completo.')).toBeVisible();
  await expect(page.getByText('Cubierto por CHB').first()).toBeVisible();
  await avanzar(page, 'REQUERIMIENTO_VALIDADO');

  // ── Responsable de presupuesto: Captura SIGEP ──
  await entrar(page, 'presupuesto@gam.bo');
  await page.goto(url);
  await page.getByRole('tab', { name: /Captura SIGEP/ }).click();
  const fila = { 'DA línea 1': '40', 'UE línea 1': '1', 'Prog. línea 1': '1', 'Proy. línea 1': '1', 'Act./Obra línea 1': '1', 'Fte. línea 1': '20', 'Org. línea 1': '210', 'Partida línea 1': '34200' };
  for (const [l, v] of Object.entries(fila)) await page.getByLabel(l, { exact: true }).fill(v);
  await expect(page.getByTestId('estado-cuadre')).toContainText('cuadran con los ítems');
  await page.getByLabel('Importe línea 1').fill('179999.99'); // descuadre intencional
  await expect(page.getByTestId('estado-cuadre')).toContainText('aún no cuadran');
  await page.getByLabel('Importe línea 1').fill('180000');
  await page.getByPlaceholder('Se completa tras registrar').fill('000321');
  await page.getByTestId('btn-guardar-c31').click();
  await expect(page.getByText('Certificación guardada y validada')).toBeVisible();
  await expect(page.getByTestId('btn-copiar-bloque')).toBeEnabled();
  await expect(page.locator('pre')).toContainText('34200\t180000.00');
  await avanzar(page, 'PRESUPUESTO_CERTIFICADO');

  // ── Responsable de contrataciones: cronograma (4 d.h.) y DBC ──
  await entrar(page, 'contrataciones@gam.bo');
  await page.goto(url);
  await page.getByRole('tab', { name: /Cronograma y DBC/ }).click();
  await page.getByTestId('fecha-publicacion').fill('2026-11-09');
  await page.getByTestId('btn-guardar-cronograma').click();
  await expect(page.getByText('Cronograma guardado.')).toBeVisible();
  await expect(page.getByText('13/11/2026')).toBeVisible(); // apertura = 4.º día hábil
  await avanzar(page, 'DBC_ELABORADO');

  // ── RPA aprueba DBC ──
  await entrar(page, 'rpa@gam.bo');
  await page.goto(url);
  await avanzar(page, 'DBC_APROBADO');

  // ── RC: publicación, evaluación ──
  await entrar(page, 'contrataciones@gam.bo');
  await page.goto(url);
  await avanzar(page, 'PUBLICADO');
  await avanzar(page, 'EVALUACION');
  await page.getByRole('tab', { name: /Evaluación/ }).click();
  await page.getByLabel('NIT', { exact: true }).fill(NIT);
  await page.getByLabel('Razón social').fill('Distribuidora Andina SRL');
  await page.getByLabel('Categoría (margen)').selectOption('MYPE_APP_OECA');
  await page.getByLabel('Monto ofertado (Bs)').fill('172000');
  await page.getByRole('button', { name: 'Registrar' }).click();
  await expect(page.getByText('Propuesta registrada.')).toBeVisible();
  for (let i = 1; i <= 6; i++) await page.getByLabel(new RegExp(`^V1-0${i} Distribuidora`)).check();
  await expect(page.getByText('Presentó', { exact: true }).first()).toBeVisible();
  await page.getByTestId('btn-evaluar').click();
  await expect(page.getByRole('status').filter({ hasText: 'Recomendación:' })).toContainText('Distribuidora Andina SRL');
  await expect(page.getByRole('cell', { name: 'Bs 141.040,00' })).toBeVisible(); // 172.000 − 18%
  await avanzar(page, 'RECOMENDACION_EMITIDA');

  // ── RPA adjudica ──
  await entrar(page, 'rpa@gam.bo');
  await page.goto(url);
  await avanzar(page, 'ADJUDICADO');

  // ── Contrato: MyPE → garantía 3,5 % ──
  await page.getByRole('tab', { name: /Contrato/ }).click();
  await expect(page.getByTestId('garantia-monto')).toContainText('6.020,00'); // 3,5 % de 172.000
  await page.getByTestId('fecha-firma').fill('2026-12-01');
  await page.getByTestId('btn-generar-contrato').click();
  await expect(page.getByText('Instrumento generado.')).toBeVisible();
  await page.reload();
  await avanzar(page, 'CONTRATO_FORMALIZADO');

  // ── Expediente único + verificación pública del QR ──
  await page.getByRole('tab', { name: /Expediente/ }).click();
  await page.getByTestId('btn-expediente').click();
  await expect(page.getByText(/Expediente compilado: \d+ documentos/)).toBeVisible();
  await expect(page.getByRole('cell', { name: 'Expediente único' })).toBeVisible();
  const hashCorto = await page.locator('tr', { hasText: 'Expediente único' }).locator('td').nth(4).getAttribute('title');
  expect(hashCorto).toMatch(/^[a-f0-9]{64}$/);
  await page.context().clearCookies();
  await page.goto(`/verificar/${hashCorto}`);
  await expect(page.getByTestId('resultado-verificacion')).toContainText('Documento auténtico');
});
