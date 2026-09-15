"use client";

import { FormEvent, useState } from "react";
import { ArrowRight, Check } from "lucide-react";

export function BetaWaitlist({ compact = false }: { compact?: boolean }) {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!email.trim()) return;
    setState("sending");
    setMessage("");
    const body = JSON.stringify({ email: email.trim() });
    try {
      const response = await fetch("/api/beta", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
      });
      if (!response.ok) { const payload = await response.json().catch(() => ({})); throw new Error(payload.detail || "signup_failed"); }
      setState("success");
      setEmail("");
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Could not join the beta list.");
      setState("error");
    }
  }

  if (state === "success") {
    return (
      <div className={`flex items-center gap-2 rounded-full border border-black/10 bg-white ${compact ? "px-4 py-3" : "px-5 py-4"}`}>
        <span className="grid h-7 w-7 place-items-center rounded-full bg-[#dfff67]"><Check className="h-4 w-4" /></span>
        <span className="text-sm font-medium">You’re on the beta list.</span>
      </div>
    );
  }

  return (
    <form
      name="buffer-blaster-beta"
      method="POST"
      data-netlify="true"
      data-netlify-honeypot="bot-field"
      onSubmit={submit}
      className={`w-full ${compact ? "max-w-xl" : "max-w-2xl"}`}
    >
      <input type="hidden" name="form-name" value="buffer-blaster-beta" />
      <p className="hidden"><label>Don’t fill this out: <input name="bot-field" /></label></p>
      <div className="flex flex-col gap-2 sm:flex-row">
        <label className="sr-only" htmlFor={compact ? "beta-email-compact" : "beta-email"}>Email address</label>
        <input
          id={compact ? "beta-email-compact" : "beta-email"}
          name="email"
          type="email"
          required
          autoComplete="email"
          placeholder="you@company.com"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="min-h-12 flex-1 rounded-full border border-black/10 bg-white px-5 text-sm outline-none transition focus:border-black/35 focus:ring-2 focus:ring-black/5"
        />
        <button
          type="submit"
          disabled={state === "sending"}
          className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full bg-black px-6 text-sm font-medium text-white transition hover:bg-black/85 disabled:cursor-wait disabled:opacity-60"
        >
          {state === "sending" ? "Joining…" : "Join the beta"}
          {state !== "sending" && <ArrowRight className="h-4 w-4" />}
        </button>
      </div>
      <p className={`mt-2.5 text-[11px] ${state === "error" ? "text-red-700" : "text-black/45"}`}>
        {state === "error" ? message || "Could not join the beta list." : "Product updates only."}
      </p>
    </form>
  );
}
