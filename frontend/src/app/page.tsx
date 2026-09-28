import { SummaryCards } from "@/components/SummaryCards";
import Link from "next/link";

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="font-display text-3xl text-ink">Dashboard</h1>
        <p className="mt-1 text-sm text-ink/60">
          Record a conversation, review your tasks, or pick up where you left off.
        </p>
      </div>
      <section className="rounded-xl border border-line bg-surface p-6">
        <h2 className="font-display text-xl">Capture your next conversation</h2>
        <p className="my-3 text-sm">Choose who it’s about, then record or upload audio. We’ll prepare notes and suggested tasks for you to review. Use fictional details during this pilot.</p>
        <Link href="/conversations" className="inline-block rounded-lg bg-accent px-5 py-3 text-white">Record a conversation</Link>
      </section>
      <SummaryCards />
    </div>
  );
}
