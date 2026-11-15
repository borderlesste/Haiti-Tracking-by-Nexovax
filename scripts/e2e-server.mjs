import { spawn, spawnSync } from "node:child_process";
import { randomUUID, randomBytes } from "node:crypto";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = fileURLToPath(new URL("../", import.meta.url));
const runId = process.env.E2E_RUN_ID || randomUUID();
const runtime = path.join(root, "apps/api/.runtime", `e2e-${runId}`);
const python = path.join(root, "apps/api/.venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const env = {
  ...process.env,
  APP_ENV: "test",
  PYTHONPATH: path.join(root, "apps/api"),
  E2E_RUN_ID: runId,
  DATABASE_URL: `sqlite:///${path.join(runtime, "test.db").replaceAll("\\", "/")}`,
  DATABASE_AUTO_CREATE: "true",
  RUNTIME_DIR: runtime,
  EVIDENCE_DIR: path.join(runtime, "evidence"),
  S3_BUCKET: "",
  RESEND_API_KEY: "",
  TRUSTED_HOSTS: "127.0.0.1,localhost",
  FORWARDED_ALLOW_IPS: "127.0.0.1",
  REWARDS_CASH_ENABLED: "false",
  SESSION_SECRET: randomBytes(32).toString("hex"),
  API_KEY_PEPPER: randomBytes(32).toString("hex"),
  DEV_PORT: "3001",
  API_PORT: "8001",
};
for (const args of [["tests/browser_fixture.py"], ["-m", "app.cli", "seed-demo"]]) {
  const result = spawnSync(python, args, { cwd: path.join(root, "apps/api"), env, stdio: "inherit" });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status || 1);
}
const server = spawn(process.execPath, ["scripts/dev.mjs"], { cwd: root, env, stdio: "inherit" });
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => server.kill(signal));
server.once("error", error => { console.error(error.message); process.exitCode = 1; });
server.once("exit", code => { process.exitCode = code || 0; });
