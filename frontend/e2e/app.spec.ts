/**
 * GUI tests written as user journeys. Each test drives the real UI in Chromium against the real backend,
 * fails on any browser console error, and saves screenshots to e2e/artifacts/ for visual review.
 */
import { expect, test, type Download, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const shot = (page: Page, name: string, fullPage = false) => page.screenshot({ path: path.join(here, "artifacts", `${name}.png`), fullPage });
const pdfBytes = async (d: Download) => readFileSync((await d.path())!);

async function openSimulation(page: Page) {
  await page.goto("/#simulation");
  await expect(page.locator("canvas")).toBeVisible();
  await expect(page.getByTestId("device-select").locator("option")).toHaveCount(9);
  await expect(page.getByTestId("kpi-attacks")).toContainText("0");
}

async function inject(page: Page, attack: string) {
  await page.getByTestId("attack-select").selectOption(attack);
  await page.getByTestId("inject-btn").click();
}

async function timelineLabelsDoNotOverlap(page: Page) {
  const boxes = await page.getByTestId("risk-timeline").locator("text").evaluateAll((els) =>
    els.map((e) => (e as SVGGraphicsElement).getBBox()).filter((b) => b.width > 0).map((b) => ({ x: b.x, y: b.y, w: b.width, h: b.height })));
  for (let i = 0; i < boxes.length; i++)
    for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i], b = boxes[j];
      const overlap = a.x < b.x + b.w - 1 && b.x < a.x + a.w - 1 && a.y < b.y + b.h - 1 && b.y < a.y + a.h - 1;
      expect(overlap, `timeline labels overlap: ${JSON.stringify(a)} vs ${JSON.stringify(b)}`).toBe(false);
    }
}

async function noPageScroll(page: Page) {
  const { scroll, view } = await page.evaluate(() => ({ scroll: document.documentElement.scrollHeight, view: window.innerHeight }));
  expect(scroll, "simulation page must fit the viewport without a page scrollbar").toBeLessThanOrEqual(view + 1);
}

test.describe("TIPPSS SafeGuard-PQ — user journeys", () => {
  let consoleErrors: string[] = [];
  test.beforeEach(({ page }) => {
    consoleErrors = [];
    page.on("console", (m) => { if (m.type() === "error") consoleErrors.push(m.text()); });
    page.on("pageerror", (e) => consoleErrors.push(e.message));
  });
  test.afterEach(() => expect(consoleErrors, "browser console errors").toEqual([]));

  for (const vp of [{ width: 1920, height: 1080 }, { width: 1440, height: 900 }]) {
    test(`Simulation fits on one screen at ${vp.width}x${vp.height}`, async ({ page }) => {
      await page.setViewportSize(vp);
      await openSimulation(page);
      await page.waitForTimeout(1500);
      await noPageScroll(page);
      for (const id of ["sim-kpis", "risk-timeline", "drill-panel", "device-panel", "run-drill"]) await expect(page.getByTestId(id)).toBeVisible();
      await shot(page, `sim-${vp.width}x${vp.height}`);
    });
  }

  test("One-click use case: ICU Q-Day drill runs end to end", async ({ page }) => {
    test.setTimeout(150_000);
    await page.setViewportSize({ width: 1920, height: 1080 });
    await openSimulation(page);
    await page.getByTestId("run-drill").click();

    const card = page.getByTestId("drill-card");
    await expect(card).toHaveAttribute("data-step", "capture", { timeout: 15_000 });
    await expect(page.getByTestId("kpi-attacks")).not.toContainText(/^Active attacks0$/);
    await expect(card).toHaveAttribute("data-step", "qday", { timeout: 20_000 });
    await page.waitForTimeout(1200);
    await shot(page, "drill-qday");

    await expect(card).toHaveAttribute("data-step", "detect", { timeout: 20_000 });
    await expect(page.getByTestId("device-status")).toHaveText("UNSAFE", { timeout: 30_000 });
    await shot(page, "drill-detect");

    await expect(card).toHaveAttribute("data-step", "verify", { timeout: 40_000 });
    await expect(page.getByTestId("device-status")).toHaveText("SAFE", { timeout: 30_000 });
    await expect(page.getByTestId("run-drill")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("kpi-hndl")).toContainText("0");
    expect(await page.getByTestId("marker-danger").count()).toBeGreaterThanOrEqual(4);
    expect(await page.getByTestId("marker-success").count()).toBeGreaterThanOrEqual(1);
    await noPageScroll(page);
    expect(await page.getByTestId("marker-findings").count()).toBeGreaterThanOrEqual(2);
    await timelineLabelsDoNotOverlap(page);
    await shot(page, "drill-verify");
  });

  test("Manual: inject a post-quantum attack, see it in the graph, assess, defend", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await openSimulation(page);
    await page.getByTestId("device-select").selectOption("PUMP-ICU-A12");
    await expect(page.locator('[data-testid="attack-select"] optgroup[label="Post-quantum attacks"] option')).toHaveCount(4);

    await inject(page, "cert_spoof");
    await expect(page.getByTestId("sim-notice")).toContainText("Injected Quantum certificate forgery");
    await expect(page.getByTestId("active-attacks")).toContainText("Quantum certificate forgery");
    await expect(page.getByTestId("kpi-attacks")).toContainText("1");
    await expect(page.getByTestId("marker-danger").first()).toBeAttached({ timeout: 5_000 });

    await page.getByTestId("assess-device").click();
    await expect(page.getByTestId("agents-done")).toHaveText(/14\/14 done/, { timeout: 30_000 });
    await expect(page.getByTestId("device-status")).toHaveText("UNSAFE");
    await page.getByTestId("open-report").click();
    await page.getByTestId("rtab-findings").click();
    await expect(page.getByTestId("finding-authentication_failed")).toBeVisible();
    await shot(page, "report-overlay");
    await page.getByTestId("close-overlay").click();

    await page.getByTestId("defence-select").selectOption("pq_certificates");
    await page.getByTestId("defend-btn").click();
    await expect(page.getByTestId("sim-notice")).toContainText("Applied ML-DSA certificates");
    await inject(page, "cert_spoof");
    await expect(page.getByTestId("sim-notice")).toContainText("Blocked");
  });

  test("Core issues and affected devices lead to detail pages and fixes", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await openSimulation(page);
    await expect(page.getByTestId("core-issues")).toBeVisible();
    await expect(page.getByTestId("affected-devices").locator("tbody tr")).toHaveCount(9);
    await expect(page.getByTestId("core-kex").locator(".sev")).toHaveText("6");

    await page.getByTestId("affected-PUMP-ICU-A12").click();
    await expect(page.getByTestId("overlay-device")).toContainText("PUMP-ICU-A12");
    await page.getByTestId("close-overlay").click();

    await page.getByTestId("core-kex").click();
    await expect(page.getByTestId("overlay-core")).toContainText("Classical key exchange");
    await expect(page.getByTestId("overlay-core")).toContainText("Hybrid ML-KEM key exchange");
    await shot(page, "core-issue");
    await page.getByTestId("fix-core").click();
    await expect(page.getByTestId("overlay-core")).toBeHidden();
    await expect(page.getByTestId("core-kex").locator(".sev")).toHaveText("0");
    await expect(page.getByTestId("core-hndl").locator(".sev")).toHaveText("0");
    await expect(page.getByTestId("marker-success").first()).toBeAttached();
    await timelineLabelsDoNotOverlap(page);
    await noPageScroll(page);
  });

  test("Q-Day assumption re-classifies HNDL exposure", async ({ page }) => {
    await openSimulation(page);
    await page.getByTestId("qday-select").selectOption("30");
    await expect(page.getByTestId("kpi-hndl")).toContainText("0");
    await page.getByTestId("qday-select").selectOption("4");
    await expect(page.getByTestId("kpi-hndl")).not.toContainText(/HNDL-exposed0$/);
  });

  test("Detail pages: device, activity, fleet report with PDF and plan", async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await openSimulation(page);
    await page.getByTestId("device-select").selectOption("AI-ASSIST-01");
    await inject(page, "pq_downgrade_prompt");

    await page.getByTestId("open-device").click();
    await expect(page.getByTestId("overlay-device")).toContainText("Lands on: Application · AI assistant");
    await page.keyboard.press("Escape");

    await page.getByTestId("open-activity").click();
    await expect(page.getByTestId("event-log")).toContainText("Injected PQ-downgrade prompt injection");
    await page.getByTestId("close-overlay").click();

    await page.getByTestId("open-fleet").click();
    await page.getByTestId("assess-fleet").click();
    await expect(page.getByTestId("fleet-verdict")).toHaveAttribute("data-status", "UNSAFE", { timeout: 30_000 });
    const [download] = await Promise.all([page.waitForEvent("download"), page.getByTestId("download-fleet-pdf").click()]);
    expect((await pdfBytes(download)).subarray(0, 5).toString()).toBe("%PDF-");
    await page.getByTestId("apply-plan").click();
    await expect(page.getByTestId("fleet-notice")).toContainText("Applied");
    await shot(page, "fleet-overlay");
  });

  test("Assessment: critical ICU gateway → UNSAFE with KPIs, tabs, evidence, PDF", async ({ page }) => {
    await page.goto("/#lab");
    await page.getByTestId("scenario-select").selectOption("icu_gateway_critical");
    await page.getByTestId("run-assessment").click();
    await expect(page.getByTestId("agents-done")).toHaveText(/14\/14 done/, { timeout: 30_000 });
    await expect(page.getByTestId("verdict")).toHaveAttribute("data-status", "UNSAFE");
    await expect(page.getByTestId("kpi-status")).toContainText("UNSAFE");
    await expect(page.getByTestId("gauge")).toBeVisible();
    await expect(page.getByTestId("radar")).toBeVisible();
    await shot(page, "assessment-unsafe", true);
    await page.getByTestId("rtab-xai").click();
    await expect(page.getByTestId("attribution")).toContainText("Harvest-now-decrypt-later");
    await page.getByTestId("rtab-findings").click();
    await page.getByTestId("finding-long_lifetime_classical_crypto").click();
    await expect(page.locator(".evidence").first()).toContainText("tls_config");
    const [download] = await Promise.all([page.waitForEvent("download"), page.getByTestId("download-pdf").click()]);
    expect((await pdfBytes(download)).subarray(0, 5).toString()).toBe("%PDF-");
  });

  test("Assessment: PQ-ready gateway → SAFE; CSV upload judged on content", async ({ page }) => {
    await page.goto("/#lab");
    await page.getByTestId("scenario-select").selectOption("nextgen_pq_safe");
    await page.getByTestId("run-assessment").click();
    await expect(page.getByTestId("verdict")).toHaveAttribute("data-status", "SAFE");
    await shot(page, "assessment-safe", true);
    await page.getByTestId("mode-upload").click();
    await page.getByTestId("file-input").setInputFiles(path.join(here, "fixtures", "synthetic_syn_flood.csv"));
    await page.getByTestId("run-assessment").click();
    await expect(page.getByTestId("verdict")).toHaveAttribute("data-status", "UNSAFE");
  });

  test("Why Post-Quantum, Agents & Tools and About pages", async ({ page }) => {
    await page.goto("/#why");
    await expect(page.getByTestId("why-attacks").locator("tbody tr")).toHaveCount(15);
    await shot(page, "why", true);
    await page.getByTestId("tab-agents").click();
    await expect(page.getByTestId("agent-table").locator("tbody tr")).toHaveCount(14);
    await page.getByTestId("tool-pqc.classify_algorithm").click();
    await page.getByTestId("tool-invoke").click();
    await expect(page.getByTestId("tool-output")).toContainText("hybrid_pq");
    await page.getByTestId("tab-about").click();
    await expect(page.getByTestId("research-status")).toContainText("early-stage concept");
  });
});
