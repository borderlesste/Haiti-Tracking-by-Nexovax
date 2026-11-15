import { test, expect } from "./test.mjs";
import { randomUUID } from "node:crypto";
import { baseURL, spanish, login, logout, testPassword, prepareOnSiteReview, confirmOnSiteReview } from "./flows.mjs";
import { onSiteGeolocation } from "./geolocation.mjs";
import { fixtureOtp, verificationLink } from "./runtime.mjs";

test.beforeEach(async ({ page }) => spanish(page, url => page.goto(url)));

test("registration and single-use email verification complete in the browser", async ({ page }) => {
  const email = "e2e-" + randomUUID() + "@example.org";
  await page.goto(baseURL + "/registro");
  await page.getByLabel("Nombre completo *", { exact: true }).fill("E2E synthetic registrant");
  await page.getByLabel("Correo electrónico *", { exact: true }).fill(email);
  await page.getByLabel("Contraseña *", { exact: true }).fill(testPassword);
  await page.getByLabel("Confirmar contraseña *", { exact: true }).fill(testPassword);
  await page.locator('input[name="terms"]').check();
  await page.locator('input[name="privacy"]').check();
  await page.getByRole("button", { name: "Crear cuenta", exact: true }).click();
  await expect(page.locator(".success-panel")).toBeVisible();
  let link;
  await expect.poll(async () => { link = await verificationLink(email); return !!link; }).toBeTruthy();
  try { await page.goto(link); }
  catch { throw new Error("Test verification page could not be opened"); }
  await page.getByRole("button", { name: "Verificar correo", exact: true }).click();
  await expect(page.getByText("Correo verificado", { exact: true })).toBeVisible();
  expect(new URL(page.url()).hash === "" && !new URL(page.url()).searchParams.has("token")).toBeTruthy();
  const token = new URL(link).hash.slice("#token=".length);
  const replay = await page.request.post(baseURL + "/v1/auth/verify-email", {
    headers: { "X-CSRF-Token": (await (await page.request.get(baseURL + "/v1/auth/csrf")).json()).data.csrf_token },
    data: { token },
  });
  expect(replay.status()).toBe(400);
  await login(page, url => page.goto(url), email);
  await expect(page.getByText("Correo verificado", { exact: true })).toBeVisible();
  await logout(page, url => page.goto(url));
});

async function review(page, needle, action, reason, canonical) {
  await page.goto(baseURL + "/admin/revision");
  const card = page.locator("article.review-card").filter({ hasText: needle });
  await card.getByRole("button", { name: action, exact: true }).click();
  const dialog = page.locator("dialog[open]");
  if (canonical) await dialog.getByLabel("Código de destino *", { exact: true }).fill(canonical);
  await dialog.getByLabel("Motivo *", { exact: true }).fill(reason);
  await dialog.getByRole("button", { name: "Guardar", exact: true }).click();
  await expect(dialog).not.toBeVisible();
  return card;
}

test("moderation, duplicate correction, stable code, rejection, merge and private exclusion", async ({ page }) => {
  test.setTimeout(120000);
  const name = "E2E moderation " + randomUUID();
  await page.addInitScript(onSiteGeolocation);
  await prepareOnSiteReview(page, url => page.goto(url), name);
  await confirmOnSiteReview(page, url => page.goto(url), name);
  await login(page, url => page.goto(url), "qa-moderator@example.org", fixtureOtp());
  const approved = await review(page, name, "Aprobar", "Moderación sintética; no representa verificación física.");
  await expect(approved.getByText("Aprobado", { exact: true })).toBeVisible();
  await logout(page, url => page.goto(url));
  const search = await page.request.get(baseURL + "/v1/locations/search?q=" + encodeURIComponent(name));
  expect(search.status()).toBe(200);
  const places = (await search.json()).data;
  expect(places.length).toBe(1);
  const code = places[0].code;
  expect("gps_observation" in places[0] || "author_user_id" in places[0]).toBeFalsy();
  await page.goto(baseURL + "/mapa?q=" + encodeURIComponent(name));
  await page.locator(".place-card").filter({ hasText: name }).click();
  await expect(page.getByRole("heading", { name, exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Proponer una corrección", exact: true }).click();
  await page.locator(".center-card").getByRole("link", { name: "Iniciar sesión", exact: true }).click();
  await page.getByLabel("Correo electrónico *", { exact: true }).fill("qa-contributor@example.org");
  await page.getByLabel("Contraseña *", { exact: true }).fill(testPassword);
  await page.getByRole("button", { name: "Iniciar sesión", exact: true }).click();
  await expect(page.getByLabel("Nombre del lugar *", { exact: true })).toHaveValue(name);
  await page.getByLabel("Punto de referencia *", { exact: true }).fill("Referencia pública corregida por el autor");
  await page.getByRole("button", { name: "Activar ubicación", exact: true }).click();
  await expect(page.locator(".quality-state.good")).toBeVisible();
  await page.getByRole("checkbox", { name: "Confirma el punto exacto en el mapa", exact: true }).check();
  await page.locator('input[name="source"]').check();
  await page.getByRole("button", { name: "Comprobar duplicados", exact: true }).click();
  await page.locator('textarea[name="justification"]').fill("Es el mismo lugar; corrijo únicamente la referencia de acceso.");
  await page.getByRole("button", { name: "Enviar para verificación", exact: true }).click();
  const created = page.waitForResponse(response => response.url() === baseURL + "/v1/contributions" && response.request().method() === "POST");
  await page.locator("dialog[open]").getByRole("button", { name: "Enviar para verificación", exact: true }).click();
  const contribution = (await (await created).json()).data;
  expect(contribution.payload.duplicate_resolution.choice).toBe("update_existing");
  await logout(page, url => page.goto(url));
  await login(page, url => page.goto(url), "qa-moderator@example.org", fixtureOtp());
  const returned = await review(page, contribution.id, "Solicitar cambios", "Aclara las instrucciones públicas de acceso al edificio.");
  await expect(returned.getByText("Requiere cambios", { exact: true })).toBeVisible();
  const rejected = await review(page, "E2E fixture reject", "Rechazar", "Evidencia insuficiente en este escenario sintético.");
  await expect(rejected.getByText("Rechazado", { exact: true })).toBeVisible();
  const merged = await review(page, "E2E fixture merge", "Fusionar", "Propuesta sintética consolidada con el registro canónico.", code);
  await expect(merged.getByText("Fusionado", { exact: true })).toBeVisible();
  await logout(page, url => page.goto(url));
  await login(page, url => page.goto(url));
  await page.goto(baseURL + "/contribuir/" + contribution.id);
  await expect(page.getByLabel("Nombre del lugar *", { exact: true })).toHaveValue(name);
  await page.getByLabel("Punto de referencia *", { exact: true }).fill("Acceso público aclarado después de revisión");
  await page.getByRole("button", { name: "Activar ubicación", exact: true }).click();
  await expect(page.locator(".quality-state.good")).toBeVisible();
  await page.getByRole("checkbox", { name: "Confirma el punto exacto en el mapa", exact: true }).check();
  await page.getByRole("button", { name: "Comprobar duplicados", exact: true }).click();
  await page.locator('textarea[name="justification"]').fill("Corrijo el mismo lugar siguiendo el mensaje de revisión.");
  await page.getByRole("button", { name: "Enviar para verificación", exact: true }).click();
  const edited = page.waitForResponse(response => response.url().endsWith("/v1/me/contributions/" + contribution.id) && response.request().method() === "PATCH");
  await page.locator("dialog[open]").getByRole("button", { name: "Enviar para verificación", exact: true }).click();
  expect((await (await edited).json()).data.payload.duplicate_resolution.choice).toBe("update_existing");
  await logout(page, url => page.goto(url));
  await login(page, url => page.goto(url), "qa-moderator@example.org", fixtureOtp());
  const updated = await review(page, contribution.id, "Aprobar", "Corrección sintética comprobada; se conserva el código original.");
  await expect(updated.getByText("Aprobado", { exact: true })).toBeVisible();
  const detail = (await (await page.request.get(baseURL + "/v1/locations/" + code)).json()).data;
  expect(detail.code).toBe(code);
  expect(detail.version).toBe(2);
  expect(detail.address.reference).toBe("Acceso público aclarado después de revisión");
  await logout(page, url => page.goto(url));
  await page.goto(baseURL + "/ubicaciones/HT-NXV-PRIVATEFIX");
  await expect(page.getByRole("heading", { name: "No encontramos este lugar público.", exact: true })).toBeVisible();
  expect((await page.request.get(baseURL + "/v1/locations/HT-NXV-PRIVATEFIX")).status()).toBe(404);
  const privateSearch = await page.request.get(baseURL + "/v1/locations/search?q=E2E%20private%20residence");
  expect((await privateSearch.json()).data.length).toBe(0);
});

test("developer creates a key, queries, observes usage and revokes it", async ({ page }) => {
  await login(page, url => page.goto(url));
  await page.goto(baseURL + "/desarrolladores/panel");
  const name = "E2E developer " + randomUUID();
  await page.getByLabel("Nombre de la aplicación *", { exact: true }).fill(name);
  await page.getByRole("button", { name: "Crear aplicación", exact: true }).click();
  const app = page.locator(".developer-app").filter({ hasText: name });
  await app.getByRole("button", { name: "Crear clave de prueba", exact: true }).click();
  const dialog = page.locator("dialog[open]");
  await dialog.getByLabel("Contraseña *", { exact: true }).fill(testPassword);
  await dialog.getByRole("button", { name: "Crear clave de prueba", exact: true }).click();
  await expect(page.locator(".secret-panel code")).toBeVisible();
  const secret = await page.locator(".secret-panel code").innerText();
  expect(secret.startsWith("ht_test_")).toBeTruthy();
  const query = await page.request.get(baseURL + "/v1/locations/search", { headers: { Authorization: "Bearer " + secret } });
  expect(query.status()).toBe(200);
  await page.reload();
  await expect(page.locator(".secret-panel")).toHaveCount(0);
  await expect(app.locator(".usage")).toContainText(/:\s*1$/);
  const metadata = await (await page.request.get(baseURL + "/v1/developer/apps")).json();
  expect(JSON.stringify(metadata).includes(secret)).toBeFalsy();
  await app.getByRole("button", { name: "Revocar", exact: true }).click();
  await page.locator("dialog[open]").getByRole("button", { name: "Revocar", exact: true }).click();
  await expect(app.getByText("Revocada", { exact: true })).toBeVisible();
  expect((await page.request.get(baseURL + "/v1/locations/search", { headers: { Authorization: "Bearer " + secret } })).status()).toBe(401);
  await logout(page, url => page.goto(url));
});
