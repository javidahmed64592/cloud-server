"use client";

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import Breadcrumb from "@/components/drive/Breadcrumb";
import FileGrid from "@/components/drive/FileGrid";
import FileViewer from "@/components/drive/FileViewer";
import FolderDialog from "@/components/drive/FolderDialog";
import MoveDialog from "@/components/drive/MoveDialog";
import UploadButton from "@/components/drive/UploadButton";
import {
  deleteFile as apiDeleteFile,
  deleteFolder as apiDeleteFolder,
  getFileBlob,
  getThumbnailBlob,
  listFiles,
  moveFolder as apiMoveFolder,
  updateFileMetadata,
  uploadFile,
} from "@/lib/api";
import type { FileMetadata } from "@/lib/types";

// ---------------------------------------------------------------------------
// Drag-and-drop folder traversal using the File System API
// ---------------------------------------------------------------------------

async function collectFilesFromEntry(
  entry: FileSystemEntry,
  parentDir: string
): Promise<{ file: File; parentDir: string }[]> {
  if (entry.isFile) {
    const file = await new Promise<File>((resolve, reject) => {
      (entry as FileSystemFileEntry).file(
        f => resolve(f),
        err => reject(err)
      );
    });
    return [{ file, parentDir }];
  }

  const childDir =
    parentDir === "." ? entry.name : `${parentDir}/${entry.name}`;
  const reader = (entry as FileSystemDirectoryEntry).createReader();
  const allEntries: FileSystemEntry[] = [];

  // readEntries returns up to 100 entries per call; loop until the batch is empty
  for (;;) {
    const batch = await new Promise<FileSystemEntry[]>((resolve, reject) => {
      reader.readEntries(
        entries => resolve(entries),
        err => reject(err)
      );
    });
    if (batch.length === 0) break;
    allEntries.push(...batch);
  }

  const nested = await Promise.all(
    allEntries.map(e => collectFilesFromEntry(e, childDir))
  );
  return nested.flat();
}

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
  const [isViewerLoading, setIsViewerLoading] = useState(false);

  // --- Move dialog ---
  const [moveDialogFile, setMoveDialogFile] = useState<FileMetadata | null>(
    null
  );

  // --- Delete confirmation ---
  const [deleteTarget, setDeleteTarget] = useState<FileMetadata | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // --- Folder operations ---
  const [folderDialogPath, setFolderDialogPath] = useState<string | null>(null);
  const [deleteFolderTarget, setDeleteFolderTarget] = useState<string | null>(
    null
  );
  const [isDeletingFolder, setIsDeletingFolder] = useState(false);

  // --- Drag-and-drop ---
  const [isDragging, setIsDragging] = useState(false);
  const [dropProgress, setDropProgress] = useState<{
    done: number;
    total: number;
  } | null>(null);
  const dragCounterRef = useRef(0);

  // ---------------------------------------------------------------------------
  // Derived state (must be before callbacks that use it)
  // ---------------------------------------------------------------------------
  const currentFiles = useMemo(
    () => getFilesInDirectory(allFiles, currentPath),
    [allFiles, currentPath]
  );
  const currentFolders = useMemo(
    () => getSubfolders(allFiles, currentPath),
    [allFiles, currentPath]
  );

  // ---------------------------------------------------------------------------
  // Fetch all file metadata on mount
  // ---------------------------------------------------------------------------
  useEffect(() => {
    let cancelled = false;
    listFiles()
      .then(files => {
        if (!cancelled) {
          setAllFiles(files);
          setIsLoading(false);
        }
      })
      .catch(err => {
        if (!cancelled) {
          setError(String(err));
          setIsLoading(false);
        }
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

      setViewerFile(file);
      setViewerBlobUrl(blobUrl);
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
  }, [viewerBlobUrl]);

  // ---------------------------------------------------------------------------
  // Navigate to previous/next file in viewer
  // ---------------------------------------------------------------------------
  const handleNavigateFile = useCallback(
    (direction: "previous" | "next") => {
      if (!viewerFile) return;
      const idx = currentFiles.findIndex(f => f.id === viewerFile.id);
      if (idx === -1) return;

      const nextIdx =
        direction === "next"
          ? (idx + 1) % currentFiles.length
          : (idx - 1 + currentFiles.length) % currentFiles.length;
      const nextFile = currentFiles[nextIdx];

      if (nextFile) {
        handleCloseViewer();
        handleOpenFile(nextFile);
      }
    },
    [viewerFile, currentFiles, handleOpenFile, handleCloseViewer]
  );

  const handlePrevious = useCallback(
    () => handleNavigateFile("previous"),
    [handleNavigateFile]
  );

  const handleNext = useCallback(
    () => handleNavigateFile("next"),
    [handleNavigateFile]
  );

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
  // Folder operations
  // ---------------------------------------------------------------------------
  const handleFolderMove = useCallback(
    (folderName: string) => {
      const fullPath =
        currentPath === "." ? folderName : `${currentPath}/${folderName}`;
      setFolderDialogPath(fullPath);
    },
    [currentPath]
  );

  const handleFolderMoveConfirm = useCallback(
    async (newName: string, newParent: string) => {
      if (!folderDialogPath) return;
      const newFullPath =
        newParent === "." ? newName : `${newParent}/${newName}`;
      await apiMoveFolder(folderDialogPath, newFullPath);
      setAllFiles(prev =>
        prev.map(f => {
          if (f.parent_directory === folderDialogPath) {
            return { ...f, parent_directory: newFullPath };
          }
          if (f.parent_directory.startsWith(folderDialogPath + "/")) {
            const suffix = f.parent_directory.slice(folderDialogPath.length);
            return { ...f, parent_directory: newFullPath + suffix };
          }
          return f;
        })
      );
    },
    [folderDialogPath]
  );

  const handleFolderDeleteConfirm = useCallback(async () => {
    if (!deleteFolderTarget) return;
    const fullPath =
      currentPath === "."
        ? deleteFolderTarget
        : `${currentPath}/${deleteFolderTarget}`;
    setIsDeletingFolder(true);
    try {
      await apiDeleteFolder(fullPath);
      const idsToRemove = allFiles
        .filter(
          f =>
            f.parent_directory === fullPath ||
            f.parent_directory.startsWith(fullPath + "/")
        )
        .map(f => f.id);
      setAllFiles(prev => prev.filter(f => !idsToRemove.includes(f.id)));
      for (const id of idsToRemove) {
        if (thumbnailCacheRef.current[id]) {
          URL.revokeObjectURL(thumbnailCacheRef.current[id]!);
          delete thumbnailCacheRef.current[id];
        }
      }
      setThumbnails(prev => {
        const next = { ...prev };
        for (const id of idsToRemove) {
          delete next[id];
        }
        return next;
      });
      setDeleteFolderTarget(null);
    } catch (err) {
      setError(String(err));
    } finally {
      setIsDeletingFolder(false);
    }
  }, [deleteFolderTarget, currentPath, allFiles]);

  // ---------------------------------------------------------------------------
  // Drag-and-drop handlers
  // ---------------------------------------------------------------------------
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current++;
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current--;
    if (dragCounterRef.current === 0) setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      dragCounterRef.current = 0;
      setIsDragging(false);

      const items = Array.from(e.dataTransfer.items);
      const allFileItems: { file: File; parentDir: string }[] = [];
      for (const item of items) {
        const entry = item.webkitGetAsEntry();
        if (!entry) continue;
        const collected = await collectFilesFromEntry(entry, currentPath);
        allFileItems.push(...collected);
      }

      if (allFileItems.length === 0) return;

      setDropProgress({ done: 0, total: allFileItems.length });
      try {
        for (let i = 0; i < allFileItems.length; i++) {
          const { file, parentDir } = allFileItems[i]!;
          const metadata = await uploadFile(file, parentDir);
          handleUpload(metadata);
          setDropProgress({ done: i + 1, total: allFileItems.length });
        }
      } catch (err) {
        setError(String(err));
        setTimeout(() => setError(null), 5000);
      } finally {
        setDropProgress(null);
      }
    },
    [currentPath, handleUpload]
  );

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
    <div
      className="relative flex flex-col gap-3"
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {isDragging && (
        <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center rounded-xl border-2 border-dashed border-border-accent bg-background/80 backdrop-blur-sm">
          <div className="text-center">
            <p className="text-sm font-semibold text-border-accent">
              Drop to upload
            </p>
            <p className="mt-1 text-xs text-text-muted">
              Folder structure will be preserved
            </p>
          </div>
        </div>
      )}

      {/* Top bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Breadcrumb path={currentPath} onNavigate={handleBreadcrumbNavigate} />
        <div className="flex items-center gap-3">
          {isViewerLoading && (
            <span className="text-xs text-text-muted">Opening…</span>
          )}
          {dropProgress !== null && (
            <span className="text-xs text-text-muted">
              Uploading {dropProgress.done}/{dropProgress.total}…
            </span>
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
        onFolderMove={handleFolderMove}
        onFolderDelete={setDeleteFolderTarget}
        onFileOpen={handleOpenFile}
        onFileMove={setMoveDialogFile}
        onFileDelete={setDeleteTarget}
      />

      {/* File viewer modal */}
      {viewerFile && viewerBlobUrl && (
        <FileViewer
          file={viewerFile}
          blobUrl={viewerBlobUrl}
          onClose={handleCloseViewer}
          {...(currentFiles.length > 1
            ? { onPrevious: handlePrevious, onNext: handleNext }
            : {})}
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

      {/* Folder rename / move dialog */}
      {folderDialogPath && (
        <FolderDialog
          folderPath={folderDialogPath}
          onConfirm={handleFolderMoveConfirm}
          onClose={() => setFolderDialogPath(null)}
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

      {/* Folder delete confirmation dialog */}
      {deleteFolderTarget && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
          onClick={() => setDeleteFolderTarget(null)}
        >
          <div
            className="w-full max-w-xs rounded-xl border border-border bg-background-secondary p-5 shadow-terminal"
            onClick={e => e.stopPropagation()}
          >
            <h3 className="mb-1 text-sm font-semibold text-text-primary">
              Delete folder?
            </h3>
            <p
              className="mb-1 truncate text-xs text-text-muted"
              title={deleteFolderTarget}
            >
              {deleteFolderTarget}
            </p>
            <p className="mb-4 text-xs text-text-muted">
              All files inside will be permanently deleted.
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setDeleteFolderTarget(null)}
                className="rounded-md px-3 py-1.5 text-xs text-text-secondary transition-colors hover:text-text-primary"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleFolderDeleteConfirm}
                disabled={isDeletingFolder}
                className="rounded-md bg-neon-red px-3 py-1.5 text-xs text-white transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {isDeletingFolder ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
