import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Creator Studio — Discover, adapt, and own your AI workflows",
    template: "%s · Creator Studio",
  },
  description:
    "Discover a small set of useful creative recipes, adapt them to your project, save them locally, and export portable agent packs you control.",
  metadataBase: new URL("https://stavarai-platform.vercel.app"),
  openGraph: {
    title: "Creator Studio — Your ideas. Your files. Your AI.",
    description:
      "Discover, adapt, save, and export portable creative workflows without giving up control of your prompts or files.",
    type: "website",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-bg text-text">{children}</body>
    </html>
  );
}
