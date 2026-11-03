import {
  getFolderCreatedDates,
  sortFiles,
  sortFolders,
  type SortOption,
} from "@/lib/sort";
import type { FileMetadata } from "@/lib/types";

const file = (
  id: number,
  filename: string,
  parent_directory: string,
  uploaded_at: number
): FileMetadata => ({
  id,
  filename,
  parent_directory,
  mime_type: "text/plain",
  size: 1,
  uploaded_at,
  updated_at: uploaded_at,
});

const asc = (key: SortOption["key"]): SortOption => ({
  key,
  direction: "asc",
});
const desc = (key: SortOption["key"]): SortOption => ({
  key,
  direction: "desc",
});

describe("sortFiles", () => {
  const files = [
    file(1, "b10.txt", ".", 300),
    file(2, "B2.txt", ".", 100),
    file(3, "a.txt", ".", 200),
  ];

  it("sorts by name naturally and case-insensitively", () => {
    expect(sortFiles(files, asc("name")).map(f => f.id)).toEqual([3, 2, 1]);
    expect(sortFiles(files, desc("name")).map(f => f.id)).toEqual([1, 2, 3]);
  });

  it("sorts by date created", () => {
    expect(sortFiles(files, asc("created")).map(f => f.id)).toEqual([2, 3, 1]);
    expect(sortFiles(files, desc("created")).map(f => f.id)).toEqual([1, 3, 2]);
  });

  it("breaks date ties by name and does not mutate the input", () => {
    const tied = [file(1, "z", ".", 5), file(2, "a", ".", 5)];
    expect(sortFiles(tied, desc("created")).map(f => f.id)).toEqual([2, 1]);
    expect(tied.map(f => f.id)).toEqual([1, 2]);
  });
});

describe("folders", () => {
  const files = [
    file(1, "x", "old/deep", 50),
    file(2, "y", "old", 400),
    file(3, "z", "new", 100),
    file(4, "w", ".", 1),
  ];

  it("dates a folder by its earliest nested file", () => {
    expect(getFolderCreatedDates(files, ".")).toEqual({ old: 50, new: 100 });
    expect(getFolderCreatedDates(files, "old")).toEqual({ deep: 50 });
  });

  it("sorts folders by name and date", () => {
    const dates = getFolderCreatedDates(files, ".");
    expect(sortFolders(["old", "new"], dates, asc("name"))).toEqual([
      "new",
      "old",
    ]);
    expect(sortFolders(["new", "old"], dates, asc("created"))).toEqual([
      "old",
      "new",
    ]);
    expect(sortFolders(["new", "old"], dates, desc("created"))).toEqual([
      "new",
      "old",
    ]);
  });
});
