"use client";

import { useEffect, useRef } from "react";
import { ChatMessage as ChatMessageType } from "@/types/chat";
import { Message } from "./Message";
import { ScrollArea } from "@/components/ui/scroll-area";

interface MessageListProps {
  messages: ChatMessageType[];
}

export function MessageList({ messages }: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <ScrollArea className="flex-1">
      <div ref={scrollRef} className="max-w-5xl mx-auto px-8 py-8 space-y-12">
        {messages.map((message, index) => (
          <Message
            key={message.id}
            message={message}
            index={index}
          />
        ))}
      </div>
    </ScrollArea>
  );
}
