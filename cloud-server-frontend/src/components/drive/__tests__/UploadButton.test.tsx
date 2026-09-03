import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { act } from "react";

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

    // Advance timers and wait for state update
    act(() => {
      jest.advanceTimersByTime(5000);
    });

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
    const { container } = render(
      <UploadButton currentPath={currentPath} onUpload={mockOnUpload} />
    );

    const fileInput = container.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;

    // Trigger change with empty files
    Object.defineProperty(fileInput, "files", {
      value: null,
      writable: false,
    });
    fileInput.dispatchEvent(new Event("change", { bubbles: true }));

    // Should not call upload functions
    await waitFor(() => {
      expect(mockUploadFile).not.toHaveBeenCalled();
      expect(mockOnUpload).not.toHaveBeenCalled();
    });
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

  it("renders folder upload button", () => {
    render(<UploadButton currentPath={currentPath} onUpload={mockOnUpload} />);

    expect(screen.getByRole("button", { name: /folder/i })).toBeInTheDocument();
  });

  it("has hidden folder input", () => {
    const { container } = render(
      <UploadButton currentPath={currentPath} onUpload={mockOnUpload} />
    );

    const inputs = container.querySelectorAll('input[type="file"]');
    expect(inputs).toHaveLength(2);
    expect(inputs[1]).toHaveClass("hidden");
    expect(inputs[1]).toHaveAttribute("multiple");
  });

  it("opens folder picker when folder button is clicked", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <UploadButton currentPath={currentPath} onUpload={mockOnUpload} />
    );

    const folderButton = screen.getByRole("button", { name: /folder/i });
    const inputs = container.querySelectorAll('input[type="file"]');
    const folderInput = inputs[1] as HTMLInputElement;
    const clickSpy = jest.spyOn(folderInput, "click");

    await user.click(folderButton);

    expect(clickSpy).toHaveBeenCalled();
  });

  it("uploads folder files preserving directory structure", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <UploadButton currentPath={currentPath} onUpload={mockOnUpload} />
    );

    const inputs = container.querySelectorAll('input[type="file"]');
    const folderInput = inputs[1] as HTMLInputElement;

    const file1 = new File(["content1"], "file1.txt", { type: "text/plain" });
    Object.defineProperty(file1, "webkitRelativePath", {
      value: "myFolder/file1.txt",
    });
    const file2 = new File(["content2"], "file2.txt", { type: "text/plain" });
    Object.defineProperty(file2, "webkitRelativePath", {
      value: "myFolder/sub/file2.txt",
    });

    mockUploadFile
      .mockResolvedValueOnce({
        ...mockFileMetadata,
        id: 1,
        filename: "file1.txt",
      })
      .mockResolvedValueOnce({
        ...mockFileMetadata,
        id: 2,
        filename: "file2.txt",
      });

    await user.upload(folderInput, [file1, file2]);

    await waitFor(() => {
      expect(mockUploadFile).toHaveBeenCalledWith(
        file1,
        `${currentPath}/myFolder`
      );
      expect(mockUploadFile).toHaveBeenCalledWith(
        file2,
        `${currentPath}/myFolder/sub`
      );
      expect(mockOnUpload).toHaveBeenCalledTimes(2);
    });
  });
});
