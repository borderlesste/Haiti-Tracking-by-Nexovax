import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
const cwd = fileURLToPath(new URL("../apps/web/", import.meta.url));
const command = process.argv[2];
if (command !== "build") throw new Error("Unknown command");
for (const args of [
  ["node_modules/vite/bin/vite.js", "build"],
  ["scripts/prepare-sites-build.mjs"],
]) {
  const result = spawnSync(process.execPath, args, { cwd, stdio: "inherit" });
  if (result.status !== 0) process.exit(result.status || 1);
}
