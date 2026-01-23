// Chat message types for AskChuck

export interface Figure {
  url: string;
  caption: string;
  document: string;
  figure_number: number;
  description: string;
}

export interface Source {
  display: string;
  document: string;
  section: string;
  chunk_id: string;
  chunk_level: string;
  // Navigation fields for PDF linking
  page_start?: number;
  pdf_url?: string;
  highlight_text?: string;
  // Source number matching LLM citation [1], [2], etc.
  source_number?: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  figures?: Figure[];
  sources?: Source[];
  created_at: string;
  isStreaming?: boolean;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}
