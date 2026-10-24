import { defineConfig, devices } from "@playwright/test";

// Starts the FastAPI backend and the Vite dev server, then drives the real GUI in Chromium (WebGL via SwiftShader).
const isWin = process.platform === "win32";
const API_PORT = process.env.E2E_API_PORT ?? "8765";
const WEB_PORT = process.env.E2E_WEB_PORT ?? "5199";
const python = process.env.SAFEGUARD_PYTHON ?? (isWin ? "..\\backend\\.venv\\Scripts\\python.exe" : "../backend/.venv/bin/python");

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never", outputFolder: "e2e-report" }]],
  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    viewport: { width: 1600, height: 1000 },
    acceptDownloads: true,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1600, height: 1000 },
             launchOptions: { args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] } },
    },
  ],
  webServer: [
    {
      command: `${python} -m uvicorn safeguard_pq.api.app:app --host 127.0.0.1 --port ${API_PORT}`,
      url: `http://127.0.0.1:${API_PORT}/api/v1/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: { LLM_PROVIDER: "none", ONLINE_TOOLS_ENABLED: "false", CORS_ORIGINS: `http://127.0.0.1:${WEB_PORT}` },
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${WEB_PORT}`,
      url: `http://127.0.0.1:${WEB_PORT}`,
      env: { SAFEGUARD_API: `http://127.0.0.1:${API_PORT}` },
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
