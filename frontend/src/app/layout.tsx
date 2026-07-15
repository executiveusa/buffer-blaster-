import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "Stavarai — Social content that ships",
    template: "%s · Stavarai",
  },
  description:
    "A content operations studio for Shopify brands. We research, write, and schedule the posts your team keeps meaning to make.",
  metadataBase: new URL("https://stavarai.example.com"),
  openGraph: {
    title: "Stavarai — Social content that ships",
    description:
      "A content operations studio for Shopify brands. Research, writing, and scheduling — done.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-bg text-text">
        {children}
      </body>
    </html>
  );
}
