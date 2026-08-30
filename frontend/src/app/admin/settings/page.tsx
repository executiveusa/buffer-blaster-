"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCircle, Bot, CheckCircle2, Database, KeyRound, Loader2, Mic, Plug, Server, Video, XCircle } from "lucide-react";
import { getSettings, testIntegration, updateRuntimeSetting, type IntegrationStatus, type SettingsData } from "@/lib/api";
import { cn } from "@/lib/utils";

type TabId = "providers" | "integrations" | "agent" | "guide";
const TABS = [
  { id: "providers" as const, label: "AI + Media", icon: Bot },
  { id: "integrations" as const, label: "Connections", icon: Plug },
  { id: "agent" as const, label: "Operator", icon: Server },
  { id: "guide" as const, label: "Environment", icon: KeyRound },
];

const SERVICE_ICONS: Record<string, typeof Plug> = {
  anthropic: Bot, openai: Bot, google: Bot, ollama: Bot,
  fal: Video, supabase: Database, telegram: Mic,
};

export default function SettingsPage() {
  const [data, setData] = useState<SettingsData | null>(null);
  const [tab, setTab] = useState<TabId>("providers");
  const [testing, setTesting] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, IntegrationStatus>>({});
  const [provider, setProvider] = useState("");
  const [maxChildren, setMaxChildren] = useState("");
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    getSettings().then((value) => {
      setData(value);
      setProvider(value.active_llm_provider);
      setMaxChildren(String(value.operator_max_children));
    }).catch((error) => setNotice(error instanceof Error ? error.message : "Settings could not be loaded."));
  }, []);

  const providerServices = useMemo(() => data?.integrations.filter((item) => ["anthropic", "openai", "google", "ollama", "fal"].includes(item.service)) || [], [data]);
  const otherServices = useMemo(() => data?.integrations.filter((item) => !["anthropic", "openai", "google", "ollama", "fal"].includes(item.service)) || [], [data]);

  async function runTest(service: string) {
    setTesting(service);
    setNotice("");
    try {
      const result = await testIntegration(service);
      setResults((current) => ({ ...current, [service]: result }));
    } catch (error) {
      setResults((current) => ({ ...current, [service]: { service, kind: "integration", env_var: "", configured: true, verified: false, state: "handshake_failed", message: error instanceof Error ? error.message : "Handshake failed." } }));
    } finally {
      setTesting(null);
    }
  }

  async function saveRuntime() {
    setSaving(true);
    setNotice("");
    try {
      await updateRuntimeSetting("ACTIVE_LLM_PROVIDER", provider);
      await updateRuntimeSetting("AGENT_MAX_CHILDREN", maxChildren);
      setNotice("Runtime settings saved to the shared Redis store.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Runtime settings could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  if (!data) return <div className="p-8 text-sm text-text-dim">Loading…</div>;

  return <div className="mx-auto max-w-5xl px-6 py-10">
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div><h1 className="text-2xl font-semibold tracking-tight">Settings</h1><p className="mt-1 max-w-2xl text-sm text-text-muted">Configured means a secret exists. Verified means a live, read-only provider handshake succeeded. The UI never treats those as the same state.</p></div>
      <span className="rounded-full border border-border bg-bg-card px-3 py-1.5 text-xs text-text-muted">Secrets: environment only</span>
    </div>

    <div className="mt-8 flex flex-wrap gap-1 border-b border-border">{TABS.map((item) => { const Icon = item.icon; return <button key={item.id} onClick={() => setTab(item.id)} className={cn("flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm transition", tab === item.id ? "border-accent text-text" : "border-transparent text-text-muted hover:text-text")}><Icon className="h-3.5 w-3.5"/>{item.label}</button>; })}</div>

    {notice && <div className="mt-5 rounded-lg border border-border bg-bg-card px-4 py-3 text-xs text-text-muted">{notice}</div>}

    <div className="mt-8">
      {tab === "providers" && <ConnectionList title="AI + media providers" items={providerServices} testing={testing} results={results} onTest={runTest}/>} 
      {tab === "integrations" && <ConnectionList title="Operational connections" items={otherServices} testing={testing} results={results} onTest={runTest}/>} 
      {tab === "agent" && <div className="grid gap-4 rounded-xl border border-border bg-bg-card p-5 md:grid-cols-2">
        <label className="text-xs text-text-muted">Active LLM provider<input value={provider} onChange={(event)=>setProvider(event.target.value)} className="mt-2 w-full rounded-lg border border-border bg-bg px-3 py-2.5 text-sm text-text"/></label>
        <label className="text-xs text-text-muted">Max concurrent children<input type="number" min="1" max="50" value={maxChildren} onChange={(event)=>setMaxChildren(event.target.value)} className="mt-2 w-full rounded-lg border border-border bg-bg px-3 py-2.5 text-sm text-text"/></label>
        <div className="md:col-span-2 flex items-center justify-between gap-4 border-t border-border pt-4"><div className="text-xs text-text-dim">Runtime store: <strong className="text-text-muted">{data.runtime_settings_store || "unknown"}</strong></div><button onClick={saveRuntime} disabled={saving || data.demo_mode} className="rounded-lg bg-accent px-4 py-2 text-xs font-medium text-white disabled:opacity-40">{saving ? "Saving…" : data.demo_mode ? "Read-only in demo" : "Save runtime settings"}</button></div>
      </div>}
      {tab === "guide" && <div className="overflow-hidden rounded-xl border border-border bg-bg-card"><div className="border-b border-border p-5"><h2 className="text-sm font-medium">Environment-managed secrets</h2><p className="mt-1 text-xs text-text-muted">Secret values cannot be written from this screen. Configure them in the deployment secret store, then use Test to verify the connection.</p></div><div className="divide-y divide-border">{data.keys.map((key)=><div key={key.env} className="flex items-center justify-between gap-4 px-5 py-3"><div><p className="text-sm">{key.label}</p><p className="mt-0.5 font-mono text-[11px] text-text-dim">{key.env}</p></div><span className={cn("rounded-full px-2.5 py-1 text-[10px]", key.configured ? "bg-success/10 text-success" : "bg-bg-elevated text-text-dim")}>{key.configured ? key.masked || "configured" : "not set"}</span></div>)}</div></div>}
    </div>
  </div>;
}

function ConnectionList({ title, items, testing, results, onTest }: { title: string; items: IntegrationStatus[]; testing: string | null; results: Record<string, IntegrationStatus>; onTest: (service: string) => void }) {
  return <div><h2 className="text-sm font-medium">{title}</h2><div className="mt-4 grid gap-3">{items.map((item) => {
    const live = results[item.service] || item;
    const Icon = SERVICE_ICONS[item.service] || Plug;
    const StateIcon = live.verified ? CheckCircle2 : live.state === "handshake_failed" ? XCircle : AlertCircle;
    return <div key={item.service} className="rounded-xl border border-border bg-bg-card p-4"><div className="flex items-start gap-4"><div className="grid h-10 w-10 place-items-center rounded-lg bg-bg-elevated"><Icon className="h-4 w-4 text-text-muted"/></div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><p className="text-sm font-medium capitalize">{item.service}</p><span className={cn("rounded-full px-2 py-0.5 text-[10px]", live.verified ? "bg-success/10 text-success" : live.configured ? "bg-warning/10 text-warning" : "bg-bg-elevated text-text-dim")}>{live.verified ? "verified" : live.configured ? "configured / unverified" : "not configured"}</span></div><p className="mt-1 text-xs text-text-muted">{live.message || item.kind}</p></div><StateIcon className={cn("mt-1 h-4 w-4", live.verified ? "text-success" : live.state === "handshake_failed" ? "text-danger" : "text-text-dim")}/><button onClick={()=>onTest(item.service)} disabled={testing === item.service} className="rounded-md border border-border px-3 py-1.5 text-xs text-text-muted hover:text-text disabled:opacity-50">{testing === item.service ? <Loader2 className="h-3 w-3 animate-spin"/> : "Test"}</button></div></div>;
  })}</div></div>;
}
