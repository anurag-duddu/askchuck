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

      // Find text positions for highlighting
      if (highlightText) {
        const textContent = await page.getTextContent();
        const searchTerms = highlightText
          .toLowerCase()
          .split(/\s+/)
          .filter((t) => t.length > 3);

        const newHighlights: HighlightBox[] = [];

        for (const item of textContent.items) {
          const textItem = item as PDFTextItem;
          if (!textItem.str || !textItem.transform) continue;

          const itemTextLower = textItem.str.toLowerCase();
          const shouldHighlight = searchTerms.some((term) =>
            itemTextLower.includes(term)
          );

          if (shouldHighlight) {
            const [scaleX, , , scaleY, tx, ty] = textItem.transform;
            const x = tx * scale;
            const y = viewport.height - (ty * scale);
            const width = (textItem.width || scaleX * textItem.str.length * 0.6) * scale;
            const height = Math.abs(scaleY) * scale;

            newHighlights.push({
              x,
              y: y - height,
              width,
              height: height + 4,
            });
          }
        }

        setHighlights(newHighlights);
      } else {
        setHighlights([]);
      }
    } catch (err) {
      console.error("Render error:", err);
    }
  }, [pdfDoc, currentPage, scale, highlightText]);

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
      </div>

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
