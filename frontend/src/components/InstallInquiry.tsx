"use client";

import { FormEvent, useState } from "react";
import { ArrowRight, Check } from "lucide-react";

export function InstallInquiry({ compact = false }: { compact?: boolean }) {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "success" | "error">("idle");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!email.trim()) return;
    setState("sending");
    const body = new URLSearchParams({ "form-name": "buffer-blaster-install", email: email.trim() });
    try {
      const response = await fetch("/", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: body.toString(),
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
      <div className={`flex items-center gap-2 rounded-full border border-black/10 bg-white ${compact ? "px-4 py-3" : "px-5 py-4"}`}>
        <span className="grid h-7 w-7 place-items-center rounded-full bg-[#dfff67]"><Check className="h-4 w-4" /></span>
        <span className="text-sm font-medium">Install request received.</span>
      </div>
    );
  }

  return (
    <form
      name="buffer-blaster-install"
      method="POST"
      data-netlify="true"
      data-netlify-honeypot="bot-field"
      onSubmit={submit}
      className={`w-full ${compact ? "max-w-xl" : "max-w-2xl"}`}
    >
      <input type="hidden" name="form-name" value="buffer-blaster-install" />
      <p className="hidden"><label>Don’t fill this out: <input name="bot-field" /></label></p>
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
          className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full bg-black px-6 text-sm font-medium text-white transition hover:bg-black/85 disabled:cursor-wait disabled:opacity-60"
        >
          {state === "sending" ? "Sending…" : "Request an install"}
          {state !== "sending" && <ArrowRight className="h-4 w-4" />}
        </button>
      </div>
      <p className={`mt-2.5 text-[11px] ${state === "error" ? "text-red-700" : "text-black/45"}`}>
        {state === "error" ? "Couldn’t save that request. Try again." : "One-time private install. Provider usage is paid directly through the accounts you connect."}
      </p>
    </form>
  );
}
