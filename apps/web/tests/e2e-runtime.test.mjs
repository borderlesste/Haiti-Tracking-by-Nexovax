import test from "node:test";
import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { mkdir, writeFile, unlink, rmdir } from "node:fs/promises";
import path from "node:path";
import { runtimeFor, fixtureOtp, verificationLink } from "./e2e/runtime.mjs";

test("test runtime rejects non-UUID paths", () => {
  for (const value of ["", "../../private", "1234", "A".repeat(36)]) assert.throws(() => runtimeFor(value), /canonical E2E UUID/);
});

test("test runtime stays in the isolated API directory", () => {
  const id = randomUUID();
  assert.ok(runtimeFor(id).endsWith(path.join("api", ".runtime", "e2e-" + id) + path.sep));
});

test("fixture authenticator matches the independent PyOTP test vector", () => {
  assert.equal(fixtureOtp(59000), "503347");
});

test("local outbox cannot redirect a test token to an external host", async () => {
  const previous = process.env.E2E_RUN_ID;
  const id = randomUUID();
  process.env.E2E_RUN_ID = id;
  const runtime = runtimeFor(id), outbox = path.join(runtime, "outbox"), file = path.join(outbox, "fixture.json");
  await mkdir(outbox, { recursive: true });
  try {
    await writeFile(file, JSON.stringify({ to: ["fixture@example.org"], text: "https://example.org/verificar#token=synthetic_fixture" }));
    await assert.rejects(verificationLink("fixture@example.org"), /Unexpected test verification destination/);
  } finally {
    await unlink(file);
    await rmdir(outbox);
    await rmdir(runtime);
    if (previous === undefined) delete process.env.E2E_RUN_ID;
    else process.env.E2E_RUN_ID = previous;
  }
});
