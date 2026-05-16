"use client";

import { useEffect, useState } from "react";
import type { FileMetadata } from "@/lib/types";

interface MoveDialogProps {
  file: FileMetadata;
  onConfirm: (filename: string, parentDirectory: string) => Promise<void>;
  onClose: () => void;
}

export default function MoveDialog({
  file,
  onConfirm,
  onClose,
}: MoveDialogProps) {
  const [filename, setFilename] = useState(file.filename);
  const [parentDirectory, setParentDirectory] = useState(file.parent_directory);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!filename.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const dir = parentDirectory.trim() || ".";
      await onConfirm(filename.trim(), dir);
      onClose();
    } catch (err) {
      setError(String(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm rounded-xl border border-border bg-background-secondary p-5 shadow-terminal"
        onClick={e => e.stopPropagation()}
      >
        <h3 className="mb-4 text-sm font-semibold text-text-primary">
          Rename / Move
        </h3>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <div>
            <label className="mb-1 block text-xs text-text-muted">
              Filename
            </label>
            <input
              type="text"
              value={filename}
              onChange={e => setFilename(e.target.value)}
              className="w-full rounded-md border border-border bg-background-tertiary px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-border-accent focus:outline-none"
              autoFocus
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-text-muted">
              Directory
            </label>
            <input
              type="text"
              value={parentDirectory}
              onChange={e => setParentDirectory(e.target.value)}
              placeholder="."
              className="w-full rounded-md border border-border bg-background-tertiary px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-border-accent focus:outline-none"
            />
          </div>
          {error && <p className="text-xs text-neon-red">{error}</p>}
          <div className="mt-1 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md px-3 py-1.5 text-xs text-text-secondary transition-colors hover:text-text-primary"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !filename.trim()}
              className="rounded-md bg-border-accent px-3 py-1.5 text-xs text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {isLoading ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
