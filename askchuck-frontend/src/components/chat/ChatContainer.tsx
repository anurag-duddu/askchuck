"use client";

import { useState, useEffect, useRef } from "react";
import { ChatMessage as ChatMessageType, Figure, Source } from "@/types/chat";
import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";
import { streamQuery } from "@/lib/askchuck-api";
import { useAuth } from "@/contexts/AuthContext";
import { useQueryLimit } from "@/hooks/useQueryLimit";
import { useSession } from "@/hooks/useSession";
import { LoginModal } from "@/components/auth/LoginModal";

export function ChatContainer() {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [limitHit, setLimitHit] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [showResumePrompt, setShowResumePrompt] = useState(false);

  const { user } = useAuth();
  const { canQuery, increment } = useQueryLimit(user);
  const { sessions, createSession, saveMessage, loadSessionMessages } =
    useSession();

  // Track the previous user uid so we can detect login/logout transitions
  const prevUserUid = useRef<string | null | undefined>(undefined);

  useEffect(() => {
    const previousUid = prevUserUid.current;
    prevUserUid.current = user?.uid ?? null;

    if (user) {
      // User just logged in (was previously null/anonymous)
      if (previousUid === null && sessions.length > 0 && messages.length === 0) {
        setShowResumePrompt(true);
      }
    } else {
      // User signed out — clear session state and messages
      if (previousUid !== null && previousUid !== undefined) {
        setActiveSessionId(null);
        setMessages([]);
        setShowResumePrompt(false);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, sessions]);

  const handleResumeSession = async () => {
    if (!sessions[0]) return;
    const sessionId = sessions[0].id;
    const loaded = await loadSessionMessages(sessionId);
    setMessages(loaded);
    setActiveSessionId(sessionId);
    setShowResumePrompt(false);
  };

  const handleSendMessage = async (content: string) => {
    // Gate anonymous users at the free query limit
    if (!user && !canQuery) {
      setLimitHit(true);
      setShowLoginModal(true);
      return;
    }

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

    // Resolve or create a session ID
    let sessionId = activeSessionId;
    if (user && !sessionId) {
      // First message in a new session — create a Firestore session
      sessionId = await createSession(content);
      setActiveSessionId(sessionId);
    } else if (!user) {
      // Anonymous fallback: use localStorage-backed ephemeral session ID
      sessionId =
        localStorage.getItem("askchuck_session_id") ||
        `session_${Date.now()}_${Math.random().toString(36).substring(7)}`;
      localStorage.setItem("askchuck_session_id", sessionId);
    }

    // Persist user message for logged-in users
    if (user && sessionId) {
      saveMessage(sessionId, userMessage).catch((err) =>
        console.error("Failed to save user message:", err)
      );
    }

    // Build conversation history from previous messages
    const conversationHistory = messages.map((msg) => ({
      role: msg.role,
      content: msg.content,
    }));

    // Increment anonymous query counter before streaming
    if (!user) {
      increment();
    }

    // Get auth token for authenticated users
    const authToken = user ? await user.getIdToken() : undefined;

    // Capture the final assistant message after streaming so we can persist it
    let finalContent = "";
    let finalFigures: Figure[] = [];
    let finalSources: Source[] = [];

    // Stream response from backend
    try {
      await streamQuery(
        {
          question: content,
          session_id: sessionId ?? "",
          conversation_history: conversationHistory,
          include_figures: true,
          top_k: 5,
        },
        {
          onToken: (token: string) => {
            finalContent += token;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? { ...msg, content: msg.content + token }
                  : msg
              )
            );
          },
          onFigures: (figures: Figure[]) => {
            finalFigures = figures;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId ? { ...msg, figures } : msg
              )
            );
          },
          onSources: (sources: Source[]) => {
            finalSources = sources;
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

            // Persist the completed assistant message for logged-in users
            if (user && sessionId) {
              const completedAssistantMessage: ChatMessageType = {
                id: assistantId,
                role: "assistant",
                content: finalContent,
                created_at: new Date().toISOString(),
                figures: finalFigures,
                sources: finalSources,
                isStreaming: false,
              };
              saveMessage(sessionId, completedAssistantMessage).catch((err) =>
                console.error("Failed to save assistant message:", err)
              );
            }
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
        },
        { authToken }
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
                        &ldquo;{question}&rdquo;
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
            {/* Resume conversation banner */}
            {showResumePrompt && sessions[0] && (
              <div className="mb-4 flex items-center justify-between px-4 py-3 bg-accent/20 border border-border rounded-sm text-sm">
                <span className="text-muted-foreground">
                  Resume your last conversation?{" "}
                  <span className="text-foreground font-medium">
                    &ldquo;{sessions[0].title}&rdquo;
                  </span>
                </span>
                <div className="flex gap-3 ml-4 shrink-0">
                  <button
                    onClick={handleResumeSession}
                    className="text-primary hover:underline"
                  >
                    Resume
                  </button>
                  <button
                    onClick={() => setShowResumePrompt(false)}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            )}
            <ChatInput onSend={handleSendMessage} isLoading={isLoading} />
          </div>
        </div>
      </div>

      {/* Login modal */}
      <LoginModal
        open={showLoginModal}
        onClose={() => setShowLoginModal(false)}
        limitHit={limitHit}
      />
    </div>
  );
}
