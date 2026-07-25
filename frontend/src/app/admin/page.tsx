"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Lock } from "lucide-react";
import { isDemoMode, isPublicConsole, verifyPassword } from "@/lib/api";

export default function AdminEntry() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const openConsole = isDemoMode() || isPublicConsole();

  useEffect(() => {
    if (openConsole) router.replace("/admin/dashboard");
  }, [openConsole, router]);

  if (openConsole) {
    return <main className="flex flex-1 items-center justify-center text-text-dim">Opening console…</main>;
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await verifyPassword(password);
      router.push("/admin/dashboard");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to sign in.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex flex-1 items-center justify-center px-6 py-24">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex items-center gap-2 text-text-dim">
          <Lock className="h-4 w-4" />
          <span className="font-mono text-xs uppercase tracking-[0.2em]">Operator access</span>
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>
        <p className="mt-2 text-sm text-text-muted">Required only when the private live console is enabled.</p>
        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <input type="password" autoFocus autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" className="w-full rounded-lg border border-border bg-bg-card px-4 py-3 text-sm text-text placeholder:text-text-dim focus:border-accent focus:outline-none" />
          {error && <p className="text-sm text-danger" role="alert">{error}</p>}
          <button type="submit" disabled={loading || !password} className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-4 py-3 text-sm font-medium text-white transition hover:bg-accent-dim disabled:opacity-50">
            {loading ? "Checking…" : "Sign in"}{!loading && <ArrowRight className="h-4 w-4" />}
          </button>
        </form>
      </div>
    </main>
  );
}
