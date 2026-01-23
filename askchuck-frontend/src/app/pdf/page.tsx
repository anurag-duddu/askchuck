"use client";

import dynamic from "next/dynamic";

// Dynamically import the PDF viewer to avoid SSR issues with PDF.js
const PDFViewerComponent = dynamic(() => import("./PDFViewerClient"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
      <div className="animate-spin w-6 h-6 border-2 border-white border-t-transparent rounded-full mr-3" />
      Loading PDF viewer...
    </div>
  ),
});

export default function PDFViewer() {
  return <PDFViewerComponent />;
}
