import { defineConfig } from '@playwright/test';
import { existsSync } from 'fs';

// Con PW_CHROMIUM_PATH o el Chromium preinstalado del entorno no se descarga ningún navegador.
const ejecutable = process.env.PW_CHROMIUM_PATH ?? (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined);

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 120_000,
  workers: 1,
  expect: { timeout: 15_000 },
  reporter: [['list']],
  use: { actionTimeout: 15_000, baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:3000', trace: 'retain-on-failure', launchOptions: { executablePath: ejecutable } },
});
