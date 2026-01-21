// API types for FastAPI backend

export interface QueryRequest {
  question: string;
  session_id: string;
  conversation_history: Array<{
    role: "user" | "assistant";
    content: string;
  }>;
  include_figures?: boolean;
  top_k?: number;
}

export interface StreamEvent {
  type: "token" | "figures" | "sources" | "chunk_ids" | "done" | "error";
  content?: string;
  figures?: Array<{
    url: string;
    caption: string;
    document: string;
    figure_number: number;
    description: string;
  }>;
  sources?: Array<{
    display: string;
    document: string;
    section: string;
    chunk_id: string;
    chunk_level: string;
  }>;
  chunk_ids?: string[];
  error?: string;
}
