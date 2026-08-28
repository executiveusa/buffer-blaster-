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

for (const file of required) {
  if (!fs.existsSync(path.join(root, file))) fail(`missing ${file}`);
}
if (ok) pass("all V1 public/product routes exist");

const publicFiles = ["src/app/page.tsx", "src/app/pricing/page.tsx", "src/app/layout.tsx", "src/app/robots.ts", "src/app/sitemap.ts"];
const forbidden = ["Buffer Blaster", "Stavarai", "Hermes", "Higgsfield"];
for (const file of publicFiles) {
  if (!fs.existsSync(path.join(root, file))) continue;
  const text = fs.readFileSync(path.join(root, file), "utf8");
  for (const term of forbidden) if (text.includes(term)) fail(`${file} exposes internal codename ${term}`);
}
if (ok) pass("public surfaces hide internal codenames");

const shell = fs.readFileSync(path.join(root, "src/components/studio-shell.tsx"), "utf8");
for (const signal of ["bg-[#e9e9e7]", "bg-[#f7f7f5]", "rounded-[26px]", "#2357ff", "Agent mode"]) {
  if (!shell.includes(signal)) fail(`studio shell missing design-bar signal ${signal}`);
}
if (ok) pass("studio shell carries Adpanel-derived quiet-shell signals");

const command = fs.readFileSync(path.join(root, "src/components/agent-command.tsx"), "utf8");
if (!command.includes("SpeechRecognition") || !command.includes("Human approval required")) fail("agent command lacks voice or approval boundary");
else pass("agent command includes voice and approval-aware intent surface");

const pricing = fs.readFileSync(path.join(root, "src/app/pricing/page.tsx"), "utf8");
for (const price of ["39", "119", "299"]) if (!pricing.includes(price)) fail(`pricing page missing $${price}`);
if (ok) pass("three-tier commercial packaging present");

if (!ok) process.exit(1);
console.log("DESIGN GAUNTLET STRUCTURAL GATE PASS");
