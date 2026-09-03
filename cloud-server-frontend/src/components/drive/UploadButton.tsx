"use client";

import { useEffect, useRef, useState } from "react";

import { uploadFile } from "@/lib/api";
import type { FileMetadata } from "@/lib/types";

interface UploadButtonProps {
  currentPath: string;
  onUpload: (file: FileMetadata) => void;
}

function joinPath(base: string, relative: string): string {
  if (!relative) return base;
  return base === "." ? relative : `${base}/${relative}`;
}

export default function UploadButton({
  currentPath,
  onUpload,
}: UploadButtonProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const [progress, setProgress] = useState<{
    done: number;
    total: number;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // webkitdirectory is not in React's HTMLInputElement typings
  useEffect(() => {
    folderInputRef.current?.setAttribute("webkitdirectory", "");
  }, []);

  const uploadBatch = async (
    items: { file: File; parentDir: string }[]
  ): Promise<void> => {
    if (items.length === 0) return;
    setProgress({ done: 0, total: items.length });
    setError(null);
    try {
      for (let i = 0; i < items.length; i++) {
        const { file, parentDir } = items[i]!;
        const metadata = await uploadFile(file, parentDir);
        onUpload(metadata);
        setProgress({ done: i + 1, total: items.length });
      }
    } catch (err) {
      const msg = String(err);
      // eslint-disable-next-line no-console
      console.error("Upload failed:", msg);
      setError(msg);
      setTimeout(() => setError(null), 5000);
    } finally {
      setProgress(null);
    }
  };

  const handleFileChange = async (files: FileList | null): Promise<void> => {
    if (!files || files.length === 0) return;
    await uploadBatch(
      Array.from(files).map(file => ({ file, parentDir: currentPath }))
    );
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleFolderChange = async (files: FileList | null): Promise<void> => {
    if (!files || files.length === 0) return;
    await uploadBatch(
      Array.from(files).map(file => {
        const parts = file.webkitRelativePath.split("/");
        parts.pop(); // strip filename, keep directory segments
        return { file, parentDir: joinPath(currentPath, parts.join("/")) };
      })
    );
    if (folderInputRef.current) folderInputRef.current.value = "";
  };

  const isUploading = progress !== null;
  const uploadLabel =
    progress !== null && progress.done > 0
      ? `Uploading ${progress.done}/${progress.total}…`
      : isUploading
        ? "Uploading…"
        : null;

  return (
    <div className="flex items-center gap-2">
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={e => handleFileChange(e.target.files)}
      />
      <input
        ref={folderInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={e => handleFolderChange(e.target.files)}
      />
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        disabled={isUploading}
        className="flex items-center gap-1.5 rounded-md bg-border-accent px-3 py-1.5 text-xs font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        {uploadLabel ?? (
          <>
            <svg
              className="h-3.5 w-3.5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
              />
            </svg>
            Upload
          </>
        )}
      </button>
      <button
        type="button"
        onClick={() => folderInputRef.current?.click()}
        disabled={isUploading}
        className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs font-medium text-text-secondary transition-colors hover:text-text-primary disabled:opacity-50"
      >
        <svg
          className="h-3.5 w-3.5"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"
          />
        </svg>
        Folder
      </button>
      {error && (
        <span className="max-w-xs truncate text-xs text-neon-red" title={error}>
          {error}
        </span>
      )}
    </div>
  );
}
