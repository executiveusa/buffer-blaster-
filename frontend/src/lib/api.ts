/**
 * Frontend data client.
 *
 * Public/demo surfaces may use seeded read-only data, but connection tests never
 * report a provider as verified unless the live backend handshake says so.
 */
import {
  DEMO_CLIENTS,
  DEMO_CONTENT,
  DEMO_DASHBOARD,
  type Client,
  type ContentUnit,
} from "./demo-data";

const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE !== "false";
const PUBLIC_CONSOLE = process.env.NEXT_PUBLIC_PUBLIC_CONSOLE !== "false";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "operator_session_token";

export function isDemoMode(): boolean { return DEMO_MODE; }
export function isPublicConsole(): boolean { return PUBLIC_CONSOLE; }

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

  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || body.error || response.statusText);
  }
  return response.json() as Promise<T>;
}

export async function verifyPassword(password: string): Promise<{ ok: boolean }> {
  if (DEMO_MODE || PUBLIC_CONSOLE) return { ok: true };
  const response = await apiFetch<{ session_token: string }>("/api/auth/verify", {
    method: "POST",
    body: JSON.stringify({ password }),
  });
  setToken(response.session_token);
  return { ok: true };
}

export interface DashboardData {
  greeting: string;
  active_clients: number;
  posts_this_week: number;
  pending_approvals: number;
  pipeline_running: boolean;
  clients?: Client[];
}

function seededConsoleEnabled(): boolean { return DEMO_MODE || PUBLIC_CONSOLE; }

export async function getDashboard(): Promise<DashboardData> {
  if (seededConsoleEnabled()) return { ...DEMO_DASHBOARD, clients: DEMO_CLIENTS };
  return apiFetch<DashboardData>("/api/admin/dashboard");
}

export async function getClients(): Promise<Client[]> {
  if (seededConsoleEnabled()) return DEMO_CLIENTS;
  const response = await apiFetch<{ clients: Client[] }>("/api/admin/clients");
  return response.clients;
}

export async function getContent(clientSlug: string): Promise<ContentUnit[]> {
  if (seededConsoleEnabled()) return DEMO_CONTENT.filter((unit) => unit.client_slug === clientSlug);
  const response = await apiFetch<{ units: ContentUnit[] }>(`/api/admin/content/${clientSlug}`);
  return response.units;
}

export interface SettingKey {
  label: string;
  env: string;
  masked: string;
  configured: boolean;
}

export interface IntegrationStatus {
  service: string;
  kind: string;
  env_var: string;
  configured: boolean;
  verified: boolean;
  state: "not_configured" | "configured_unverified" | "verified" | "handshake_failed" | "unknown_service" | string;
  message?: string;
  status?: number;
  missing?: string[];
  simulated?: boolean;
}

export interface SettingsData {
  active_llm_provider: string;
  operator_max_children: number;
  demo_mode: boolean;
  keys: SettingKey[];
  integrations: IntegrationStatus[];
  secret_updates?: string;
  runtime_settings_store?: string;
}

const demoIntegrations: IntegrationStatus[] = [
  ["anthropic", "AI provider", "ANTHROPIC_API_KEY"],
  ["openai", "AI provider", "OPENAI_API_KEY"],
  ["google", "AI provider", "GOOGLE_AI_API_KEY"],
  ["fal", "Media generation", "FAL_KEY"],
  ["supabase", "Database", "SUPABASE_SERVICE_KEY"],
  ["telegram", "Voice control (Telegram)", "TELEGRAM_BOT_TOKEN"],
].map(([service, kind, env_var]) => ({
  service,
  kind,
  env_var,
  configured: false,
  verified: false,
  state: "not_configured",
  message: "Demo/public mode does not perform provider verification.",
  simulated: true,
}));

export async function getSettings(): Promise<SettingsData> {
  if (seededConsoleEnabled()) {
    return {
      active_llm_provider: "anthropic",
      operator_max_children: 10,
      demo_mode: true,
      keys: [
        { label: "Anthropic API Key", env: "ANTHROPIC_API_KEY", masked: "", configured: false },
        { label: "OpenAI API Key", env: "OPENAI_API_KEY", masked: "", configured: false },
        { label: "Google AI Key", env: "GOOGLE_AI_API_KEY", masked: "", configured: false },
        { label: "Fal API Key", env: "FAL_KEY", masked: "", configured: false },
        { label: "Supabase Service Key", env: "SUPABASE_SERVICE_KEY", masked: "", configured: false },
        { label: "Stripe Secret Key", env: "STRIPE_SECRET_KEY", masked: "", configured: false },
        { label: "7-Day Trial Stripe Price", env: "STRIPE_TRIAL_7_PRICE_ID", masked: "", configured: false },
        { label: "30-Day Trial Stripe Price", env: "STRIPE_TRIAL_30_PRICE_ID", masked: "", configured: false },
        { label: "Starter Stripe Price", env: "STRIPE_STARTER_PRICE_ID", masked: "", configured: false },
        { label: "Pro Stripe Price", env: "STRIPE_PRO_PRICE_ID", masked: "", configured: false },
        { label: "Telegram Bot Token", env: "TELEGRAM_BOT_TOKEN", masked: "", configured: false },
      ],
      integrations: demoIntegrations,
      secret_updates: "environment_only",
      runtime_settings_store: "unavailable",
    };
  }
  return apiFetch<SettingsData>("/api/admin/settings");
}

export async function testIntegration(service: string): Promise<IntegrationStatus> {
  if (seededConsoleEnabled()) {
    return {
      service,
      kind: "integration",
      env_var: "",
      configured: false,
      verified: false,
      state: "not_configured",
      message: "Provider verification is disabled in demo/public mode.",
      simulated: true,
    };
  }
  return apiFetch<IntegrationStatus>(`/api/admin/settings/test/${encodeURIComponent(service)}`, { method: "POST" });
}

export async function updateRuntimeSetting(env: "ACTIVE_LLM_PROVIDER" | "AGENT_MAX_CHILDREN", value: string) {
  if (seededConsoleEnabled()) throw new Error("Runtime settings are read-only in demo/public mode.");
  return apiFetch<{ ok: boolean; env: string; value: string }>("/api/admin/settings", {
    method: "PUT",
    body: JSON.stringify({ env, value }),
  });
}
