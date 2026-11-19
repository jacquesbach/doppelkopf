import { test, expect } from "@playwright/test";

test("Startseite zeigt die Hauptueberschrift und fuehrt zum Tisch-Formular", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toContainText("DOPPELKOPF");
  await page.getByRole("link", { name: "TISCH ERÖFFNEN" }).click();
  await expect(page).toHaveURL(/\/neu$/);
  await expect(page.getByRole("heading", { name: /Neuer Tisch/i })).toBeVisible();
});
