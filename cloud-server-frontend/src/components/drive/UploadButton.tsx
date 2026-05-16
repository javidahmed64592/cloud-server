"use client";

import { useRef, useState } from "react";
import { uploadFile } from "@/lib/api";
import type { FileMetadata } from "@/lib/types";

interface UploadButtonProps {
  currentPath: string;
  onUpload: (file: FileMetadata) => void;
}

export default function UploadButton({
  currentPath,
  onUpload,
}: UploadButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setIsUploading(true);
    setError(null);
    try {
      for (const file of Array.from(files)) {
        const metadata = await uploadFile(file, currentPath);
        onUpload(metadata);
      }
      // Clear error on success
      setError(null);
    } catch (err) {
      const errorMsg = String(err);
      console.error("Upload failed:", errorMsg);
      setError(errorMsg);
      // Keep error visible for 5 seconds
      setTimeout(() => setError(null), 5000);
    } finally {
      setIsUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div className="flex items-center gap-2">
      <input
        ref={inputRef}
        type="file"
        multiple
        className="hidden"
        onChange={e => handleFiles(e.target.files)}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={isUploading}
        className="flex items-center gap-1.5 rounded-md bg-border-accent px-3 py-1.5 text-xs font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        {isUploading ? (
          "Uploading…"
        ) : (
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
      {error && (
        <span className="max-w-xs truncate text-xs text-neon-red" title={error}>
          {error}
        </span>
      )}
    </div>
  );
}
