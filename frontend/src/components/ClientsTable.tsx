"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { listClients } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { WaveformMark } from "./WaveformMark";

export function ClientsTable() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["clients"],
    queryFn: listClients,
  });

  if (isLoading) {
    return <p className="py-10 text-center text-sm text-ink/50">Loading clients…</p>;
  }

  if (isError) {
    return (
      <p className="py-10 text-center text-sm text-status-failed">
        Couldn&apos;t load clients. Check that the backend is running.
      </p>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-line py-16 text-center">
        <WaveformMark className="h-6 w-auto text-ink/20" />
        <p className="text-sm font-medium text-ink">No clients yet</p>
        <p className="text-xs text-ink/50">
          Clients appear here once conversations are reconciled to them.
        </p>
      </div>
    );
  }

  return (
    <table className="w-full border-collapse overflow-hidden rounded-xl border border-line bg-surface text-sm">
      <thead>
        <tr className="border-b border-line bg-paper text-left text-xs uppercase tracking-wide text-ink/50">
          <th className="px-4 py-3 font-medium">Name</th>
          <th className="px-4 py-3 font-medium">Email</th>
          <th className="px-4 py-3 font-medium">Phone</th>
          <th className="px-4 py-3 font-medium">Added</th>
        </tr>
      </thead>
      <tbody>
        {data.map((client) => (
          <tr key={client.id} className="border-b border-line last:border-0">
            <td className="px-4 py-3">
              <Link
                href={`/clients/${client.id}`}
                className="font-medium text-ink hover:text-accent"
              >
                {client.full_name}
              </Link>
            </td>
            <td className="px-4 py-3 text-ink/70">{client.email ?? "—"}</td>
            <td className="px-4 py-3 text-ink/70">{client.phone ?? "—"}</td>
            <td className="px-4 py-3 text-ink/70">{formatDate(client.created_at)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
