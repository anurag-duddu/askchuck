// API client for FastAPI backend

import { QueryRequest, StreamEvent } from "@/types/api";
import { Figure, Source } from "@/types/chat";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Shown when the request itself fails (network down, non-2xx). Technical detail
// goes to the console, not the visitor.
const SERVICE_UNAVAILABLE_MESSAGE =
  "AskChuck couldn't be reached right now. Please try again in a moment.";

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onFigures: (figures: Figure[]) => void;
  onSources: (sources: Source[]) => void;
  onDone: () => void;
  // Always receives a message that is safe to show the visitor as-is
  onError: (error: string) => void;
}

export interface StreamOptions {
  authToken?: string;
}

/**
 * Stream a query to the FastAPI backend using Server-Sent Events
 */
export async function streamQuery(
  request: QueryRequest,
  callbacks: StreamCallbacks,
  options?: StreamOptions
): Promise<void> {
  try {
    const response = await fetch(`${API_URL}/stream_query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(options?.authToken
          ? { Authorization: `Bearer ${options.authToken}` }
          : {}),
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error("No response body");
    }

    const decoder = new TextDecoder();
    let buffer = "";
    let currentEvent = "";

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        // Track event type
        if (line.startsWith("event: ")) {
          currentEvent = line.slice(7).trim();
        }
        // Parse data
        else if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));

            // Handle based on type field in data or currentEvent
            const eventType = data.type || currentEvent;

            switch (eventType) {
              case "token":
                if (data.content) {
                  callbacks.onToken(data.content);
                }
                break;

              case "figures":
                if (data.figures) {
                  callbacks.onFigures(data.figures);
                }
                break;

              case "sources":
                if (data.sources) {
                  callbacks.onSources(data.sources);
                }
                break;

              case "done":
                callbacks.onDone();
                return; // Exit the loop

              case "error":
                callbacks.onError(data.error || SERVICE_UNAVAILABLE_MESSAGE);
                return; // Exit on error
            }

            // Reset event type after processing
            currentEvent = "";
          } catch (parseError) {
            console.error("Error parsing SSE data:", parseError, "Line:", line);
          }
        }
      }
    }

    // Ensure done is called if stream ended without explicit done event
    callbacks.onDone();
  } catch (error) {
    console.error("Stream error:", error);
    callbacks.onError(SERVICE_UNAVAILABLE_MESSAGE);
  }
}

/**
 * Check if the FastAPI backend is healthy
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_URL}/health`);
    return response.ok;
  } catch {
    return false;
  }
}
