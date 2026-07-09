"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { ApiError, uploadConversation } from "@/lib/api";
import { useToast } from "./Toast";
import { WaveformMark } from "./WaveformMark";

const ACCEPTED_EXTENSIONS = [".mp3", ".wav", ".m4a", ".aac"];

export function UploadDropzone() {
  const [isDragging, setIsDragging] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [activeFileName, setActiveFileName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { notify } = useToast();
  const queryClient = useQueryClient();

  const isUploading = progress !== null;

  async function handleFile(file: File) {
    setActiveFileName(file.name);
    setProgress(0);
    try {
      await uploadConversation(file, setProgress);
      notify(`${file.name} uploaded successfully.`, "success");
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Upload failed.";
      notify(message, "error");
    } finally {
      setProgress(null);
      setActiveFileName(null);
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

  return (
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
  );
}
