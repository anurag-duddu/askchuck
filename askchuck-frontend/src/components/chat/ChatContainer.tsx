"use client";

import { useState } from "react";
import { ChatMessage as ChatMessageType, Figure, Source } from "@/types/chat";
import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";
import { streamQuery } from "@/lib/askchuck-api";

export function ChatContainer() {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async (content: string) => {
    // Add user message immediately
    const userMessage: ChatMessageType = {
      id: Date.now().toString(),
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // Create assistant message placeholder
    const assistantId = (Date.now() + 1).toString();
    const assistantMessage: ChatMessageType = {
      id: assistantId,
      role: "assistant",
      content: "",
      created_at: new Date().toISOString(),
      isStreaming: true,
      figures: [],
      sources: [],
    };

    setMessages((prev) => [...prev, assistantMessage]);

    // Generate random session ID (will be replaced with Supabase session later)
    const sessionId = localStorage.getItem("askchuck_session_id") ||
      `session_${Date.now()}_${Math.random().toString(36).substring(7)}`;
    localStorage.setItem("askchuck_session_id", sessionId);

    // Build conversation history from previous messages
    const conversationHistory = messages.map((msg) => ({
      role: msg.role,
      content: msg.content,
    }));

    // Stream response from backend
    try {
      await streamQuery(
        {
          question: content,
          session_id: sessionId,
          conversation_history: conversationHistory,
          include_figures: true,
          top_k: 5,
        },
        {
          onToken: (token: string) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? { ...msg, content: msg.content + token }
                  : msg
              )
            );
          },
          onFigures: (figures: Figure[]) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId ? { ...msg, figures } : msg
              )
            );
          },
          onSources: (sources: Source[]) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId ? { ...msg, sources } : msg
              )
            );
          },
          onDone: () => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId ? { ...msg, isStreaming: false } : msg
              )
            );
            setIsLoading(false);
          },
          onError: (error: string) => {
            console.error("Streaming error:", error);
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? {
                      ...msg,
                      content: `Error: ${error}. The service may be temporarily unavailable — please try again in a moment.`,
                      isStreaming: false,
                    }
                  : msg
              )
            );
            setIsLoading(false);
          },
        }
      );
    } catch (error) {
      console.error("Failed to send message:", error);
      setIsLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header - Editorial style with generous spacing */}
      <header className="border-b border-border bg-card">
        <div className="max-w-5xl mx-auto px-8 py-6">
          <h1 className="text-3xl font-serif text-foreground tracking-tight">
            Ask<span className="text-primary">Chuck</span>
          </h1>
          <p className="text-sm text-muted-foreground mt-1 font-serif italic">
            Explore Charles Owen's design research
          </p>
        </div>
      </header>

      {/* Main content area - Asymmetric layout with wide margins */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {/* Welcome state or message list */}
        {messages.length === 0 ? (
          <div className="flex-1 flex items-center justify-center px-8">
            <div className="max-w-2xl text-center space-y-6">
              <div className="space-y-2">
                <h2 className="text-4xl font-serif text-foreground">
                  Welcome to the Archive
                </h2>
                <p className="text-lg text-muted-foreground leading-relaxed">
                  Ask questions about Charles Owen's pioneering work in design
                  methodology, structured planning, and design research.
                </p>
              </div>

              {/* Sample questions with elegant styling */}
              <div className="space-y-3 mt-8">
                <p className="text-sm uppercase tracking-wider text-muted-foreground font-serif">
                  Try asking about:
                </p>
                <div className="grid gap-3">
                  {[
                    "What is a Design Factor?",
                    "How does Structured Planning work?",
                    "What is the role of visualization in design?",
                  ].map((question, i) => (
                    <button
                      key={i}
                      onClick={() => handleSendMessage(question)}
                      className="px-6 py-4 text-left border border-border rounded-sm hover:border-primary hover:bg-accent/10 transition-all duration-300 group"
                    >
                      <span className="text-foreground group-hover:text-primary transition-colors">
                        "{question}"
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <MessageList messages={messages} />
        )}

        {/* Input area - Fixed at bottom */}
        <div className="border-t border-border bg-card">
          <div className="max-w-5xl mx-auto px-8 py-6">
            <ChatInput onSend={handleSendMessage} isLoading={isLoading} />
          </div>
        </div>
      </div>
    </div>
  );
}
