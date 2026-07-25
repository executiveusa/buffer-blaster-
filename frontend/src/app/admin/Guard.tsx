"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  LayoutDashboard,
  Users,
  FileText,
  Settings as SettingsIcon,
  PenSquare,
  LineChart,
  ArrowLeft,
} from "lucide-react";
import { isDemoMode } from "@/lib/api";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/admin/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/clients", label: "Clients", icon: Users },
  { href: "/admin/content", label: "Content", icon: FileText },
  { href: "/admin/blog", label: "Blog", icon: PenSquare },
  { href: "/admin/analytics", label: "Analytics", icon: LineChart },
  { href: "/admin/settings", label: "Settings", icon: SettingsIcon },
];

export default function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex flex-1">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-border bg-bg-elevated md:flex">
        <div className="px-5 py-6">
          <Link href="/admin/dashboard" className="text-sm font-semibold tracking-tight">
            Console
          </Link>
          <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.2em] text-text-dim">
            {isDemoMode() ? "demo mode" : "operator console"}
          </p>
        </div>

        <nav className="flex-1 space-y-1 px-3">
          {NAV.map((item) => {
            const active = pathname?.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition",
                  active
                    ? "bg-bg-card text-text"
                    : "text-text-muted hover:bg-bg-card/60 hover:text-text",
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-border p-3">
          <Link
            href="/"
            className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-text-muted transition hover:bg-bg-card/60 hover:text-text"
          >
            <ArrowLeft className="h-4 w-4" />
            Creator Studio
          </Link>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-border px-6 py-4 md:hidden">
          <span className="text-sm font-semibold">Console</span>
          <Link href="/" className="text-text-dim" aria-label="Return to Creator Studio">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </header>
        <div className="flex-1">{children}</div>
      </div>
    </div>
  );
}
