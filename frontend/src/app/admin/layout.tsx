import type { Metadata } from "next";
import Guard from "./Guard";

export const metadata: Metadata = {
  title: "Console",
  robots: { index: false, follow: false },
};

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <Guard>{children}</Guard>;
}
