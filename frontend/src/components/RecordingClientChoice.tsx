"use client";

import { useDeferredValue, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createClient, listClients } from "@/lib/api";

export type RecordingClient = { id: string | null; name: string };

export function RecordingClientChoice({ onConfirm }: { onConfirm: (client: RecordingClient) => void }) {
  const [mode, setMode] = useState("existing");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const cache = useQueryClient();
  const query = useDeferredValue(search.trim());
  const clients = useQuery({ queryKey: ["client-picker", query], queryFn: () => listClients({ search: query || undefined, limit: 20 }), enabled: mode === "existing" });
  async function confirm() {
    setError(""); setBusy(true);
    try {
      if (mode === "later") onConfirm({ id: null, name: "Assign later" });
      else if (mode === "new") {
        const client = await createClient(name.trim());
        void cache.invalidateQueries({ queryKey: ["client-picker"] });
        void cache.invalidateQueries({ queryKey: ["clients"] });
        onConfirm({ id: client.id, name: client.full_name });
      } else {
        const client = clients.data?.find(item => item.id === selected);
        if (client) onConfirm({ id: client.id, name: client.full_name });
      }
    } catch { setError("Couldn't save the client. Please try again."); }
    finally { setBusy(false); }
  }
  return <section className="rounded-xl border border-line bg-surface p-6">
    <h2 className="font-display text-xl">Who is this conversation about?</h2>
    <label className="my-3 block">Client choice
      <select aria-label="Client choice" value={mode} disabled={busy} onChange={e => setMode(e.target.value)} className="mt-2 block w-full rounded border border-line p-2">
        <option value="existing">Select an existing client</option><option value="new">Add a new client</option><option value="later">Assign later</option>
      </select>
    </label>
    {mode === "existing" && <>
      <input aria-label="Search clients" placeholder="Search by name" value={search} disabled={busy} onChange={e => { setSearch(e.target.value); setSelected(""); }} className="mb-2 w-full rounded border border-line p-2" />
      <select aria-label="Recording client" value={selected} disabled={busy || clients.isFetching} onChange={e => setSelected(e.target.value)} className="w-full rounded border border-line p-2">
        <option value="">Choose a client</option>{clients.data?.map(client => <option key={client.id} value={client.id}>{client.full_name}{client.email ? ` (${client.email})` : ""}</option>)}
      </select>
      {clients.isError ? <p role="alert">Couldn&apos;t load clients. <button onClick={() => void clients.refetch()} className="underline">Try again</button></p> : <p className="my-2 text-sm">Showing up to 20 matches. Search to narrow the list, or add a new client.</p>}
    </>}
    {mode === "new" && <label className="block">Client name<input aria-label="New client name" maxLength={255} value={name} disabled={busy} onChange={e => setName(e.target.value)} className="my-2 block w-full rounded border border-line p-2" /></label>}
    {mode === "later" && <p className="my-2">This recording will stay unassigned until you choose a client.</p>}
    {error && <p role="alert">{error}</p>}
    <button onClick={() => void confirm()} disabled={busy || (mode === "new" && !name.trim()) || (mode === "existing" && (!selected || clients.isFetching || clients.isError))} className="mt-3 rounded bg-accent px-4 py-3 text-white disabled:opacity-50">{busy ? "Saving…" : "Continue to record or upload"}</button>
  </section>;
}
