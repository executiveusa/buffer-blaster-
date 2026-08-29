import { getToken, isDemoMode, isPublicConsole } from "./api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const seeded = () => isDemoMode() || isPublicConsole();

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(init?.headers as Record<string, string> | undefined) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || body.error || response.statusText);
  return body as T;
}

export type UGCBrief = {
  idea: string; product?: string; camera?: string; subject?: string; environment?: string;
  lighting?: string; style?: string; motion?: string; dialogue?: string; platform?: string;
  aspect_ratio?: string; image_url?: string; duration?: string; generate_audio?: boolean;
};

export type UGCFactoryBrief = {
  product: string;
  audience: string;
  pain: string;
  mechanism: string;
  offer?: string;
  platform?: string;
  actor_description?: string;
  delivery_tone?: string;
  visual_lane?: string;
};

export type UGCFactoryClip = {
  clip: number;
  duration_seconds: number;
  purpose: string;
  script: string;
  script_word_count: number;
  prompt: string;
  seed_from_previous: boolean;
};

export type UGCFactoryPlan = {
  ok: boolean;
  factory_version: string;
  brief: UGCFactoryBrief;
  gate: { passed: boolean; checks: Array<{ name: string; passed: boolean; detail: string }> };
  clips: UGCFactoryClip[];
  continuity: { steps: string[]; seam_threshold_mean_abs_diff: number; claim: string };
  icm: { template: string; stages: string[] };
  commercial: {
    billable_unit: string;
    price_cents: number;
    estimated_generation_cost_cents: number;
    expected_paid_clip_calls: number;
    gross_margin_cents: number;
    gross_margin_pct: number;
    charges_customer: boolean;
    estimate_only: boolean;
  };
  approval_required_before_publish: boolean;
};

export type FactoryRenderResult = {
  ok: boolean;
  error?: string;
  provider?: string;
  model?: string;
  request_id?: string;
  status_url?: string;
  response_url?: string;
  cancel_url?: string;
  factory_version?: string;
  clip?: number;
  state?: string;
  compiled_prompt?: string;
  script?: string;
  purpose?: string;
  simulated?: boolean;
  approval_required?: boolean;
  approval_required_before_publish?: boolean;
};

export type AgentCommandResult = {
  ok: boolean;
  intent: "create_ugc" | "create_campaign" | "schedule_content" | "status";
  entity?: string | null;
  requires_approval: boolean;
  next: string;
  simulated?: boolean;
};

export type SocialAccount = {
  id: string;
  platform: string;
  display_name?: string | null;
  username?: string | null;
  is_active?: boolean;
  status?: string | null;
};

export function localPrompt(brief: UGCBrief): string {
  return [
    `SCENE: ${brief.idea}${brief.product ? ` Product focus: ${brief.product}.` : ""}`,
    `CAMERA: ${brief.camera || "stable handheld medium shot with one smooth push-in"}. Composition ${brief.aspect_ratio || "9:16"} for ${brief.platform || "instagram"}.`,
    `SUBJECT: ${brief.subject || "a natural creator demonstrating the product"}.`,
    `ENVIRONMENT: ${brief.environment || "a believable everyday setting"}.`,
    `LIGHTING & STYLE: ${brief.lighting || "soft natural light"}; ${(brief.style || "realistic").split(",")[0]}.`,
    `MOTION: ${brief.motion || "small continuous movements with natural pacing"}. Keep the action continuous and physically plausible.`,
    ...(brief.dialogue ? [`DIALOGUE: "${brief.dialogue}" Spoken naturally, not like a staged sales read.`] : []),
    "QUALITY: Preserve product identity, readable packaging, natural hands, consistent subject identity, and believable physics.",
  ].join("\n");
}

function wordCount(value: string) {
  return value.trim().split(/\s+/).filter(Boolean).length;
}

function localFactoryPlan(brief: UGCFactoryBrief): UGCFactoryPlan {
  const pain = brief.pain.trim();
  const mechanism = brief.mechanism.trim();
  const product = brief.product.trim();
  const clip1 = `I kept dealing with ${pain}. I thought I could ignore it, but it was getting old. Same frustration every single time.`;
  const clip2 = `I tried ${product} because ${mechanism}. Annoying that I needed it, but the result is finally repeatable and I can stop thinking about it.`;
  const promptFor = (script: string, continuation: boolean) => [
    `SCENE: ${continuation ? "Continue directly from the prior clean frame and reveal the mechanism." : "Open on the customer problem and tension."} Product focus: ${product}.`,
    "CAMERA: stable handheld talking-head framing. Composition 9:16.",
    `SUBJECT: ${continuation ? "the same creator from the prior frame" : "a natural creator speaking like they are sharing something they use"}.`,
    "ENVIRONMENT: believable everyday setting with ordinary details.",
    "LIGHTING & STYLE: soft natural light; realistic.",
    "MOTION: small natural gestures; finish on a stable frame.",
    `DIALOGUE: "${script}" Spoken naturally, not like a staged sales read.`,
  ].join("\n");
  const clips: UGCFactoryClip[] = [
    { clip: 1, duration_seconds: 10, purpose: "problem_and_tension", script: clip1, script_word_count: wordCount(clip1), prompt: promptFor(clip1, false), seed_from_previous: false },
    { clip: 2, duration_seconds: 10, purpose: "mechanism_and_reluctant_resolution", script: clip2, script_word_count: wordCount(clip2), prompt: promptFor(clip2, true), seed_from_previous: true },
  ];
  return {
    ok: true,
    factory_version: "ugc-ad-factory-v1",
    brief,
    gate: { passed: true, checks: [
      { name: "two_clip_contract", passed: true, detail: "clips=2" },
      { name: "spoken_word_budget", passed: true, detail: `word_counts=${clips.map((clip) => clip.script_word_count).join(",")}` },
      { name: "not_an_ad_mechanical_tells", passed: true, detail: "clear" },
    ] },
    clips,
    continuity: { steps: ["generate_clip_1", "trim_clip_1_tail", "extract_final_clean_seed_frame", "generate_clip_2_from_seed", "seam_check", "trim_clip_2_tail", "stitch"], seam_threshold_mean_abs_diff: 5 / 255, claim: "planning_contract_only" },
    icm: { template: "icm/_templates/ugc_ad_factory", stages: ["01_research", "02_script_gate", "03_cast", "04_generate", "05_seam_qa", "06_deliver"] },
    commercial: { billable_unit: "finished_ugc_ad", price_cents: 9900, estimated_generation_cost_cents: 240, expected_paid_clip_calls: 3, gross_margin_cents: 9660, gross_margin_pct: 97.6, charges_customer: false, estimate_only: true },
    approval_required_before_publish: true,
  };
}

function localAgentCommand(command: string): AgentCommandResult {
  const text = command.toLowerCase();
  if (/schedule|publish|post now|send live/.test(text)) return { ok: true, intent: "schedule_content", entity: null, requires_approval: true, next: "/api/studio/social/schedule", simulated: true };
  if (/status|ready|connected|connection/.test(text)) return { ok: true, intent: "status", entity: null, requires_approval: false, next: "/api/studio/status", simulated: true };
  if (/ugc|video ad|unboxing|creator ad|testimonial/.test(text)) return { ok: true, intent: "create_ugc", entity: null, requires_approval: false, next: "/api/studio/ugc/factory/plan", simulated: true };
  return { ok: true, intent: "create_campaign", entity: null, requires_approval: false, next: "/api/studio/campaigns/plan", simulated: true };
}

export async function runAgentCommand(command: string): Promise<AgentCommandResult> {
  if (seeded()) return localAgentCommand(command);
  return call<AgentCommandResult>("/api/studio/agent/command", { method: "POST", body: JSON.stringify({ command }) });
}

export async function createUGCPrompt(brief: UGCBrief) {
  if (seeded()) return { ok: true, prompt: localPrompt(brief), brief };
  return call<{ ok: boolean; prompt: string; brief: UGCBrief }>("/api/studio/ugc/prompt", { method: "POST", body: JSON.stringify(brief) });
}

export async function queueUGCRender(brief: UGCBrief) {
  if (seeded()) return { ok: true, provider: "demo", simulated: true, request_id: `demo-${Date.now()}`, status_url: "demo://rendering", response_url: "demo://result" };
  return call<Record<string, unknown>>("/api/studio/ugc/render", { method: "POST", body: JSON.stringify(brief) });
}

export async function createUGCFactoryPlan(brief: UGCFactoryBrief): Promise<UGCFactoryPlan> {
  if (seeded()) return localFactoryPlan(brief);
  return call<UGCFactoryPlan>("/api/studio/ugc/factory/plan", { method: "POST", body: JSON.stringify(brief) });
}

export async function renderUGCFactoryClip(payload: UGCFactoryBrief & { clip_number: number; approved: boolean; image_url?: string }): Promise<FactoryRenderResult> {
  if (!payload.approved) return { ok: false, error: "human_approval_required", approval_required: true, state: "planned" };
  if (seeded()) return { ok: true, provider: "demo", simulated: true, request_id: `demo-${Date.now()}`, status_url: "demo://rendering", response_url: "demo://result", factory_version: "ugc-ad-factory-v1", clip: payload.clip_number, state: "render_queued", approval_required_before_publish: true };
  return call<FactoryRenderResult>("/api/studio/ugc/factory/render", { method: "POST", body: JSON.stringify(payload) });
}

export async function getStudioStatus() {
  if (seeded()) return { ok: true, simulated: true, media: { provider: "fal", configured: false }, publishing: { provider: null, configured: false, enabled: false, required_for_core: false }, approval_gate: true };
  return call<Record<string, unknown>>("/api/studio/status");
}

export async function listSocialAccounts(): Promise<{ ok: boolean; provider: string | null; accounts: SocialAccount[]; simulated?: boolean }> {
  if (seeded()) return { ok: true, provider: "demo", simulated: true, accounts: [
    { id: "demo-instagram", platform: "instagram", display_name: "Demo Instagram", username: "@demo", is_active: true, status: "connected" },
    { id: "demo-tiktok", platform: "tiktok", display_name: "Demo TikTok", username: "@demo", is_active: true, status: "connected" },
  ] };
  const response = await call<{ ok: boolean; provider?: string; accounts?: SocialAccount[] | { data?: SocialAccount[] } }>("/api/studio/social/accounts");
  const raw = response.accounts;
  const accounts = Array.isArray(raw) ? raw : Array.isArray(raw?.data) ? raw.data : [];
  return { ok: response.ok, provider: response.provider || null, accounts };
}

export async function scheduleDrop(payload: Record<string, unknown>) {
  if (!payload.approved) throw new Error("Human approval is required before scheduling.");
  if (seeded()) return { ok: true, provider: "demo", simulated: true, receipt: { external_id: `demo-post-${Date.now()}`, scheduled_at: payload.scheduled_at, recorded_at: new Date().toISOString() } };
  return call<Record<string, unknown>>("/api/studio/social/schedule", { method: "POST", body: JSON.stringify(payload) });
}
