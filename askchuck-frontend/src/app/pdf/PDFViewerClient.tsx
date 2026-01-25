"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import type { TextItem as PDFTextItem } from "pdfjs-dist/types/src/display/api";

// Configure PDF.js worker from CDN
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`;

interface HighlightBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface DebugInfo {
  highlightTextLength: number;
  normalizedHighlightPreview: string;
  normalizedPageTextPreview: string;
  textItemCount: number;
  matchFound: boolean;
  matchPosition: number;
  matchLength: number;
  highlightBoxCount: number;
}

function PDFViewerContent() {
  const searchParams = useSearchParams();
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [scale, setScale] = useState(1.5);
  const [highlights, setHighlights] = useState<HighlightBox[]>([]);
  const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [debugInfo, setDebugInfo] = useState<DebugInfo | null>(null);
  const [showDebug, setShowDebug] = useState(false);

  const pdfUrl = searchParams.get("url");
  const pageParam = searchParams.get("page");
  const highlightText = searchParams.get("highlight");
  const targetPage = pageParam ? parseInt(pageParam, 10) : 1;

  // Load PDF
  useEffect(() => {
    if (!pdfUrl) {
      setError("No PDF URL provided");
      setLoading(false);
      return;
    }

    let mounted = true;
    const loadPdf = async () => {
      try {
        setLoading(true);
        const pdf = await pdfjsLib.getDocument({
          url: pdfUrl,
          cMapUrl: `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/cmaps/`,
          cMapPacked: true,
        }).promise;

        if (!mounted) return;
        setPdfDoc(pdf);
        setTotalPages(pdf.numPages);
        setCurrentPage(Math.min(targetPage, pdf.numPages));
        setLoading(false);
      } catch (err) {
        if (!mounted) return;
        setError(`Failed to load PDF: ${err instanceof Error ? err.message : "Unknown error"}`);
        setLoading(false);
      }
    };

    loadPdf();
    return () => { mounted = false; };
  }, [pdfUrl, targetPage]);

  // Render page
  const renderPage = useCallback(async () => {
    if (!pdfDoc || !containerRef.current) return;

    try {
      const page = await pdfDoc.getPage(currentPage);
      const viewport = page.getViewport({ scale });

      const container = containerRef.current;
      container.innerHTML = "";

      // Create canvas
      const canvas = document.createElement("canvas");
      const context = canvas.getContext("2d");
      if (!context) return;

      canvas.width = viewport.width;
      canvas.height = viewport.height;
      canvas.style.display = "block";

      // Render PDF to canvas
      await page.render({
        canvasContext: context,
        viewport: viewport,
        canvas: canvas,
      } as Parameters<typeof page.render>[0]).promise;

      container.appendChild(canvas);

      // Find text positions for highlighting - contiguous block matching
      if (highlightText && currentPage === targetPage) {
        const textContent = await page.getTextContent();
        const newHighlights: HighlightBox[] = [];

        // Build page text and track text item positions
        interface TextItemInfo {
          item: PDFTextItem;
          startPos: number;
          endPos: number;
        }
        const textItems: TextItemInfo[] = [];
        let pageText = "";

        for (const item of textContent.items) {
          const textItem = item as PDFTextItem;
          if (!textItem.str || !textItem.transform) continue;

          const startPos = pageText.length;
          // Add space between text items to prevent word concatenation
          if (pageText.length > 0 && !pageText.endsWith(" ") && !pageText.endsWith("\n")) {
            pageText += " ";
          }
          pageText += textItem.str;
          const endPos = pageText.length;

          textItems.push({ item: textItem, startPos, endPos });
        }

        // Normalize both texts for matching (lowercase, collapse whitespace)
        const normalizeText = (text: string) =>
          text.toLowerCase().replace(/\s+/g, " ").trim();

        const normalizedPageText = normalizeText(pageText);
        const normalizedHighlight = normalizeText(highlightText);

        // Debug info - will be displayed on page
        const debug: DebugInfo = {
          highlightTextLength: highlightText.length,
          normalizedHighlightPreview: normalizedHighlight.substring(0, 100),
          normalizedPageTextPreview: normalizedPageText.substring(0, 200),
          textItemCount: textItems.length,
          matchFound: false,
          matchPosition: -1,
          matchLength: 0,
          highlightBoxCount: 0,
        };

        // Debug logging
        console.log("=== PDF Highlighting Debug ===");
        console.log("Highlight text length:", highlightText.length);
        console.log("Normalized highlight (first 200):", normalizedHighlight.substring(0, 200));
        console.log("Normalized page text (first 500):", normalizedPageText.substring(0, 500));
        console.log("Total text items:", textItems.length);

        // Find where the chunk text appears in the page using multiple strategies
        let matchStart = -1;
        let matchLength = 0;

        // Strategy 1: Try exact substring match with progressively shorter prefixes
        const minMatchLength = Math.min(50, normalizedHighlight.length);
        for (let len = normalizedHighlight.length; len >= minMatchLength; len -= 25) {
          const searchText = normalizedHighlight.substring(0, len);
          const idx = normalizedPageText.indexOf(searchText);
          if (idx !== -1) {
            matchStart = idx;
            matchLength = len;
            console.log(`Strategy 1: Match found at position ${idx} with length ${len}`);
            break;
          }
        }

        // Strategy 2: If no match, try finding distinctive phrases from the middle
        if (matchStart === -1) {
          const words = normalizedHighlight.split(" ");
          // Try to find a sequence of 5-8 words that appears in the page text
          for (let windowSize = 8; windowSize >= 5 && matchStart === -1; windowSize--) {
            for (let i = 0; i <= words.length - windowSize && matchStart === -1; i++) {
              const phrase = words.slice(i, i + windowSize).join(" ");
              const idx = normalizedPageText.indexOf(phrase);
              if (idx !== -1) {
                matchStart = idx;
                matchLength = phrase.length;
                console.log(`Strategy 2: Found phrase "${phrase}" at position ${idx}`);
                break;
              }
            }
          }
        }

        // Strategy 3: If still no match, try individual significant words and find clusters
        if (matchStart === -1) {
          const words = normalizedHighlight.split(" ").filter(w => w.length > 4);
          const wordPositions: number[] = [];

          for (const word of words.slice(0, 10)) { // Check first 10 significant words
            const idx = normalizedPageText.indexOf(word);
            if (idx !== -1) {
              wordPositions.push(idx);
            }
          }

          if (wordPositions.length >= 3) {
            // Find cluster of nearby words
            wordPositions.sort((a, b) => a - b);
            matchStart = wordPositions[0];
            matchLength = Math.min(300, wordPositions[wordPositions.length - 1] - wordPositions[0] + 50);
            console.log(`Strategy 3: Found word cluster starting at ${matchStart}, length ${matchLength}`);
          }
        }

        // Update debug info
        if (matchStart !== -1) {
          debug.matchFound = true;
          debug.matchPosition = matchStart;
          debug.matchLength = matchLength;
        } else {
          console.log("No match found with any strategy");
        }

        if (matchStart !== -1) {
          // Map normalized position back to original page text position
          // Build a mapping from normalized positions to original positions
          let origPos = 0;
          let normPos = 0;
          const normToOrig: number[] = [];

          for (let i = 0; i < pageText.length; i++) {
            const char = pageText[i];
            const isWhitespace = /\s/.test(char);

            if (isWhitespace) {
              // In normalized text, consecutive whitespace becomes single space
              if (normPos === 0 || normToOrig[normPos - 1] !== origPos) {
                normToOrig[normPos] = origPos;
                normPos++;
              }
            } else {
              normToOrig[normPos] = origPos;
              normPos++;
            }
            origPos++;
          }

          // Get original text positions
          const origMatchStart = normToOrig[matchStart] ?? 0;
          const origMatchEnd = normToOrig[Math.min(matchStart + matchLength, normToOrig.length - 1)] ?? pageText.length;

          // Find text items that fall within the match range
          for (const { item, startPos, endPos } of textItems) {
            // Check if this text item overlaps with the match
            if (startPos < origMatchEnd && endPos > origMatchStart) {
              const [scaleX, , , scaleY, tx, ty] = item.transform;
              const x = tx * scale;
              const y = viewport.height - (ty * scale);
              const width = (item.width || scaleX * item.str.length * 0.6) * scale;
              const height = Math.abs(scaleY) * scale;

              newHighlights.push({
                x,
                y: y - height,
                width,
                height: height + 4,
              });
            }
          }
        }

        debug.highlightBoxCount = newHighlights.length;
        console.log(`Created ${newHighlights.length} highlight boxes`);

        setDebugInfo(debug);
        setHighlights(newHighlights);
      } else {
        console.log("No highlighting: either no highlightText or not on target page");
        console.log("currentPage:", currentPage, "targetPage:", targetPage, "highlightText:", !!highlightText);
        setDebugInfo({
          highlightTextLength: highlightText?.length || 0,
          normalizedHighlightPreview: "N/A - not on target page",
          normalizedPageTextPreview: "N/A",
          textItemCount: 0,
          matchFound: false,
          matchPosition: -1,
          matchLength: 0,
          highlightBoxCount: 0,
        });
        setHighlights([]);
      }
    } catch (err) {
      console.error("Render error:", err);
    }
  }, [pdfDoc, currentPage, scale, highlightText, targetPage]);

  useEffect(() => {
    renderPage();
  }, [renderPage]);

  const goToPage = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 p-4">
        <div className="bg-white rounded-lg shadow-lg p-6 max-w-md">
          <h1 className="text-xl font-semibold text-red-600 mb-2">Error</h1>
          <p className="text-gray-600 mb-4">{error}</p>
          <a
            href={pdfUrl || "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline"
          >
            Open PDF directly →
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-gray-900">
      {/* Toolbar */}
      <div className="sticky top-0 z-10 bg-gray-800 border-b border-gray-700 px-4 py-2 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <button
            onClick={() => goToPage(currentPage - 1)}
            disabled={currentPage <= 1}
            className="px-3 py-1.5 bg-gray-700 text-white rounded disabled:opacity-40 hover:bg-gray-600 transition-colors"
          >
            ← Prev
          </button>
          <span className="text-white text-sm">
            Page {currentPage} / {totalPages}
          </span>
          <button
            onClick={() => goToPage(currentPage + 1)}
            disabled={currentPage >= totalPages}
            className="px-3 py-1.5 bg-gray-700 text-white rounded disabled:opacity-40 hover:bg-gray-600 transition-colors"
          >
            Next →
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setScale((s) => Math.max(0.5, s - 0.25))}
            className="px-3 py-1.5 bg-gray-700 text-white rounded hover:bg-gray-600"
          >
            −
          </button>
          <span className="text-white text-sm w-14 text-center">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={() => setScale((s) => Math.min(3, s + 0.25))}
            className="px-3 py-1.5 bg-gray-700 text-white rounded hover:bg-gray-600"
          >
            +
          </button>
        </div>

        {highlights.length > 0 && (
          <div className="flex items-center gap-2 text-yellow-400 text-sm">
            <div className="w-3 h-3 bg-yellow-400/60 border border-yellow-500 rounded-sm" />
            {highlights.length} highlighted
          </div>
        )}

        {/* Debug toggle button */}
        <button
          onClick={() => setShowDebug(!showDebug)}
          className="px-2 py-1 text-xs bg-gray-700 text-gray-300 rounded hover:bg-gray-600"
          title="Toggle debug panel"
        >
          {showDebug ? "Hide Debug" : "Debug"}
        </button>
      </div>

      {/* Debug Panel - hidden by default */}
      {showDebug && debugInfo && (
        <div className="bg-black/90 text-green-400 text-xs font-mono p-3 border-b border-green-600 max-h-48 overflow-auto">
          <div className="font-bold text-green-300 mb-2">🔍 HIGHLIGHT DEBUG (currentPage: {currentPage}, targetPage: {targetPage})</div>
          <div>Highlight text length: {debugInfo.highlightTextLength}</div>
          <div>Text items on page: {debugInfo.textItemCount}</div>
          <div>Match found: <span className={debugInfo.matchFound ? "text-green-400" : "text-red-400"}>{debugInfo.matchFound ? "YES" : "NO"}</span></div>
          {debugInfo.matchFound && <div>Match position: {debugInfo.matchPosition}, length: {debugInfo.matchLength}</div>}
          <div>Highlight boxes: {debugInfo.highlightBoxCount}</div>
          <div className="mt-2 text-gray-400">
            <div>Normalized highlight: &quot;{debugInfo.normalizedHighlightPreview}...&quot;</div>
            <div className="mt-1">Normalized page text: &quot;{debugInfo.normalizedPageTextPreview}...&quot;</div>
          </div>
        </div>
      )}

      {/* PDF */}
      <div className="flex-1 overflow-auto flex justify-center p-4 bg-gray-800">
        {loading ? (
          <div className="flex items-center text-white">
            <div className="animate-spin w-6 h-6 border-2 border-white border-t-transparent rounded-full mr-3" />
            Loading PDF...
          </div>
        ) : (
          <div className="relative inline-block shadow-2xl">
            <div ref={containerRef} className="bg-white" />
            {/* Highlight overlays */}
            {highlights.map((box, i) => (
              <div
                key={i}
                className="absolute pointer-events-none rounded-sm"
                style={{
                  left: box.x,
                  top: box.y,
                  width: box.width,
                  height: box.height,
                  backgroundColor: "rgba(255, 220, 0, 0.35)",
                  border: "1px solid rgba(255, 180, 0, 0.5)",
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function PDFViewerClient() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
          Loading...
        </div>
      }
    >
      <PDFViewerContent />
    </Suspense>
  );
}
