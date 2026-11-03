import { useCallback, useEffect, useRef, useState } from "react";

import {
  computeProgress,
  uploadBatch,
  type BatchProgress,
  type BatchResult,
  type UploadEntry,
  type UploadItem,
} from "@/lib/batchUpload";
import type { FileMetadata } from "@/lib/types";

const RENDER_INTERVAL_MS = 100;

/** Runs batch uploads and exposes throttled progress (null when idle). */
export function useBatchUpload(onUploaded: (metadata: FileMetadata) => void): {
  progress: BatchProgress | null;
  run: (items: UploadItem[]) => Promise<BatchResult>;
} {
  const [progress, setProgress] = useState<BatchProgress | null>(null);
  const latest = useRef<readonly UploadEntry[]>([]);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onUploadedRef = useRef(onUploaded);
  useEffect(() => {
    onUploadedRef.current = onUploaded;
  }, [onUploaded]);

  const clearTimer = () => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
  };

  useEffect(() => clearTimer, []);

  const run = useCallback(async (items: UploadItem[]): Promise<BatchResult> => {
    try {
      return await uploadBatch(
        items,
        metadata => onUploadedRef.current(metadata),
        entries => {
          const isFirst = latest.current !== entries;
          latest.current = entries;
          if (isFirst) {
            setProgress(computeProgress(entries));
          } else if (!timer.current) {
            timer.current = setTimeout(() => {
              timer.current = null;
              setProgress(computeProgress(latest.current));
            }, RENDER_INTERVAL_MS);
          }
        }
      );
    } finally {
      clearTimer();
      latest.current = [];
      setProgress(null);
    }
  }, []);

  return { progress, run };
}
