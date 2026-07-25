"use client";

import { useState } from "react";
import { ArrowRight } from "lucide-react";

export function FoundingCheckoutButton() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function beginCheckout() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/checkout/founding", { method: "POST" });
      const payload = (await response.json()) as { url?: string; detail?: string };
      if (!response.ok || !payload.url) throw new Error(payload.detail ?? "Checkout unavailable");
      window.location.assign(payload.url);
    } catch (checkoutError) {
      setError(checkoutError instanceof Error ? checkoutError.message : "Checkout unavailable");
      setLoading(false);
    }
  }

  return (
    <div className="mt-8">
      <button
        type="button"
        onClick={beginCheckout}
        disabled={loading}
        className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-accent px-5 py-3 text-sm font-medium text-white transition hover:bg-accent-dim disabled:cursor-not-allowed disabled:opacity-60"
      >
        {loading ? "Opening secure checkout…" : "Become a Founding Creator"}
        {!loading && <ArrowRight className="h-4 w-4" aria-hidden />}
      </button>
      {error && (
        <p className="mt-3 text-xs leading-relaxed text-warning" role="alert">
          {error} Add Stripe keys later; the rest of the site remains available.
        </p>
      )}
      <p className="mt-3 text-center text-[11px] leading-relaxed text-text-dim">
        Stripe loads only after this button is selected. No Stripe package is included in the build.
      </p>
    </div>
  );
}
