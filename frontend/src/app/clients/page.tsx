import { ClientsTable } from "@/components/ClientsTable";

export default function ClientsPage() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="font-display text-3xl text-ink">Clients</h1>
        <p className="mt-1 text-sm text-ink/60">
          Everyone ConversationOS has remembered across your conversations.
        </p>
      </div>
      <ClientsTable />
    </div>
  );
}
