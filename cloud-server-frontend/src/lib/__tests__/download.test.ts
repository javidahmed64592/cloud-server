import { downloadFolder, folderZipName } from "@/lib/download";

describe("folderZipName", () => {
  it("names zips after the folder, or storage for the root", () => {
    expect(folderZipName(".")).toBe("storage.zip");
    expect(folderZipName("a/b")).toBe("b.zip");
  });
});

describe("downloadFolder", () => {
  afterEach(() => {
    delete (window as { showSaveFilePicker?: unknown }).showSaveFilePicker;
    jest.restoreAllMocks();
  });

  it("falls back to a native link download without the File System API", async () => {
    const click = jest
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
    const onProgress = jest.fn();

    expect(await downloadFolder("docs", onProgress)).toBe(true);

    expect(click).toHaveBeenCalled();
    expect(onProgress).not.toHaveBeenCalled();
  });

  it("streams to the chosen file and reports progress", async () => {
    const written: Uint8Array[] = [];
    const writer = {
      write: jest.fn(async (c: Uint8Array) => void written.push(c)),
      close: jest.fn(async () => undefined),
      abort: jest.fn(async () => undefined),
    };
    (window as unknown as Record<string, unknown>).showSaveFilePicker = jest.fn(
      async () => ({
        createWritable: async () => ({ getWriter: () => writer }),
      })
    );
    const chunks = [new Uint8Array(30), new Uint8Array(70)];
    global.fetch = jest.fn(async () => ({
      ok: true,
      headers: { get: () => "100" },
      body: {
        getReader: () => ({
          read: async () =>
            chunks.length
              ? { done: false, value: chunks.shift() }
              : { done: true, value: undefined },
        }),
      },
    })) as unknown as typeof fetch;
    const onProgress = jest.fn();

    expect(await downloadFolder("docs", onProgress)).toBe(true);

    expect(written).toHaveLength(2);
    expect(writer.close).toHaveBeenCalled();
    expect(onProgress).toHaveBeenLastCalledWith({
      phase: "downloading",
      received: 100,
      total: 100,
    });
  });

  it("returns false when the save dialog is cancelled", async () => {
    (window as unknown as Record<string, unknown>).showSaveFilePicker = jest.fn(
      async () => {
        throw Object.assign(new Error("cancelled"), { name: "AbortError" });
      }
    );
    expect(await downloadFolder("docs", jest.fn())).toBe(false);
  });
});
