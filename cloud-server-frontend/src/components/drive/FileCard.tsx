"use client";

import type { FileMetadata } from "@/lib/types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export function canViewFile(mimeType: string): boolean {
  return (
    mimeType.startsWith("image/") ||
    mimeType.startsWith("video/") ||
    mimeType.startsWith("text/")
  );
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1_073_741_824) return `${(bytes / 1_048_576).toFixed(1)} MB`;
  return `${(bytes / 1_073_741_824).toFixed(1)} GB`;
}

// ---------------------------------------------------------------------------
// File type icon
// ---------------------------------------------------------------------------

function FileTypeIcon({ mimeType }: { mimeType: string }) {
  if (mimeType.startsWith("image/")) {
    return (
      <svg
        className="h-10 w-10"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
      >
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <circle cx="8.5" cy="8.5" r="1.5" fill="currentColor" stroke="none" />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M21 15l-5-5L5 21"
        />
      </svg>
    );
  }
  if (mimeType.startsWith("video/")) {
    return (
      <svg
        className="h-10 w-10"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
      >
        <rect x="2" y="6" width="15" height="12" rx="2" />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M17 10l5-2v8l-5-2"
        />
      </svg>
    );
  }
  if (mimeType.startsWith("text/")) {
    return (
      <svg
        className="h-10 w-10"
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
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M14 2v6h6M16 13H8M16 17H8M10 9H8"
        />
      </svg>
    );
  }
  return (
    <svg
      className="h-10 w-10"
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
  );
}

// ---------------------------------------------------------------------------
// Action icons
// ---------------------------------------------------------------------------

function EyeIcon() {
  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"
      />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function MoveIcon() {
  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
      />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
      />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// FileCard
// ---------------------------------------------------------------------------

interface FileCardProps {
  file: FileMetadata;
  thumbnail?: string | undefined;
  onOpen: () => void;
  onMove: () => void;
  onDelete: () => void;
}

export default function FileCard({
  file,
  thumbnail,
  onOpen,
  onMove,
  onDelete,
}: FileCardProps) {
  const viewable = canViewFile(file.mime_type);
  const hasThumbnail =
    file.mime_type.startsWith("image/") || file.mime_type.startsWith("video/");

  return (
    <div className="group relative flex flex-col rounded-lg border border-border bg-background-secondary overflow-hidden transition-colors duration-150 hover:border-border-accent">
      {/* Preview area */}
      <div
        className="relative flex h-28 w-full cursor-pointer items-center justify-center bg-background-tertiary select-none"
        onClick={onOpen}
        title={viewable ? `View ${file.filename}` : `Download ${file.filename}`}
      >
        {thumbnail ? (
          <img
            src={thumbnail}
            alt={file.filename}
            className="h-full w-full object-cover"
          />
        ) : hasThumbnail ? (
          // Thumbnail pending — show skeleton
          <div className="h-full w-full animate-pulse bg-background-tertiary" />
        ) : (
          <span className="text-text-muted opacity-50">
            <FileTypeIcon mimeType={file.mime_type} />
          </span>
        )}

        {/* Hover action overlay */}
        <div className="absolute inset-0 flex items-center justify-center gap-1.5 bg-black/65 opacity-0 transition-opacity duration-150 group-hover:opacity-100">
          {viewable && (
            <button
              type="button"
              onClick={e => {
                e.stopPropagation();
                onOpen();
              }}
              className="rounded p-1.5 bg-white/10 text-white hover:bg-border-accent transition-colors"
              title="View"
            >
              <EyeIcon />
            </button>
          )}
          <button
            type="button"
            onClick={e => {
              e.stopPropagation();
              onMove();
            }}
            className="rounded p-1.5 bg-white/10 text-white hover:bg-white/25 transition-colors"
            title="Rename / Move"
          >
            <MoveIcon />
          </button>
          <button
            type="button"
            onClick={e => {
              e.stopPropagation();
              onDelete();
            }}
            className="rounded p-1.5 bg-white/10 text-neon-red hover:bg-neon-red hover:text-white transition-colors"
            title="Delete"
          >
            <TrashIcon />
          </button>
        </div>
      </div>

      {/* Info */}
      <div className="px-2 py-1.5">
        <p
          className="truncate text-xs font-medium text-text-primary"
          title={file.filename}
        >
          {file.filename}
        </p>
        <p className="text-xs text-text-muted">{formatFileSize(file.size)}</p>
      </div>
    </div>
  );
}
