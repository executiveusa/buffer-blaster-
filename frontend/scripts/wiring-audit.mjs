import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
let ok = true;
const fail = (message) => { console.error(`WIRING FAIL: ${message}`); ok = false; };
const pass = (message) => console.log(`WIRING PASS: ${message}`);
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");
const exists = (file) => fs.existsSync(path.join(root, file));

const home = read("src/app/page.tsx");
const anchorTargets = [...home.matchAll(/href="#([^"]+)"/g)].map((match) => match[1]);
for (const id of new Set(anchorTargets)) {
  if (!home.includes(`id="${id}"`)) fail(`homepage link #${id} has no matching section`);
}
if (ok) pass("homepage anchor CTAs resolve to real sections");

for (const route of [
  "src/app/install/page.tsx",
  "src/app/studio/page.tsx",
  "src/app/studio/create/page.tsx",
  "src/app/studio/library/page.tsx",
  "src/app/studio/moodboards/page.tsx",
  "src/app/studio/canvas/page.tsx",
  "src/app/studio/campaigns/page.tsx",
  "src/app/studio/calendar/page.tsx",
  "src/app/studio/analytics/page.tsx",
  "src/app/studio/settings/page.tsx",
  "src/app/admin/page.tsx",
  "src/app/admin/settings/page.tsx",
]) {
  if (!exists(route)) fail(`missing routed surface ${route}`);
}
if (ok) pass("public, Studio, and operator routes exist");

const shell = read("src/components/studio-shell.tsx");
for (const signal of ['router.replace("/admin")', "getToken()", "!isDemoMode()", "!isPublicConsole()"]) {
  if (!shell.includes(signal)) fail(`Studio auth guard missing ${signal}`);
}
if (ok) pass("live Studio redirects unauthenticated operators to sign-in");

const create = read("src/app/studio/create/page.tsx");
if (create.includes('href="/pricing"') || create.includes("Start with a paid test pass")) fail("Studio create still points at retired public billing");
if (!create.includes('href="/studio/settings"') || !create.includes("server-side generation allowance")) fail("Studio create does not route blocked generation to operator readiness");
if (ok) pass("Studio create no longer exposes retired paid-pass CTA");

const clients = read("src/app/admin/clients/page.tsx");
if (clients.includes(">Add client<") || clients.includes("<Plus")) fail("admin clients still exposes a dead Add client button");
if (ok) pass("admin clients contains no dead add-client control");

const inquiry = read("src/components/InstallInquiry.tsx");
const forms = read("public/forms.html");
for (const signal of ['name="buffer-blaster-install"', 'data-netlify="true"', 'data-netlify-honeypot="bot-field"', 'name="email"']) {
  if (!inquiry.includes(signal) || !forms.includes(signal)) fail(`install inquiry registration mismatch: ${signal}`);
}
if (!inquiry.includes('aria-live="polite"')) fail("install inquiry lacks accessible status feedback");
if (ok) pass("install inquiry matches registered Netlify form contract");

const studioApi = read("src/lib/studio-api.ts");
const studioState = read("src/lib/studio-state.ts");
const campaignApi = read("src/lib/campaign-api.ts");
const refs = read("src/lib/studio-references.ts");
for (const [name, source] of [["studio-api",studioApi],["studio-state",studioState],["campaign-api",campaignApi],["studio-references",refs]]) {
  if (!source.includes('response.status === 401') || !source.includes('window.location.assign("/admin")')) fail(`${name} does not fail closed on expired operator auth`);
}
if (ok) pass("live Studio API clients fail closed and return expired sessions to sign-in");

if (process.env.NETLIFY === "true" && process.env.CONTEXT === "production") {
  const exact = {
    NEXT_PUBLIC_DEMO_MODE: "false",
    NEXT_PUBLIC_PUBLIC_CONSOLE: "false",
  };
  for (const [key, expected] of Object.entries(exact)) {
    if (process.env[key] !== expected) fail(`production ${key} must equal ${expected}`);
  }
  for (const key of ["NEXT_PUBLIC_API_URL", "BLASTER_API_URL", "SITE_URL"]) {
    const value = process.env[key] || "";
    if (!value.startsWith("https://")) fail(`production ${key} must be an https URL`);
  }
  if (ok) pass("Netlify production is configured for live private mode and HTTPS backend wiring");
}

if (!ok) process.exit(1);
console.log("PRODUCTION WIRING AUDIT PASS");
