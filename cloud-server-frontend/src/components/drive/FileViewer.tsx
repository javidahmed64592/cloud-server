"use client";

import Image from "next/image";
import { useEffect } from "react";

import type { FileMetadata } from "@/lib/types";

interface FileViewerProps {
  file: FileMetadata;
  blobUrl: string;
  onClose: () => void;
  onPrevious?: () => void;
  onNext?: () => void;
}

export default function FileViewer({
  file,
  blobUrl,
  onClose,
  onPrevious,
  onNext,
}: FileViewerProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft" && onPrevious) onPrevious();
      if (e.key === "ArrowRight" && onNext) onNext();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, onPrevious, onNext]);

  const renderContent = () => {
    if (file.mime_type.startsWith("image/")) {
      return (
        <div className="relative max-h-[72vh] max-w-full">
          <Image
            src={blobUrl}
            alt={file.filename}
            width={1920}
            height={1080}
            className="max-h-[72vh] max-w-full rounded object-contain"
            unoptimized
          />
        </div>
      );
    }
    if (file.mime_type.startsWith("video/")) {
      return (
        <video
          src={blobUrl}
          controls
          autoPlay
          className="max-h-[72vh] max-w-full rounded"
          onError={e => {
            // eslint-disable-next-line no-console
            console.error("Video playback error:", e);
          }}
        />
      );
    }
    // Placeholder for other file types
    return (
      <div className="flex flex-col items-center justify-center gap-3 p-8 text-text-muted">
        <svg
          className="h-16 w-16 opacity-50"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"
          />
          <path strokeLinecap="round" strokeLinejoin="round" d="M14 2v6h6" />
        </svg>
        <p className="text-sm">Preview not available for this file type</p>
        <p className="text-xs opacity-70">
          Use the download button to save the file
        </p>
      </div>
    );
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
      onClick={onClose}
    >
      {/* Previous button */}
      {onPrevious && (
        <button
          type="button"
          onClick={e => {
            e.stopPropagation();
            onPrevious();
          }}
          className="absolute left-4 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-3 text-white transition-all hover:bg-black/70 hover:scale-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-border-accent"
          title="Previous (←)"
        >
          <svg
            className="h-6 w-6"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M15 19l-7-7 7-7"
            />
          </svg>
        </button>
      )}

      {/* Next button */}
      {onNext && (
        <button
          type="button"
          onClick={e => {
            e.stopPropagation();
            onNext();
          }}
          className="absolute right-4 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-3 text-white transition-all hover:bg-black/70 hover:scale-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-border-accent"
          title="Next (→)"
        >
          <svg
            className="h-6 w-6"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 5l7 7-7 7"
            />
          </svg>
        </button>
      )}

      <div
        className="flex w-full max-w-4xl flex-col gap-3 rounded-xl border border-border bg-background-secondary p-4 shadow-terminal"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between gap-4">
          <p
            className="truncate text-sm font-medium text-text-primary"
            title={file.filename}
          >
            {file.filename}
          </p>
          <div className="flex shrink-0 items-center gap-2">
            <a
              href={blobUrl}
              download={file.filename}
              className="rounded-md px-3 py-1.5 text-xs bg-background-tertiary text-text-secondary transition-colors hover:text-text-primary"
            >
              Download
            </a>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md px-3 py-1.5 text-xs bg-background-tertiary text-text-secondary transition-colors hover:text-text-primary"
            >
              Close
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex items-center justify-center overflow-hidden">
          {renderContent()}
        </div>
      </div>
    </div>
  );
}
