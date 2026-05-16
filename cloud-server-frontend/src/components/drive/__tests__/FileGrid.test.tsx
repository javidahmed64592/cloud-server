import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import FileGrid from "@/components/drive/FileGrid";
import type { FileMetadata } from "@/lib/types";

describe("FileGrid", () => {
  const mockOnFolderClick = jest.fn();
  const mockOnFileOpen = jest.fn();
  const mockOnFileMove = jest.fn();
  const mockOnFileDelete = jest.fn();

  const mockFiles: FileMetadata[] = [
    {
      id: 1,
      filename: "image.jpg",
      parent_directory: ".",
      mime_type: "image/jpeg",
      size: 1024,
      uploaded_at: 1672531200,
      updated_at: 1672531200,
    },
    {
      id: 2,
      filename: "document.pdf",
      parent_directory: ".",
      mime_type: "application/pdf",
      size: 2048,
      uploaded_at: 1672617600,
      updated_at: 1672617600,
    },
  ];

  const mockThumbnails = {
    1: "blob:http://localhost/thumb1",
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders empty state when no folders or files", () => {
    render(
      <FileGrid
        folders={[]}
        files={[]}
        thumbnails={{}}
        onFolderClick={mockOnFolderClick}
        onFileOpen={mockOnFileOpen}
        onFileMove={mockOnFileMove}
        onFileDelete={mockOnFileDelete}
      />
    );

    expect(screen.getByText("This folder is empty")).toBeInTheDocument();
  });

  it("renders folders correctly", () => {
    render(
      <FileGrid
        folders={["Folder1", "Folder2"]}
        files={[]}
        thumbnails={{}}
        onFolderClick={mockOnFolderClick}
        onFileOpen={mockOnFileOpen}
        onFileMove={mockOnFileMove}
        onFileDelete={mockOnFileDelete}
      />
    );

    expect(screen.getByText("Folder1")).toBeInTheDocument();
    expect(screen.getByText("Folder2")).toBeInTheDocument();
  });

  it("renders files correctly", () => {
    render(
      <FileGrid
        folders={[]}
        files={mockFiles}
        thumbnails={mockThumbnails}
        onFolderClick={mockOnFolderClick}
        onFileOpen={mockOnFileOpen}
        onFileMove={mockOnFileMove}
        onFileDelete={mockOnFileDelete}
      />
    );

    expect(screen.getByText("image.jpg")).toBeInTheDocument();
    expect(screen.getByText("document.pdf")).toBeInTheDocument();
  });

  it("renders both folders and files", () => {
    render(
      <FileGrid
        folders={["Documents"]}
        files={mockFiles}
        thumbnails={mockThumbnails}
        onFolderClick={mockOnFolderClick}
        onFileOpen={mockOnFileOpen}
        onFileMove={mockOnFileMove}
        onFileDelete={mockOnFileDelete}
      />
    );

    expect(screen.getByText("Documents")).toBeInTheDocument();
    expect(screen.getByText("image.jpg")).toBeInTheDocument();
    expect(screen.getByText("document.pdf")).toBeInTheDocument();
  });

  it("calls onFolderClick when folder is clicked", async () => {
    const user = userEvent.setup();
    render(
      <FileGrid
        folders={["TestFolder"]}
        files={[]}
        thumbnails={{}}
        onFolderClick={mockOnFolderClick}
        onFileOpen={mockOnFileOpen}
        onFileMove={mockOnFileMove}
        onFileDelete={mockOnFileDelete}
      />
    );

    const folder = screen.getByText("TestFolder");
    await user.click(folder);

    expect(mockOnFolderClick).toHaveBeenCalledWith("TestFolder");
    expect(mockOnFolderClick).toHaveBeenCalledTimes(1);
  });

  it("passes thumbnails to FileCard correctly", () => {
    render(
      <FileGrid
        folders={[]}
        files={mockFiles}
        thumbnails={mockThumbnails}
        onFolderClick={mockOnFolderClick}
        onFileOpen={mockOnFileOpen}
        onFileMove={mockOnFileMove}
        onFileDelete={mockOnFileDelete}
      />
    );

    const thumbnail = screen.getByAltText("image.jpg");
    expect(thumbnail).toHaveAttribute("src", mockThumbnails[1]);
  });

  it("uses grid layout", () => {
    const { container } = render(
      <FileGrid
        folders={["Folder"]}
        files={mockFiles}
        thumbnails={mockThumbnails}
        onFolderClick={mockOnFolderClick}
        onFileOpen={mockOnFileOpen}
        onFileMove={mockOnFileMove}
        onFileDelete={mockOnFileDelete}
      />
    );

    const grid = container.querySelector(".grid");
    expect(grid).toBeInTheDocument();
    expect(grid).toHaveClass("grid-cols-[repeat(auto-fill,minmax(200px,1fr))]");
  });

  it("renders folders before files", () => {
    const firstFile: FileMetadata = {
      ...mockFiles[0]!,
      filename: "AFile.jpg",
    };
    const { container } = render(
      <FileGrid
        folders={["ZFolder"]}
        files={[firstFile]}
        thumbnails={{}}
        onFolderClick={mockOnFolderClick}
        onFileOpen={mockOnFileOpen}
        onFileMove={mockOnFileMove}
        onFileDelete={mockOnFileDelete}
      />
    );

    const grid = container.querySelector(".grid");
    const children = grid?.children;
    expect(children?.[0]).toHaveTextContent("ZFolder");
    expect(children?.[1]).toHaveTextContent("AFile.jpg");
  });

  it("handles large number of items", () => {
    const manyFolders = Array.from({ length: 20 }, (_, i) => `Folder${i}`);
    const manyFiles: FileMetadata[] = Array.from({ length: 30 }, (_, i) => ({
      id: i,
      filename: `file${i}.txt`,
      parent_directory: ".",
      mime_type: "text/plain",
      size: 100,
      uploaded_at: 1672531200,
      updated_at: 1672531200,
    }));

    render(
      <FileGrid
        folders={manyFolders}
        files={manyFiles}
        thumbnails={{}}
        onFolderClick={mockOnFolderClick}
        onFileOpen={mockOnFileOpen}
        onFileMove={mockOnFileMove}
        onFileDelete={mockOnFileDelete}
      />
    );

    expect(screen.getByText("Folder0")).toBeInTheDocument();
    expect(screen.getByText("file0.txt")).toBeInTheDocument();
  });
});
