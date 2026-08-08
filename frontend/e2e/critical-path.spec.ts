import { expect, test } from "@playwright/test";

/**
 * The MVP's single most important test (brief section 39): the full
 * order -> risk -> pick -> inspect -> REJECT -> replace -> reinspect ->
 * PASS -> pack -> deliver -> feedback -> analytics loop, driven entirely
 * through the UI against the seeded FG-10241 demo order.
 *
 * Requires a freshly-seeded backend (`python3 -m app.seed`) and both dev
 * servers running (backend :8000, frontend :3000) before each run — this
 * test consumes FG-10241's pristine state, same as a real demo would.
 */

const API_BASE = process.env.E2E_API_URL || "http://localhost:8000";

test("full risk -> inspect -> reject -> replace -> reinspect -> pass -> pack -> deliver -> feedback loop", async ({ page }) => {
  const orders = await (await page.request.get(`${API_BASE}/api/orders?limit=500`)).json();
  const demoOrder = orders.find((o: any) => o.order_code === "FG-10241");
  test.skip(!demoOrder, "FG-10241 demo order not found — run `python3 -m app.seed` first");
  const orderId = demoOrder.id;

  // Risk prediction is visible on the order detail page.
  await page.goto(`/orders/${orderId}`);
  await expect(page.getByText("HIGH RISK")).toBeVisible();
  await expect(page.getByText("Top Risk Factors")).toBeVisible();
  await expect(page.getByText("Recommended Actions")).toBeVisible();

  // Picker: start the order, find the high-risk Tomatoes line.
  // .click() auto-waits for the async queue to load — don't gate it behind
  // .count(), which checks synchronously and would race the fetch.
  await page.goto("/picker");
  await page.getByRole("button", { name: /FG-10241/ }).click();
  await page.getByRole("button", { name: "Start Picking" }).click();

  await page.getByRole("link", { name: /Inspect with AI/ }).first().click();
  await expect(page).toHaveURL(/\/inspection\//);

  // AI Inspection: use the deterministic "severe damage" sample -> REJECT.
  await page.getByRole("button", { name: /severe visible damage/i }).click();
  await expect(page.getByText("REJECT", { exact: true })).toBeVisible({ timeout: 10_000 });
  await page.getByRole("button", { name: "Reject", exact: true }).click();

  // Replacement: pick any replacement product and scan it.
  await expect(page.getByText("Product Rejected")).toBeVisible();
  await page.locator("select").selectOption({ index: 1 });
  await page.getByRole("button", { name: "Scan Replacement" }).click();

  // Reinspection: use the "no visible defect" sample -> PASS -> Accept.
  await expect(page).toHaveURL(/\/inspection\//);
  await page.getByRole("button", { name: /no visible defect/i }).click();
  await expect(page.getByText("PASS", { exact: true })).toBeVisible({ timeout: 10_000 });
  await page.getByRole("button", { name: "Accept", exact: true }).click();
  await expect(page.getByText("Quality check completed")).toBeVisible();

  // Packing: the replaced line is excluded, confirm the plan.
  await page.goto(`/packing/${orderId}`);
  await page.getByRole("button", { name: "Confirm Recommendation" }).click();
  await expect(page.getByText(/confirmed/i)).toBeVisible();

  // Delivery: accept instructions, mark delivered.
  await page.goto(`/delivery/${orderId}`);
  await page.getByRole("button", { name: "Accept Handling Instructions" }).click();
  await page.getByRole("button", { name: "Mark Delivered" }).click();
  await expect(page.getByRole("link", { name: "Collect Customer Feedback" })).toBeVisible();

  // Customer feedback.
  await page.goto(`/feedback/${orderId}`);
  await page.getByLabel(/No issue/).check();
  await page.getByRole("button", { name: "5" }).click();
  await page.getByRole("button", { name: "Submit Feedback" }).click();
  await expect(page.getByText("Thanks for your feedback!")).toBeVisible();

  // Analytics reflects the workflow without manual DB intervention.
  await page.goto("/analytics");
  await expect(page.getByText("AI Pass")).toBeVisible();
  await expect(page.getByText("Damage-Free Rate", { exact: true })).toBeVisible();
});
