import { OperatorGate } from "@/components/operator-gate";

export default function StudioLayout({ children }: { children: React.ReactNode }) {
  return <OperatorGate>{children}</OperatorGate>;
}
