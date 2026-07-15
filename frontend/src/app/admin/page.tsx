"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Lock, ArrowRight } from "lucide-react";
import { verifyPassword } from "@/lib/api";

export default function AdminGate() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const { ok } = await verifyPassword(password);
    setLoading(false);
    if (ok) {
      router.push("/admin/dashboard");
    } else {
      setError("That password didn’t match.");
    }
  }

  return (
    <main className="flex flex-1 items-center justify-center px-6 py-24">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex items-center gap-2 text-text-dim">
          <Lock className="h-4 w-4" />
          <span className="font-mono text-xs uppercase tracking-[0.2em]">
            Restricted
          </span>
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">Sign in</h1>
        <p className="mt-2 text-sm text-text-muted">
          Operators only. This is not a customer portal.
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <div>
            <label htmlFor="password" className="sr-only">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoFocus
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              className="w-full rounded-lg border border-border bg-bg-card px-4 py-3 text-sm text-text placeholder:text-text-dim focus:border-accent focus:outline-none"
            />
          </div>

          {error && (
            <p className="text-sm text-danger" role="alert">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !password}
            className="group inline-flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-4 py-3 text-sm font-medium text-white transition hover:bg-accent-dim disabled:opacity-50"
          >
            {loading ? "Checking…" : "Sign in"}
            {!loading && (
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
            )}
          </button>
        </form>

        <p className="mt-8 text-xs text-text-dim">
          Forgot it? It’s in <code className="text-text-muted">.env</code>.
        </p>
      </div>
    </main>
  );
}
