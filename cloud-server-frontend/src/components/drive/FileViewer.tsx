"use client";

import { useEffect } from "react";
import type { FileMetadata } from "@/lib/types";

interface FileViewerProps {
  file: FileMetadata;
  blobUrl: string;
  textContent: string | null;
  onClose: () => void;
}

export default function FileViewer({
  file,
  blobUrl,
  textContent,
  onClose,
}: FileViewerProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const renderContent = () => {
    if (file.mime_type.startsWith("image/")) {
      return (
        <img
          src={blobUrl}
          alt={file.filename}
          className="max-h-[72vh] max-w-full rounded object-contain"
        />
      );
    }
    if (file.mime_type.startsWith("video/")) {
      return (
        // eslint-disable-next-line jsx-a11y/media-has-caption
        <video
          src={blobUrl}
          controls
          autoPlay
          className="max-h-[72vh] max-w-full rounded"
          onError={e => console.error("Video playback error:", e)}
        />
      );
    }
    if (file.mime_type.startsWith("text/")) {
      return (
        <pre className="max-h-[72vh] w-full overflow-auto whitespace-pre-wrap rounded bg-background-tertiary p-4 text-sm text-text-secondary font-mono leading-relaxed">
          {textContent || "Loading..."}
        </pre>
      );
    }
    return null;
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
      onClick={onClose}
    >
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
