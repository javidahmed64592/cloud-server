"use client";

import Image from "next/image";

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
  const isMediaFile =
    file.mime_type.startsWith("image/") || file.mime_type.startsWith("video/");

  return (
    <button
      type="button"
      onClick={onOpen}
      className="group relative flex flex-col items-center gap-2 rounded-lg p-3 transition-colors duration-150 hover:bg-background-secondary focus:outline-none focus-visible:ring-2 focus-visible:ring-border-accent w-full"
    >
      {/* Thumbnail/Icon area */}
      <div className="relative flex h-36 w-36 items-center justify-center rounded bg-background-tertiary">
        {thumbnail ? (
          <Image
            src={thumbnail}
            alt={file.filename}
            width={144}
            height={144}
            className="h-full w-full rounded object-cover"
            unoptimized
          />
        ) : isMediaFile ? (
          // Thumbnail loading skeleton
          <div className="h-full w-full animate-pulse rounded bg-background-tertiary" />
        ) : (
          // Placeholder icon for non-media files
          <span className="text-text-muted opacity-50">
            <FileTypeIcon mimeType={file.mime_type} />
          </span>
        )}

        {/* Hover action overlay */}
        <div className="absolute inset-0 flex items-center justify-center gap-1 rounded bg-black/70 opacity-0 transition-opacity duration-150 group-hover:opacity-100">
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

      {/* File info */}
      <div className="w-full text-center">
        <p
          className="truncate text-sm text-text-primary px-1"
          title={file.filename}
        >
          {file.filename}
        </p>
        <p className="text-xs text-text-muted">{formatFileSize(file.size)}</p>
      </div>
    </button>
  );
}
