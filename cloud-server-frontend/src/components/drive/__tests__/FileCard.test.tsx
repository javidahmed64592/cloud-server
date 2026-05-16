import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import FileCard from "@/components/drive/FileCard";
import type { FileMetadata } from "@/lib/types";

describe("FileCard", () => {
  const mockOnOpen = jest.fn();
  const mockOnMove = jest.fn();
  const mockOnDelete = jest.fn();

  const mockImageFile: FileMetadata = {
    id: 1,
    filename: "test-image.jpg",
    parent_directory: ".",
    mime_type: "image/jpeg",
    size: 1024000,
    uploaded_at: 1672531200,
    updated_at: 1672531200,
  };

  const mockTextFile: FileMetadata = {
    id: 3,
    filename: "document.pdf",
    parent_directory: ".",
    mime_type: "application/pdf",
    size: 204800,
    uploaded_at: 1672531200,
    updated_at: 1672531200,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders filename correctly", () => {
    render(
      <FileCard
        file={mockImageFile}
        onOpen={mockOnOpen}
        onMove={mockOnMove}
        onDelete={mockOnDelete}
      />
    );

    expect(screen.getByText("test-image.jpg")).toBeInTheDocument();
  });

  it("renders file size correctly", () => {
    render(
      <FileCard
        file={mockImageFile}
        onOpen={mockOnOpen}
        onMove={mockOnMove}
        onDelete={mockOnDelete}
      />
    );

    expect(screen.getByText("1000.0 KB")).toBeInTheDocument();
  });

  it("displays thumbnail when provided", () => {
    const thumbnailUrl = "blob:http://localhost/thumbnail";
    render(
      <FileCard
        file={mockImageFile}
        thumbnail={thumbnailUrl}
        onOpen={mockOnOpen}
        onMove={mockOnMove}
        onDelete={mockOnDelete}
      />
    );

    const img = screen.getByAltText("test-image.jpg");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", thumbnailUrl);
  });

  it("shows loading skeleton for media files without thumbnail", () => {
    const { container } = render(
      <FileCard
        file={mockImageFile}
        onOpen={mockOnOpen}
        onMove={mockOnMove}
        onDelete={mockOnDelete}
      />
    );

    const skeleton = container.querySelector(".animate-pulse");
    expect(skeleton).toBeInTheDocument();
  });

  it("shows placeholder icon for non-media files", () => {
    const { container } = render(
      <FileCard
        file={mockTextFile}
        onOpen={mockOnOpen}
        onMove={mockOnMove}
        onDelete={mockOnDelete}
      />
    );

    // Check for FileTypeIcon component rendering
    const icon = container.querySelector("svg");
    expect(icon).toBeInTheDocument();
  });

  it("calls onOpen when card is clicked", async () => {
    const user = userEvent.setup();
    render(
      <FileCard
        file={mockImageFile}
        onOpen={mockOnOpen}
        onMove={mockOnMove}
        onDelete={mockOnDelete}
      />
    );

    // Click the main card button (not the action buttons)
    const buttons = screen.getAllByRole("button");
    const cardButton = buttons[0]; // The outer button is first
    if (!cardButton) throw new Error("Card button not found");
    await user.click(cardButton);

    expect(mockOnOpen).toHaveBeenCalledTimes(1);
  });

  it("calls onMove when move button is clicked", async () => {
    const user = userEvent.setup();
    render(
      <FileCard
        file={mockImageFile}
        onOpen={mockOnOpen}
        onMove={mockOnMove}
        onDelete={mockOnDelete}
      />
    );

    const moveButton = screen.getByTitle("Rename / Move");
    await user.click(moveButton);

    expect(mockOnMove).toHaveBeenCalledTimes(1);
    expect(mockOnOpen).not.toHaveBeenCalled();
  });

  it("calls onDelete when delete button is clicked", async () => {
    const user = userEvent.setup();
    render(
      <FileCard
        file={mockImageFile}
        onOpen={mockOnOpen}
        onMove={mockOnMove}
        onDelete={mockOnDelete}
      />
    );

    const deleteButton = screen.getByTitle("Delete");
    await user.click(deleteButton);

    expect(mockOnDelete).toHaveBeenCalledTimes(1);
    expect(mockOnOpen).not.toHaveBeenCalled();
  });

  it("formats file sizes correctly", () => {
    const files: Array<{ file: FileMetadata; expected: string }> = [
      { file: { ...mockImageFile, size: 500 }, expected: "500 B" },
      { file: { ...mockImageFile, size: 1536 }, expected: "1.5 KB" },
      { file: { ...mockImageFile, size: 1048576 }, expected: "1.0 MB" },
      { file: { ...mockImageFile, size: 1073741824 }, expected: "1.0 GB" },
    ];

    files.forEach(({ file, expected }) => {
      const { unmount } = render(
        <FileCard
          file={file}
          onOpen={mockOnOpen}
          onMove={mockOnMove}
          onDelete={mockOnDelete}
        />
      );
      expect(screen.getByText(expected)).toBeInTheDocument();
      unmount();
    });
  });

  it("truncates long filenames", () => {
    const longFile = {
      ...mockImageFile,
      filename: "very-long-filename-that-should-be-truncated-properly.jpg",
    };

    render(
      <FileCard
        file={longFile}
        onOpen={mockOnOpen}
        onMove={mockOnMove}
        onDelete={mockOnDelete}
      />
    );

    const filename = screen.getByText(longFile.filename);
    expect(filename).toHaveClass("truncate");
    expect(filename).toHaveAttribute("title", longFile.filename);
  });

  it("has correct accessibility attributes", () => {
    render(
      <FileCard
        file={mockImageFile}
        onOpen={mockOnOpen}
        onMove={mockOnMove}
        onDelete={mockOnDelete}
      />
    );

    const buttons = screen.getAllByRole("button");
    const mainButton = buttons[0]; // The outer card button
    expect(mainButton).toHaveClass("focus-visible:ring-2");
  });
});
