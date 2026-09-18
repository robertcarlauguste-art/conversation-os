import { SummaryCards } from "@/components/SummaryCards";
import Link from "next/link";

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="font-display text-3xl text-ink">Dashboard</h1>
        <p className="mt-1 text-sm text-ink/60">
          A running view of every conversation moving through ConversationOS.
        </p>
      </div>
      <section className="rounded-xl border border-line bg-surface p-6">
        <h2 className="font-display text-xl">Start with a short voice note</h2>
        <p className="my-3 text-sm">Record or upload audio, wait for processing, then open the conversation to review your results. For this pilot, use fictional details.</p>
        <Link href="/conversations" className="inline-block rounded-lg bg-accent px-5 py-3 text-white">Record or upload audio</Link>
      </section>
      <SummaryCards />
    </div>
  );
}
