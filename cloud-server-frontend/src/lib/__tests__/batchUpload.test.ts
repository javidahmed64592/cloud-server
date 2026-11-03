import { uploadFile } from "@/lib/api";
import {
  computeProgress,
  uploadBatch,
  type UploadEntry,
  type UploadItem,
} from "@/lib/batchUpload";
import type { FileMetadata } from "@/lib/types";

jest.mock("@/lib/api", () => ({ uploadFile: jest.fn() }));
const mockUpload = uploadFile as jest.MockedFunction<typeof uploadFile>;

const item = (name: string, size = 10): UploadItem => ({
  file: new File(["x".repeat(size)], name),
  parentDir: ".",
});
const meta = (name: string): FileMetadata => ({
  id: 1,
  filename: name,
  parent_directory: ".",
  mime_type: "text/plain",
  size: 1,
  uploaded_at: 0,
  updated_at: 0,
});

describe("uploadBatch", () => {
  beforeEach(() => jest.clearAllMocks());

  it("runs uploads concurrently up to the limit", async () => {
    let inFlight = 0;
    let peak = 0;
    mockUpload.mockImplementation(async file => {
      inFlight++;
      peak = Math.max(peak, inFlight);
      await new Promise(r => setTimeout(r, 5));
      inFlight--;
      return meta(file.name);
    });
    const items = Array.from({ length: 10 }, (_, i) => item(`f${i}`));

    const result = await uploadBatch(items, jest.fn(), jest.fn(), 3);

    expect(result.uploaded).toBe(10);
    expect(peak).toBe(3);
  });

  it("skips existing files, records failures and keeps going", async () => {
    mockUpload.mockImplementation(async file => {
      if (file.name === "exists") {
        throw Object.assign(new Error("exists"), { status: 409 });
      }
      if (file.name === "bad") throw new Error("boom");
      return meta(file.name);
    });
    const onUploaded = jest.fn();

    const result = await uploadBatch(
      [item("exists"), item("bad"), item("ok")],
      onUploaded,
      jest.fn()
    );

    expect(result.skipped).toBe(1);
    expect(result.uploaded).toBe(1);
    expect(result.failed).toHaveLength(1);
    expect(onUploaded).toHaveBeenCalledTimes(1);
  });

  it("reports per-file progress", async () => {
    mockUpload.mockImplementation(async (file, _dir, onProgress) => {
      onProgress?.(0.5);
      return meta(file.name);
    });
    const seen: number[] = [];

    await uploadBatch([item("a")], jest.fn(), entries => {
      seen.push(entries[0]!.fraction);
    });

    expect(seen).toContain(0.5);
  });
});

describe("computeProgress", () => {
  const entry = (
    status: UploadEntry["status"],
    size: number,
    fraction = 0
  ): UploadEntry => ({ name: "n", status, size, fraction });

  it("weights overall percent by file size", () => {
    const p = computeProgress([entry("done", 75), entry("uploading", 25, 0.5)]);
    expect(p.percent).toBe(88); // (75 + 12.5) / 100
    expect(p.finished).toBe(1);
    expect(p.active).toHaveLength(1);
  });

  it("falls back to file counts for empty files", () => {
    expect(
      computeProgress([entry("done", 0), entry("queued", 0)]).percent
    ).toBe(50);
  });
});
