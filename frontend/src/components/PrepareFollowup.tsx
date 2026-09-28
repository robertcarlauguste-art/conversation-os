"use client";

import { useState } from "react";
import { prepareFollowup } from "@/lib/api";
import type { MemoryDetail } from "@/lib/types";

export function PrepareFollowup({ conversationId, memory }: { conversationId: string; memory: MemoryDetail }) {
  const [channel, setChannel] = useState<"email" | "text">("email");
  const [summary, setSummary] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [draft, setDraft] = useState<{ subject: string; body: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const field = "mt-1 block w-full rounded border border-line bg-paper p-3 text-ink";

  async function generate() {
    setBusy(true); setNotice("");
    try {
      setDraft(await prepareFollowup(conversationId, { channel, include_summary: summary, action_ids: selected }));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Couldn't prepare a draft.");
    } finally { setBusy(false); }
  }

  async function copy() {
    if (!draft) return;
    try {
      await navigator.clipboard.writeText(draft.subject ? `Subject: ${draft.subject}\n\n${draft.body}` : draft.body);
      setNotice("Copied. Review it in your messaging app before sending.");
    } catch { setNotice("Couldn't copy automatically. Select the draft text and copy it manually."); }
  }

  return <details className="rounded-xl border border-line bg-surface p-6">
    <summary className="cursor-pointer py-2 font-display text-xl text-ink">Prepare follow-up</summary>
    <p className="mt-3 text-sm text-ink/70">Turn selected details into an email or text. Nothing is sent, and tasks stay unchanged.</p>
    {!draft ? <>
      <label className="mt-4 block text-sm">Message format
        <select className={field} value={channel} disabled={busy} onChange={e => setChannel(e.target.value as "email" | "text")}>
          <option value="email">Email</option><option value="text">Text message</option>
        </select>
      </label>
      <fieldset disabled={busy} className="mt-4 space-y-3">
        <legend className="mb-2 text-sm font-medium">Choose details safe to share with the recipient</legend>
        <label className="flex items-start gap-3 rounded border border-line p-3 text-sm">
          <input type="checkbox" checked={summary} onChange={e => setSummary(e.target.checked)} className="mt-1" />
          <span>Include summary<span className="mt-1 block break-words text-ink/70">{memory.summary}</span></span>
        </label>
        {memory.action_items.map(item => <label key={item.id} className="flex items-start gap-3 rounded border border-line p-3 text-sm">
          <input type="checkbox" checked={selected.includes(item.id)} onChange={e => setSelected(ids => e.target.checked ? [...ids, item.id] : ids.filter(id => id !== item.id))} className="mt-1" />
          <span className="break-words">{item.task}<span className="mt-1 block text-ink/60">{item.owner ? `Owner: ${item.owner}` : "Owner unspecified"}{item.due ? ` · Due: ${item.due}` : ""} · {item.status.toLowerCase()}</span></span>
        </label>)}
      </fieldset>
      <p className="mt-3 text-xs text-ink/70">Leave out private or internal details. Each generation uses one AI request from your shared pilot allowance, including unsuccessful attempts.</p>
      <button type="button" disabled={busy || (!summary && !selected.length)} onClick={generate} className="mt-4 min-h-11 rounded bg-accent px-4 py-2 text-white disabled:opacity-50">{busy ? "Preparing…" : "Prepare draft"}</button>
    </> : <>
      <p className="mt-4 text-sm text-ink/70">Review names, dates, responsibilities and private details before sharing. This draft is only kept while this page stays open.</p>
      {channel === "email" && <label className="mt-3 block text-sm">Subject<input maxLength={200} className={field} value={draft.subject} onChange={e => setDraft({ ...draft, subject: e.target.value })} /></label>}
      <label className="mt-3 block text-sm">Message<textarea rows={8} maxLength={5000} className={field} value={draft.body} onChange={e => setDraft({ ...draft, body: e.target.value })} /></label>
      <div className="mt-4 flex flex-wrap gap-3">
        <button type="button" disabled={!draft.body.trim()} onClick={copy} className="min-h-11 rounded bg-accent px-4 py-2 text-white disabled:opacity-50">Copy draft</button>
        <button type="button" onClick={() => { if (window.confirm("Discard this draft and choose details again?")) { setDraft(null); setNotice(""); } }} className="min-h-11 rounded border border-line px-4 py-2">Discard draft</button>
      </div>
    </>}
    <p role="status" aria-live="polite" className="mt-3 text-sm">{notice}</p>
  </details>;
}
