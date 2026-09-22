import { expect, test, type Page } from "@playwright/test";

const PUBLIC_ROUTES = ["/", "/install", "/pricing", "/blog", "/blog/rss.xml", "/robots.txt", "/sitemap.xml"];
const APP_ROUTES = [
  "/studio",
  "/studio/create",
  "/studio/library",
  "/studio/moodboards",
  "/studio/canvas",
  "/studio/campaigns",
  "/studio/calendar",
  "/studio/analytics",
  "/studio/settings",
  "/admin",
  "/admin/settings",
];

const HIGH_RISK = /(approve .*build final|publish|go live|launch ad|render|activate ad|pause ad|delete|remove|checkout|pay now|purchase|upgrade|schedule approved content)/i;
const DRAFT_WRITE = /(generate canonical campaign|build ad plan|run command|resolve connected accounts)/i;
const allowDraftWrites = process.env.PLAYWRIGHT_ALLOW_DRAFT_WRITES === "true";

function collectRuntimeFailures(page: Page) {
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(`pageerror: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error") failures.push(`console: ${message.text()}`);
  });
  page.on("requestfailed", (request) => {
    const failure = request.failure();
    failures.push(`requestfailed: ${request.method()} ${request.url()} ${failure?.errorText || ""}`);
  });
  return failures;
}

test.describe("production public journey", () => {
  for (const route of PUBLIC_ROUTES) {
    test(`${route} loads without browser runtime failures`, async ({ page }) => {
      const failures = collectRuntimeFailures(page);
      const response = await page.goto(route, { waitUntil: "networkidle" });
      expect(response?.status(), `HTTP status for ${route}`).toBeLessThan(400);

      if (route === "/pricing") {
        await expect(page).toHaveURL(/\/install\/?$/);
      }

      if (route.endsWith(".txt") || route.endsWith(".xml")) return;
      await expect(page.locator("body")).toBeVisible();
      expect(failures, failures.join("\n")).toEqual([]);
    });
  }

  test("retired public product routes cannot expose stale offers or ungoverned creator UI", async ({ page }) => {
    await page.goto("/founding", { waitUntil: "networkidle" });
    await expect(page).toHaveURL(/\/install\/?$/);
    await expect(page.getByText("$29", { exact: false })).toHaveCount(0);

    await page.goto("/create", { waitUntil: "networkidle" });
    await expect(page).toHaveURL(/\/admin\?next=%2Fstudio%2Fcreate/);
    await expect(page.getByText("Operator access", { exact: false })).toBeVisible();
  });

  test("blog cards and RSS stay on the canonical Buffer Blaster host", async ({ page, request }) => {
    await page.goto("/blog", { waitUntil: "networkidle" });
    const postLinks = page.locator('a[href^="/blog/"]');
    const hrefs = await postLinks.evaluateAll((links) => [...new Set(links.map((link) => link.getAttribute("href")).filter(Boolean))] as string[]);
    expect(hrefs.length).toBeGreaterThan(0);
    for (const href of hrefs) {
      const response = await request.get(href);
      expect(response.status(), href).toBe(200);
    }

    const rss = await request.get("/blog/rss.xml");
    expect(rss.status()).toBe(200);
    const xml = await rss.text();
    expect(xml).toContain("https://bufferblaster.netlify.app/blog");
    expect(xml).not.toContain("https://example.com");
    expect(xml).not.toContain("stavarai-platform.vercel.app");
  });

  test("homepage public controls resolve and media loads", async ({ page }) => {
    const failures = collectRuntimeFailures(page);
    await page.goto("/", { waitUntil: "networkidle" });

    const anchorLinks = page.locator('a[href^="#"]');
    const anchorCount = await anchorLinks.count();
    for (let i = 0; i < anchorCount; i += 1) {
      const link = anchorLinks.nth(i);
      const href = await link.getAttribute("href");
      if (!href || href === "#") continue;
      await link.click();
      await expect(page.locator(href)).toBeVisible();
    }

    const internalLinks = page.locator('a[href^="/"]');
    const internalCount = await internalLinks.count();
    expect(internalCount).toBeGreaterThan(0);

    const videos = page.locator("video");
    const videoCount = await videos.count();
    expect(videoCount).toBeGreaterThanOrEqual(2);
    for (let i = 0; i < videoCount; i += 1) {
      const state = await videos.nth(i).evaluate((video: HTMLVideoElement) => ({
        readyState: video.readyState,
        currentSrc: video.currentSrc,
        error: video.error?.message || null,
      }));
      expect(state.currentSrc).toMatch(/^https?:\/\//);
      expect(state.error).toBeNull();
      expect(state.readyState).toBeGreaterThanOrEqual(1);
    }

    expect(failures, failures.join("\n")).toEqual([]);
  });

  test("install form is interactive and only submits when explicitly enabled", async ({ page }) => {
    const failures = collectRuntimeFailures(page);
    await page.goto("/install", { waitUntil: "networkidle" });

    const email = page.locator('input[name="email"]').first();
    await expect(email).toBeVisible();
    await email.fill(process.env.PLAYWRIGHT_FORM_EMAIL || "buffer-blaster-playwright-qa@example.com");

    const submit = page.getByRole("button", { name: /request|install|submit|send/i }).first();
    await expect(submit).toBeEnabled();

    if (process.env.PLAYWRIGHT_ALLOW_FORM_SUBMIT === "true") {
      await submit.click();
      await expect(page.getByText(/received|request|thanks|thank you/i).first()).toBeVisible();
    }

    expect(failures, failures.join("\n")).toEqual([]);
  });
});

test.describe("anonymous application boundary", () => {
  for (const route of APP_ROUTES) {
    test(`${route} has a truthful anonymous state`, async ({ page }) => {
      const failures = collectRuntimeFailures(page);
      const response = await page.goto(route, { waitUntil: "networkidle" });
      expect(response?.status()).toBeLessThan(500);

      if (route.startsWith("/studio")) {
        const url = page.url();
        const body = await page.locator("body").innerText();
        const guarded = /\/admin\/?$/.test(new URL(url).pathname) || /sign in|operator access|checking operator access/i.test(body);
        expect(guarded, `Studio route ${route} must not silently expose live operator controls anonymously`).toBeTruthy();
      }

      expect(failures.filter((failure) => !failure.includes("/api/")), failures.join("\n")).toEqual([]);
    });
  }
});

test.describe("mobile navigation contract", () => {
  test("public homepage has no page-level horizontal overflow", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/", { waitUntil: "networkidle" });
    const dimensions = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(dimensions.scrollWidth).toBe(dimensions.clientWidth);
  });

  test("anonymous mobile Studio still lands at operator access", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/studio", { waitUntil: "networkidle" });
    await expect(page).toHaveURL(/\/admin\?next=/);
    await expect(page.getByText("Operator access", { exact: false })).toBeVisible();
  });
});

test.describe("authenticated operator journey", () => {
  test.skip(!process.env.PLAYWRIGHT_OPERATOR_PASSWORD, "Set PLAYWRIGHT_OPERATOR_PASSWORD to exercise private Studio controls.");

  test("login and exercise every safe visible Studio button", async ({ page }) => {
    const failures = collectRuntimeFailures(page);
    await page.goto("/admin", { waitUntil: "networkidle" });

    const password = page.locator('input[type="password"]').first();
    await expect(password).toBeVisible();
    await password.fill(process.env.PLAYWRIGHT_OPERATOR_PASSWORD || "");

    const login = page.getByRole("button", { name: /sign in|login|enter/i }).first();
    await login.click();
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveURL(/\/studio|\/admin/);

    const studioRoutes = APP_ROUTES.filter((route) => route.startsWith("/studio"));
    for (const route of studioRoutes) {
      await page.goto(route, { waitUntil: "networkidle" });

      const buttons = page.getByRole("button");
      const count = await buttons.count();
      for (let i = 0; i < count; i += 1) {
        const button = buttons.nth(i);
        if (!(await button.isVisible()) || !(await button.isEnabled())) continue;
        const name = ((await button.getAttribute("aria-label")) || (await button.innerText()) || "").trim();
        if (!name || HIGH_RISK.test(name)) continue;
        if (DRAFT_WRITE.test(name) && !allowDraftWrites) continue;

        await button.click();
        await page.waitForTimeout(250);
      }
    }

    expect(failures, failures.join("\n")).toEqual([]);
  });
});
