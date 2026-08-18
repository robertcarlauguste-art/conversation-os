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
  client_id: string | null;
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

export type TranscriptionStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";

export interface TranscriptDetail {
  id: string;
  conversation_id: string;
  text: string | null;
  language: string | null;
  status: TranscriptionStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DecisionOut {
  id: string;
  description: string;
}

export interface ActionItemOut {
  id: string;
  description: string;
  owner: string | null;
}

export interface PersonOut {
  id: string;
  name: string;
  role: string | null;
}

export interface MemoryDetail {
  id: string;
  conversation_id: string;
  title: string | null;
  summary: string;
  memory_type: string;
  topics: string[];
  confidence: number;
  source: string;
  decisions: DecisionOut[];
  action_items: ActionItemOut[];
  people: PersonOut[];
  created_at: string;
  updated_at: string;
}

export interface ClientFactOut {
  id: string;
  fact_text: string;
  source_conversation_id: string;
  source_memory_id: string;
  confidence: number | null;
  created_at: string;
}

export interface ClientListItem {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  created_at: string;
}

export interface ClientDetail {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  facts: ClientFactOut[];
  created_at: string;
  updated_at: string;
}

export interface ClientConversationItem {
  id: string;
  title: string | null;
  filename: string;
  status: string;
  created_at: string;
}

export interface DashboardOverview {
  clients: number;
  conversations: number;
  completed: number;
  processing: number;
  failed: number;
}

export interface DashboardPriority {
  rank: number;
  severity: "critical" | "high" | "medium";
  category: "processing" | "followup";
  title: string;
  description: string;
  href: string | null;
}

export interface DashboardBriefItem {
  category: "conversations" | "processing" | "attention" | "clients" | "followups";
  text: string;
  tone: "neutral" | "positive" | "warning";
}

export interface DashboardData {
  overview: DashboardOverview;
  recent_clients: ClientListItem[];
  recent_conversations: ConversationListItem[];
  daily_brief: DashboardBriefItem[];
  priorities: DashboardPriority[];
  alerts: string[];
  followups: string[];
}
