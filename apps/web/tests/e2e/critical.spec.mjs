import { test, expect } from "@playwright/test";
import { spanish, publicSearchAndQr, draftEditAndWithdraw, noGpsAndNoAdmin, deniedGpsDraft, prepareOnSiteReview, confirmOnSiteReview } from "./flows.mjs";
import { onSiteGeolocation, deniedGeolocation } from "./geolocation.mjs";

test.beforeEach(async ({ page }) => spanish(page, url => page.goto(url)));
test("anonymous public search and accessible QR dialog", async ({ page }) => {
  await publicSearchAndQr(page, url => page.goto(url));
  await expect(page.getByRole("button", { name: "Compartir ficha y QR", exact: true })).toBeFocused();
});
test("draft without street or number, edit and owned withdrawal", async ({ page }) => {
  await draftEditAndWithdraw(page, url => page.goto(url), "E2E draft — " + test.info().testId,
    () => page.screenshot({ path: test.info().outputPath("withdrawn.png") }));
});
test("GPS-less submission and administrative access are blocked", async ({ page }) => {
  await noGpsAndNoAdmin(page, url => page.goto(url), "E2E blocked — " + test.info().testId);
});
test("permission denial offers a draft without verified presence", async ({ page }) => {
  await page.addInitScript(deniedGeolocation);
  await deniedGpsDraft(page, url => page.goto(url), "E2E denied — " + test.info().testId);
});
test("on-site review precedes submission, using a synthetic device response", async ({ page }) => {
  const name = "E2E on-site — " + test.info().testId;
  await page.addInitScript(onSiteGeolocation);
  await prepareOnSiteReview(page, url => page.goto(url), name);
  const before = await page.request.get("http://127.0.0.1:3001/v1/me/contributions");
  expect(before.ok()).toBeTruthy();
  expect((await before.json()).data.some(row => row.payload.name === name)).toBeFalsy();
  await confirmOnSiteReview(page, url => page.goto(url), name);
});
