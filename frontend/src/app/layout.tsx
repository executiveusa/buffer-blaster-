import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Buffer Blaster — One-time private AI ad factory",
    template: "%s · Buffer Blaster",
  },
  description:
    "Own the system that turns products into ads. Buffer Blaster is a one-time private install with provider-neutral video generation, cost controls, approvals, and agent access.",
  metadataBase: new URL("https://bufferblaster.netlify.app"),
  openGraph: {
    title: "Buffer Blaster — Own the system that turns products into ads.",
    description:
      "A one-time private AI ad factory install for teams that want their own model accounts, approvals, and agent-ready creative workflow.",
    url: "https://bufferblaster.netlify.app",
    siteName: "Buffer Blaster",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Buffer Blaster — One-time private install",
    description: "Own the system that turns products into ads.",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" className="h-full antialiased"><body className="min-h-full bg-bg text-text">{children}</body></html>;
}
