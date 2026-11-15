import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import net from "node:net";
const root = fileURLToPath(new URL("../", import.meta.url));
if (process.env.APP_ENV !== "test" && existsSync(path.join(root, ".env")))
  process.loadEnvFile(path.join(root, ".env"));
const webPort = Number(process.env.DEV_PORT || 3000),
  apiPort = Number(process.env.API_PORT || 8000);
for (const port of [webPort, apiPort])
  await new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", () =>
      reject(
        new Error(
          `Port ${port} is in use. Select DEV_PORT/API_PORT; no existing process was stopped.`,
        ),
      ),
    );
    server.listen(port, "127.0.0.1", () => server.close(resolve));
  });
const python = path.join(
  root,
  "apps/api/.venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
if (!existsSync(python))
  throw new Error("Prepare apps/api/.venv using the README quick start.");
const origin = `http://127.0.0.1:${webPort}`;
const env = {
  ...process.env,
  WEB_BASE_URL: origin,
  ALLOWED_ORIGINS: origin,
  API_TARGET: `http://127.0.0.1:${apiPort}`,
};
const children = [
  spawn(
    python,
    [
      "-m",
      "uvicorn",
      "app.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      String(apiPort),
      "--no-access-log",
    ],
    { cwd: path.join(root, "apps/api"), env, stdio: "inherit" },
  ),
  spawn(
    process.execPath,
    [
      "node_modules/vite/bin/vite.js",
      "--host",
      "127.0.0.1",
      "--port",
      String(webPort),
      "--strictPort",
    ],
    { cwd: path.join(root, "apps/web"), env, stdio: "inherit" },
  ),
];
let stopping = false;
function stop() {
  if (stopping) return;
  stopping = true;
  for (const child of children) child.kill();
}
process.on("SIGINT", stop);
process.on("SIGTERM", stop);
for (const child of children) {
  child.once("error", (error) => {
    console.error(error.message);
    stop();
    process.exitCode = 1;
  });
  child.once("exit", (code) => {
    if (!stopping) {
      stop();
      process.exitCode = code || 1;
    }
  });
}
console.log(`Haiti Tracking: ${origin}`);
