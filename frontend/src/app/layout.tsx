import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Social Studio — Create, approve, publish, learn",
    template: "%s · Social Studio",
  },
  description: "Plan campaigns, create UGC, review content, schedule social posts, and keep the performance loop in one agent-ready workspace.",
  metadataBase: new URL("https://stavarai-platform.vercel.app"),
  openGraph: {
    title: "Social Studio — Make the content. Keep the cadence.",
    description: "One workspace for campaign planning, UGC creation, approvals, scheduling, and the next campaign.",
    type: "website",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" className="h-full antialiased"><body className="min-h-full bg-bg text-text">{children}</body></html>;
}
