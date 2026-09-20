import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Buffer Blaster — AI Ad Factory",
    template: "%s · Buffer Blaster",
  },
  description:
    "Create AI ads and own the workflow. Buffer Blaster is a one-time private AI ad factory install that connects to the model providers you choose.",
  metadataBase: new URL("https://bufferblaster.netlify.app"),
  openGraph: {
    title: "Buffer Blaster — Create AI ads. Own the factory.",
    description:
      "Turn one product brief into angles, scripts, and UGC-style video ads inside a private system you control.",
    url: "https://bufferblaster.netlify.app",
    siteName: "Buffer Blaster",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Buffer Blaster — Create AI ads. Own the factory.",
    description: "One-time private install. Bring your provider accounts and keep the creative workflow.",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" className="h-full antialiased"><body className="min-h-full bg-bg text-text">{children}</body></html>;
}
