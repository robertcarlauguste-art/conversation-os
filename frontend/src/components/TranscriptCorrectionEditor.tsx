"use client";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getTranscriptCorrection, saveTranscriptCorrection, previewTranscriptCorrection, type TranscriptCorrection } from "@/lib/api";
import { useLanguage } from "./LanguageProvider";

export function TranscriptCorrectionEditor({conversationId, original, currentSummary}: {conversationId:string; original:string; currentSummary?:string}) {
  const {t}=useLanguage();
  const cache=useQueryClient();
  const key=["transcript-correction",conversationId];
  const query=useQuery({queryKey:key,queryFn:()=>getTranscriptCorrection(conversationId)});
  const [editing,setEditing]=useState(false),[text,setText]=useState(""),[version,setVersion]=useState(0),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const dirty=editing && text !== (query.data?.text ?? original);
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
      if (!window.confirm(t("This transcript has unsaved changes. Leave without saving?"))) {
        event.preventDefault(); event.stopImmediatePropagation();
      }
    };
    window.addEventListener("beforeunload", warn);
    document.addEventListener("click", warnOnLink, true);
    // Only cancel history traversals the browser explicitly allows us to cancel.
    // Do not push synthetic history entries or interfere with Next's router state.
    const navigation = (window as Window & { navigation?: EventTarget }).navigation;
    const warnOnHistory = (event: Event) => {
      const navigationEvent = event as Event & { navigationType?: string; destination?: { url: string }; hashChange?: boolean };
      if (navigationEvent.navigationType !== "traverse" || !event.cancelable || event.defaultPrevented || navigationEvent.hashChange || !navigationEvent.destination) return;
      const destination = new URL(navigationEvent.destination.url, window.location.href);
      if (destination.origin === location.origin && destination.pathname === location.pathname && destination.search === location.search) return;
      if (!window.confirm(t("This transcript has unsaved changes. Leave without saving?"))) event.preventDefault();
    };
    navigation?.addEventListener("navigate", warnOnHistory);
    return () => {
      window.removeEventListener("beforeunload", warn);
      document.removeEventListener("click", warnOnLink, true);
      navigation?.removeEventListener("navigate", warnOnHistory);
    };
  }, [dirty, t]);
  function accept(result:TranscriptCorrection){cache.setQueryData(key,result);setEditing(false);}
  async function save(){setBusy(true);setError("");try{accept(await saveTranscriptCorrection(conversationId,text,version));}catch(e){setError(e instanceof Error?e.message:"Could not save correction.");}finally{setBusy(false);}}
  async function generate(){if(!query.data)return;setBusy(true);setError("");try{accept(await previewTranscriptCorrection(conversationId,query.data.version));}catch(e){setError(e instanceof Error?e.message:"Could not generate updated notes.");}finally{setBusy(false);void cache.invalidateQueries({queryKey:["pilot-usage"]});}}
  if(query.isLoading)return <p>{t("Loading…")}</p>;
  if(query.isError)return <p role="alert">{t("Could not load corrections.")} <button onClick={()=>void query.refetch()}>{t("Try again")}</button></p>;
  return <div className="mt-4 space-y-3">
    <p className="text-sm">{t("Corrections keep the original transcript. Saving does not use AI or change existing notes, tasks, client links or drafts.")}</p>
    {editing ? <form onSubmit={e=>{e.preventDefault();void save();}} className="space-y-3">
      <label className="block">{t("Corrected transcript")}<textarea className="mt-2 min-h-48 w-full rounded border border-line bg-paper p-3" value={text} onChange={e=>setText(e.target.value)} maxLength={50000} disabled={busy} /></label>
      <p>{t("Save your correction before leaving this page.")}</p>
      <div className="flex flex-wrap gap-3"><button disabled={busy||!text.trim()} className="rounded bg-accent px-3 py-2 text-white">{t("Save correction")}</button><button type="button" disabled={busy} onClick={()=>{if(!dirty||window.confirm(t("Discard unsaved transcript edits?")))setEditing(false);}}>{t("Cancel")}</button></div>
    </form> : <>
      {query.data && <><h4 className="font-medium">{t("Corrected transcript")}</h4><p className="whitespace-pre-wrap break-words">{query.data.text}</p></>}
      <button className="min-h-11 text-accent underline" disabled={busy} onClick={()=>{setText(query.data?.text??original);setVersion(query.data?.version??0);setError("");setEditing(true);}}>{t("Correct transcript")}</button>
      {query.data && <><p>{t("Generate a separate notes preview from the saved correction. This uses one AI request, including failed attempts. Existing work stays unchanged; review suggestions before manually editing your tasks.")}</p><button disabled={busy} onClick={()=>void generate()} className="rounded border border-line px-3 py-2">{busy?t("Generating…"):t("Preview updated notes")}</button></>}
    </>}
    {error&&<p role="alert">{t(error)}</p>}
    {query.data?.preview&&<section className="space-y-2 rounded border border-line p-3"><h4 className="font-medium">{t("Updated notes preview — not applied")}</h4><p className="text-sm">{t("Compare the suggestions below. To update a task or decision, use Edit on that item. This preview does not replace your summary or drafts.")}</p><div className="grid gap-4 md:grid-cols-2">{currentSummary && <div><h5 className="font-medium">{t("Current summary")}</h5><p className="whitespace-pre-wrap break-words">{currentSummary}</p></div>}<div><h5 className="font-medium">{t("Suggested summary")}</h5><p className="whitespace-pre-wrap break-words">{query.data.preview.summary}</p></div></div><h5>{t("Suggested tasks")}</h5><ul>{query.data.preview.tasks.map((x,i)=><li key={i}>{x}</li>)}</ul><h5>{t("Decisions")}</h5><ul>{query.data.preview.decisions.map((x,i)=><li key={i}>{x}</li>)}</ul></section>}
  </div>;
}

