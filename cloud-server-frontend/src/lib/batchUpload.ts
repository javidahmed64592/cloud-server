import { uploadFile } from "@/lib/api";
import type { FileMetadata } from "@/lib/types";

export interface UploadItem {
  file: File;
  parentDir: string;
}

export type UploadStatus =
  | "queued"
  | "uploading"
  | "done"
  | "skipped" // already existed on the server
  | "failed";

export interface UploadEntry {
  name: string;
  size: number;
  status: UploadStatus;
  fraction: number; // 0..1 of this file's bytes sent
}

export interface BatchResult {
  uploaded: number;
  skipped: number;
  failed: { item: UploadItem; error: string }[];
}

export interface BatchProgress {
  total: number;
  finished: number; // done + skipped + failed
  percent: number; // 0..100, weighted by file size
  active: UploadEntry[];
}

const HTTP_CONFLICT = 409;
export const UPLOAD_CONCURRENCY = 4;

export function computeProgress(
  entries: readonly UploadEntry[]
): BatchProgress {
  let finished = 0;
  let bytes = 0;
  let sent = 0;
  const active: UploadEntry[] = [];
  for (const e of entries) {
    const isFinished =
      e.status === "done" || e.status === "skipped" || e.status === "failed";
    if (isFinished) finished++;
    if (e.status === "uploading") active.push({ ...e });
    bytes += e.size;
    sent += e.size * (isFinished ? 1 : e.fraction);
  }
  // Fall back to file counts when every file is empty
  const ratio =
    bytes > 0 ? sent / bytes : entries.length ? finished / entries.length : 0;
  return {
    total: entries.length,
    finished,
    percent: Math.round(ratio * 100),
    active,
  };
}

/**
 * Upload items with limited concurrency, continuing past failures. Files that
 * already exist (HTTP 409) count as skipped, so re-uploading a folder is safe.
 *
 * `onUpdate` receives the same (mutated in place) entries array on every
 * change and may be called very frequently; throttle on the receiving side.
 */
export async function uploadBatch(
  items: UploadItem[],
  onUploaded: (metadata: FileMetadata) => void,
  onUpdate: (entries: readonly UploadEntry[]) => void,
  concurrency: number = UPLOAD_CONCURRENCY
): Promise<BatchResult> {
  const result: BatchResult = { uploaded: 0, skipped: 0, failed: [] };
  const entries: UploadEntry[] = items.map(({ file }) => ({
    name: file.name,
    size: file.size,
    status: "queued",
    fraction: 0,
  }));
  onUpdate(entries);

  let next = 0;
  const worker = async (): Promise<void> => {
    while (next < items.length) {
      const index = next++;
      const item = items[index]!;
      const entry = entries[index]!;
      entry.status = "uploading";
      onUpdate(entries);
      try {
        const metadata = await uploadFile(
          item.file,
          item.parentDir,
          fraction => {
            entry.fraction = fraction;
            onUpdate(entries);
          }
        );
        entry.status = "done";
        result.uploaded++;
        onUploaded(metadata);
      } catch (err) {
        if ((err as { status?: number }).status === HTTP_CONFLICT) {
          entry.status = "skipped";
          result.skipped++;
        } else {
          entry.status = "failed";
          result.failed.push({ item, error: String(err) });
        }
      }
      onUpdate(entries);
    }
  };

  await Promise.all(
    Array.from({ length: Math.min(concurrency, items.length) }, worker)
  );
  return result;
}

export function summarizeBatch(r: BatchResult): string | null {
  if (r.failed.length === 0) return null;
  return `${r.failed.length} file(s) failed (${r.uploaded} uploaded, ${r.skipped} already existed). ${r.failed[0]!.error}`;
}
