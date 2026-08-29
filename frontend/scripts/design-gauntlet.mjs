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
  "src/components/checkout-button.tsx",
  "src/app/api/checkout/offer/route.ts",
  "src/app/api/trial/activate/route.ts",
  "src/app/api/trial/execute/route.ts",
];

let ok = true;
const fail = (message) => { console.error(`GAUNTLET FAIL: ${message}`); ok = false; };
const pass = (message) => console.log(`GAUNTLET PASS: ${message}`);
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");

for (const file of required) if (!fs.existsSync(path.join(root, file))) fail(`missing ${file}`);
if (ok) pass("all public, studio, checkout, and trial surfaces exist");

const publicFiles = ["src/app/page.tsx", "src/app/pricing/page.tsx", "src/app/layout.tsx", "src/app/robots.ts", "src/app/sitemap.ts"];
const forbidden = ["Buffer Blaster", "Stavarai", "Hermes", "Higgsfield"];
for (const file of publicFiles) {
  if (!fs.existsSync(path.join(root, file))) continue;
  const text = read(file);
  for (const term of forbidden) if (text.includes(term)) fail(`${file} exposes internal codename ${term}`);
}
if (ok) pass("public surfaces hide internal codenames");

const shell = read("src/components/studio-shell.tsx");
for (const signal of ["bg-[#e9e9e7]", "bg-[#f7f7f5]", "rounded-[26px]", "#2357ff", "Agent mode"]) if (!shell.includes(signal)) fail(`studio shell missing design-bar signal ${signal}`);
if (ok) pass("studio shell carries quiet-shell design signals");

const command = read("src/components/agent-command.tsx");
if (!command.includes("SpeechRecognition") || !command.includes("Human approval required")) fail("agent command lacks voice or approval boundary");
else pass("agent command includes voice and approval-aware intent surface");
if (!command.includes("runAgentCommand") || !command.includes("await runAgentCommand")) fail("agent command is not wired to the studio agent API");
else pass("agent command executes through the shared studio API when live");

const calendar = read("src/app/studio/calendar/page.tsx");
for (const signal of ["listSocialAccounts", "scheduleDrop", "social_account_id", "scheduled_at", "Simulation only"]) if (!calendar.includes(signal)) fail(`calendar missing scheduling signal ${signal}`);
if (ok) pass("calendar preserves explicit publishing approval boundary");

const pricing = read("src/app/pricing/page.tsx");
for (const signal of ["7-Day Test Drive", "$19", "3 Ad Credits", "30-Day Launch Pass", "$49", "8 Ad Credits", "$99", "$199", "under $1", "unused trial credits expire"]) if (!pricing.toLowerCase().includes(signal.toLowerCase())) fail(`pricing page missing paid-trial signal ${signal}`);
for (const stale of ["Founding Ad Batch", "3 vertical UGC ads", "$249"]) if (pricing.includes(stale)) fail(`pricing page still exposes superseded launch offer ${stale}`);
if (pricing.toLowerCase().includes("free trial")) fail("paid pass is mislabeled as a free trial");
if (ok) pass("paid test-pass pricing is explicit and non-deceptive");

const checkout = read("src/app/api/checkout/offer/route.ts");
for (const signal of ["trial-7", "trial-30", "starter-monthly", "pro-monthly", "metadata[offer]", "CHECKOUT_SESSION_ID"]) if (!checkout.includes(signal)) fail(`checkout route missing offer-safety signal ${signal}`);
const activation = read("src/app/api/trial/activate/route.ts");
for (const signal of ["billing/activate", "HttpOnly", "httpOnly: true", "TRIAL_COOKIE"]) if (!activation.includes(signal)) fail(`trial activation missing security signal ${signal}`);
if (ok) pass("paid checkout activates a signed HttpOnly trial session");

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
