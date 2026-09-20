"use client";

import { FormEvent, useState } from "react";
import { ArrowRight, Check } from "lucide-react";

export function InstallInquiry({ compact = false, inverse = false }: { compact?: boolean; inverse?: boolean }) {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "success" | "error">("idle");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!email.trim()) return;
    setState("sending");
    const body = { email: email.trim(), bot_field: "" };
    try {
      const response = await fetch("/api/install-inquiry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error("install_inquiry_failed");
      setState("success");
      setEmail("");
    } catch {
      setState("error");
    }
  }

  if (state === "success") {
    return (
      <div role="status" aria-live="polite" className={`flex items-center gap-2 rounded-full border border-black/10 bg-white ${compact ? "px-4 py-3" : "px-5 py-4"}`}>
        <span className="grid h-7 w-7 place-items-center rounded-full bg-[#dfff67]"><Check className="h-4 w-4" /></span>
        <span className="text-sm font-medium">Install request received.</span>
      </div>
    );
  }

  return (
    <form
      name="buffer-blaster-install"
      method="POST"
      onSubmit={submit}
      className={`w-full ${compact ? "max-w-xl" : "max-w-2xl"}`}
    >
      <div className="flex flex-col gap-2 sm:flex-row">
        <label className="sr-only" htmlFor={compact ? "install-email-compact" : "install-email"}>Work email</label>
        <input
          id={compact ? "install-email-compact" : "install-email"}
          name="email"
          type="email"
          required
          autoComplete="email"
          placeholder="you@company.com"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="min-h-12 flex-1 rounded-full border border-black/10 bg-white px-5 text-sm text-black outline-none transition focus:border-black/35 focus:ring-2 focus:ring-black/5"
        />
        <button
          type="submit"
          disabled={state === "sending"}
          className={`inline-flex min-h-12 items-center justify-center gap-2 rounded-full px-6 text-sm font-medium transition disabled:cursor-wait disabled:opacity-60 ${inverse ? "bg-white text-black hover:bg-white/90" : "bg-black text-white hover:bg-black/85"}`}
        >
          {state === "sending" ? "Sending…" : "Request an install"}
          {state !== "sending" && <ArrowRight className="h-4 w-4" />}
        </button>
      </div>
      <p aria-live="polite" className={`mt-2.5 text-[11px] ${state === "error" ? (inverse ? "text-red-300" : "text-red-700") : (inverse ? "text-white/52" : "text-black/45")}`}>
        {state === "error" ? "Couldn’t save that request. Try again." : "One-time private install. Provider usage is paid directly through the accounts you connect."}
      </p>
    </form>
  );
}
