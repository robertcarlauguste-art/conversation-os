import type {
  ActionItemOut,
  ApiErrorBody,
  ApiResponse,
  ClientConversationItem,
  ClientDetail,
  ClientListItem,
  ConversationDetail,
  ConversationListItem,
  DashboardAIBriefing,
  DashboardData,
  FollowupAction,
  FollowupActionResult,
  MemoryDetail,
  TranscriptDetail,
} from "./types";
import { authenticatedFetch, getAccessToken } from "./auth-token";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type SavedFollowup = { subject: string; body: string; channel: "email" | "text"; version: number; updated_at: string };
export async function getSavedFollowup(id: string, channel: "email" | "text"): Promise<SavedFollowup | null> {
  return unwrap(await authenticatedFetch(`${API_BASE_URL}/api/v1/memories/by-conversation/${id}/drafts/${channel}`, { cache: "no-store" }));
}
export async function saveFollowup(id: string, channel: "email" | "text", draft: { subject: string; body: string }, version: number): Promise<SavedFollowup> {
  return unwrap(await authenticatedFetch(`${API_BASE_URL}/api/v1/memories/by-conversation/${id}/drafts/${channel}`, {
    method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...draft, expected_version: version }),
  }));
}

export async function prepareFollowup(conversationId: string, selection: {
  channel: "email" | "text"; include_summary: boolean; action_ids: string[]; recipient_person_id?: string;
}): Promise<{ subject: string; body: string }> {
  return unwrap(await authenticatedFetch(`${API_BASE_URL}/api/v1/memories/by-conversation/${conversationId}/follow-up`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(selection),
  }));
}

type Allowances = Record<"recordings" | "storage_bytes" | "uploads" | "audio_seconds" | "ai" | "retries", number>;
export type PilotUsageData = { enabled: false } | {
  enabled: true; used: Allowances; limits: Allowances; remaining: Allowances; resets_at: string;
};
export async function getPilotUsage(): Promise<PilotUsageData> {
  return unwrap<PilotUsageData>(await authenticatedFetch(`${API_BASE_URL}/api/v1/usage`, { cache: "no-store" }));
}

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function unwrap<T>(response: Response): Promise<T> {
  const body = await response.json();
  if (!response.ok) {
    const errorBody = body as ApiErrorBody;
    throw new ApiError(errorBody.detail ?? "Something went wrong. Please try again.");
  }
  return (body as ApiResponse<T>).data;
}

export interface ConversationListOptions {
  limit?: number;
  offset?: number;
  search?: string;
  status?: string;
}

export async function listConversations(
  options: ConversationListOptions = {},
): Promise<ConversationListItem[]> {
  const params = new URLSearchParams();
  if (options.limit) params.set("limit", String(options.limit));
  if (options.offset) params.set("offset", String(options.offset));
  if (options.search) params.set("search", options.search);
  if (options.status) params.set("status", options.status);
  const query = params.size ? `?${params}` : "";
  const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/conversations${query}`, {
    cache: "no-store",
  });
  return unwrap<ConversationListItem[]>(response);
}

export async function getConversation(id: string): Promise<ConversationDetail> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/conversations/${id}`, {
    cache: "no-store",
  });
  return unwrap<ConversationDetail>(response);
}

/** Returns null on 404 — no memory yet is a normal state, not an error. */
export async function getMemoryByConversation(
  conversationId: string,
): Promise<MemoryDetail | null> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/v1/memories/by-conversation/${conversationId}`,
    { cache: "no-store" },
  );
  if (response.status === 404) return null;
  return unwrap<MemoryDetail>(response);
}

/** Returns null on 404 — no transcript yet is a normal state, not an error. */
export async function getTranscriptByConversation(
  conversationId: string,
): Promise<TranscriptDetail | null> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/v1/transcriptions/by-conversation/${conversationId}`,
    { cache: "no-store" },
  );
  if (response.status === 404) return null;
  return unwrap<TranscriptDetail>(response);
}

export async function deleteConversation(id: string): Promise<void> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/conversations/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as Partial<ApiErrorBody>;
    throw new ApiError(body.detail ?? "Couldn't delete this conversation.");
  }
}

/**
 * Uses XMLHttpRequest (not fetch) specifically because fetch has no
 * upload-progress event — and the spec requires a visible progress bar.
 */
export async function uploadConversation(
  file: File,
  onProgress: (percent: number) => void,
  clientId?: string | null,
): Promise<{ id: string; status: string }> {
  const token = await getAccessToken();
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE_URL}/api/v1/conversations`);
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      let body: unknown;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        reject(new ApiError("Upload failed: the server returned an unexpected response."));
        return;
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve((body as ApiResponse<{ id: string; status: string }>).data);
      } else {
        reject(new ApiError((body as ApiErrorBody).detail ?? "Upload failed."));
      }
    };

    xhr.onerror = () => reject(new ApiError("Upload failed: couldn't reach the server."));

    const formData = new FormData();
    formData.append("file", file);
    if (clientId !== undefined) {
      formData.append("client_assignment_manual", "true");
      if (clientId) formData.append("client_id", clientId);
    }
    xhr.send(formData);
  });
}

export interface ClientListOptions {
  limit?: number;
  offset?: number;
  search?: string;
  role?: string;
}

export async function listClients(options: ClientListOptions = {}): Promise<ClientListItem[]> {
  const params = new URLSearchParams();
  if (options.limit) params.set("limit", String(options.limit));
  if (options.offset) params.set("offset", String(options.offset));
  if (options.search) params.set("search", options.search);
  if (options.role) params.set("role", options.role);
  const query = params.size ? `?${params}` : "";
  const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/clients${query}`, {
    cache: "no-store",
  });
  return unwrap<ClientListItem[]>(response);
}

export async function confirmPerson(memoryId: string, personId: string, clientId: string | null): Promise<void> {
  await unwrap(await authenticatedFetch(`${API_BASE_URL}/api/v1/memories/${memoryId}/people/${personId}/confirmation`, {
    method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_id: clientId }),
  }));
}

export async function getClient(id: string): Promise<ClientDetail> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/clients/${id}`, {
    cache: "no-store",
  });
  return unwrap<ClientDetail>(response);
}

export async function getClientConversations(id: string, search = ""): Promise<ClientConversationItem[]> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/clients/${id}/conversations${search.trim() ? `?${new URLSearchParams({search: search.trim()})}` : ""}`, {
    cache: "no-store",
  });
  return unwrap<ClientConversationItem[]>(response);
}

export async function linkConversationToClient(
  clientId: string,
  conversationId: string,
): Promise<void> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/v1/clients/${clientId}/conversations/${conversationId}`,
    { method: "POST" },
  );
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as Partial<ApiErrorBody>;
    throw new ApiError(body.detail ?? "Couldn't link this conversation.");
  }
}

export async function unlinkConversationFromClient(
  clientId: string,
  conversationId: string,
): Promise<void> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/v1/clients/${clientId}/conversations/${conversationId}`,
    { method: "DELETE" },
  );
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as Partial<ApiErrorBody>;
    throw new ApiError(body.detail ?? "Couldn't unlink this conversation.");
  }
}

export async function getDashboard(): Promise<DashboardData> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/dashboard`, {
    cache: "no-store",
  });
  return unwrap<DashboardData>(response);
}

export async function generateDashboardBriefing(): Promise<DashboardAIBriefing> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/dashboard/briefing`, {
    method: "POST",
  });
  return unwrap<DashboardAIBriefing>(response);
}

export async function recordFollowupAction(
  clientId: string,
  action: FollowupAction,
  snoozeDays?: number,
): Promise<FollowupActionResult> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/v1/dashboard/recommendations/${clientId}/actions`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action,
        ...(snoozeDays ? { snooze_days: snoozeDays } : {}),
      }),
    },
  );
  return unwrap<FollowupActionResult>(response);
}

export async function completeActionItem(actionItemId: string): Promise<ActionItemOut> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/v1/memories/action-items/${actionItemId}/complete`,
    { method: "POST" },
  );
  return unwrap<ActionItemOut>(response);
}

export async function reopenActionItem(actionItemId: string): Promise<ActionItemOut> {
  const response = await authenticatedFetch(
    `${API_BASE_URL}/api/v1/memories/action-items/${actionItemId}/reopen`,
    { method: "POST" },
  );
  return unwrap<ActionItemOut>(response);
}

export async function retryConversation(id: string): Promise<ConversationDetail> {
  try {
    const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/conversations/${id}/retry`, {
      method: "POST",
    });
    if (!response.ok) throw new Error("Retry rejected");
    return await unwrap<ConversationDetail>(response);
  } catch {
    throw new ApiError("Couldn't queue the retry. Refresh the conversation before trying again.");
  }
}

export interface ClientReview {
  saved_at?: string | null;
  stale?: boolean;
  conversation_count: number;
  details: { label: string; value: string; source_conversation_id: string; quote: string }[];
  completed_actions: { action_id: string; source_conversation_id: string; quote: string }[];
  actions: Record<string, string>;
}

export async function createClient(fullName: string): Promise<ClientListItem> {
  return unwrap<ClientListItem>(await authenticatedFetch(`${API_BASE_URL}/api/v1/clients`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ full_name: fullName }),
  }));
}

export async function reviewClientUpdates(clientId: string): Promise<ClientReview> {
  return unwrap<ClientReview>(await authenticatedFetch(`${API_BASE_URL}/api/v1/clients/${clientId}/review`, { method: "POST" }));
}

export async function getSavedClientReview(clientId: string): Promise<ClientReview | null> {
  return unwrap<ClientReview | null>(await authenticatedFetch(`${API_BASE_URL}/api/v1/clients/${clientId}/review`, { cache: "no-store" }));
}

export async function editMemoryItem(memoryId: string, itemId: string, kind: "decisions" | "action-items", values: { description: string } | { task: string; owner: string | null; due: string | null }): Promise<unknown> {
  return unwrap(await authenticatedFetch(`${API_BASE_URL}/api/v1/memories/${memoryId}/${kind}/${itemId}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(values),
  }));
}

export async function renameConversation(id: string, title: string): Promise<void> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/conversations/${id}/title`, {
    method: "PATCH", headers: {"Content-Type": "application/json"}, body: JSON.stringify({title}),
  });
  if (!response.ok) await unwrap(response);
}

export type ClientMergePreview = { source: { full_name: string; email: string | null; phone: string | null; role: string | null }; target: { full_name: string; email: string | null; phone: string | null; role: string | null }; token: string; moved: Record<string, number> };
export type ClientMergeHistoryItem = { id: string; source_name: string; target_name: string; created_at: string; undone_at: string | null; supports_undo: boolean };
export async function listClientMerges(): Promise<ClientMergeHistoryItem[]> {
  return unwrap(await authenticatedFetch(API_BASE_URL + "/api/v1/clients/merge-history/recent", {cache: "no-store"}));
}
export async function undoClientMerge(id: string): Promise<{source_id: string; target_id: string}> {
  return unwrap(await authenticatedFetch(API_BASE_URL + "/api/v1/clients/merge-history/" + id + "/undo", {method: "POST"}));
}
export async function previewClientMerge(source: string, target: string): Promise<ClientMergePreview> {
  return unwrap(await authenticatedFetch(API_BASE_URL + "/api/v1/clients/" + source + "/merge-preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ target_id: target }) }));
}
export async function confirmClientMerge(source: string, target: string, token: string, name: string): Promise<{ client_id: string }> {
  return unwrap(await authenticatedFetch(API_BASE_URL + "/api/v1/clients/" + source + "/merge", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ target_id: target, expected_token: token, confirmed_name: name }) }));
}

export type TranscriptCorrection = { text: string; version: number; updated_at: string; preview: { summary: string; tasks: string[]; decisions: string[] } | null };
export async function getTranscriptCorrection(id: string): Promise<TranscriptCorrection | null> {
  return unwrap(await authenticatedFetch(`${API_BASE_URL}/api/v1/transcriptions/by-conversation/${id}/correction`, { cache: "no-store" }));
}
export async function saveTranscriptCorrection(id: string, text: string, version: number): Promise<TranscriptCorrection> {
  return unwrap(await authenticatedFetch(`${API_BASE_URL}/api/v1/transcriptions/by-conversation/${id}/correction`, {method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({text,expected_version:version})}));
}
export async function previewTranscriptCorrection(id: string, version: number): Promise<TranscriptCorrection> {
  return unwrap(await authenticatedFetch(`${API_BASE_URL}/api/v1/transcriptions/by-conversation/${id}/correction/preview`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({expected_version:version})}));
}
