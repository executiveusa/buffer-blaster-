import type { ReactNode } from "react";

export function PageHeader({ kicker, title, body, action }: { kicker?: string; title: string; body?: string; action?: ReactNode }) {
  return <div className="flex flex-col gap-5 border-b border-black/6 px-6 py-7 sm:flex-row sm:items-end sm:justify-between lg:px-10 lg:py-9">
    <div className="max-w-3xl">
      {kicker && <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-black/35">{kicker}</p>}
      <h2 className="mt-2 text-3xl font-semibold tracking-[-0.045em] sm:text-4xl">{title}</h2>
      {body && <p className="mt-3 max-w-2xl text-sm leading-6 text-black/52">{body}</p>}
    </div>
    {action}
  </div>;
}

export function Metric({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return <div className="rounded-2xl border border-black/7 bg-white p-5 shadow-[0_12px_40px_rgba(0,0,0,.035)]">
    <p className="text-xs text-black/45">{label}</p><p className="mt-2 text-3xl font-semibold tracking-[-0.05em]">{value}</p>{detail && <p className="mt-2 text-xs text-black/38">{detail}</p>}
  </div>;
}

export function StatusPill({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "green" | "blue" | "amber" }) {
  const toneClass = { neutral: "bg-black/[0.05] text-black/55", green: "bg-[#e9f8ef] text-[#137a42]", blue: "bg-[#e8eeff] text-[#2357ff]", amber: "bg-[#fff4dd] text-[#94610d]" }[tone];
  return <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.1em] ${toneClass}`}>{children}</span>;
}

export function EmptyPanel({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return <div className="grid min-h-64 place-items-center rounded-2xl border border-dashed border-black/14 bg-[#fafaf8] p-8 text-center"><div className="max-w-sm"><h3 className="text-lg font-medium">{title}</h3><p className="mt-2 text-sm leading-6 text-black/45">{body}</p>{action && <div className="mt-5">{action}</div>}</div></div>;
}
