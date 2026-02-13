import { test, expect } from "@playwright/test";
import { execSync, spawn, ChildProcess } from "child_process";
import * as path from "path";
import * as fs from "fs";

const ROOT = path.resolve(__dirname, "..");
const VENV_PYTHON = path.join(ROOT, ".venv", "bin", "python");
const GEN_SCRIPT = path.join(ROOT, "scripts", "generate_pid.py");
const MANIFEST_SCRIPT = path.join(ROOT, "scripts", "generate_manifest.py");
const VALIDATOR = path.join(ROOT, "tests", "helpers", "validate_title_block.py");
const GEN_IMAGES = path.join(ROOT, "data", "DigitizePID_Dataset", "images", "generated");
const TEST_IMAGE = path.join(GEN_IMAGES, "gen_0000.jpg");
const PORT = 8106;

let server: ChildProcess;

test.beforeAll(async () => {
  // Generate 1 test image with seed 42
  execSync(`${VENV_PYTHON} ${GEN_SCRIPT} generate -n 1 --seed 42`, {
    cwd: ROOT,
    timeout: 120_000,
    stdio: "pipe",
  });

  // Regenerate manifest
  execSync(`${VENV_PYTHON} ${MANIFEST_SCRIPT}`, {
    cwd: ROOT,
    timeout: 30_000,
    stdio: "pipe",
  });

  // Start HTTP server
  server = spawn(VENV_PYTHON, [path.join(ROOT, "server.py"), String(PORT)], {
    cwd: ROOT,
    stdio: "pipe",
  });

  // Wait for server to be ready
  const maxWait = 10_000;
  const start = Date.now();
  while (Date.now() - start < maxWait) {
    try {
      execSync(`curl -s -o /dev/null -w "%{http_code}" http://localhost:${PORT}/viewer/`, {
        timeout: 2_000,
      });
      break;
    } catch {
      await new Promise((r) => setTimeout(r, 500));
    }
  }
});

test.afterAll(() => {
  if (server) {
    server.kill("SIGTERM");
  }
});

// ── Test 1: Pixel-level validation ─────────────────────────────
test("generated image passes pixel-level title block validation", () => {
  expect(fs.existsSync(TEST_IMAGE)).toBe(true);

  const result = execSync(`${VENV_PYTHON} ${VALIDATOR} ${TEST_IMAGE}`, {
    timeout: 30_000,
    encoding: "utf-8",
  });

  const json = JSON.parse(result.trim());
  expect(json.pass).toBe(true);

  // Verify each individual check
  for (const [name, check] of Object.entries(json.checks)) {
    expect((check as { pass: boolean }).pass).toBe(true);
  }
});

// ── Test 2: Viewer loads generated image in gallery ────────────
test("viewer loads generated image in gallery", async ({ page }) => {
  await page.goto("/viewer/");
  await page.waitForSelector(".thumb-card", { timeout: 15_000 });

  // Click the Generated filter
  await page.click('[data-filter="generated"]');
  await page.waitForTimeout(500);

  const thumbs = await page.locator(".thumb-card").count();
  expect(thumbs).toBeGreaterThanOrEqual(1);
});

// ── Test 3: Viewer detail view shows generated image ───────────
test("viewer detail view shows generated image", async ({ page }) => {
  await page.goto("/viewer/");
  await page.waitForSelector(".thumb-card", { timeout: 15_000 });

  // Filter to generated
  await page.click('[data-filter="generated"]');
  await page.waitForTimeout(500);

  // Click first thumbnail to open detail
  await page.click(".thumb-card");
  await page.waitForSelector("#detail", { state: "visible", timeout: 10_000 });

  // Verify detail title contains gen_0000
  const title = await page.locator("#detail-title").textContent();
  expect(title).toContain("gen_0000");

  // Verify canvas exists
  const canvas = page.locator("#pid-canvas");
  await expect(canvas).toBeVisible();
});

// ── Test 4: Keyboard navigation works ──────────────────────────
test("keyboard navigation works", async ({ page }) => {
  await page.goto("/viewer/");
  await page.waitForSelector(".thumb-card", { timeout: 15_000 });

  // Open first image
  await page.click('[data-filter="generated"]');
  await page.waitForTimeout(500);
  await page.click(".thumb-card");
  await page.waitForSelector("#detail", { state: "visible", timeout: 10_000 });

  // Press Escape to close detail view
  await page.keyboard.press("Escape");
  await page.waitForTimeout(500);

  // Detail should be hidden
  const detail = page.locator("#detail");
  await expect(detail).toBeHidden();
});
