"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { confirmPerson, listClients } from "@/lib/api";
import type { PersonOut } from "@/lib/types";

export function PersonConfirmation({ memoryId, person }: { memoryId: string; person: PersonOut }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [choice, setChoice] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const cache = useQueryClient();
  const clients = useQuery({ queryKey: ["confirmation-clients", search], queryFn: () => listClients({ search, limit: 20 }), enabled: open });
  async function save(id: string | null) {
    setBusy(true); setError("");
    try {
      await confirmPerson(memoryId, person.id, id);
      await cache.invalidateQueries({ queryKey: ["memory"] });
      setOpen(false); setChoice("");
    } catch { setError("Couldn't save this confirmation. Your selection is still here; try again."); }
    finally { setBusy(false); }
  }
  return <li className="rounded border border-line p-3 text-sm">
    <p>{person.confirmed_name || person.name}{person.role ? ` — ${person.role}` : ""}</p>
    {person.confirmed_name && <p className="mt-1 text-ink/60">Confirmed name: {person.confirmed_name}. Originally extracted: {person.name}.</p>}
    <button className="min-h-11 underline" type="button" disabled={busy} onClick={() => setOpen(!open)}>{person.confirmed_name ? "Change confirmation" : "Confirm this person"}</button>
    {open && <div className="space-y-2">
      <p>Choose the client this person refers to. This confirms this mention only; it does not move the conversation or rewrite its transcript, summary, tasks or drafts.</p>
      <label className="block">Search clients<input className="block w-full rounded border border-line bg-paper p-2" value={search} disabled={busy} onChange={e => { setSearch(e.target.value); setChoice(""); }} /></label>
      {clients.isError ? <p role="alert">Couldn&apos;t load clients. <button type="button" onClick={() => clients.refetch()}>Retry</button></p> : <label className="block">Client for {person.name}<select className="block w-full rounded border border-line bg-paper p-2" value={choice} disabled={busy || clients.isFetching} onChange={e => setChoice(e.target.value)}><option value="">Choose a client</option>{clients.data?.map(c => <option key={c.id} value={c.id}>{c.full_name}</option>)}</select></label>}
      <p className="text-ink/60">Showing up to 20 matches. Search to narrow the list.</p>
      <button className="min-h-11 rounded bg-accent px-3 text-white disabled:opacity-50" disabled={busy || !choice || clients.isFetching || clients.isError} onClick={() => save(choice)}>Save confirmation</button>
      {person.confirmed_name && <button className="ml-3 min-h-11 underline" disabled={busy} onClick={() => save(null)}>Remove confirmation</button>}
    </div>}
    {error && <p role="alert">{error}</p>}
  </li>;
}
