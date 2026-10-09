"use client";
import { useLanguage } from "@/components/LanguageProvider";

import { CompareClients } from "./CompareClients";
import { ClientMergeHistory } from "./ClientMergeHistory";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useDeferredValue, useState } from "react";
import { listClients } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { WaveformMark } from "./WaveformMark";

export function ClientsTable() {
  const { t } = useLanguage();
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const deferredSearch = useDeferredValue(search.trim());
  const pageSize = 20;
  const { data, isLoading, isError } = useQuery({
    placeholderData: previous => previous,
    queryKey: ["clients", page, deferredSearch, role],
    queryFn: () =>
      listClients({
        limit: pageSize + 1,
        offset: page * pageSize,
        search: deferredSearch || undefined,
        role: role || undefined,
      }),
  });

  if (isLoading) {
    return <p className="py-10 text-center text-sm text-ink/50">{t("Loading clients…")}</p>;
  }

  if (isError) {
    return (
      <p className="py-10 text-center text-sm text-status-failed">{" "}{t("Couldn't load clients. Please refresh the page and try again.")}{" "}</p>
    );
  }

  if (!data || (data.length === 0 && page === 0 && !deferredSearch && !role)) {
    return (
      <div className="space-y-3">
      <ClientMergeHistory />
      <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-line py-16 text-center">
        <WaveformMark className="h-6 w-auto text-ink/20" />
        <p className="text-sm font-medium text-ink">{t("No clients yet")}</p>
        <p className="text-xs text-ink/50">{" "}{t("Record a note mentioning a person. After processing, check the client linked to that conversation.")}{" "}</p>
      </div>
      </div>
    );
  }

  const rows = data.slice(0, pageSize);
  const hasNextPage = data.length > pageSize;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(0);
          }}
          placeholder={t("Search name, email, or phone")}
          aria-label={t("Search clients")}
          className="min-w-0 flex-1 rounded-md border border-line bg-surface px-3 py-2 text-sm"
        />
        <select
          value={role}
          onChange={(event) => {
            setRole(event.target.value);
            setPage(0);
          }}
          aria-label={t("Filter client role")}
          className="rounded-md border border-line bg-surface px-3 py-2 text-sm"
        >
          <option value="">{t("All roles")}</option>
          <option value="buyer">{t("Buyer")}</option>
          <option value="seller">{t("Seller")}</option>
        </select>
      </div>
      <CompareClients key={JSON.stringify([page, deferredSearch, role])} clients={rows} />
      <ClientMergeHistory />
      {rows.length === 0 ? (
        <p className="rounded-xl border border-dashed border-line py-10 text-center text-sm text-ink/50">{" "}{t("No clients match these filters.")}{" "}</p>
      ) : (
      <table className="w-full border-collapse overflow-hidden rounded-xl border border-line bg-surface text-sm">
      <thead>
        <tr className="border-b border-line bg-paper text-left text-xs uppercase tracking-wide text-ink/50">
          <th className="px-4 py-3 font-medium">{t("Name")}</th>
          <th className="px-4 py-3 font-medium">{t("Email")}</th>
          <th className="px-4 py-3 font-medium">{t("Phone")}</th>
          <th className="px-4 py-3 font-medium">{t("Added")}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((client) => (
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
      )}
      <div className="flex items-center justify-between text-sm text-ink/60">
        <span>{t("Page")}{" "}{page + 1}</span>
        <div className="flex gap-2">
          <button type="button" onClick={() => setPage((value) => Math.max(0, value - 1))} disabled={page === 0} className="rounded-md border border-line px-3 py-1.5 disabled:opacity-40">{" "}{t("Previous")}{" "}</button>
          <button type="button" onClick={() => setPage((value) => value + 1)} disabled={!hasNextPage} className="rounded-md border border-line px-3 py-1.5 disabled:opacity-40">{" "}{t("Next")}{" "}</button>
        </div>
      </div>
    </div>
  );
}
