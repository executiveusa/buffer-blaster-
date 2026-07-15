export default function AnalyticsPage() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <h1 className="text-2xl font-semibold tracking-tight">Analytics</h1>
      <p className="mt-1 text-sm text-text-muted">
        Engagement data populates here once Buffer posts start publishing and
        the flywheel records results.
      </p>
      <div className="mt-12 rounded-xl border border-dashed border-border p-12 text-center">
        <p className="text-sm text-text-dim">
          No engagement data yet. Analytics activate after the first published
          batch on the VPS.
        </p>
      </div>
    </div>
  );
}
