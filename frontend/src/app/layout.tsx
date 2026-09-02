import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Buffer Blaster — Private creative infrastructure",
    template: "%s · Buffer Blaster",
  },
  description:
    "Private creative infrastructure for client teams: research, concepts, UGC production, approvals, cost controls, and evidence in one governed system.",
  metadataBase: new URL("https://stavarai-platform.vercel.app"),
  openGraph: {
    title: "Buffer Blaster — Find the angle. Make the ad. Learn what works.",
    description:
      "A private creative operating system for managed client work and dedicated installations — built for people and agents, with human control where it matters.",
    type: "website",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" className="h-full antialiased"><body className="min-h-full bg-bg text-text">{children}</body></html>;
}
