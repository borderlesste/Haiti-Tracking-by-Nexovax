import assert from "node:assert/strict";

export const baseURL = "http://127.0.0.1:3001";
const contributor = "qa-contributor@example.org";
const password = "Synthetic-browser-test-only-2026!";
const button = (ui, name) => ui.getByRole("button", { name, exact: true });
const field = (ui, name) => ui.getByLabel(name, { exact: true });

// The same UI steps run through CUA locally and Playwright in CI.
export async function spanish(ui, go) {
  await go(baseURL + "/");
  await ui.locator("#language").selectOption("es");
}
async function login(ui, go) {
  await go(baseURL + "/acceso");
  await field(ui, "Correo electrónico *").fill(contributor);
  await field(ui, "Contraseña *").fill(password);
  await button(ui, "Iniciar sesión").click();
  await ui.getByRole("heading", { name: "Perfil y privacidad", exact: true }).waitFor({ state: "visible" });
}
async function logout(ui, go) {
  await go(baseURL + "/cuenta");
  await button(ui, "Cerrar sesión").click();
  await ui.getByRole("heading", { name: "Construyendo direcciones digitales para Haití", exact: true }).waitFor({ state: "visible" });
}
async function fillPlace(ui, go, name) {
  await go(baseURL + "/contribuir/nueva");
  await field(ui, "Departamento *").selectOption({ label: "Ouest" });
  await field(ui, "Municipio / Comuna *").selectOption({ label: "Delmas" });
  await field(ui, "Barrio o zona *").fill("Démonstration");
  await field(ui, "Punto de referencia *").fill("Référence publique fictive — test automatisé");
  await field(ui, "Tipo de ubicación *").selectOption({ label: "Comercio" });
  await field(ui, "Nombre del lugar *").fill(name);
  await field(ui, "Latitud").fill("18.548");
  await field(ui, "Longitud").fill("-72.299");
  await ui.getByRole("checkbox", { name: "Confirma el punto exacto en el mapa", exact: true }).check();
  await ui.getByRole("checkbox", { name: "Confirmo que esta información es original o tengo permiso para aportarla. No es una residencia privada.", exact: true }).check();
}

export async function publicSearchAndQr(ui, go) {
  await go(baseURL + "/mapa");
  await ui.getByRole("textbox", { name: "Buscar una ubicación en Haití…", exact: true }).fill("Pharmacie Démo");
  await button(ui, "Buscar una ubicación en Haití…").click();
  await ui.getByRole("link", { name: /Pharmacie Démo — Delmas/ }).click();
  await ui.getByText("Demostración sin verificación de campo", { exact: true }).waitFor({ state: "visible" });
  await button(ui, "Compartir ficha y QR").click();
  const dialog = ui.locator("dialog[open]");
  const qr = dialog.getByRole("img", { name: "QR del enlace público de este lugar", exact: true });
  await qr.waitFor({ state: "visible" });
  assert.match(await qr.getAttribute("src"), /^\/v1\/locations\/HT-NXV-\d+\/qr$/);
  await button(dialog, "Cerrar").press("Escape");
  await dialog.waitFor({ state: "hidden" });
}

export async function draftEditAndWithdraw(ui, go, name, capture) {
  await login(ui, go);
  await fillPlace(ui, go, name);
  await ui.getByText("Unidad e indicaciones adicionales", { exact: true }).click();
  await field(ui, "Nombres alternativos").fill("Boutik tès\nMagasin de test");
  await button(ui, "Guardar borrador").click();
  const row = ui.locator("article").filter({ hasText: name });
  await row.getByText("Borrador", { exact: true }).waitFor({ state: "visible" });
  assert.match(await row.innerText(), /Número de contribución.*[a-f0-9-]{36}/s);
  await row.getByRole("link", { name: "Editar", exact: true }).click();
  const aliases = field(ui, "Nombres alternativos");
  await aliases.waitFor({ state: "visible" });
  assert.equal(await aliases.evaluate(el => el.value), "Boutik tès\nMagasin de test");
  await go(baseURL + "/contribuciones");
  await button(row, "Retirar propuesta").click();
  await button(ui.locator("dialog[open]"), "Retirar propuesta").click();
  await row.getByText("Retirado", { exact: true }).waitFor({ state: "visible" });
  assert.equal(await row.getByRole("link", { name: "Editar", exact: true }).count(), 0);
  if (capture) await capture();
  await logout(ui, go);
}

export async function noGpsAndNoAdmin(ui, go, name) {
  await login(ui, go);
  await go(baseURL + "/admin");
  await ui.getByRole("heading", { name: "No tienes acceso a esta sección.", exact: true }).waitFor({ state: "visible" });
  await fillPlace(ui, go, name);
  await button(ui, "Enviar para verificación").click();
  const error = ui.getByRole("alert");
  await error.waitFor({ state: "visible" });
  assert.equal(await error.innerText(), "GPS para aporte presencial");
  await go(baseURL + "/contribuciones");
  await ui.getByText(/Resultados:/).waitFor({ state: "visible" });
  assert.equal(await ui.locator("article").filter({ hasText: name }).count(), 0);
  await logout(ui, go);
}

export async function deniedGpsDraft(ui, go, name) {
  await login(ui, go);
  await fillPlace(ui, go, name);
  await button(ui, "Activar ubicación").click();
  const error = ui.getByRole("alert");
  await error.waitFor({ state: "visible" });
  assert.equal(await error.innerText(), "No pudimos obtener tu posición. Reintenta o guarda un borrador sin GPS.");
  await button(ui, "Guardar borrador").click();
  await ui.locator("article").filter({ hasText: name }).getByText("Borrador", { exact: true }).waitFor({ state: "visible" });
  await logout(ui, go);
}

export async function prepareOnSiteReview(ui, go, name) {
  await login(ui, go);
  await fillPlace(ui, go, name);
  await button(ui, "Activar ubicación").click();
  await ui.locator(".quality-state.good").waitFor({ state: "visible" });
  assert.match(await ui.locator(".gps-values").innerText(), /18\.580000/);
  await ui.getByRole("checkbox", { name: "Confirma el punto exacto en el mapa", exact: true }).check();
  await button(ui, "Comprobar duplicados").click();
  await ui.getByText("No encontramos coincidencias. La propuesta aún requiere revisión.", { exact: true }).waitFor({ state: "visible" });
  await button(ui, "Enviar para verificación").click();
  const dialog = ui.locator("dialog[open]");
  await dialog.getByRole("heading", { name: "Revisar antes de enviar", exact: true }).waitFor({ state: "visible" });
  assert.match(await dialog.innerText(), /±\s*18[.,]5\s*m/);
  assert.ok((await dialog.innerText()).includes(name));
}

export async function confirmOnSiteReview(ui, go, name) {
  await button(ui.locator("dialog[open]"), "Enviar para verificación").click();
  await ui.locator("article").filter({ hasText: name }).getByText("En revisión", { exact: true }).waitFor({ state: "visible" });
  await logout(ui, go);
}
