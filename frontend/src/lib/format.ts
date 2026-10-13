import { translate, type Language } from "./onboarding-translations";

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  const mb = kb / 1024;
  return `${mb.toFixed(1)} MB`;
}

// Creole has no consistently available browser date locale. Use a stable numeric
// day/month/year fallback; do not silently fall back to the browser's language.
export function formatTimestamp(iso: string, language: Language = "en", options: Intl.DateTimeFormatOptions = {}): string {
  return new Date(iso).toLocaleString(language === "ht" ? "en-GB" : language, {
    ...options,
    ...(language === "ht" ? { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false } : {}),
  });
}

export function formatDate(iso: string, language: Language = "en"): string {
  return formatTimestamp(iso, language, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return `${minutes}:${remaining.toString().padStart(2, "0")}`;
}

export function conversationTitle(conversation: { title: string | null; created_at: string }, language: Language = "en"): string {
  return conversation.title?.trim() || `${translate(language, "Conversation")} — ${formatDate(conversation.created_at, language)}`;
}
