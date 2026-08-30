"use client";

import { useState } from "react";
import { ArrowRight, Loader2 } from "lucide-react";
import { startCheckout } from "@/lib/trial-api";

export function CheckoutButton({ offer, label, className = "" }: { offer: string; label: string; className?: string }) {
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");

  async function begin() {
    setWorking(true);
    setError("");
    try {
      const result = await startCheckout(offer);
      window.location.assign(result.url);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Checkout could not start.");
      setWorking(false);
    }
  }

  return <div>
    <button onClick={begin} disabled={working} className={className}>
      {working ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
      {label}
      {!working ? <ArrowRight className="h-4 w-4" /> : null}
    </button>
    {error ? <p className="mt-2 text-[11px] leading-4 text-red-600">{error}</p> : null}
  </div>;
}
