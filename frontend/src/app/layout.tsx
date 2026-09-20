import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Buffer Blaster — AI Ad Factory",
    template: "%s · Buffer Blaster",
  },
  description:
    "A one-time private AI ad factory install for turning product briefs into UGC-style video ads, routing approved models, and keeping costs, approvals, and evidence under your control.",
  metadataBase: new URL("https://bufferblaster.netlify.app"),
  openGraph: {
    title: "Buffer Blaster — Your AI ad factory. Installed once. Yours to run.",
    description:
      "Own the creative workflow instead of renting another subscription. Buffer Blaster installs privately and connects to approved model providers you choose.",
    url: "https://bufferblaster.netlify.app",
    siteName: "Buffer Blaster",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Buffer Blaster — AI Ad Factory",
    description: "One-time private install. Your stack, your provider accounts, your creative workflow.",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" className="h-full antialiased"><body className="min-h-full bg-bg text-text">{children}</body></html>;
}
