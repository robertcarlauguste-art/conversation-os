import type { ApiErrorBody, ApiResponse, ConversationDetail, ConversationListItem } from "./types";

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

export async function listConversations(): Promise<ConversationListItem[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/conversations`, { cache: "no-store" });
  return unwrap<ConversationListItem[]>(response);
}

export async function getConversation(id: string): Promise<ConversationDetail> {
  const response = await fetch(`${API_BASE_URL}/api/v1/conversations/${id}`, {
    cache: "no-store",
  });
  return unwrap<ConversationDetail>(response);
}

export async function deleteConversation(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/conversations/${id}`, {
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
export function uploadConversation(
  file: File,
  onProgress: (percent: number) => void,
): Promise<{ id: string; status: string }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE_URL}/api/v1/conversations`);

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
