import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Buffer Blaster — AI Ad Factory",
    template: "%s · Buffer Blaster",
  },
  description:
    "Turn one product into ads worth testing. Buffer Blaster finds creative angles, builds UGC-style video ads, shows generation cost before spend, and keeps approvals and results with the work.",
  metadataBase: new URL("https://bufferblaster.netlify.app"),
  openGraph: {
    title: "Buffer Blaster — Turn one product into ads worth testing.",
    description:
      "An AI ad factory for creative angles, UGC-style video, controlled generation spend, and repeatable testing.",
    url: "https://bufferblaster.netlify.app",
    siteName: "Buffer Blaster",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Buffer Blaster — AI Ad Factory",
    description: "Turn one product into ads worth testing.",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" className="h-full antialiased"><body className="min-h-full bg-bg text-text">{children}</body></html>;
}
