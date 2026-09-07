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

export async function getClient(id: string): Promise<ClientDetail> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/clients/${id}`, {
    cache: "no-store",
  });
  return unwrap<ClientDetail>(response);
}

export async function getClientConversations(id: string): Promise<ClientConversationItem[]> {
  const response = await authenticatedFetch(`${API_BASE_URL}/api/v1/clients/${id}/conversations`, {
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
