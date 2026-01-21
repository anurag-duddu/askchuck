"use client";

import { ChatMessage } from "@/types/chat";
import { StreamingMessage } from "./StreamingMessage";
import { FigureDisplay } from "./FigureDisplay";
import { SourceCitations } from "./SourceCitations";
import { Avatar } from "@/components/ui/avatar";
import { User, BookOpen } from "lucide-react";

interface MessageProps {
  message: ChatMessage;
  index: number;
}

export function Message({ message, index }: MessageProps) {
  const isUser = message.role === "user";

  return (
    <div
      className="animate-in fade-in slide-in-from-bottom-4 duration-700"
      style={{ animationDelay: `${index * 100}ms` }}
    >
      <div className={`flex gap-6 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
        {/* Avatar */}
        <Avatar className={`w-12 h-12 flex-shrink-0 ${isUser ? "bg-secondary" : "bg-primary"}`}>
          <div className="w-full h-full flex items-center justify-center text-primary-foreground">
            {isUser ? <User className="w-6 h-6" /> : <BookOpen className="w-6 h-6" />}
          </div>
        </Avatar>

        {/* Message content */}
        <div className={`flex-1 min-w-0 ${isUser ? "max-w-2xl ml-auto" : "max-w-3xl"}`}>
          {/* Role label */}
          <div className={`text-xs uppercase tracking-wider text-muted-foreground mb-2 font-serif ${isUser ? "text-right" : "text-left"}`}>
            {isUser ? "You" : "Charles Owen Archive"}
          </div>

          {/* Message bubble */}
          <div
            className={`
              rounded-sm border border-border p-6
              ${isUser ? "bg-card" : "bg-accent/5"}
              transition-all duration-300
            `}
          >
            {message.isStreaming ? (
              <StreamingMessage content={message.content} />
            ) : (
              <div className="text-foreground leading-relaxed whitespace-pre-wrap">
                {message.content}
              </div>
            )}

            {/* Figures */}
            {message.figures && message.figures.length > 0 && (
              <div className="mt-6 pt-6 border-t border-border/50">
                <FigureDisplay figures={message.figures} />
              </div>
            )}

            {/* Sources */}
            {message.sources && message.sources.length > 0 && (
              <div className="mt-6">
                <SourceCitations sources={message.sources} />
              </div>
            )}
          </div>

          {/* Timestamp */}
          <div className={`text-xs text-muted-foreground mt-2 font-mono ${isUser ? "text-right" : "text-left"}`}>
            {new Date(message.created_at).toLocaleTimeString()}
          </div>
        </div>
      </div>
    </div>
  );
}
