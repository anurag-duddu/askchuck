"use client";

import { useState, useCallback, useId } from "react";
import { Source } from "@/types/chat";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronUp, FileText, ExternalLink } from "lucide-react";

interface SourceCitationsProps {
  sources: Source[];
}

/**
 * Validates if a string is a valid URL
 */
function isValidUrl(url: string): boolean {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}

export function SourceCitations({ sources }: SourceCitationsProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const sourcesListId = useId();

  // Guard against null/undefined sources
  if (!sources || !Array.isArray(sources) || sources.length === 0) {
    return null;
  }

  const handleSourceClick = useCallback((source: Source) => {
    // Validate URL before opening
    if (!source.pdf_url || !isValidUrl(source.pdf_url)) {
      console.warn("Invalid or missing PDF URL:", source.pdf_url);
      return;
    }

    try {
      const newWindow = window.open(source.pdf_url, "_blank", "noopener,noreferrer");
      if (!newWindow) {
        // Popup was blocked
        console.warn("Popup blocked for:", source.pdf_url);
        // Could show a toast notification here
      }
    } catch (error) {
      console.error("Failed to open PDF:", error);
    }
  }, []);

  const handleKeyDown = useCallback((event: React.KeyboardEvent, source: Source) => {
    // Allow keyboard activation with Enter or Space
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handleSourceClick(source);
    }
  }, [handleSourceClick]);

  return (
    <div className="space-y-3">
      {/* Expandable header - footnote style */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
        aria-controls={sourcesListId}
        className="w-full flex items-center justify-between px-4 py-3 rounded-sm border border-border bg-muted/30 hover:bg-muted/50 transition-all duration-300 group"
      >
        <div className="flex items-center gap-3">
          <FileText className="w-4 h-4 text-primary" aria-hidden="true" />
          <span className="text-sm font-serif text-foreground">
            <span className="text-primary font-semibold">{sources.length}</span>{" "}
            {sources.length === 1 ? "Source" : "Sources"} Referenced
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" aria-hidden="true" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" aria-hidden="true" />
        )}
      </button>

      {/* Expanded source list */}
      {isExpanded && (
        <div
          id={sourcesListId}
          className="space-y-3 animate-in slide-in-from-top-2 duration-500"
          role="list"
          aria-label="Source citations"
        >
          {sources.map((source, index) => {
            const hasValidPdfUrl = source.pdf_url && isValidUrl(source.pdf_url);
            const displayText = source.display || "Unknown Source";
            const documentText = source.document || "Unknown Document";
            const sectionText = source.section || "";
            const pageNumber = source.page_start ?? 1;
            const chunkLevel = source.chunk_level || "unknown";

            return (
              <Card
                key={source.chunk_id || `source-${index}`}
                onClick={() => hasValidPdfUrl && handleSourceClick(source)}
                onKeyDown={(e) => hasValidPdfUrl && handleKeyDown(e, source)}
                tabIndex={hasValidPdfUrl ? 0 : undefined}
                role={hasValidPdfUrl ? "button" : "article"}
                aria-label={hasValidPdfUrl
                  ? `Open ${displayText} PDF at page ${pageNumber}`
                  : displayText
                }
                className={`p-4 border border-border bg-card transition-all duration-300 animate-in fade-in slide-in-from-left-2 ${
                  hasValidPdfUrl
                    ? "cursor-pointer hover:border-primary hover:bg-primary/5 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                    : ""
                }`}
                style={{ animationDelay: `${index * 100}ms` }}
              >
                {/* Source header */}
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="font-mono text-xs border-primary/50 text-primary">
                      [{index + 1}]
                    </Badge>
                    <span className="text-sm font-serif font-medium text-foreground">
                      {displayText}
                    </span>
                    {hasValidPdfUrl && (
                      <ExternalLink
                        className="w-3 h-3 text-muted-foreground"
                        aria-hidden="true"
                      />
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {pageNumber > 0 && (
                      <Badge variant="outline" className="text-xs font-mono">
                        p. {pageNumber}
                      </Badge>
                    )}
                    <Badge variant="secondary" className="text-xs font-mono flex-shrink-0">
                      {chunkLevel}
                    </Badge>
                  </div>
                </div>

                {/* Document and section */}
                <div className="text-xs text-muted-foreground mb-2">
                  {sectionText ? `${documentText} • ${sectionText}` : documentText}
                </div>

                {/* Click hint when PDF available */}
                {hasValidPdfUrl && (
                  <div className="text-xs text-primary/70 flex items-center gap-1">
                    <ExternalLink className="w-3 h-3" aria-hidden="true" />
                    <span>Click to open PDF at page {pageNumber}</span>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
