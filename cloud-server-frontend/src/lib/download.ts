import { getFolderDownloadUrl } from "@/lib/api";

export interface DownloadProgress {
  phase: "preparing" | "downloading";
  received: number;
  total: number | null; // null when the server sent no Content-Length
}

interface WritableFileHandle {
  createWritable: () => Promise<WritableStream<Uint8Array>>;
}

type SaveFilePicker = (options: {
  suggestedName: string;
  types?: { description: string; accept: Record<string, string[]> }[];
}) => Promise<WritableFileHandle>;

const getSaveFilePicker = (): SaveFilePicker | undefined =>
  (window as unknown as { showSaveFilePicker?: SaveFilePicker })
    .showSaveFilePicker;

export const folderZipName = (path: string): string =>
  `${path === "." ? "storage" : (path.split("/").pop() ?? "folder")}.zip`;

function startNativeDownload(url: string): void {
  const a = document.createElement("a");
  a.href = url;
  a.download = "";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

/**
 * Download a folder as a zip. Where the browser supports the File System
 * Access API (Chromium), the zip is streamed to the chosen file with live
 * progress and without holding it in memory. Elsewhere this falls back to a
 * normal browser download, whose progress the browser shows itself.
 *
 * Resolves to false if the user cancelled the save dialog.
 */
export async function downloadFolder(
  path: string,
  onProgress: (progress: DownloadProgress) => void
): Promise<boolean> {
  const url = getFolderDownloadUrl(path);
  const picker = getSaveFilePicker();
  if (!picker) {
    startNativeDownload(url);
    return true;
  }

  // Must be called straight from the click, before any await on the network
  let handle: WritableFileHandle;
  try {
    handle = await picker({
      suggestedName: folderZipName(path),
      types: [
        { description: "Zip archive", accept: { "application/zip": [".zip"] } },
      ],
    });
  } catch (err) {
    if ((err as Error).name === "AbortError") return false;
    throw err;
  }

  const writer = (await handle.createWritable()).getWriter();
  try {
    // The server builds the whole archive before sending the first byte
    onProgress({ phase: "preparing", received: 0, total: null });
    const response = await fetch(url);
    if (!response.ok || !response.body) {
      let detail = `${response.status} ${response.statusText}`;
      try {
        detail =
          ((await response.json()) as { detail?: string }).detail ?? detail;
      } catch {
        // not JSON; keep the status line
      }
      throw new Error(`Download failed: ${detail}`);
    }
    const length = Number(response.headers.get("Content-Length"));
    const total = length > 0 ? length : null;
    let received = 0;
    const reader = response.body.getReader();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      await writer.write(value);
      received += value.length;
      onProgress({ phase: "downloading", received, total });
    }
    await writer.close();
    return true;
  } catch (err) {
    await writer.abort().catch(() => undefined);
    throw err;
  }
}
