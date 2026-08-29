import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Social Studio — Find the angle. Make the ad.",
    template: "%s · Social Studio",
  },
  description: "Turn product truth into testable UGC: research the pain, gate the script, approve the render, and keep the receipt.",
  metadataBase: new URL("https://stavarai-platform.vercel.app"),
  openGraph: {
    title: "Social Studio — Find the angle. Make the ad. Prove what works.",
    description: "A research-first UGC ad factory with explicit spend approval, inspectable scripts, and render receipts.",
    type: "website",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" className="h-full antialiased"><body className="min-h-full bg-bg text-text">{children}</body></html>;
}
