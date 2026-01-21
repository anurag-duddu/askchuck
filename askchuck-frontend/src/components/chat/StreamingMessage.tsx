"use client";

interface StreamingMessageProps {
  content: string;
}

export function StreamingMessage({ content }: StreamingMessageProps) {
  return (
    <div className="text-foreground leading-relaxed whitespace-pre-wrap">
      {content}
      <span className="inline-block w-0.5 h-4 bg-primary ml-1 animate-pulse" />
    </div>
  );
}
