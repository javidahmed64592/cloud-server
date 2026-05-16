import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import FileViewer from "@/components/drive/FileViewer";
import type { FileMetadata } from "@/lib/types";

describe("FileViewer", () => {
  const mockOnClose = jest.fn();
  const mockOnPrevious = jest.fn();
  const mockOnNext = jest.fn();

  const mockImageFile: FileMetadata = {
    id: 1,
    filename: "test-image.jpg",
    parent_directory: ".",
    mime_type: "image/jpeg",
    size: 1024000,
    uploaded_at: 1672531200,
    updated_at: 1672531200,
  };

  const mockVideoFile: FileMetadata = {
    id: 2,
    filename: "test-video.mp4",
    parent_directory: ".",
    mime_type: "video/mp4",
    size: 5242880,
    uploaded_at: 1672531200,
    updated_at: 1672531200,
  };

  const mockPdfFile: FileMetadata = {
    id: 3,
    filename: "document.pdf",
    parent_directory: ".",
    mime_type: "application/pdf",
    size: 204800,
    uploaded_at: 1672531200,
    updated_at: 1672531200,
  };

  const blobUrl = "blob:http://localhost/test";

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders image file correctly", () => {
    render(
      <FileViewer
        file={mockImageFile}
        blobUrl={blobUrl}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText("test-image.jpg")).toBeInTheDocument();
    const img = screen.getByAltText("test-image.jpg");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", blobUrl);
  });

  it("renders video file correctly", () => {
    render(
      <FileViewer
        file={mockVideoFile}
        blobUrl={blobUrl}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText("test-video.mp4")).toBeInTheDocument();
    const video = document.querySelector("video");
    expect(video).toBeInTheDocument();
    expect(video).toHaveAttribute("src", blobUrl);
    expect(video).toHaveAttribute("controls");
    expect(video).toHaveAttribute("autoPlay");
  });

  it("renders placeholder for unsupported file types", () => {
    render(
      <FileViewer file={mockPdfFile} blobUrl={blobUrl} onClose={mockOnClose} />
    );

    expect(screen.getByText("document.pdf")).toBeInTheDocument();
    expect(
      screen.getByText("Preview not available for this file type")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Use the download button to save the file")
    ).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", async () => {
    const user = userEvent.setup();
    render(
      <FileViewer
        file={mockImageFile}
        blobUrl={blobUrl}
        onClose={mockOnClose}
      />
    );

    const closeButton = screen.getByRole("button", { name: "Close" });
    await user.click(closeButton);

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when backdrop is clicked", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <FileViewer
        file={mockImageFile}
        blobUrl={blobUrl}
        onClose={mockOnClose}
      />
    );

    const backdrop = container.firstChild as HTMLElement;
    await user.click(backdrop);

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it("does not close when content is clicked", async () => {
    const user = userEvent.setup();
    render(
      <FileViewer
        file={mockImageFile}
        blobUrl={blobUrl}
        onClose={mockOnClose}
      />
    );

    const image = screen.getByAltText("test-image.jpg");
    await user.click(image);

    expect(mockOnClose).not.toHaveBeenCalled();
  });

  it("renders download button with correct href", () => {
    render(
      <FileViewer
        file={mockImageFile}
        blobUrl={blobUrl}
        onClose={mockOnClose}
      />
    );

    const downloadLink = screen.getByRole("link", { name: "Download" });
    expect(downloadLink).toHaveAttribute("href", blobUrl);
    expect(downloadLink).toHaveAttribute("download", "test-image.jpg");
  });

  it("shows navigation arrows when callbacks provided", () => {
    render(
      <FileViewer
        file={mockImageFile}
        blobUrl={blobUrl}
        onClose={mockOnClose}
        onPrevious={mockOnPrevious}
        onNext={mockOnNext}
      />
    );

    expect(screen.getByTitle("Previous (←)")).toBeInTheDocument();
    expect(screen.getByTitle("Next (→)")).toBeInTheDocument();
  });

  it("hides navigation arrows when callbacks not provided", () => {
    render(
      <FileViewer
        file={mockImageFile}
        blobUrl={blobUrl}
        onClose={mockOnClose}
      />
    );

    expect(screen.queryByTitle("Previous (←)")).not.toBeInTheDocument();
    expect(screen.queryByTitle("Next (→)")).not.toBeInTheDocument();
  });

  it("calls onPrevious when previous button is clicked", async () => {
    const user = userEvent.setup();
    render(
      <FileViewer
        file={mockImageFile}
        blobUrl={blobUrl}
        onClose={mockOnClose}
        onPrevious={mockOnPrevious}
        onNext={mockOnNext}
      />
    );

    const prevButton = screen.getByTitle("Previous (←)");
    await user.click(prevButton);

    expect(mockOnPrevious).toHaveBeenCalledTimes(1);
    expect(mockOnNext).not.toHaveBeenCalled();
  });

  it("calls onNext when next button is clicked", async () => {
    const user = userEvent.setup();
    render(
      <FileViewer
        file={mockImageFile}
        blobUrl={blobUrl}
        onClose={mockOnClose}
        onPrevious={mockOnPrevious}
        onNext={mockOnNext}
      />
    );

    const nextButton = screen.getByTitle("Next (→)");
    await user.click(nextButton);

    expect(mockOnNext).toHaveBeenCalledTimes(1);
    expect(mockOnPrevious).not.toHaveBeenCalled();
  });

  it("closes on Escape key press", async () => {
    const user = userEvent.setup();
    render(
      <FileViewer
        file={mockImageFile}
        blobUrl={blobUrl}
        onClose={mockOnClose}
      />
    );

    await user.keyboard("{Escape}");

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it("navigates on ArrowLeft key press", async () => {
    const user = userEvent.setup();
    render(
      <FileViewer
        file={mockImageFile}
        blobUrl={blobUrl}
        onClose={mockOnClose}
        onPrevious={mockOnPrevious}
        onNext={mockOnNext}
      />
    );

    await user.keyboard("{ArrowLeft}");

    expect(mockOnPrevious).toHaveBeenCalledTimes(1);
  });

  it("navigates on ArrowRight key press", async () => {
    const user = userEvent.setup();
    render(
      <FileViewer
        file={mockImageFile}
        blobUrl={blobUrl}
        onClose={mockOnClose}
        onPrevious={mockOnPrevious}
        onNext={mockOnNext}
      />
    );

    await user.keyboard("{ArrowRight}");

    expect(mockOnNext).toHaveBeenCalledTimes(1);
  });

  it("does not navigate when callbacks not provided", async () => {
    const user = userEvent.setup();
    render(
      <FileViewer
        file={mockImageFile}
        blobUrl={blobUrl}
        onClose={mockOnClose}
      />
    );

    await user.keyboard("{ArrowLeft}");
    await user.keyboard("{ArrowRight}");

    // Should not throw errors
    expect(mockOnClose).not.toHaveBeenCalled();
  });
});
