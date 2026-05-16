"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import Breadcrumb from "@/components/drive/Breadcrumb";
import { canViewFile } from "@/components/drive/FileCard";
import FileGrid from "@/components/drive/FileGrid";
import FileViewer from "@/components/drive/FileViewer";
import MoveDialog from "@/components/drive/MoveDialog";
import UploadButton from "@/components/drive/UploadButton";
import {
  deleteFile as apiDeleteFile,
  getFileBlob,
  getThumbnailBlob,
  listFiles,
  updateFileMetadata,
} from "@/lib/api";
import type { FileMetadata } from "@/lib/types";

// ---------------------------------------------------------------------------
// Directory helpers
// ---------------------------------------------------------------------------

function getFilesInDirectory(
  files: FileMetadata[],
  path: string
): FileMetadata[] {
  return files.filter(f => f.parent_directory === path);
}

function getSubfolders(files: FileMetadata[], currentPath: string): string[] {
  const subfolders = new Set<string>();
  for (const file of files) {
    const dir = file.parent_directory;
    if (dir === currentPath) continue;
    if (currentPath === ".") {
      // Any dir that isn't root is a (possibly nested) subfolder; take the first component
      if (dir !== ".") subfolders.add(dir.split("/")[0] ?? dir);
    } else {
      const prefix = `${currentPath}/`;
      if (dir.startsWith(prefix)) {
        const first = dir.slice(prefix.length).split("/")[0];
        if (first) subfolders.add(first);
      }
    }
  }
  return Array.from(subfolders).sort();
}

// ---------------------------------------------------------------------------
// DrivePage
// ---------------------------------------------------------------------------

export default function DrivePage() {
  // --- All file metadata (single source of truth, fetched once on mount) ---
  const [allFiles, setAllFiles] = useState<FileMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // --- Navigation ---
  const [currentPath, setCurrentPath] = useState(".");

  // --- Thumbnail cache (blob URLs keyed by file ID) ---
  const thumbnailCacheRef = useRef<Record<number, string>>({});
  const thumbnailFetchingRef = useRef<Set<number>>(new Set());
  const [thumbnails, setThumbnails] = useState<Record<number, string>>({});

  // --- File viewer ---
  const [viewerFile, setViewerFile] = useState<FileMetadata | null>(null);
  const [viewerBlobUrl, setViewerBlobUrl] = useState<string | null>(null);
  const [viewerTextContent, setViewerTextContent] = useState<string | null>(
    null
  );
  const [isViewerLoading, setIsViewerLoading] = useState(false);

  // --- Move dialog ---
  const [moveDialogFile, setMoveDialogFile] = useState<FileMetadata | null>(
    null
  );

  // --- Delete confirmation ---
  const [deleteTarget, setDeleteTarget] = useState<FileMetadata | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // ---------------------------------------------------------------------------
  // Fetch all file metadata on mount
  // ---------------------------------------------------------------------------
  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    listFiles()
      .then(files => {
        if (!cancelled) setAllFiles(files);
      })
      .catch(err => {
        if (!cancelled) setError(String(err));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Revoke all cached thumbnail blob URLs on unmount
  useEffect(() => {
    const cache = thumbnailCacheRef.current;
    return () => {
      Object.values(cache).forEach(url => URL.revokeObjectURL(url));
    };
  }, []);

  // ---------------------------------------------------------------------------
  // Fetch thumbnails for files in the current directory (whenever path or
  // allFiles change — e.g. after upload). Already-cached entries are skipped.
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const currentFiles = getFilesInDirectory(allFiles, currentPath);
    for (const file of currentFiles) {
      const needsThumbnail =
        file.mime_type.startsWith("image/") ||
        file.mime_type.startsWith("video/");
      if (!needsThumbnail) continue;
      if (
        thumbnailCacheRef.current[file.id] !== undefined ||
        thumbnailFetchingRef.current.has(file.id)
      )
        continue;

      thumbnailFetchingRef.current.add(file.id);
      getThumbnailBlob(file.id)
        .then(url => {
          thumbnailCacheRef.current[file.id] = url;
          setThumbnails(prev => ({ ...prev, [file.id]: url }));
        })
        .catch(() => {
          // Thumbnail may not be available (e.g. generation failed); ignore silently
        })
        .finally(() => {
          thumbnailFetchingRef.current.delete(file.id);
        });
    }
  }, [currentPath, allFiles]);

  // ---------------------------------------------------------------------------
  // Navigation
  // ---------------------------------------------------------------------------
  const handleNavigateFolder = useCallback((folderName: string) => {
    setCurrentPath(prev =>
      prev === "." ? folderName : `${prev}/${folderName}`
    );
  }, []);

  const handleBreadcrumbNavigate = useCallback((path: string) => {
    setCurrentPath(path);
  }, []);

  // ---------------------------------------------------------------------------
  // Open / view / download a file (fetch on demand)
  // ---------------------------------------------------------------------------
  const handleOpenFile = useCallback(async (file: FileMetadata) => {
    setIsViewerLoading(true);
    setError(null);
    try {
      const blobUrl = await getFileBlob(file.id);

      if (!canViewFile(file.mime_type)) {
        // Non-viewable file — trigger browser download then release the URL
        const a = document.createElement("a");
        a.href = blobUrl;
        a.download = file.filename;
        a.click();
        URL.revokeObjectURL(blobUrl);
        setIsViewerLoading(false);
        return;
      }

      let textContent: string | null = null;
      if (file.mime_type.startsWith("text/")) {
        try {
          const resp = await fetch(blobUrl);
          textContent = await resp.text();
        } catch (fetchErr) {
          console.error("Failed to read text content:", fetchErr);
          textContent = `Error loading text content: ${String(fetchErr)}`;
        }
      }

      setViewerFile(file);
      setViewerBlobUrl(blobUrl);
      setViewerTextContent(textContent);
    } catch (err) {
      setError(`Failed to open file: ${String(err)}`);
    } finally {
      setIsViewerLoading(false);
    }
  }, []);

  const handleCloseViewer = useCallback(() => {
    if (viewerBlobUrl) URL.revokeObjectURL(viewerBlobUrl);
    setViewerFile(null);
    setViewerBlobUrl(null);
    setViewerTextContent(null);
  }, [viewerBlobUrl]);

  // ---------------------------------------------------------------------------
  // Upload — add new entry to cache without re-fetching everything
  // ---------------------------------------------------------------------------
  const handleUpload = useCallback((newFile: FileMetadata) => {
    setAllFiles(prev => [...prev, newFile]);
  }, []);

  // ---------------------------------------------------------------------------
  // Delete — remove from cache, revoke thumbnail blob URL
  // ---------------------------------------------------------------------------
  const handleDeleteConfirm = useCallback(async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await apiDeleteFile(deleteTarget.id);
      const id = deleteTarget.id;
      setAllFiles(prev => prev.filter(f => f.id !== id));
      if (thumbnailCacheRef.current[id]) {
        URL.revokeObjectURL(thumbnailCacheRef.current[id]);
        delete thumbnailCacheRef.current[id];
        setThumbnails(prev => {
          const next = { ...prev };
          delete next[id];
          return next;
        });
      }
      setDeleteTarget(null);
    } catch (err) {
      setError(String(err));
    } finally {
      setIsDeleting(false);
    }
  }, [deleteTarget]);

  // ---------------------------------------------------------------------------
  // Move / rename — update the cached entry in-place
  // ---------------------------------------------------------------------------
  const handleMove = useCallback(
    async (filename: string, parentDirectory: string) => {
      if (!moveDialogFile) return;
      const updated = await updateFileMetadata(moveDialogFile.id, {
        filename,
        parentDirectory,
      });
      setAllFiles(prev => prev.map(f => (f.id === updated.id ? updated : f)));
    },
    [moveDialogFile]
  );

  // ---------------------------------------------------------------------------
  // Derived state
  // ---------------------------------------------------------------------------
  const currentFiles = getFilesInDirectory(allFiles, currentPath);
  const currentFolders = getSubfolders(allFiles, currentPath);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-text-muted">
        Loading…
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Top bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Breadcrumb path={currentPath} onNavigate={handleBreadcrumbNavigate} />
        <div className="flex items-center gap-3">
          {isViewerLoading && (
            <span className="text-xs text-text-muted">Opening…</span>
          )}
          <UploadButton currentPath={currentPath} onUpload={handleUpload} />
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center justify-between rounded-lg border border-neon-red/30 bg-neon-red/10 px-3 py-2 text-xs text-neon-red">
          <span>{error}</span>
          <button
            type="button"
            onClick={() => setError(null)}
            className="ml-2 opacity-70 hover:opacity-100"
          >
            ✕
          </button>
        </div>
      )}

      {/* File / folder grid */}
      <FileGrid
        folders={currentFolders}
        files={currentFiles}
        thumbnails={thumbnails}
        onFolderClick={handleNavigateFolder}
        onFileOpen={handleOpenFile}
        onFileMove={setMoveDialogFile}
        onFileDelete={setDeleteTarget}
      />

      {/* File viewer modal */}
      {viewerFile && viewerBlobUrl && (
        <FileViewer
          file={viewerFile}
          blobUrl={viewerBlobUrl}
          textContent={viewerTextContent}
          onClose={handleCloseViewer}
        />
      )}

      {/* Move / rename dialog */}
      {moveDialogFile && (
        <MoveDialog
          file={moveDialogFile}
          onConfirm={handleMove}
          onClose={() => setMoveDialogFile(null)}
        />
      )}

      {/* Delete confirmation dialog */}
      {deleteTarget && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
          onClick={() => setDeleteTarget(null)}
        >
          <div
            className="w-full max-w-xs rounded-xl border border-border bg-background-secondary p-5 shadow-terminal"
            onClick={e => e.stopPropagation()}
          >
            <h3 className="mb-1 text-sm font-semibold text-text-primary">
              Delete file?
            </h3>
            <p
              className="mb-4 truncate text-xs text-text-muted"
              title={deleteTarget.filename}
            >
              {deleteTarget.filename}
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setDeleteTarget(null)}
                className="rounded-md px-3 py-1.5 text-xs text-text-secondary transition-colors hover:text-text-primary"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteConfirm}
                disabled={isDeleting}
                className="rounded-md bg-neon-red px-3 py-1.5 text-xs text-white transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {isDeleting ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
