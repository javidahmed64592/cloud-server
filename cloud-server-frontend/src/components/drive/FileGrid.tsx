"use client";

import FileCard from "@/components/drive/FileCard";
import FolderCard from "@/components/drive/FolderCard";
import type { FileMetadata } from "@/lib/types";

interface FileGridProps {
  folders: string[];
  files: FileMetadata[];
  thumbnails: Record<number, string>;
  onFolderClick: (name: string) => void;
  onFileOpen: (file: FileMetadata) => void;
  onFileMove: (file: FileMetadata) => void;
  onFileDelete: (file: FileMetadata) => void;
}

export default function FileGrid({
  folders,
  files,
  thumbnails,
  onFolderClick,
  onFileOpen,
  onFileMove,
  onFileDelete,
}: FileGridProps) {
  if (folders.length === 0 && files.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-text-muted">
        This folder is empty
      </div>
    );
  }

  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-3">
      {folders.map(name => (
        <FolderCard
          key={name}
          name={name}
          onClick={() => onFolderClick(name)}
        />
      ))}
      {files.map(file => (
        <FileCard
          key={file.id}
          file={file}
          thumbnail={thumbnails[file.id]}
          onOpen={() => onFileOpen(file)}
          onMove={() => onFileMove(file)}
          onDelete={() => onFileDelete(file)}
        />
      ))}
    </div>
  );
}
