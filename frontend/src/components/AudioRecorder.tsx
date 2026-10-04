"use client";
import { useLanguage } from "./LanguageProvider";

import { useEffect, useRef, useState } from "react";

export function AudioRecorder({ onSubmit, disabled, onActiveChange }: { onSubmit: (file: File) => Promise<boolean>; disabled: boolean; onActiveChange?: (active: boolean) => void }) {
  const { t, language } = useLanguage();
  const [phase, setPhase] = useState<"idle" | "requesting" | "recording" | "review">("idle");
  const [error, setError] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState("");
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mounted = useRef(false);

  useEffect(() => { onActiveChange?.(phase !== "idle"); }, [phase, onActiveChange]);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      if (timer.current) clearTimeout(timer.current);
      if (recorder.current?.state === "recording") recorder.current.stop();
      stream.current?.getTracks().forEach(track => track.stop());
    };
  }, []);
  useEffect(() => {
    if (!file) { setUrl(""); return; }
    const preview = URL.createObjectURL(file);
    setUrl(preview);
    return () => URL.revokeObjectURL(preview);
  }, [file]);

  async function start() {
    setError("");
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("Recording is unavailable in this browser. You can upload an audio file below.");
      return;
    }
    const mime = ["audio/webm;codecs=opus", "audio/mp4", "audio/webm"].find(type => MediaRecorder.isTypeSupported(type));
    if (!mime) { setError("This browser cannot record a supported format. Please upload a file below."); return; }
    setPhase("requesting");
    try {
      const microphone = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!mounted.current) { microphone.getTracks().forEach(track => track.stop()); return; }
      stream.current = microphone;
      const active = new MediaRecorder(microphone, { mimeType: mime });
      recorder.current = active;
      const chunks: Blob[] = [];
      let size = 0;
      active.ondataavailable = event => {
        if (event.data.size) { chunks.push(event.data); size += event.data.size; }
        if (size > 20 * 1024 * 1024 && active.state === "recording") active.stop();
      };
      active.onstop = () => {
        if (timer.current) clearTimeout(timer.current);
        microphone.getTracks().forEach(track => track.stop());
        if (!mounted.current) return;
        const type = mime.split(";")[0];
        const audio = new File(chunks, `voice-note-${Date.now()}.${type === "audio/mp4" ? "m4a" : "webm"}`, { type });
        if (!audio.size || audio.size > 24 * 1024 * 1024) {
          setError("The recording was empty or too large. Please record a shorter note."); setPhase("idle"); return;
        }
        setFile(audio); setPhase("review");
      };
      active.onerror = () => {
        setError("Recording was interrupted. Review any captured audio or try again.");
        if (active.state === "recording") active.stop();
        microphone.getTracks().forEach(track => track.stop());
      };
      active.start(1000);
      setPhase("recording");
      timer.current = setTimeout(() => { if (active.state === "recording") active.stop(); }, 180_000);
    } catch {
      stream.current?.getTracks().forEach(track => track.stop());
      if (mounted.current) { setError("Could not access your microphone. Allow microphone access and try again, or upload a file below."); setPhase("idle"); }
    }
  }

  return <section lang={language} className="rounded-xl border border-line bg-surface p-6">
    <h2 className="font-display text-xl">{t("Record a voice note")}</h2>
    <p className="my-3 text-sm text-ink/70">{t("Use fictional details for this pilot. Record up to 3 minutes, listen, then submit. Recording starts only when you allow microphone access.")}</p>
    {error && <p role="alert" className="my-3 text-red-700">{t(error)}</p>}
    {phase === "idle" && <button disabled={disabled} onClick={() => void start()} className="rounded-lg bg-accent px-5 py-3 text-white disabled:opacity-50">{t("Start recording")}</button>}
    {phase === "requesting" && <p role="status">{t("Waiting for microphone permission…")}</p>}
    {phase === "recording" && <><p role="status" className="mb-3">{t("Recording… Stops automatically after 3 minutes.")}</p><button onClick={() => recorder.current?.stop()} className="rounded-lg bg-red-700 px-5 py-3 text-white">{t("Stop and review")}</button></>}
    {phase === "review" && file && <>
      <audio controls src={url} className="my-4 w-full" aria-label={t("Recording preview")} />
      <div className="flex flex-wrap gap-3">
        <button disabled={disabled} className="rounded-lg bg-accent px-5 py-3 text-white disabled:opacity-50" onClick={async () => { if (await onSubmit(file)) { setFile(null); setPhase("idle"); } }}>{t("Submit recording")}</button>
        <button disabled={disabled} className="rounded-lg border border-line px-5 py-3" onClick={() => { setFile(null); setPhase("idle"); }}>{t("Discard recording")}</button>
      </div>
      <p className="mt-3 text-sm">{t("Nothing is uploaded until you select Submit recording.")}</p>
    </>}
  </section>;
}
