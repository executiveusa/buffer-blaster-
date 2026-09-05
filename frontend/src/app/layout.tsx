import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Buffer Blaster — Private creative infrastructure",
    template: "%s · Buffer Blaster",
  },
  description:
    "Buffer Blaster turns product truth and customer signals into governed UGC creative, provider routes, approvals, and evidence. Private beta coming soon.",
  metadataBase: new URL("https://bufferblaster.netlify.app"),
  openGraph: {
    title: "Buffer Blaster — Find the angle. Make the ad. Learn what works.",
    description:
      "Private creative infrastructure for teams and AI agents. Join the Buffer Blaster beta.",
    url: "https://bufferblaster.netlify.app",
    siteName: "Buffer Blaster",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Buffer Blaster — Private beta",
    description: "Find the angle. Make the ad. Learn what works.",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" className="h-full antialiased"><body className="min-h-full bg-bg text-text">{children}</body></html>;
}
