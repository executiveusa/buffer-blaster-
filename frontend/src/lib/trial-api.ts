import type { UGCFactoryBrief, UGCFactoryPlan } from "./studio-api";

export type TrialStatus = {
  ok: boolean;
  active: boolean;
  trial?: {
    offer_id: string;
    state: string;
    remaining_ad_credits: number;
    expires_at?: string | null;
  };
};

async function json<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || body.error || response.statusText);
  return body as T;
}

export async function startCheckout(offer: string) {
  const response = await fetch("/api/checkout/offer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ offer }),
  });
  return json<{ url: string; offer: string }>(response);
}

export async function activateTrial(sessionId: string) {
  const response = await fetch("/api/trial/activate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  return json<TrialStatus>(response);
}

export async function getTrialStatus(): Promise<TrialStatus> {
  const response = await fetch("/api/trial/status", { cache: "no-store" });
  if (response.status === 401) return { ok: false, active: false };
  return json<TrialStatus>(response);
}

export async function createTrialFactoryPlan(brief: UGCFactoryBrief): Promise<UGCFactoryPlan> {
  const response = await fetch("/api/trial/plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(brief),
  });
  return json<UGCFactoryPlan>(response);
}

export async function executeTrialFactoryAd(brief: UGCFactoryBrief & { approved: boolean }) {
  const response = await fetch("/api/trial/execute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(brief),
  });
  return json<Record<string, unknown>>(response);
}
