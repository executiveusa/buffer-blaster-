import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Social Content Studio — Social content that ships",
    template: "%s · Social Content Studio",
  },
  description:
    "A content operations studio for Shopify brands. We research, write, and schedule the posts your team keeps meaning to make.",
  metadataBase: new URL("https://example.com"),
  openGraph: {
    title: "Social Content Studio — Social content that ships",
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
      className="h-full antialiased"
    >
      <body className="min-h-full flex flex-col bg-bg text-text">
        {children}
      </body>
    </html>
  );
}
