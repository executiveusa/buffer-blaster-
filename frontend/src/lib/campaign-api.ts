"use client";

import { getToken, isDemoMode, isPublicConsole } from "./api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type CampaignBrief = {
  brand: string;
  objective: string;
  audience: string;
  offer: string;
  duration_days: number;
  platforms: string[];
};

export type CampaignDay = {
  day: number;
  format: string;
  angle: string;
  platforms: string[];
  cta: string;
  state: string;
};

export type CampaignPlan = {
  id: string;
  brand: string;
  objective: string;
  audience: string;
  offer: string;
  days: CampaignDay[];
  approval_required_before_publish: boolean;
};

export type CampaignPlanResult = {
  ok: boolean;
  plan: CampaignPlan;
  ledger?: Record<string, unknown>;
  simulated?: boolean;
};

function localSimulation(brief: CampaignBrief): CampaignPlanResult {
  const formats = ["reel", "post", "carousel", "post", "reel", "post", "carousel"];
  const angles = ["problem and tension", "product proof", "use case", "objection handling", "UGC testimonial", "offer and urgency", "community proof"];
  return {
    ok: true,
    simulated: true,
    plan: {
      id: `simulation-${Date.now()}`,
      brand: brief.brand,
      objective: brief.objective,
      audience: brief.audience,
      offer: brief.offer,
      days: Array.from({ length: brief.duration_days }, (_, index) => ({
        day: index + 1,
        format: formats[index % formats.length],
        angle: angles[index % angles.length],
        platforms: brief.platforms,
        cta: brief.offer || brief.objective,
        state: "simulation",
      })),
      approval_required_before_publish: true,
    },
  };
}

export async function createCampaignPlan(brief: CampaignBrief): Promise<CampaignPlanResult> {
  if (isDemoMode() || isPublicConsole()) return localSimulation(brief);
  const token = getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_URL}/api/studio/campaigns/plan`, {
    method: "POST",
    headers,
    body: JSON.stringify(brief),
    cache: "no-store",
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok || body.ok === false) throw new Error(body.detail || body.error || "Campaign planning failed.");
  return body as CampaignPlanResult;
}
