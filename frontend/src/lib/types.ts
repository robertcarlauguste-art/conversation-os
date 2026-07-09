export type ConversationStatus =
  | "UPLOADED"
  | "QUEUED"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED";

export type ConversationSource = "UPLOAD" | "PHONE" | "EMAIL" | "IMPORT";

export interface ConversationListItem {
  id: string;
  title: string | null;
  status: ConversationStatus;
  file_size: number;
  created_at: string;
}

export interface ConversationDetail {
  id: string;
  title: string | null;
  filename: string;
  mime_type: string;
  file_size: number;
  duration_seconds: number | null;
  status: ConversationStatus;
  source: ConversationSource;
  created_at: string;
  updated_at: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
}

export interface ApiErrorBody {
  detail: string;
}
