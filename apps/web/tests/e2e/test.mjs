import { test as base, expect } from "@playwright/test";
import { createHash } from "node:crypto";
import { baseURL } from "./flows.mjs";

export const test = base.extend({
  page: async ({ page }, use, info) => {
    const digest = createHash("sha256").update(info.testId).digest("hex");
    const client = `2001:db8:${digest.slice(0, 4)}:${digest.slice(4, 8)}::1`;
    // Separate synthetic clients through the trusted loopback proxy, keeping all real limits enabled.
    await page.route(baseURL + "/v1/**", route => route.continue({
      headers: { ...route.request().headers(), "x-forwarded-for": client },
    }));
    const errors = [];
    page.on("pageerror", error => errors.push(error.name + ": " + error.message));
    await use(page);
    expect(errors, "No uncaught browser exceptions").toEqual([]);
  },
});
export { expect };
