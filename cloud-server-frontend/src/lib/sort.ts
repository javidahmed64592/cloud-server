import type { FileMetadata } from "@/lib/types";

export type SortKey = "name" | "created";
export type SortDirection = "asc" | "desc";

export interface SortOption {
  key: SortKey;
  direction: SortDirection;
}

export const DEFAULT_SORT: SortOption = { key: "name", direction: "asc" };

const compareNames = (a: string, b: string): number =>
  a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" });

const applyDirection = (result: number, direction: SortDirection): number =>
  direction === "asc" ? result : -result;

export function sortFiles(
  files: FileMetadata[],
  { key, direction }: SortOption
): FileMetadata[] {
  return [...files].sort((a, b) => {
    const byKey =
      key === "name"
        ? compareNames(a.filename, b.filename)
        : a.uploaded_at - b.uploaded_at;
    // Fall back to name so the order is stable when dates tie (e.g. batch uploads)
    return (
      applyDirection(byKey, direction) || compareNames(a.filename, b.filename)
    );
  });
}

/**
 * Folders have no stored creation date, so a folder's date is the earliest
 * upload time of any file inside it (including nested subfolders).
 */
export function getFolderCreatedDates(
  files: FileMetadata[],
  currentPath: string
): Record<string, number> {
  const prefix = currentPath === "." ? "" : `${currentPath}/`;
  const dates: Record<string, number> = {};
  for (const file of files) {
    const dir = file.parent_directory;
    if (!dir.startsWith(prefix) || dir === currentPath) continue;
    const name = dir.slice(prefix.length).split("/")[0];
    if (!name) continue;
    const existing = dates[name];
    if (existing === undefined || file.uploaded_at < existing) {
      dates[name] = file.uploaded_at;
    }
  }
  return dates;
}

export function sortFolders(
  folders: string[],
  createdDates: Record<string, number>,
  { key, direction }: SortOption
): string[] {
  return [...folders].sort((a, b) => {
    const byKey =
      key === "name"
        ? compareNames(a, b)
        : (createdDates[a] ?? 0) - (createdDates[b] ?? 0);
    return applyDirection(byKey, direction) || compareNames(a, b);
  });
}
