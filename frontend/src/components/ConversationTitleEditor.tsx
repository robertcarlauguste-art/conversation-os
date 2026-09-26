"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { renameConversation } from "@/lib/api";

export function ConversationTitleEditor({id, title}: {id: string; title: string | null}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(title ?? "");
  const cache = useQueryClient();
  const save = useMutation({mutationFn: () => renameConversation(id, draft.trim()), onSuccess: async () => {
    await Promise.all(["conversations", "clients", "dashboard", "client-review"].map(key => cache.invalidateQueries({queryKey:[key]})));
    setEditing(false);
  }});
  if (!editing) return <button className="mt-2 min-h-11 text-sm text-accent underline" onClick={() => {setDraft(title ?? ""); save.reset(); setEditing(true);}}>Edit title</button>;
  return <form className="mt-3 space-y-2" onSubmit={event => {event.preventDefault(); if(draft.trim()) save.mutate();}}>
    <label className="block text-sm">Conversation title
      <input autoFocus className="mt-1 block min-h-11 w-full rounded-lg border border-line px-3" maxLength={255} value={draft} onChange={event => setDraft(event.target.value)} disabled={save.isPending} />
    </label>
    <button className="min-h-11 rounded-lg bg-accent px-4 text-white disabled:opacity-50" disabled={save.isPending || !draft.trim()}>{save.isPending ? "Saving…" : "Save title"}</button>
    <button type="button" className="ml-2 min-h-11 px-3 underline" disabled={save.isPending} onClick={() => setEditing(false)}>Cancel</button>
    {save.isError && <p role="alert">Couldn&apos;t save your title. Your entry is still here; please try again.</p>}
  </form>;
}
