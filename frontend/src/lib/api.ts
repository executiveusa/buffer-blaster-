/**
 * API client — one code path, two modes.
 *
 * - DEMO mode (default): returns seeded data from ./demo-data. No backend.
 * - PRODUCTION: calls FastAPI at NEXT_PUBLIC_API_URL with the session token.
 *
 * The toggle is NEXT_PUBLIC_DEMO_MODE. Flip to "false" + set the API URL on
 * the VPS and the same components fetch live data.
 */
import {
  DEMO_CLIENTS,
  DEMO_CONTENT,
  DEMO_DASHBOARD,
  type Client,
  type ContentUnit,
} from "./demo-data";

const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE !== "false";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TOKEN_KEY = "stavarai_token";

export function isDemoMode(): boolean {
  return DEMO_MODE;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  const r = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail || r.statusText);
  }
  return r.json() as Promise<T>;
}

// ── Auth ──────────────────────────────────────────────────────

export async function verifyPassword(password: string): Promise<{ ok: boolean }> {
  if (DEMO_MODE) {
    // Demo: accept the canonical password locally.
    if (password === "BLASTER2026") {
      setToken("demo-" + Math.random().toString(36).slice(2));
      return { ok: true };
    }
    return { ok: false };
  }
  const r = await apiFetch<{ session_token: string }>("/api/auth/verify", {
    method: "POST",
    body: JSON.stringify({ password }),
  });
  setToken(r.session_token);
  return { ok: true };
}

// ── Dashboard ─────────────────────────────────────────────────

export interface DashboardData {
  greeting: string;
  active_clients: number;
  posts_this_week: number;
  pending_approvals: number;
  pipeline_running: boolean;
  clients?: Client[];
}

export async function getDashboard(): Promise<DashboardData> {
  if (DEMO_MODE) return { ...DEMO_DASHBOARD, clients: DEMO_CLIENTS };
  return apiFetch<DashboardData>("/api/admin/dashboard");
}

// ── Clients ───────────────────────────────────────────────────

export async function getClients(): Promise<Client[]> {
  if (DEMO_MODE) return DEMO_CLIENTS;
  const r = await apiFetch<{ clients: Client[] }>("/api/admin/clients");
  return r.clients;
}

// ── Content ───────────────────────────────────────────────────

export async function getContent(clientSlug: string): Promise<ContentUnit[]> {
  if (DEMO_MODE) {
    return DEMO_CONTENT.filter((u) => u.client_slug === clientSlug);
  }
  const r = await apiFetch<{ units: ContentUnit[] }>(
    `/api/admin/content/${clientSlug}`,
  );
  return r.units;
}

// ── Settings ──────────────────────────────────────────────────

export interface SettingKey {
  label: string;
  env: string;
  masked: string;
  configured: boolean;
}

export interface SettingsData {
  active_llm_provider: string;
  hermes_max_children: number;
  demo_mode: boolean;
  keys: SettingKey[];
}

export async function getSettings(): Promise<SettingsData> {
  if (DEMO_MODE) {
    return {
      active_llm_provider: "anthropic",
      hermes_max_children: 10,
      demo_mode: true,
      keys: [
        { label: "Anthropic API Key", env: "ANTHROPIC_API_KEY", masked: "", configured: false },
        { label: "OpenAI API Key", env: "OPENAI_API_KEY", masked: "", configured: false },
        { label: "Higgsfield API Key", env: "HIGGSFIELD_API_KEY", masked: "", configured: false },
        { label: "Buffer Access Token", env: "BUFFER_ACCESS_TOKEN", masked: "", configured: false },
        { label: "Airtable API Key", env: "AIRTABLE_API_KEY", masked: "", configured: false },
        { label: "Telegram Bot Token", env: "TELEGRAM_BOT_TOKEN", masked: "", configured: false },
      ],
    };
  }
  return apiFetch<SettingsData>("/api/admin/settings");
}
