"use client";
import { useLanguage } from "@/components/LanguageProvider";
import { MergeClients } from "./MergeClients";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { getClientConversations } from "@/lib/api";
import type { ClientListItem } from "@/lib/types";
import { ClientConversations } from "./ClientConversations";

function History({ client }: { client: ClientListItem }) {
  const { t } = useLanguage();
  const query = useQuery({ queryKey: ["clients", client.id, "conversations", ""], queryFn: () => getClientConversations(client.id, "") });
  return <div className="min-w-0 space-y-3">
    <Link href={"/clients/" + client.id} className="font-semibold text-accent underline">{client.full_name}</Link>
    <p className="text-sm">{client.email ?? t("No email")} · {client.phone ?? t("No phone")}</p>
    <ClientConversations conversations={query.data ?? []} loading={query.isPending} error={query.isError} onRetry={() => { void query.refetch(); }} />
  </div>;
}
export function CompareClients({ clients }: { clients: ClientListItem[] }) {
  const { t } = useLanguage();
  const [first, setFirst] = useState("");
  const [second, setSecond] = useState("");
  const a = clients.find(client => client.id === first);
  const b = clients.find(client => client.id === second);
  return <details className="rounded-xl border border-line bg-surface p-4">
    <summary className="cursor-pointer font-medium">{t("Different spellings? Compare client records")}</summary>
    <p className="my-3 text-sm text-ink/70">{t("Choose two records from this page to compare their linked conversations. Similar names do not prove they are the same person. Comparing does not change records. Combining requires a separate confirmation; the second client is the one you keep.")}</p>
    <div className="grid gap-3 sm:grid-cols-2">
      <label className="text-sm">{t("First client")}<select className="mt-1 block w-full rounded border border-line p-2" value={first} onChange={event => setFirst(event.target.value)}><option value="">{t("Choose a client")}</option>{clients.map(client => <option key={client.id} value={client.id} disabled={client.id === second}>{client.full_name} · {client.email ?? client.id.slice(0, 8)}</option>)}</select></label>
      <label className="text-sm">{t("Second client")}<select className="mt-1 block w-full rounded border border-line p-2" value={second} onChange={event => setSecond(event.target.value)}><option value="">{t("Choose a client")}</option>{clients.map(client => <option key={client.id} value={client.id} disabled={client.id === first}>{client.full_name} · {client.email ?? client.id.slice(0, 8)}</option>)}</select></label>
    </div>
    {a && b && a.id !== b.id && <MergeClients key={a.id + b.id} source={a.id} target={b.id} onMerged={() => { setFirst(""); setSecond(""); }} />}
    {a && b && a.id !== b.id && <div className="mt-5 grid gap-5 lg:grid-cols-2"><History key={a.id} client={a} /><History key={b.id} client={b} /></div>}
  </details>;
}
