import { createHmac } from "node:crypto";
import { readdir, readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { baseURL } from "./flows.mjs";

export function runtimeFor(runId = process.env.E2E_RUN_ID) {
  if (typeof runId !== "string" || !/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(runId)) throw new Error("A canonical E2E UUID is required");
  return fileURLToPath(new URL(`../../../api/.runtime/e2e-${runId}/`, import.meta.url));
}

export async function verificationLink(email) {
  const outbox = path.join(runtimeFor(), "outbox");
  let files;
  try { files = await readdir(outbox); }
  catch (error) { if (error.code === "ENOENT") return null; throw error; }
  for (const name of files.filter(name => name.endsWith(".json"))) {
    const message = JSON.parse(await readFile(path.join(outbox, name), "utf8"));
    if (!message.to?.includes(email)) continue;
    const match = message.text?.match(/https?:\/\/[^\s]+\/verificar#token=[A-Za-z0-9_-]+/);
    if (!match) continue;
    const link = new URL(match[0]);
    if (link.origin !== baseURL || link.pathname !== "/verificar" || link.search) throw new Error("Unexpected test verification destination");
    return link.href;
  }
  return null;
}

export function fixtureOtp(time = Date.now()) {
  const bits = [..."JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"].map(c => "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567".indexOf(c).toString(2).padStart(5, "0")).join("");
  const key = Buffer.from(bits.match(/.{8}/g).map(byte => parseInt(byte, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(time / 30000)));
  const digest = createHmac("sha1", key).update(counter).digest();
  return String((digest.readUInt32BE(digest[19] & 15) & 0x7fffffff) % 1000000).padStart(6, "0");
}
