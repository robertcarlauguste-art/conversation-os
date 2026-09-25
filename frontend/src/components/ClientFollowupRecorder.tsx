"use client";

import { useState } from "react";
import { UploadDropzone } from "./UploadDropzone";

export function ClientFollowupRecorder({ clientId, clientName }: { clientId: string; clientName: string }) {
  const [opened, setOpened] = useState(false);
  return <section aria-label="Record a client follow-up" className="space-y-4">
    <div>
      <h2 className="font-display text-xl">Add a follow-up</h2>
      <p className="mt-1 text-sm text-ink/70">Record what changed, what you discussed, or which tasks you finished. {clientName} will be selected for you.</p>
      {!opened && <button onClick={() => setOpened(true)} className="mt-3 min-h-11 rounded-lg bg-accent px-4 py-3 text-white">Record a follow-up</button>}
    </div>
    {opened && <UploadDropzone initialClient={{id: clientId, name: clientName}} />}
  </section>;
}
