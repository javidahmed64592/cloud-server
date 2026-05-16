import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import UploadButton from "@/components/drive/UploadButton";
import * as api from "@/lib/api";
import type { FileMetadata } from "@/lib/types";

jest.mock("@/lib/api", () => ({
  uploadFile: jest.fn(),
}));

const mockUploadFile = api.uploadFile as jest.MockedFunction<
  typeof api.uploadFile
>;

describe("UploadButton", () => {
  const mockOnUpload = jest.fn();
  const currentPath = "test-folder";

  const mockFileMetadata: FileMetadata = {
    id: 1,
    filename: "test.jpg",
    parent_directory: "test-folder",
    mime_type: "image/jpeg",
    size: 1024,
    uploaded_at: 1672531200,
    updated_at: 1672531200,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUploadFile.mockResolvedValue(mockFileMetadata);
  });

  afterEach(() => {
    jest.clearAllTimers();
    jest.useRealTimers();
  });

  it("renders upload button", () => {
    render(<UploadButton currentPath={currentPath} onUpload={mockOnUpload} />);

    expect(screen.getByRole("button", { name: /upload/i })).toBeInTheDocument();
  });

  it("renders upload icon", () => {
    const { container } = render(
      <UploadButton currentPath={currentPath} onUpload={mockOnUpload} />
    );

    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
  });

  it("has hidden file input", () => {
    const { container } = render(
      <UploadButton currentPath={currentPath} onUpload={mockOnUpload} />
    );

    const fileInput = container.querySelector('input[type="file"]');
    expect(fileInput).toBeInTheDocument();
    expect(fileInput).toHaveClass("hidden");
    expect(fileInput).toHaveAttribute("multiple");
  });

  it("opens file picker when button is clicked", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <UploadButton currentPath={currentPath} onUpload={mockOnUpload} />
    );

    const button = screen.getByRole("button", { name: /upload/i });
    const fileInput = container.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    const clickSpy = jest.spyOn(fileInput, "click");

    await user.click(button);

    expect(clickSpy).toHaveBeenCalled();
  });

  it("uploads file when selected", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <UploadButton currentPath={currentPath} onUpload={mockOnUpload} />
    );

    const fileInput = container.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    const file = new File(["test content"], "test.jpg", {
      type: "image/jpeg",
    });

    await user.upload(fileInput, file);

    await waitFor(() => {
      expect(mockUploadFile).toHaveBeenCalledWith(file, currentPath);
      expect(mockOnUpload).toHaveBeenCalledWith(mockFileMetadata);
    });
  });

  it("uploads multiple files", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <UploadButton currentPath={currentPath} onUpload={mockOnUpload} />
    );

    const fileInput = container.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    const file1 = new File(["content1"], "file1.jpg", { type: "image/jpeg" });
    const file2 = new File(["content2"], "file2.jpg", { type: "image/jpeg" });

    mockUploadFile
      .mockResolvedValueOnce({
        ...mockFileMetadata,
        id: 1,
        filename: "file1.jpg",
      })
      .mockResolvedValueOnce({
        ...mockFileMetadata,
        id: 2,
        filename: "file2.jpg",
      });

    await user.upload(fileInput, [file1, file2]);

    await waitFor(() => {
      expect(mockUploadFile).toHaveBeenCalledTimes(2);
      expect(mockOnUpload).toHaveBeenCalledTimes(2);
    });
  });

  it("shows uploading state during upload", async () => {
    const user = userEvent.setup();
    mockUploadFile.mockImplementation(
      () =>
        new Promise(resolve => setTimeout(() => resolve(mockFileMetadata), 100))
    );

    const { container } = render(
      <UploadButton currentPath={currentPath} onUpload={mockOnUpload} />
    );

    const fileInput = container.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    const file = new File(["test"], "test.jpg", { type: "image/jpeg" });
    await user.upload(fileInput, file);

    expect(screen.getByText("Uploading…")).toBeInTheDocument();
    const button = screen.getByRole("button", { name: /uploading/i });
    expect(button).toBeDisabled();

    await waitFor(() => {
      expect(screen.getByText(/upload/i)).toBeInTheDocument();
    });
  });

  it("displays error message on upload failure", async () => {
    const user = userEvent.setup();
    const errorMessage = "Upload failed: Network error";
    mockUploadFile.mockRejectedValue(errorMessage); // Send string directly

    const { container } = render(
      <UploadButton currentPath={currentPath} onUpload={mockOnUpload} />
    );

    const fileInput = container.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    const file = new File(["test"], "test.jpg", { type: "image/jpeg" });
    await user.upload(fileInput, file);

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
    expect(mockOnUpload).not.toHaveBeenCalled();
  });

  it("clears error after 5 seconds", async () => {
    jest.useFakeTimers();
    const user = userEvent.setup({ delay: null });
    const errorMessage = "Upload failed";
    mockUploadFile.mockRejectedValue(errorMessage);

    const { container, unmount } = render(
      <UploadButton currentPath={currentPath} onUpload={mockOnUpload} />
    );

    const fileInput = container.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    const file = new File(["test"], "test.jpg", { type: "image/jpeg" });
    await user.upload(fileInput, file);

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    jest.advanceTimersByTime(5000);

    await waitFor(() => {
      expect(screen.queryByText(errorMessage)).not.toBeInTheDocument();
    });

    unmount();
    jest.useRealTimers();
  });

  it("clears file input after upload", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <UploadButton currentPath={currentPath} onUpload={mockOnUpload} />
    );

    const fileInput = container.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    const file = new File(["test"], "test.jpg", { type: "image/jpeg" });
    await user.upload(fileInput, file);

    await waitFor(() => {
      expect(fileInput.value).toBe("");
    });
  });

  it("does not upload when no file selected", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <UploadButton currentPath={currentPath} onUpload={mockOnUpload} />
    );

    const fileInput = container.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    // Trigger change without files
    await user.upload(fileInput, []);

    expect(mockUploadFile).not.toHaveBeenCalled();
    expect(mockOnUpload).not.toHaveBeenCalled();
  });

  it("handles empty FileList", async () => {
    const { container } = render(
      <UploadButton currentPath={currentPath} onUpload={mockOnUpload} />
    );

    const fileInput = container.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    // Manually trigger change with null
    Object.defineProperty(fileInput, "files", {
      value: null,
      writable: true,
    });

    fileInput.dispatchEvent(new Event("change", { bubbles: true }));

    expect(mockUploadFile).not.toHaveBeenCalled();
  });

  it("clears error on successful upload after previous error", async () => {
    const user = userEvent.setup();
    mockUploadFile
      .mockRejectedValueOnce("First upload failed")
      .mockResolvedValueOnce(mockFileMetadata);

    const { container } = render(
      <UploadButton currentPath={currentPath} onUpload={mockOnUpload} />
    );

    const fileInput = container.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    const file = new File(["test"], "test.jpg", { type: "image/jpeg" });

    // First upload (fails)
    await user.upload(fileInput, file);
    await waitFor(() => {
      expect(screen.getByText("First upload failed")).toBeInTheDocument();
    });

    // Second upload (succeeds)
    await user.upload(fileInput, file);
    await waitFor(() => {
      expect(screen.queryByText("First upload failed")).not.toBeInTheDocument();
    });
  });
});
