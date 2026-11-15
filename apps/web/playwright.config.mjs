import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "*.spec.mjs",
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0,
  timeout: 60000,
  globalTimeout: 5 * 60000,
  reporter: "list",
  outputDir: "../../.runtime/e2e-results",
  use: { browserName: "chromium", viewport: { width: 390, height: 844 }, locale: "es-ES", trace: "off", screenshot: "only-on-failure" },
  webServer: {
    command: "node ../../scripts/e2e-server.mjs",
    url: "http://127.0.0.1:3001/v1/health",
    reuseExistingServer: false,
    timeout: 90000,
  },
});
