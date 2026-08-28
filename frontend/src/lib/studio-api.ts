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

function localAgentCommand(command: string): AgentCommandResult {
  const text = command.toLowerCase();
  if (/schedule|publish|post now|send live/.test(text)) {
    return { ok: true, intent: "schedule_content", entity: null, requires_approval: true, next: "/api/studio/social/schedule", simulated: true };
  }
  if (/status|ready|connected|connection/.test(text)) {
    return { ok: true, intent: "status", entity: null, requires_approval: false, next: "/api/studio/status", simulated: true };
  }
  if (/ugc|video ad|unboxing|creator ad|testimonial/.test(text)) {
    return { ok: true, intent: "create_ugc", entity: null, requires_approval: false, next: "/api/studio/ugc/prompt", simulated: true };
  }
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

export async function getStudioStatus() {
  if (seeded()) return { ok: true, simulated: true, media: { provider: "fal", configured: false }, publisher: { provider: "trypost", configured: false }, approval_gate: true };
  return call<Record<string, unknown>>("/api/studio/status");
}

export async function listSocialAccounts(): Promise<{ ok: boolean; provider: string; accounts: SocialAccount[]; simulated?: boolean }> {
  if (seeded()) {
    return {
      ok: true,
      provider: "demo",
      simulated: true,
      accounts: [
        { id: "demo-instagram", platform: "instagram", display_name: "Demo Instagram", username: "@demo", is_active: true, status: "connected" },
        { id: "demo-tiktok", platform: "tiktok", display_name: "Demo TikTok", username: "@demo", is_active: true, status: "connected" },
      ],
    };
  }
  const response = await call<{ ok: boolean; provider?: string; accounts?: SocialAccount[] | { data?: SocialAccount[] } }>("/api/studio/social/accounts");
  const raw = response.accounts;
  const accounts = Array.isArray(raw) ? raw : Array.isArray(raw?.data) ? raw.data : [];
  return { ok: response.ok, provider: response.provider || "trypost", accounts };
}

export async function scheduleDrop(payload: Record<string, unknown>) {
  if (!payload.approved) throw new Error("Human approval is required before scheduling.");
  if (seeded()) return { ok: true, provider: "demo", simulated: true, receipt: { external_id: `demo-post-${Date.now()}`, scheduled_at: payload.scheduled_at, recorded_at: new Date().toISOString() } };
  return call<Record<string, unknown>>("/api/studio/social/schedule", { method: "POST", body: JSON.stringify(payload) });
}
