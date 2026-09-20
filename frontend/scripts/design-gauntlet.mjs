import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const required = [
  "src/app/page.tsx",
  "src/app/pricing/page.tsx",
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
  "src/components/studio-shell.tsx",
  "src/components/agent-command.tsx",
];

let ok = true;
const fail = (message) => { console.error(`GAUNTLET FAIL: ${message}`); ok = false; };
const pass = (message) => console.log(`GAUNTLET PASS: ${message}`);
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");

for (const file of required) if (!fs.existsSync(path.join(root, file))) fail(`missing ${file}`);
if (ok) pass("all public and Studio surfaces exist");

const publicFiles = ["src/app/page.tsx", "src/app/install/page.tsx", "src/app/pricing/page.tsx", "src/app/layout.tsx", "src/app/robots.ts", "src/app/sitemap.ts"];
const forbidden = ["Social Studio", "Stavarai", "Hermes", "Higgsfield"];
for (const file of publicFiles) {
  if (!fs.existsSync(path.join(root, file))) continue;
  const text = read(file);
  for (const term of forbidden) if (text.includes(term)) fail(`${file} exposes retired/internal identity ${term}`);
}
const combinedPublic = publicFiles.filter(file => fs.existsSync(path.join(root, file))).map(read).join("\n");
if (!combinedPublic.includes("Buffer Blaster")) fail("public surfaces do not identify the product as Buffer Blaster");
if (ok) pass("public identity is Buffer Blaster without internal codenames");

const home = read("src/app/page.tsx");
for (const signal of ["AI video ad factory · private install", "Create AI ads.", "Own the factory.", "Watch real output", "Watch what Buffer Blaster makes.", "Request a private install", "No Buffer Blaster subscription"]) {
  if (!home.includes(signal)) fail(`homepage missing proof-first positioning signal ${signal}`);
}
for (const stale of ["Private creative infrastructure", "Installed once. Yours to run.", "Proof before promises.", "Stop renting the workflow.", "Keep the operating truth", "Provider-neutral generation", "One workflow. Different model doors.", "See the $249 pilot", "Founding Ad Batch", "$249"]) {
  if (home.includes(stale)) fail(`homepage exposes stale or jargon-heavy signal ${stale}`);
}
if (!home.includes('id="proof"')) fail("homepage has no proof section");
if (!home.includes('id="ownership"')) fail("homepage has no ownership section");
if (!home.includes('id="install"')) fail("homepage has no install conversion section");
if (!home.includes("controls playsInline")) fail("homepage proof video is not directly watchable");
if (!home.includes("aspect-[9/16]")) fail("homepage vertical proof is not framed at 9:16");
if (home.includes("/media/ugc-skincare.mp4")) fail("homepage still exposes the superseded skincare proof");
if (!home.includes("Selva & Sea")) fail("homepage is missing the locked Selva & Sea proof");
if (!home.includes("Placeholder only · not proof") || !home.includes("UGC slot 03")) fail("homepage is missing the explicit future UGC placeholder");
if (!home.includes("md:grid-cols-3")) fail("proof wall is missing the responsive three-slot composition");
if (ok) pass("homepage leads with outcome, uncropped proof, an honest future UGC slot, ownership, and a concrete install action");

const inquiry = read("src/components/InstallInquiry.tsx");
if (!inquiry.includes('role="status"') || !inquiry.includes('aria-live="polite"')) fail("install inquiry does not announce success/error state accessibly");
if (!inquiry.includes("inverse = false") || !home.includes("<InstallInquiry compact inverse />")) fail("dark install surface does not use the high-contrast form treatment");
else pass("install inquiry exposes accessible feedback and correct dark-surface contrast");

const access = read("src/app/install/page.tsx");
for (const signal of ["One-time private install", "Install the factory once.", "One install. Yours to run.", "No recurring Buffer Blaster SaaS plan", "Studio + REST + MCP + CLI access", "Usage stays transparent"]) {
  if (!access.toLowerCase().includes(signal.toLowerCase())) fail(`install page missing ownership signal ${signal}`);
}
for (const stale of ["7-Day Test Drive", "$19", "$49", "$99", "$199", "Ad Credits", "CheckoutButton", "Join the beta", "Private beta"]) {
  if (access.toLowerCase().includes(stale.toLowerCase())) fail(`install page exposes retired public subscription signal ${stale}`);
}
if (ok) pass("install page sells a one-time owned deployment rather than a recurring Buffer Blaster subscription");

const shell = read("src/components/studio-shell.tsx");
for (const signal of ["bg-[#e9e9e7]", "bg-[#f7f7f5]", "rounded-[26px]", "#2357ff", "Agent mode"]) if (!shell.includes(signal)) fail(`studio shell missing design-bar signal ${signal}`);
if (ok) pass("studio shell carries quiet-shell design signals");

const command = read("src/components/agent-command.tsx");
if (!command.includes("SpeechRecognition") || !command.includes("Human approval required")) fail("agent command lacks voice or approval boundary");
else pass("agent command includes voice and approval-aware intent surface");
if (!command.includes("runAgentCommand") || !command.includes("await runAgentCommand")) fail("agent command is not wired to the studio agent API");
else pass("agent command executes through the shared Studio API when live");

const calendar = read("src/app/studio/calendar/page.tsx");
for (const signal of ["listSocialAccounts", "scheduleDrop", "social_account_id", "scheduled_at", "Simulation only"]) if (!calendar.includes(signal)) fail(`calendar missing scheduling signal ${signal}`);
if (ok) pass("calendar preserves explicit publishing approval boundary");

const accessImportsCheckout = access.includes("CheckoutButton") || access.includes("/api/checkout/offer");
if (accessImportsCheckout) fail("private access page still depends on legacy public checkout");
else pass("private access positioning is decoupled from legacy low-ticket checkout");

const create = read("src/app/studio/create/page.tsx");
for (const signal of ["Build ad plan", "Customer pain", "Product mechanism", "Estimated generation reserve", "Credits required", "build final ad", "Factory receipt"]) if (!create.toLowerCase().includes(signal.toLowerCase())) fail(`create surface missing trust signal ${signal}`);
if (create.includes("Approve & render clip 1")) fail("create surface still exposes superseded single-clip paid path");
if (ok) pass("create surface is full-ad-plan-first with explicit spend approval");

const overview = read("src/app/studio/page.tsx");
const library = read("src/app/studio/library/page.tsx");
const analytics = read("src/app/studio/analytics/page.tsx");
for (const fake of ["84.2K", "6.4K", "1,284", "2 videos processing", "3 awaiting review", "Active campaigns\" value=\"4"]) {
  if (overview.includes(fake) || library.includes(fake) || analytics.includes(fake)) fail(`live Studio still exposes synthetic operating value ${fake}`);
}
if (!overview.includes("getLedgerSummary") || !library.includes("listCreativeJobs")) fail("Studio or Library is not wired to canonical ledger state");
if (!analytics.includes("No performance evidence yet")) fail("analytics does not fail closed without real performance events");
if (ok) pass("production-facing Studio state is canonical or explicitly empty");

if (!ok) process.exit(1);
console.log("DESIGN GAUNTLET STRUCTURAL GATE PASS");
