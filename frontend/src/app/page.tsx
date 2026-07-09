import { SummaryCards } from "@/components/SummaryCards";

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="font-display text-3xl text-ink">Dashboard</h1>
        <p className="mt-1 text-sm text-ink/60">
          A running view of every conversation moving through ConversationOS.
        </p>
      </div>
      <SummaryCards />
    </div>
  );
}
