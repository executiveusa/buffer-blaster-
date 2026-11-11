"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { clearToken, getToken, setToken, usesSupabaseAuth } from "@/lib/api";
import { freshAccessToken } from "@/lib/supabase";

const API_URL = "/api/backend";

export function OperatorGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const login = `/admin?next=${encodeURIComponent(pathname || "/studio")}`;
    if (usesSupabaseAuth()) {
      let cancelled = false;
      (async () => {
        const fresh = await freshAccessToken();
        if (cancelled) return;
        if (!fresh) { clearToken(); router.replace(login); return; }
        setToken(fresh);
        fetch(`${API_URL}/api/auth/session`, { headers: { Authorization: `Bearer ${fresh}` }, cache: "no-store" })
          .then((response) => { if (!response.ok) throw new Error("invalid_session"); if (!cancelled) setReady(true); })
          .catch(() => { if (cancelled) return; clearToken(); router.replace(login); });
      })();
      return () => { cancelled = true; };
    }
    const token = getToken();
    if (!token) { router.replace(login); return; }
    fetch(`${API_URL}/api/auth/session`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" })
      .then((response) => { if (!response.ok) throw new Error("invalid_session"); setReady(true); })
      .catch(() => { clearToken(); router.replace(login); });
  }, [pathname, router]);

  if (!ready) return <main className="grid min-h-screen place-items-center bg-[#e9e9e7] text-sm text-black/45">Checking operator access…</main>;
  return <>{children}</>;
}
