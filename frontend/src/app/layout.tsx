import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Buffer Blaster — Make better UGC ads",
    template: "%s · Buffer Blaster",
  },
  description:
    "Brief the product, review the scripts and cost, then approve the render.",
  metadataBase: new URL("https://bufferblaster.netlify.app"),
  openGraph: {
    title: "Buffer Blaster — Make better UGC ads",
    description:
      "Plan, review, and render UGC ads.",
    url: "https://bufferblaster.netlify.app",
    siteName: "Buffer Blaster",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Buffer Blaster — Private beta",
    description: "Plan, review, and render UGC ads.",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" className="h-full antialiased"><body className="min-h-full bg-bg text-text">{children}</body></html>;
}
