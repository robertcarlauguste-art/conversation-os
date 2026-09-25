"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { ApiError, uploadConversation } from "@/lib/api";
import { useToast } from "./Toast";
import { WaveformMark } from "./WaveformMark";
import { AudioRecorder } from "./AudioRecorder";
import Link from "next/link";
import { RecordingClientChoice, type RecordingClient } from "./RecordingClientChoice";

const ACCEPTED_EXTENSIONS = [".mp3", ".wav", ".m4a", ".aac", ".webm", ".mp4"];

export function UploadDropzone({ initialClient = null }: { initialClient?: RecordingClient | null }) {
  const [client, setClient] = useState<RecordingClient | null>(initialClient);
  const [recordingActive, setRecordingActive] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [activeFileName, setActiveFileName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const busy = useRef(false);
  const [uploadedId, setUploadedId] = useState<string | null>(null);
  const { notify } = useToast();
  const queryClient = useQueryClient();

  const isUploading = progress !== null;

  async function handleFile(file: File) {
    if (busy.current || !client) return false;
    if (!file.size || file.size > 100 * 1024 * 1024) {
      notify("Choose a non-empty audio file up to 100 MB.", "error");
      return false;
    }
    busy.current = true;
    setUploadedId(null);
    setActiveFileName(file.name);
    setProgress(0);
    try {
      const result = await uploadConversation(file, setProgress, client.id);
      setUploadedId(result.id);
      notify(`${file.name} uploaded successfully.`, "success");
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      queryClient.invalidateQueries({ queryKey: ["client-review"] });
      return true;
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Upload failed.";
      notify(message, "error");
      return false;
    } finally {
      setProgress(null);
      setActiveFileName(null);
      busy.current = false;
    }
  }

  function onDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (file) void handleFile(file);
  }

  function onFilePicked(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) void handleFile(file);
    event.target.value = "";
  }

  if (!client) return <RecordingClientChoice onConfirm={setClient} />;

  return (
    <>
    <section className="rounded-xl border border-line bg-surface p-4">
      <p>{client.id ? `This recording will be saved to ${client.name}.` : "This recording will stay unassigned."}</p>
      <p className="mt-2 text-sm">Mention names when discussing multiple people so the notes are easier to follow.</p>
      <button disabled={isUploading || recordingActive} onClick={() => setClient(null)} className="mt-2 text-accent underline disabled:opacity-50">Change client</button>
    </section>
    <AudioRecorder onSubmit={handleFile} disabled={isUploading} onActiveChange={setRecordingActive} />
    {uploadedId && <p role="status">Audio uploaded. Processing may take a moment. <Link className="text-accent underline" href={`/conversations/${uploadedId}`}>Open your conversation to follow progress and review results.</Link></p>}
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={onDrop}
      className={`rounded-xl border-2 border-dashed p-10 text-center transition-colors ${
        isDragging ? "border-accent bg-accent-soft" : "border-line bg-surface"
      }`}
    >
      <WaveformMark className="mx-auto h-6 w-auto text-accent" />

      {isUploading ? (
        <div className="mx-auto mt-4 max-w-xs">
          <p className="text-sm font-medium text-ink">Uploading {activeFileName}…</p>
          <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-paper">
            <div
              className="h-full rounded-full bg-accent transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="mt-1.5 text-xs text-ink/50">{progress}%</p>
        </div>
      ) : (
        <>
          <p className="mt-4 text-sm font-medium text-ink">
            Drag an audio recording here, or{" "}
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="text-accent underline underline-offset-2 hover:text-accent/80"
            >
              choose a file
            </button>
          </p>
          <p className="mt-1.5 text-xs text-ink/50">
            {ACCEPTED_EXTENSIONS.join(", ")} · up to 100 MB
          </p>
        </>
      )}

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS.join(",")}
        onChange={onFilePicked}
        className="hidden"
      />
    </div>
    <p className="text-sm text-ink/70">Review AI summaries and actions for mistakes. You can organize conversations by linking them to a client. This pilot does not include unlimited storage.</p>
    </>
  );
}
