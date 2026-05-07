'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';
import { Entity } from '@/lib/types';

// Configure pdf.js worker for Next.js 15 — Use CDN matching the exact version react-pdf is using
if (typeof window !== 'undefined') {
  pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
}

interface InteractivePDFViewerProps {
  pdfUrl: string;
  entities: Entity[];
  activeFieldId: string | null;
}

export default function InteractivePDFViewer({
  pdfUrl,
  entities,
  activeFieldId,
}: InteractivePDFViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageWidth, setPageWidth] = useState<number>(0);
  const [pageHeight, setPageHeight] = useState<number>(0);
  const [pdfOriginalWidth, setPdfOriginalWidth] = useState<number>(612); // default US Letter
  const [pdfOriginalHeight, setPdfOriginalHeight] = useState<number>(792);
  const [loadError, setLoadError] = useState<string | null>(null);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRef = useRef<HTMLDivElement>(null);

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setLoadError(null);
  }, []);

  const onDocumentLoadError = useCallback((error: Error) => {
    setLoadError(error.message);
  }, []);

  const onPageRenderSuccess = useCallback(() => {
    if (pageRef.current) {
      const pageCanvas = pageRef.current.querySelector('canvas');
      if (pageCanvas) {
        setPageWidth(pageCanvas.width);
        setPageHeight(pageCanvas.height);
      }
    }
  }, []);

  const onPageLoadSuccess = useCallback((page: any) => {
    const viewport = page.getViewport({ scale: 1 });
    setPdfOriginalWidth(viewport.width);
    setPdfOriginalHeight(viewport.height);
  }, []);

  // Draw bounding box highlights on the canvas overlay
  const drawHighlights = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || pageWidth === 0 || pageHeight === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Match canvas resolution to page
    canvas.width = pageWidth;
    canvas.height = pageHeight;

    // Clear previous drawings
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const scaleX = pageWidth / pdfOriginalWidth;
    const scaleY = pageHeight / pdfOriginalHeight;

    // Filter entities for the current page (0-indexed in bounding_box_coords)
    const pageEntities = entities.filter(
      (e) => e.bounding_box_coords && e.bounding_box_coords.page === currentPage - 1
    );

    for (const entity of pageEntities) {
      if (!entity.bounding_box_coords) continue;

      const { x0, y0, x1, y1 } = entity.bounding_box_coords;

      // Scale coordinates from PDF space to rendered space
      const scaledX0 = x0 * scaleX;
      const scaledY0 = y0 * scaleY;
      const scaledX1 = x1 * scaleX;
      const scaledY1 = y1 * scaleY;

      const width = scaledX1 - scaledX0;
      const height = scaledY1 - scaledY0;

      const isActive = String(entity.id) === activeFieldId;

      // Draw fill
      if (isActive) {
        ctx.fillStyle = 'rgba(234, 179, 8, 0.4)'; // yellow highlight
      } else {
        ctx.fillStyle = 'rgba(59, 130, 246, 0.08)'; // subtle blue
      }
      ctx.fillRect(scaledX0, scaledY0, width, height);

      // Draw border
      ctx.lineWidth = isActive ? 3 : 1.5;
      if (entity.requires_review) {
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.9)'; // red border
      } else {
        ctx.strokeStyle = 'rgba(34, 197, 94, 0.9)'; // green border
      }
      ctx.strokeRect(scaledX0, scaledY0, width, height);
    }
  }, [entities, activeFieldId, currentPage, pageWidth, pageHeight, pdfOriginalWidth, pdfOriginalHeight]);

  // Re-draw whenever dependencies change
  useEffect(() => {
    drawHighlights();
  }, [drawHighlights]);

  // Observe resize to re-draw
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver(() => {
      if (pageRef.current) {
        const pageCanvas = pageRef.current.querySelector('canvas');
        if (pageCanvas) {
          setPageWidth(pageCanvas.width);
          setPageHeight(pageCanvas.height);
        }
      }
    });

    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // Navigate to the page of the active entity
  useEffect(() => {
    if (activeFieldId) {
      const activeEntity = entities.find((e) => String(e.id) === activeFieldId);
      if (activeEntity?.bounding_box_coords) {
        const targetPage = activeEntity.bounding_box_coords.page + 1;
        if (targetPage !== currentPage && targetPage >= 1 && targetPage <= numPages) {
          setCurrentPage(targetPage);
        }
      }
    }
  }, [activeFieldId, entities, numPages, currentPage]);

  // Container width for responsive rendering
  const [containerWidth, setContainerWidth] = useState<number>(600);

  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.clientWidth - 32); // padding
      }
    };
    updateWidth();
    window.addEventListener('resize', updateWidth);
    return () => window.removeEventListener('resize', updateWidth);
  }, []);

  return (
    <div ref={containerRef} className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800 text-white rounded-t-lg shrink-0">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage <= 1}
            className="px-2.5 py-1 rounded bg-slate-600 hover:bg-slate-500 disabled:opacity-40 disabled:cursor-not-allowed text-sm font-medium transition-colors"
          >
            ◀
          </button>
          <span className="text-sm font-medium tabular-nums">
            {currentPage} / {numPages || '—'}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(numPages, p + 1))}
            disabled={currentPage >= numPages}
            className="px-2.5 py-1 rounded bg-slate-600 hover:bg-slate-500 disabled:opacity-40 disabled:cursor-not-allowed text-sm font-medium transition-colors"
          >
            ▶
          </button>
        </div>
        <span className="text-xs text-slate-300">
          {entities.filter((e) => e.bounding_box_coords?.page === currentPage - 1).length} highlights on page
        </span>
      </div>

      {/* PDF + Canvas Overlay */}
      <div className="flex-1 overflow-auto bg-slate-100 rounded-b-lg">
        {loadError ? (
          <div className="flex items-center justify-center h-64 text-red-600">
            <div className="text-center">
              <p className="text-lg font-semibold mb-2">Failed to load PDF</p>
              <p className="text-sm text-red-400">{loadError}</p>
            </div>
          </div>
        ) : (
          <div className="flex justify-center py-4">
            <Document
              file={pdfUrl}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              loading={
                <div className="flex items-center justify-center h-64">
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-8 h-8 border-4 border-slate-300 border-t-blue-600 rounded-full animate-spin" />
                    <p className="text-sm text-slate-500">Loading PDF…</p>
                  </div>
                </div>
              }
            >
              <div ref={pageRef} className="relative inline-block shadow-lg">
                <Page
                  pageNumber={currentPage}
                  width={Math.min(containerWidth, 800)}
                  onRenderSuccess={onPageRenderSuccess}
                  onLoadSuccess={onPageLoadSuccess}
                  renderTextLayer={true}
                  renderAnnotationLayer={true}
                />
                {/* Canvas overlay for bounding box highlights */}
                <canvas
                  ref={canvasRef}
                  className="absolute top-0 left-0 w-full h-full pointer-events-none"
                  style={{ width: '100%', height: '100%' }}
                />
              </div>
            </Document>
          </div>
        )}
      </div>
    </div>
  );
}
