"use client";

import { useState } from "react";
import { Source } from "@/types/chat";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronUp, FileText } from "lucide-react";

interface SourceCitationsProps {
  sources: Source[];
}

export function SourceCitations({ sources }: SourceCitationsProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="space-y-3">
      {/* Expandable header - footnote style */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-3 rounded-sm border border-border bg-muted/30 hover:bg-muted/50 transition-all duration-300 group"
      >
        <div className="flex items-center gap-3">
          <FileText className="w-4 h-4 text-primary" />
          <span className="text-sm font-serif text-foreground">
            <span className="text-primary font-semibold">{sources.length}</span>{" "}
            {sources.length === 1 ? "Source" : "Sources"} Referenced
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
        )}
      </button>

      {/* Expanded source list */}
      {isExpanded && (
        <div className="space-y-3 animate-in slide-in-from-top-2 duration-500">
          {sources.map((source, index) => (
            <Card
              key={source.chunk_id}
              className="p-4 border border-border bg-card hover:border-primary/50 transition-all duration-300 animate-in fade-in slide-in-from-left-2"
              style={{ animationDelay: `${index * 100}ms` }}
            >
              {/* Source header */}
              <div className="flex items-start justify-between gap-4 mb-3">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="font-mono text-xs border-primary/50 text-primary">
                    [{index + 1}]
                  </Badge>
                  <span className="text-sm font-serif font-medium text-foreground">
                    {source.display}
                  </span>
                </div>
                <Badge variant="secondary" className="text-xs font-mono flex-shrink-0">
                  {source.chunk_level}
                </Badge>
              </div>

              {/* Document and section */}
              <div className="text-xs text-muted-foreground mb-2">
                {source.document} • {source.section}
              </div>

              {/* Debug info */}
              <div className="text-xs text-muted-foreground/50 font-mono">
                {source.chunk_id}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
