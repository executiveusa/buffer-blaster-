/**
 * API client — one code path, two modes.
 *
 * - DEMO mode (default): returns seeded data from ./demo-data. No backend.
 * - PRODUCTION: calls FastAPI at NEXT_PUBLIC_API_URL.
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

export function isDemoMode(): boolean {
  return DEMO_MODE;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string>),
  };
  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || response.statusText);
  }
  return response.json() as Promise<T>;
}

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

export async function getClients(): Promise<Client[]> {
  if (DEMO_MODE) return DEMO_CLIENTS;
  const response = await apiFetch<{ clients: Client[] }>("/api/admin/clients");
  return response.clients;
}

export async function getContent(clientSlug: string): Promise<ContentUnit[]> {
  if (DEMO_MODE) return DEMO_CONTENT.filter((unit) => unit.client_slug === clientSlug);
  const response = await apiFetch<{ units: ContentUnit[] }>(`/api/admin/content/${clientSlug}`);
  return response.units;
}

export interface SettingKey {
  label: string;
  env: string;
  masked: string;
  configured: boolean;
}

export interface SettingsData {
  active_llm_provider: string;
  operator_max_children: number;
  demo_mode: boolean;
  keys: SettingKey[];
}

export async function getSettings(): Promise<SettingsData> {
  if (DEMO_MODE) {
    return {
      active_llm_provider: "anthropic",
      operator_max_children: 10,
      demo_mode: true,
      keys: [
        { label: "Anthropic API Key", env: "ANTHROPIC_API_KEY", masked: "", configured: false },
        { label: "OpenAI API Key", env: "OPENAI_API_KEY", masked: "", configured: false },
        { label: "Higgsfield API Key", env: "HIGGSFIELD_API_KEY", masked: "", configured: false },
        { label: "Buffer Access Token", env: "BUFFER_ACCESS_TOKEN", masked: "", configured: false },
        { label: "Airtable API Key", env: "AIRTABLE_API_KEY", masked: "", configured: false },
        { label: "Telegram Bot Token", env: "TELEGRAM_BOT_TOKEN", masked: "", configured: false },
        { label: "Stripe Secret Key", env: "STRIPE_SECRET_KEY", masked: "", configured: false },
        { label: "Stripe Founding Price", env: "STRIPE_FOUNDING_PRICE_ID", masked: "", configured: false },
      ],
    };
  }
  return apiFetch<SettingsData>("/api/admin/settings");
}
