"use client";

import { useEffect, useId, useState } from "react";
import { getSavedFollowup, prepareFollowup, saveFollowup } from "@/lib/api";
import type { MemoryDetail } from "@/lib/types";

export function PrepareFollowup({ conversationId, memory }: { conversationId: string; memory: MemoryDetail }) {
  const [open, setOpen] = useState(false);
  const controlsId = useId();
  const [channel, setChannel] = useState<"email" | "text">("email");
  const [summary, setSummary] = useState(false);
  const [recipient, setRecipient] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [draft, setDraft] = useState<{ subject: string; body: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [reload, setReload] = useState(0);
  const [version, setVersion] = useState(0);
  const [dirty, setDirty] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    setLoading(true); setLoadError(false); setDraft(null); setNotice("");
    getSavedFollowup(conversationId, channel).then(saved => {
      if (!active) return;
      setDraft(saved ? { subject: saved.subject, body: saved.body } : null);
      setVersion(saved?.version ?? 0); setSavedAt(saved?.updated_at ?? null); setDirty(false);
    }).catch(() => { if (active) { setLoadError(true); setNotice("Couldn't load your saved draft. Retry before making changes."); } })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [conversationId, channel, reload]);
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    const warnOnLink = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const link = event.target instanceof Element ? event.target.closest("a[href]") : null;
      if (!(link instanceof HTMLAnchorElement) || link.hasAttribute("download") || (link.target && link.target !== "_self")) return;
      const destination = new URL(link.href, window.location.href);
      if (!["http:", "https:"].includes(destination.protocol)) return;
      if (destination.origin === location.origin && destination.pathname === location.pathname && destination.search === location.search) return;
      if (!window.confirm("This draft has unsaved changes. Leave without saving? Choose Cancel to stay and save your draft.")) {
        event.preventDefault(); event.stopImmediatePropagation();
      }
    };
    window.addEventListener("beforeunload", warn);
    document.addEventListener("click", warnOnLink, true);
    return () => { window.removeEventListener("beforeunload", warn); document.removeEventListener("click", warnOnLink, true); };
  }, [dirty]);
  const field = "mt-1 block w-full rounded border border-line bg-paper p-3 text-ink";

  async function generate() {
    setBusy(true); setNotice("");
    try {
      setDraft(await prepareFollowup(conversationId, { channel, include_summary: summary, action_ids: selected, ...(recipient ? { recipient_person_id: recipient } : {}) }));
      setDirty(true);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Couldn't prepare a draft.");
    } finally { setBusy(false); }
  }

  async function save() {
    if (!draft) return;
    setBusy(true); setNotice("");
    try {
      const saved = await saveFollowup(conversationId, channel, draft, version);
      setVersion(saved.version); setSavedAt(saved.updated_at); setDirty(false);
      setNotice("Draft saved. You can return to this conversation later.");
    } catch (error) { setNotice(error instanceof Error ? error.message : "Couldn't save. Your edits are still here; copy them before leaving."); }
    finally { setBusy(false); }
  }

  async function copy() {
    if (!draft) return;
    try {
      await navigator.clipboard.writeText(draft.subject ? `Subject: ${draft.subject}\n\n${draft.body}` : draft.body);
      setNotice("Copied. Review it in your messaging app before sending.");
    } catch { setNotice("Couldn't copy automatically. Select the draft text and copy it manually."); }
  }

  return <section className="rounded-xl border border-line bg-surface p-6">
    <button type="button" aria-expanded={open} aria-controls={controlsId} onClick={() => setOpen(value => !value)} className="min-h-11 w-full rounded bg-accent px-4 py-3 font-medium text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:w-auto">Draft email or text</button>
    <p className="mt-3 text-sm text-ink/70">Turn selected details into an email or text. Nothing is sent, and tasks stay unchanged.</p>
    {dirty && <p role="status" className="mt-3 rounded border border-amber-500 bg-amber-50 p-3 font-medium text-amber-950">Unsaved draft — open the editor and choose Save draft before leaving.</p>}
    <div id={controlsId} hidden={!open}>
      <label className="mt-4 block text-sm">Message format
        <select className={field} value={channel} disabled={busy || loading} onChange={e => { if (!dirty || window.confirm("Leave unsaved edits? Your last saved draft will remain.")) setChannel(e.target.value as "email" | "text"); }}>
          <option value="email">Email</option><option value="text">Text message</option>
        </select>
      </label>
    {loading ? <p role="status">Loading saved draft…</p> : loadError ? <button type="button" className="min-h-11 underline" onClick={() => setReload(n => n + 1)}>Retry loading draft</button> : !draft ? <>
      <fieldset disabled={busy} className="mt-4 space-y-3">
        <legend className="mb-2 text-sm font-medium">Choose details safe to share with the recipient</legend>
        <label className="block text-sm">Who is this message for?
          <select className={field} value={recipient} onChange={e => setRecipient(e.target.value)}>
            <option value="">Recipient unspecified — neutral wording</option>
            {memory.people?.filter(p => p.confirmed_name).map(p => <option key={p.id} value={p.id}>{p.confirmed_name}</option>)}
          </select>
        </label>
        <p className="text-xs text-ink/70">To add a choice, confirm the person in the People section below. Selecting a recipient shares their confirmed and original name with AI for this draft only. It does not send a message or change saved drafts.</p>
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
      <p className="mt-4 text-sm text-ink/70">Review names, dates, responsibilities and private details before sharing. Save your edits before leaving. Saving and reopening do not use AI requests.</p>
      <p className="mt-2 text-sm" role="status">{dirty ? "Unsaved changes" : savedAt ? `Saved ${new Date(savedAt).toLocaleString()}` : "Not saved"}</p>
      {channel === "email" && <label className="mt-3 block text-sm">Subject<input disabled={busy} maxLength={200} className={field} value={draft.subject} onChange={e => { setDraft({ ...draft, subject: e.target.value }); setDirty(true); }} /></label>}
      <label className="mt-3 block text-sm">Message<textarea disabled={busy} rows={8} maxLength={5000} className={field} value={draft.body} onChange={e => { setDraft({ ...draft, body: e.target.value }); setDirty(true); }} /></label>
      <div className="mt-4 flex flex-wrap gap-3">
        <button type="button" disabled={busy || !dirty || !draft.body.trim()} onClick={save} className="min-h-11 rounded bg-accent px-4 py-2 text-white disabled:opacity-50">{busy ? "Saving…" : "Save draft"}</button>
        <button type="button" disabled={!draft.body.trim()} onClick={copy} className="min-h-11 rounded bg-accent px-4 py-2 text-white disabled:opacity-50">Copy draft</button>
        <button type="button" disabled={busy} onClick={() => { if (window.confirm("Start a new draft? Unsaved edits will be lost. Your saved version stays until you save its replacement.")) { setDraft(null); setDirty(false); setNotice(""); } }} className="min-h-11 rounded border border-line px-4 py-2">Start new draft</button>
        <button type="button" disabled={busy} onClick={() => { if (!dirty || window.confirm("Reopen the saved version and discard unsaved edits?")) setReload(n => n + 1); }} className="min-h-11 rounded border border-line px-4 py-2">Reopen saved draft</button>
      </div>
    </>}
    <p role="status" aria-live="polite" className="mt-3 text-sm">{notice}</p>
    </div>
  </section>;
}
