"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import {
  Users,
  FileText,
  Clock,
  Activity,
  X,
  CheckCircle2,
} from "lucide-react";
import { getDashboard, type DashboardData } from "@/lib/api";
import { DEMO_CLIENTS, NICHE_LABELS } from "@/lib/demo-data";

const ONBOARDING_KEY = "operator_onboarding_done";

const ONBOARDING_STEPS = [
  "Connect your AI provider in Settings",
  "Add your first client",
  "Run the grill-me intake interview",
  "Trigger a content pipeline run",
  "Review the scored content queue",
  "Approve your first batch",
  "Watch the flywheel learn",
];

const subscribeToOnboarding = (callback: () => void) => {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
};

const onboardingDoneSnapshot = () =>
  localStorage.getItem(ONBOARDING_KEY) === "1";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dismissedThisSession, setDismissedThisSession] = useState(false);
  const onboardingDone = useSyncExternalStore(
    subscribeToOnboarding,
    onboardingDoneSnapshot,
    () => true,
  );
  const showOnboarding = !onboardingDone && !dismissedThisSession;

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  function dismissOnboarding() {
    localStorage.setItem(ONBOARDING_KEY, "1");
    setDismissedThisSession(true);
  }

  if (error) {
    return (
      <div className="p-8 text-sm text-danger">
        Couldn’t load the dashboard: {error}
      </div>
    );
  }

  if (!data) {
    return <div className="p-8 text-sm text-text-dim">Loading…</div>;
  }

  const stats = [
    { label: "Active clients", value: data.active_clients, icon: Users },
    { label: "Posts this week", value: data.posts_this_week, icon: FileText },
    { label: "Pending approval", value: data.pending_approvals, icon: Clock },
    {
      label: "Pipeline",
      value: data.pipeline_running ? "Running" : "Idle",
      icon: Activity,
    },
  ];

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      {showOnboarding && (
        <div className="mb-8 rounded-xl border border-accent/30 bg-accent/5 p-6">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-sm font-semibold text-accent-soft">
                Getting started
              </h2>
              <p className="mt-1 text-xs text-text-muted">
                Seven steps to your first published batch.
              </p>
            </div>
            <button
              onClick={dismissOnboarding}
              className="text-text-dim transition hover:text-text"
              aria-label="Dismiss onboarding"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <ol className="mt-4 space-y-2">
            {ONBOARDING_STEPS.map((step, i) => (
              <li key={step} className="flex items-center gap-3 text-sm">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-border font-mono text-[10px] text-text-dim">
                  {i + 1}
                </span>
                <span className="text-text-muted">{step}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      <h1 className="text-2xl font-semibold tracking-tight">{data.greeting}</h1>
      <p className="mt-1 text-sm text-text-muted">
        Here’s where your content stands today.
      </p>

      <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {stats.map((s) => {
          const Icon = s.icon;
          return (
            <div
              key={s.label}
              className="rounded-xl border border-border bg-bg-card p-5"
            >
              <Icon className="h-4 w-4 text-text-dim" />
              <div className="mt-3 font-mono text-2xl font-semibold">
                {s.value}
              </div>
              <div className="mt-1 text-xs text-text-dim">{s.label}</div>
            </div>
          );
        })}
      </div>

      <div className="mt-10">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium">Clients</h2>
          <Link
            href="/admin/clients"
            className="text-xs text-accent-soft hover:underline"
          >
            View all
          </Link>
        </div>
        <div className="mt-4 overflow-hidden rounded-xl border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-bg-elevated text-left text-xs text-text-dim">
                <th className="px-4 py-3 font-medium">Client</th>
                <th className="px-4 py-3 font-medium">Niche</th>
                <th className="px-4 py-3 font-medium">Posts scheduled</th>
                <th className="px-4 py-3 font-medium">Avg score</th>
                <th className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {(data.clients ?? DEMO_CLIENTS).map((c) => (
                <tr key={c.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-3 font-medium">{c.name}</td>
                  <td className="px-4 py-3 text-text-muted">
                    {NICHE_LABELS[c.niche]}
                  </td>
                  <td className="px-4 py-3 font-mono text-text-muted">
                    {c.posts_scheduled}
                  </td>
                  <td className="px-4 py-3 font-mono text-text-muted">
                    {c.avg_score.toFixed(1)}
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1 text-xs text-success">
                      <CheckCircle2 className="h-3 w-3" />
                      {c.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
