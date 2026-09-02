import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const required = [
  "src/app/page.tsx",
  "src/app/pricing/page.tsx",
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

const publicFiles = ["src/app/page.tsx", "src/app/pricing/page.tsx", "src/app/layout.tsx", "src/app/robots.ts", "src/app/sitemap.ts"];
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
for (const signal of ["Private creative infrastructure", "Find the angle.", "Make the ad.", "Learn what works.", "We sell the outcome. Buffer Blaster is how we deliver it."]) {
  if (!home.includes(signal)) fail(`homepage missing positioning signal ${signal}`);
}
for (const stale of ["See the $249 pilot", "Founding Ad Batch", "$249"] ) if (home.includes(stale)) fail(`homepage exposes retired offer ${stale}`);
if (ok) pass("homepage leads with the private creative-infrastructure outcome");

const access = read("src/app/pricing/page.tsx");
for (const signal of ["The software is not the offer", "Creative Engine", "Private Install", "another login is not leverage", "Studio + REST + MCP + CLI access"]) {
  if (!access.toLowerCase().includes(signal.toLowerCase())) fail(`access page missing private-infrastructure signal ${signal}`);
}
for (const stale of ["7-Day Test Drive", "$19", "$49", "$99", "$199", "Ad Credits", "CheckoutButton"]) {
  if (access.toLowerCase().includes(stale.toLowerCase())) fail(`access page exposes retired public subscription signal ${stale}`);
}
if (ok) pass("access page sells managed outcomes and private installs rather than token plans");

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

// Legacy checkout/trial routes may remain for compatibility, but the public access page must not depend on them.
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
