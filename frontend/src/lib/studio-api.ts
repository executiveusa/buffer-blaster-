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

export async function createUGCPrompt(brief: UGCBrief) {
  if (seeded()) return { ok: true, prompt: localPrompt(brief), brief };
  return call<{ ok: boolean; prompt: string; brief: UGCBrief }>("/api/studio/ugc/prompt", { method: "POST", body: JSON.stringify(brief) });
}

export async function queueUGCRender(brief: UGCBrief) {
  if (seeded()) return { ok: true, provider: "demo", request_id: `demo-${Date.now()}`, status_url: "demo://rendering", response_url: "demo://result" };
  return call<Record<string, unknown>>("/api/studio/ugc/render", { method: "POST", body: JSON.stringify(brief) });
}

export async function getStudioStatus() {
  if (seeded()) return { ok: true, media: { provider: "fal", configured: false }, publisher: { provider: "trypost", configured: false }, approval_gate: true };
  return call<Record<string, unknown>>("/api/studio/status");
}

export async function scheduleDrop(payload: Record<string, unknown>) {
  if (!payload.approved) throw new Error("Human approval is required before scheduling.");
  if (seeded()) return { ok: true, provider: "demo", receipt: { external_id: `demo-post-${Date.now()}`, scheduled_at: payload.scheduled_at, recorded_at: new Date().toISOString() } };
  return call<Record<string, unknown>>("/api/studio/social/schedule", { method: "POST", body: JSON.stringify(payload) });
}
