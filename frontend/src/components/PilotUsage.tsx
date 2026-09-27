"use client";

import { useQuery } from "@tanstack/react-query";
import { getPilotUsage } from "@/lib/api";

export function PilotUsage() {
  const query = useQuery({ queryKey: ["pilot-usage"], queryFn: getPilotUsage,
    refetchInterval: 30_000, refetchOnWindowFocus: true, retry: false });
  if (query.isError) return <p className="mb-4 text-sm" role="status">Your allowance could not be loaded. <button className="underline" onClick={() => query.refetch()}>Refresh allowance</button></p>;
  const data = query.data;
  if (!data?.enabled) return null;
  const r = data.remaining;
  return <details className="mb-6 rounded-xl border border-line bg-surface p-4 text-sm">
    <summary className="cursor-pointer font-medium">Your pilot allowance: {r.uploads} recordings and {r.ai} AI requests left today</summary>
    <ul className="mt-3 space-y-1">
      <li>{r.recordings} saved-recording slots available of {data.limits.recordings}.</li>
      <li>{Math.floor(r.storage_bytes / (1024 * 1024))} MiB audio storage remaining.</li>
      <li>{Math.floor(r.audio_seconds / 60)} minutes of new audio left today; three minutes maximum per recording or uploaded file.</li>
      <li>{r.retries} processing retries left today.</li>
      <li>Client reviews and dashboard briefings share the AI allowance.</li>
    </ul>
    <p className="mt-3">Daily allowances reset {new Date(data.resets_at).toLocaleString()}. Reading and editing saved notes remain available. Deleting a recording frees storage, but does not refund today&apos;s usage.</p>
    <p className="mt-2">AI requests count once processing starts, including unsuccessful or outdated reviews. This display updates every 30 seconds.</p>
    <button className="mt-2 text-accent underline" onClick={() => query.refetch()}>Refresh allowance</button>
  </details>;
}
