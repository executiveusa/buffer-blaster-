"use client";

import { getToken, isDemoMode, isPublicConsole } from "./api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function liveCall<T>(path: string): Promise<T> {
  if (isDemoMode() || isPublicConsole()) throw new Error("canonical_live_state_disabled");
  const token = getToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_URL}${path}`, { headers, cache: "no-store" });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || body.error || response.statusText);
  return body as T;
}

export type LedgerSummary = {
  ok: boolean;
  ledger: { backend: string; persistent: boolean; canonical: boolean; degraded_from?: string };
  campaigns: number;
  jobs_total: number;
  jobs_active: number;
  jobs_completed: number;
  jobs_failed: number;
  states: Record<string, number>;
};

export type CreativeJob = {
  id: string;
  kind: string;
  state: string;
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
  provider_receipt?: Record<string, unknown>;
  estimated_provider_cost_cents?: number;
  actual_provider_cost_cents?: number | null;
  offer_id?: string | null;
  created_at?: string;
  updated_at?: string;
};

export async function getLedgerSummary(): Promise<LedgerSummary> {
  if (isDemoMode() || isPublicConsole()) return { ok: false, ledger: { backend: "demo", persistent: false, canonical: false }, campaigns: 0, jobs_total: 0, jobs_active: 0, jobs_completed: 0, jobs_failed: 0, states: {} };
  return liveCall<LedgerSummary>("/api/studio/ledger/summary");
}

export async function listCreativeJobs(limit = 50): Promise<CreativeJob[]> {
  if (isDemoMode() || isPublicConsole()) return [];
  const response = await liveCall<{ ok: boolean; jobs: CreativeJob[] }>(`/api/studio/jobs?limit=${Math.max(1, Math.min(limit, 200))}`);
  return response.jobs || [];
}

export async function getStudioPricing() {
  return liveCall<Record<string, unknown>>("/api/studio/pricing");
}
