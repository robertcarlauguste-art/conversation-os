"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { editMemoryItem } from "@/lib/api";
import type { ActionItemOut, DecisionOut } from "@/lib/types";

export function MemoryItemEditor({ memoryId, item }: { memoryId: string; item: ActionItemOut | DecisionOut }) {
  const action = "task" in item;
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(action ? item.task : item.description);
  const [owner, setOwner] = useState(action ? item.owner ?? "" : "");
  const [due, setDue] = useState(action ? item.due ?? "" : "");
  const [saved, setSaved] = useState(false);
  const cache = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => editMemoryItem(memoryId, item.id, action ? "action-items" : "decisions",
      action ? { task: text.trim(), owner: owner.trim() || null, due: due.trim() || null } : { description: text.trim() }),
    onSuccess: async () => {
      await Promise.all(["memory", "dashboard", "client-review"].map(key => cache.invalidateQueries({ queryKey: [key] })));
      setEditing(false);
      setSaved(true);
    },
  });
  const start = () => {
    setText(action ? item.task : item.description);
    setOwner(action ? item.owner ?? "" : "");
    setDue(action ? item.due ?? "" : "");
    setSaved(false);
    mutation.reset();
    setEditing(true);
  };
  return <li className="rounded-lg border border-line p-3 text-sm">
    {editing ? <form onSubmit={event => { event.preventDefault(); mutation.mutate(); }} className="flex flex-col gap-3">
      <label className="flex flex-col gap-1">{action ? "Task" : "Decision"}
        <textarea autoFocus required maxLength={5000} value={text} onChange={e => setText(e.target.value)} disabled={mutation.isPending} className="rounded border border-line bg-paper p-2" />
      </label>
      {action && <>
        <label className="flex flex-col gap-1">Owner (optional)<input maxLength={255} value={owner} onChange={e => setOwner(e.target.value)} disabled={mutation.isPending} className="rounded border border-line bg-paper p-2" /></label>
        <label className="flex flex-col gap-1">Due date (optional)<input maxLength={255} placeholder="For example, Friday or September 25" value={due} onChange={e => setDue(e.target.value)} disabled={mutation.isPending} className="rounded border border-line bg-paper p-2" /></label>
      </>}
      {mutation.isError && <p role="alert">Couldn&apos;t save your changes. Your edits are still here; try again.</p>}
      <div className="flex gap-3">
        <button type="submit" disabled={mutation.isPending || !text.trim()} className="rounded bg-accent px-3 py-2 text-white disabled:opacity-50">{mutation.isPending ? "Saving…" : "Save changes"}</button>
        <button type="button" disabled={mutation.isPending} onClick={() => setEditing(false)}>Cancel</button>
      </div>
    </form> : <>
      <p>{action ? item.task : item.description}</p>
      {action && <p className="mt-1 text-xs text-ink/60">{item.owner ? `Owner: ${item.owner} · ` : ""}{item.due ? `Due: ${item.due}` : "No due date"}{item.status === "COMPLETED" ? " · Completed" : ""}</p>}
      <button type="button" onClick={start} className="mt-2 text-accent underline" aria-label={`Edit ${action ? "task" : "decision"}: ${action ? item.task : item.description}`}>Edit</button>
      {saved && <p role="status" className="mt-1 text-accent">Changes saved.</p>}
    </>}
    {item.original && <details className="mt-3 text-xs text-ink/60"><summary className="cursor-pointer">Original AI extraction</summary>
      {Object.entries(item.original).map(([key, value]) => <p key={key} className="mt-1">{key}: {value || "Not specified"}</p>)}
    </details>}
  </li>;
}
