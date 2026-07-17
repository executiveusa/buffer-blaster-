"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Plug,
  Bot,
  Mic,
  BookOpen,
  Server,
} from "lucide-react";
import { getSettings, type SettingsData } from "@/lib/api";
import { cn } from "@/lib/utils";

type TabId =
  | "providers"
  | "integrations"
  | "agent"
  | "mcp"
  | "voice"
  | "guide";

const TABS: { id: TabId; label: string; icon: typeof Plug }[] = [
  { id: "providers", label: "AI Providers", icon: Bot },
  { id: "integrations", label: "Integrations", icon: Plug },
  { id: "agent", label: "Agent Config", icon: Server },
  { id: "mcp", label: "MCP Servers", icon: Plug },
  { id: "voice", label: "Voice Control", icon: Mic },
  { id: "guide", label: "API Guide", icon: BookOpen },
];

const MCP_SERVERS = [
  { name: "higgsfield", url: "https://mcp.higgsfield.ai/mcp", purpose: "Video generation" },
];

const API_GUIDE = [
  { env: "ANTHROPIC_API_KEY", where: "console.anthropic.com → API Keys", required: true },
  { env: "SUPABASE_URL + SUPABASE_SERVICE_KEY", where: "supabase.com → Project Settings → API", required: true },
  { env: "BUFFER_ACCESS_TOKEN", where: "buffer.com → Account → Apps", required: false },
  { env: "HIGGSFIELD_API_KEY", where: "higgsfield.ai → Settings", required: false },
  { env: "AIRTABLE_API_KEY + AIRTABLE_BASE_ID", where: "airtable.com → Account → API", required: false },
  { env: "TELEGRAM_BOT_TOKEN + TELEGRAM_USER_ID", where: "@BotFather → /newbot", required: false },
  { env: "APIFY_API_TOKEN", where: "apify.com → Account → Integrations", required: false },
  { env: "FIRECRAWL_API_KEY", where: "firecrawl.dev → Dashboard", required: false },
];

export default function SettingsPage() {
  const [data, setData] = useState<SettingsData | null>(null);
  const [tab, setTab] = useState<TabId>("providers");
  const [testing, setTesting] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, boolean>>({});

  useEffect(() => {
    getSettings().then(setData).catch(() => {});
  }, []);

  async function runTest(env: string) {
    setTesting(env);
    // In demo mode we just reflect the configured state after a short delay.
    await new Promise((r) => setTimeout(r, 600));
    const key = data?.keys.find((k) => k.env === env);
    setTestResults((prev) => ({ ...prev, [env]: !!key?.configured }));
    setTesting(null);
  }

  if (!data) {
    return <div className="p-8 text-sm text-text-dim">Loading…</div>;
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
      <p className="mt-1 text-sm text-text-muted">
        Keys are encrypted at rest. We only ever show the last four characters.
      </p>

      {/* Tabs */}
      <div className="mt-8 flex flex-wrap gap-1 border-b border-border">
        {TABS.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                "flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm transition",
                tab === t.id
                  ? "border-accent text-text"
                  : "border-transparent text-text-muted hover:text-text",
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {t.label}
            </button>
          );
        })}
      </div>

      <div className="mt-8">
        {tab === "providers" && (
          <KeyList
            title="AI Providers"
            description="One active at a time. Set in .env as ACTIVE_LLM_PROVIDER."
            keys={data.keys.filter((k) =>
              ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_AI_API_KEY"].includes(
                k.env,
              ),
            )}
            active={`Active: ${data.active_llm_provider}`}
            testing={testing}
            testResults={testResults}
            onTest={runTest}
          />
        )}

        {tab === "integrations" && (
          <KeyList
            title="Integrations"
            description="Each activates the moment its env var is set."
            keys={data.keys.filter((k) =>
              [
                "HIGGSFIELD_API_KEY",
                "BUFFER_ACCESS_TOKEN",
                "AIRTABLE_API_KEY",
              ].includes(k.env),
            )}
            testing={testing}
            testResults={testResults}
            onTest={runTest}
          />
        )}

        {tab === "agent" && (
          <div className="space-y-4">
            <SettingRow label="Operator profile" value="content-ops-console" />
            <SettingRow
              label="Max concurrent children"
              value={String(data.operator_max_children)}
            />
            <SettingRow
              label="Operating mode"
              value={data.demo_mode ? "Demo (no backend)" : "Production"}
            />
          </div>
        )}

        {tab === "mcp" && (
          <div className="space-y-3">
            {MCP_SERVERS.map((s) => (
              <div
                key={s.name}
                className="rounded-lg border border-border bg-bg-card p-4"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm">{s.name}</span>
                  <span className="text-xs text-text-dim">{s.purpose}</span>
                </div>
                <p className="mt-2 text-xs text-text-muted">{s.url}</p>
              </div>
            ))}
          </div>
        )}

        {tab === "voice" && (
          <div className="space-y-3">
            <KeyList
              title="Voice Control"
              description="Telegram bot + Meta glasses webhook. Only the approved operator user ID gets a response."
              keys={data.keys.filter((k) => k.env === "TELEGRAM_BOT_TOKEN")}
              testing={testing}
              testResults={testResults}
              onTest={runTest}
            />
          </div>
        )}

        {tab === "guide" && (
          <div className="overflow-hidden rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-bg-elevated text-left text-xs text-text-dim">
                  <th className="px-4 py-3 font-medium">Variable</th>
                  <th className="px-4 py-3 font-medium">Where to get it</th>
                  <th className="px-4 py-3 font-medium">Required?</th>
                </tr>
              </thead>
              <tbody>
                {API_GUIDE.map((row) => (
                  <tr
                    key={row.env}
                    className="border-b border-border last:border-0"
                  >
                    <td className="px-4 py-3 font-mono text-xs">{row.env}</td>
                    <td className="px-4 py-3 text-text-muted">{row.where}</td>
                    <td className="px-4 py-3">
                      {row.required ? (
                        <span className="text-xs text-warning">Required</span>
                      ) : (
                        <span className="text-xs text-text-dim">Optional</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function KeyList({
  title,
  description,
  keys,
  active,
  testing,
  testResults,
  onTest,
}: {
  title: string;
  description: string;
  keys: SettingsData["keys"];
  active?: string;
  testing: string | null;
  testResults: Record<string, boolean>;
  onTest: (env: string) => void;
}) {
  return (
    <div>
      <h2 className="text-sm font-medium">{title}</h2>
      {active && <p className="mt-1 text-xs text-accent-soft">{active}</p>}
      <p className="mt-1 text-xs text-text-muted">{description}</p>
      <div className="mt-4 space-y-2">
        {keys.map((k) => {
          const result = testResults[k.env];
          const isTesting = testing === k.env;
          return (
            <div
              key={k.env}
              className="flex items-center justify-between rounded-lg border border-border bg-bg-card px-4 py-3"
            >
              <div className="min-w-0">
                <div className="text-sm">{k.label}</div>
                <div className="mt-0.5 font-mono text-xs text-text-dim">
                  {k.configured ? k.masked || "configured" : "not set"}
                </div>
              </div>
              <div className="flex items-center gap-3">
                {result === true && (
                  <CheckCircle2 className="h-4 w-4 text-success" />
                )}
                {result === false && <XCircle className="h-4 w-4 text-danger" />}
                <button
                  onClick={() => onTest(k.env)}
                  disabled={isTesting}
                  className="rounded-md border border-border px-3 py-1.5 text-xs text-text-muted transition hover:border-border-strong hover:text-text disabled:opacity-50"
                >
                  {isTesting ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    "Test"
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SettingRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-bg-card px-4 py-3">
      <span className="text-sm text-text-muted">{label}</span>
      <span className="font-mono text-sm">{value}</span>
    </div>
  );
}
