"use client";
import { useLanguage } from "@/components/LanguageProvider";

import { useDeferredValue, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { getClient, listClients, linkConversationToClient, unlinkConversationFromClient } from "@/lib/api";

export function ClientField({ conversationId, clientId }: { conversationId: string; clientId: string | null }) {
  const { t } = useLanguage();
  const cache = useQueryClient();
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const deferredSearch = useDeferredValue(search.trim());
  const current = useQuery({ queryKey: ["clients", clientId], queryFn: () => getClient(clientId!), enabled: Boolean(clientId) });
  const choices = useQuery({ queryKey: ["client-picker", deferredSearch], queryFn: () => listClients({ search: deferredSearch || undefined, limit: 20 }), enabled: !clientId });
  async function change(unlink: boolean) {
    setBusy(true); setError("");
    try {
      if (unlink && clientId) await unlinkConversationFromClient(clientId, conversationId);
      else if (selected) await linkConversationToClient(selected, conversationId);
      else return;
      setSelected(""); setSearch("");
      await Promise.all(["conversations", "clients", "client-conversations", "client-review", "dashboard"].map(key => cache.invalidateQueries({ queryKey: [key] })));
    } catch {
      setError("Couldn't update the client. Please try again.");
    } finally { setBusy(false); }
  }
  return <div className="flex min-w-0 flex-col gap-2 text-sm">
    {clientId ? <div className="flex flex-wrap items-center gap-2">
      {current.data ? <Link href={`/clients/${clientId}`} className="text-accent hover:underline">{current.data.full_name}</Link> : <span>{current.isError ? t("Couldn't load client") : t("Loading…")}</span>}
      <button type="button" disabled={busy} onClick={() => void change(true)} className="text-xs text-accent underline disabled:opacity-50">{t("Unlink")}</button>
    </div> : <>
      <span className="text-ink/60">{t("Choose an existing client to keep related recordings together.")}</span>
      <input aria-label={t("Search clients to link")} placeholder={t("Search client name")} value={search} onChange={e => { setSearch(e.target.value); setSelected(""); }} className="w-full rounded border border-line bg-paper p-2" />
      <select aria-label={t("Client to link")} value={selected} onChange={e => setSelected(e.target.value)} disabled={choices.isFetching || busy} className="w-full rounded border border-line bg-paper p-2">
        <option value="">{t("Choose a client")}</option>
        {choices.data?.map(client => <option key={client.id} value={client.id}>{client.full_name}{client.email ? ` (${client.email})` : ""}</option>)}
      </select>
      {choices.isError ? <p role="alert">{t("Couldn't load clients. Change the search or refresh to try again.")}</p> : choices.isFetching ? <p>{t("Finding clients…")}</p> : choices.data?.length === 0 ? <p>{t("No matching clients. You can add a client before your next recording.")}</p> : <p className="text-xs text-ink/60">{t("Showing up to 20 matches. Search to narrow the list.")}</p>}
      <button type="button" disabled={busy || !selected || choices.isFetching} onClick={() => void change(false)} className="self-start rounded bg-accent px-3 py-2 text-white disabled:opacity-50">{busy ? t("Saving…") : t("Link client")}</button>
    </>}
    {error && <p role="alert" className="text-red-700">{t(error)}</p>}
  </div>;
}
