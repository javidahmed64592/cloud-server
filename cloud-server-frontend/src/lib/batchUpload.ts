import { uploadFile } from "@/lib/api";
import type { FileMetadata } from "@/lib/types";

export interface UploadItem {
  file: File;
  parentDir: string;
}

export interface BatchResult {
  uploaded: number;
  skipped: number; // already existed on the server
  failed: { item: UploadItem; error: string }[];
}

const HTTP_CONFLICT = 409;

/**
 * Upload every item, continuing past failures. Files that already exist
 * (HTTP 409) count as skipped, so re-uploading a folder is safe.
 */
export async function uploadBatch(
  items: UploadItem[],
  onUploaded: (metadata: FileMetadata) => void,
  onProgress: (done: number, total: number) => void
): Promise<BatchResult> {
  const result: BatchResult = { uploaded: 0, skipped: 0, failed: [] };
  onProgress(0, items.length);
  for (let i = 0; i < items.length; i++) {
    const item = items[i]!;
    try {
      onUploaded(await uploadFile(item.file, item.parentDir));
      result.uploaded++;
    } catch (err) {
      if ((err as { status?: number }).status === HTTP_CONFLICT) {
        result.skipped++;
      } else {
        result.failed.push({ item, error: String(err) });
      }
    }
    onProgress(i + 1, items.length);
  }
  return result;
}

export function summarizeBatch(r: BatchResult): string | null {
  if (r.failed.length === 0) return null;
  return `${r.failed.length} file(s) failed (${r.uploaded} uploaded, ${r.skipped} already existed). ${r.failed[0]!.error}`;
}
