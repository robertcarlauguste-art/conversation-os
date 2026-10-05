"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { listClientMerges, undoClientMerge } from "@/lib/api";
import { formatDate } from "@/lib/format";

export function ClientMergeHistory() {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const cache = useQueryClient();
  const history = useQuery({ queryKey: ["client-merges"], queryFn: listClientMerges, enabled: open });

  async function undo(id: string) {
    if (busy) return;
    setBusy(true); setError(""); setMessage("");
    try {
      await undoClientMerge(id);
      setSelected(null);
      await cache.invalidateQueries();
      setMessage("Merge undone. Both clients and their original conversation links have been restored.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not undo this merge. Please try again.");
      setSelected(null);
    } finally { setBusy(false); }
  }

  return <section className="rounded-xl border border-line bg-surface p-4">
    <button type="button" aria-expanded={open} onClick={() => setOpen(!open)} className="font-medium underline">Recent merges &amp; undo</button>
    {open && <div className="mt-3 space-y-4">
      <p className="text-sm">Undo restores the two original clients and their conversation links. If records changed after the merge, we stop to protect newer work. Showing your 20 most recent merges.</p>
      {history.isLoading && <p>Loading merge history…</p>}
      {history.isError && <p role="alert">Could not load merge history. <button className="underline" onClick={() => void history.refetch()}>Try again</button></p>}
      {history.data?.length === 0 && <p>No merges yet.</p>}
      {history.data?.map(row => <div key={row.id} className="space-y-2 rounded border border-line p-3">
        <p><strong>{row.source_name}</strong> combined into <strong>{row.target_name}</strong></p>
        <p className="text-sm">{formatDate(row.created_at)}</p>
        {row.undone_at ? <p>Undone {formatDate(row.undone_at)}</p> : !row.supports_undo ? <p>This older merge needs manual recovery review.</p> : selected === row.id ? <>
          <p>Restore {row.source_name} and {row.target_name} as separate clients?</p>
          <button disabled={busy} onClick={() => void undo(row.id)} className="rounded bg-accent px-3 py-2 text-white disabled:opacity-50">{busy ? "Restoring…" : "Confirm undo merge"}</button>
          <button disabled={busy} className="ml-3 underline" onClick={() => setSelected(null)}>Cancel</button>
        </> : <button disabled={busy} className="underline" onClick={() => { setSelected(row.id); setMessage(""); setError(""); }}>Undo merge</button>}
      </div>)}
      {message && <p role="status">{message}</p>}
      {error && <p role="alert">{error}</p>}
    </div>}
  </section>;
}
