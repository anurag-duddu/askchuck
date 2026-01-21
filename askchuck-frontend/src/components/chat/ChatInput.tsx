"use client";

import { useState, KeyboardEvent } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Send } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading: boolean;
}

export function ChatInput({ onSend, isLoading }: ChatInputProps) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (!input.trim() || isLoading) return;
    onSend(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex gap-3 items-end">
      <div className="flex-1 relative">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about Charles Owen's work..."
          disabled={isLoading}
          className="min-h-[60px] max-h-[200px] resize-none pr-12 text-base leading-relaxed border-border bg-input focus:border-primary transition-colors"
          rows={1}
        />
        <div className="absolute bottom-3 right-3 text-xs text-muted-foreground font-mono">
          ⌘↵
        </div>
      </div>
      <Button
        onClick={handleSend}
        disabled={!input.trim() || isLoading}
        size="lg"
        className="h-[60px] px-6 bg-primary hover:bg-primary/90 text-primary-foreground transition-all duration-300 group"
      >
        <Send className="w-5 h-5 group-hover:translate-x-0.5 transition-transform" />
      </Button>
    </div>
  );
}
