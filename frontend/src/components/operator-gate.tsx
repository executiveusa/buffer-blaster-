"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { clearToken, getToken } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function OperatorGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = getToken();
    const login = `/admin?next=${encodeURIComponent(pathname || "/studio")}`;
    if (!token) { router.replace(login); return; }
    fetch(`${API_URL}/api/auth/session`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" })
      .then((response) => { if (!response.ok) throw new Error("invalid_session"); setReady(true); })
      .catch(() => { clearToken(); router.replace(login); });
  }, [pathname, router]);

  if (!ready) return <main className="grid min-h-screen place-items-center bg-[#e9e9e7] text-sm text-black/45">Checking operator access…</main>;
  return <>{children}</>;
}
