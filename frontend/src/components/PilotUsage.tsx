"use client";
import { useQuery } from "@tanstack/react-query";
import { getPilotUsage } from "@/lib/api";
import { useLanguage } from "./LanguageProvider";
export function PilotUsage() {
  const { t, language } = useLanguage();
  const query = useQuery({ queryKey: ["pilot-usage"], queryFn: getPilotUsage,
    refetchInterval: 30_000, refetchOnWindowFocus: true, retry: false });
  if (query.isError) return <p lang={language} className="mb-4 text-sm" role="status">{t("Your allowance could not be loaded.")} <button className="underline" onClick={() => query.refetch()}>{t("Refresh allowance")}</button></p>;
  const data = query.data;
  if (!data?.enabled) return null;
  const r = data.remaining;
  return <details lang={language} className="mb-6 rounded-xl border border-line bg-surface p-4 text-sm">
    <summary className="cursor-pointer font-medium"><span className="block">{t("Recordings left today: {count}", { count: String(r.uploads) })}</span><span className="block">{t("AI requests left today: {count}", { count: String(r.ai) })}</span></summary>
    <ul className="mt-3 space-y-1">
      <li>{t("Saved-recording slots available: {count} of {total}.", { count: String(r.recordings), total: String(data.limits.recordings) })}</li>
      <li>{t("Audio storage remaining: {count} MiB.", { count: String(Math.floor(r.storage_bytes / (1024 * 1024))) })}</li>
      <li>{t("New audio left today: {count} minutes. Maximum 3 minutes per recording or uploaded file.", { count: String(Math.floor(r.audio_seconds / 60)) })}</li>
      <li>{t("Processing retries left today: {count}.", { count: String(r.retries) })}</li>
      <li>{t("Client reviews, dashboard briefings and follow-up drafts share the AI allowance.")}</li>
    </ul>
    <p className="mt-3">{t("Daily allowances reset: {date}. Reading and editing saved notes remain available. Deleting a recording frees storage but does not refund today’s usage.", { date: new Date(data.resets_at).toLocaleString(language) })}</p>
    <p className="mt-2">{t("AI requests count once processing starts, including unsuccessful or outdated reviews. This display updates every 30 seconds.")}</p>
    <button className="mt-2 text-accent underline" onClick={() => query.refetch()}>{t("Refresh allowance")}</button>
  </details>;
}
