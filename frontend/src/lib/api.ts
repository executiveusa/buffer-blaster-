/**
 * Frontend data client.
 *
 * The public console uses seeded, read-only data by default. Set
 * NEXT_PUBLIC_PUBLIC_CONSOLE=false to require the authenticated live backend.
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

export function isDemoMode(): boolean {
  return DEMO_MODE;
}

export function isPublicConsole(): boolean {
  return PUBLIC_CONSOLE;
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

  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || response.statusText);
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

function useSeededConsole(): boolean {
  return DEMO_MODE || PUBLIC_CONSOLE;
}

export async function getDashboard(): Promise<DashboardData> {
  if (useSeededConsole()) return { ...DEMO_DASHBOARD, clients: DEMO_CLIENTS };
  return apiFetch<DashboardData>("/api/admin/dashboard");
}

export async function getClients(): Promise<Client[]> {
  if (useSeededConsole()) return DEMO_CLIENTS;
  const response = await apiFetch<{ clients: Client[] }>("/api/admin/clients");
  return response.clients;
}

export async function getContent(clientSlug: string): Promise<ContentUnit[]> {
  if (useSeededConsole()) return DEMO_CONTENT.filter((unit) => unit.client_slug === clientSlug);
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
  if (useSeededConsole()) {
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
