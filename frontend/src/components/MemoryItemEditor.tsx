"use client";
import { useLanguage } from "@/components/LanguageProvider";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { editMemoryItem, completeActionItem, reopenActionItem } from "@/lib/api";
import type { ActionItemOut, DecisionOut } from "@/lib/types";

export function MemoryItemEditor({ memoryId, item }: { memoryId: string; item: ActionItemOut | DecisionOut }) {
  const { t } = useLanguage();
  const action = "task" in item;
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(action ? item.task : item.description);
  const [owner, setOwner] = useState(action ? item.owner ?? "" : "");
  const [due, setDue] = useState(action ? item.due ?? "" : "");
  const [saved, setSaved] = useState(false);
  const cache = useQueryClient();
  const statusMutation = useMutation({
    mutationFn: () => action && item.status === "COMPLETED" ? reopenActionItem(item.id) : completeActionItem(item.id),
    onSuccess: async () => {
      await Promise.all(["memory", "dashboard", "client-review"].map(key => cache.invalidateQueries({ queryKey: [key] })));
    },
  });
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
  return <li className="min-w-0 break-words rounded-lg border border-line p-3 text-sm">
    {editing ? <form onSubmit={event => { event.preventDefault(); mutation.mutate(); }} className="flex flex-col gap-3">
      <label className="flex flex-col gap-1">{action ? t("Task") : t("Decision")}
        <textarea autoFocus required maxLength={5000} value={text} onChange={e => setText(e.target.value)} disabled={mutation.isPending} className="rounded border border-line bg-paper p-2" />
      </label>
      {action && <>
        <label className="flex flex-col gap-1">{t("Owner (optional)")}<input maxLength={255} value={owner} onChange={e => setOwner(e.target.value)} disabled={mutation.isPending} className="rounded border border-line bg-paper p-2" /></label>
        <label className="flex flex-col gap-1">{t("Due date (optional)")}<input maxLength={255} placeholder={t("For example, Friday or September 25")} value={due} onChange={e => setDue(e.target.value)} disabled={mutation.isPending} className="rounded border border-line bg-paper p-2" /></label>
      </>}
      {mutation.isError && <p role="alert">{t("Couldn't save your changes. Your edits are still here; try again.")}</p>}
      <div className="flex gap-3">
        <button type="submit" disabled={mutation.isPending || !text.trim()} className="rounded bg-accent px-3 py-2 text-white disabled:opacity-50">{mutation.isPending ? t("Saving…") : t("Save changes")}</button>
        <button type="button" disabled={mutation.isPending} onClick={() => setEditing(false)}>{t("Cancel")}</button>
      </div>
    </form> : <>
      <p>{action ? item.task : item.description}</p>
      {action && <p className="mt-1 text-xs text-ink/60">{item.owner ? t("Owner: {name} · ", { name: item.owner }) : ""}{item.due ? t("Due: {date}", { date: item.due }) : t("No due date")}{item.status === "COMPLETED" ? t(" · Completed") : ""}</p>}
      <div className="mt-2 flex flex-wrap gap-3">
        <button type="button" disabled={statusMutation.isPending} onClick={start} className="min-h-11 text-accent underline" aria-label={t(action ? "Edit task: {text}" : "Edit decision: {text}", { text: action ? item.task : item.description })}>{t("Edit")}</button>
        {action && <button type="button" disabled={statusMutation.isPending} onClick={() => statusMutation.mutate()} className="min-h-11 rounded border border-line px-3 text-accent disabled:opacity-50" aria-label={t(item.status === "COMPLETED" ? "Reopen task: {text}" : "Complete task: {text}", { text: item.task })}>{statusMutation.isPending ? t("Saving…") : item.status === "COMPLETED" ? t("Reopen task") : t("Mark complete")}</button>}
      </div>
      {statusMutation.isError && <p role="alert">{t("Couldn't update the task. Please try again.")}</p>}
      {saved && <p role="status" className="mt-1 text-accent">{t("Changes saved.")}</p>}
    </>}
    {item.original && <details className="mt-3 text-xs text-ink/60"><summary className="cursor-pointer">{t("Original AI extraction")}</summary>
      {Object.entries(item.original).map(([key, value]) => <p key={key} className="mt-1">{key}: {value || t("Not specified")}</p>)}
    </details>}
  </li>;
}
