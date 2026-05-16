import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import MoveDialog from "@/components/drive/MoveDialog";
import type { FileMetadata } from "@/lib/types";

describe("MoveDialog", () => {
  const mockOnConfirm = jest.fn();
  const mockOnClose = jest.fn();

  const mockFile: FileMetadata = {
    id: 1,
    filename: "test-file.jpg",
    parent_directory: "folder1",
    mime_type: "image/jpeg",
    size: 1024,
    uploaded_at: 1672531200,
    updated_at: 1672531200,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockOnConfirm.mockResolvedValue(undefined);
  });

  it("renders with initial file values", () => {
    render(
      <MoveDialog
        file={mockFile}
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText("Rename / Move")).toBeInTheDocument();
    expect(screen.getByDisplayValue("test-file.jpg")).toBeInTheDocument();
    expect(screen.getByDisplayValue("folder1")).toBeInTheDocument();
  });

  it("has autofocus on filename input", () => {
    render(
      <MoveDialog
        file={mockFile}
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    const filenameInput = screen.getByDisplayValue("test-file.jpg");
    // In React, autoFocus is a boolean prop, not an HTML attribute
    // The actual HTML attribute will be "autofocus" (lowercase) when rendered
    // Check that the element is focused after render
    expect(document.activeElement).toBe(filenameInput);
  });

  it("updates filename when typing", async () => {
    const user = userEvent.setup();
    render(
      <MoveDialog
        file={mockFile}
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    const filenameInput = screen.getByDisplayValue("test-file.jpg");
    await user.clear(filenameInput);
    await user.type(filenameInput, "new-name.jpg");

    expect(screen.getByDisplayValue("new-name.jpg")).toBeInTheDocument();
  });

  it("updates directory when typing", async () => {
    const user = userEvent.setup();
    render(
      <MoveDialog
        file={mockFile}
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    const dirInput = screen.getByDisplayValue("folder1");
    await user.clear(dirInput);
    await user.type(dirInput, "new-folder");

    expect(screen.getByDisplayValue("new-folder")).toBeInTheDocument();
  });

  it("calls onConfirm with updated values on submit", async () => {
    const user = userEvent.setup();
    render(
      <MoveDialog
        file={mockFile}
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    const filenameInput = screen.getByDisplayValue("test-file.jpg");
    const dirInput = screen.getByDisplayValue("folder1");

    await user.clear(filenameInput);
    await user.type(filenameInput, "renamed.jpg");
    await user.clear(dirInput);
    await user.type(dirInput, "new-dir");

    const saveButton = screen.getByRole("button", { name: "Save" });
    await user.click(saveButton);

    await waitFor(() => {
      expect(mockOnConfirm).toHaveBeenCalledWith("renamed.jpg", "new-dir");
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  it("uses '.' as default directory when empty", async () => {
    const user = userEvent.setup();
    render(
      <MoveDialog
        file={mockFile}
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    const dirInput = screen.getByDisplayValue("folder1");
    await user.clear(dirInput);

    const saveButton = screen.getByRole("button", { name: "Save" });
    await user.click(saveButton);

    await waitFor(() => {
      expect(mockOnConfirm).toHaveBeenCalledWith("test-file.jpg", ".");
    });
  });

  it("trims whitespace from filename and directory", async () => {
    const user = userEvent.setup();
    render(
      <MoveDialog
        file={mockFile}
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    const filenameInput = screen.getByDisplayValue("test-file.jpg");
    const dirInput = screen.getByDisplayValue("folder1");

    await user.clear(filenameInput);
    await user.type(filenameInput, "  spaced.jpg  ");
    await user.clear(dirInput);
    await user.type(dirInput, "  folder  ");

    const saveButton = screen.getByRole("button", { name: "Save" });
    await user.click(saveButton);

    await waitFor(() => {
      expect(mockOnConfirm).toHaveBeenCalledWith("spaced.jpg", "folder");
    });
  });

  it("disables save button when filename is empty", async () => {
    const user = userEvent.setup();
    render(
      <MoveDialog
        file={mockFile}
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    const filenameInput = screen.getByDisplayValue("test-file.jpg");
    await user.clear(filenameInput);

    const saveButton = screen.getByRole("button", { name: "Save" });
    expect(saveButton).toBeDisabled();
  });

  it("shows loading state during save", async () => {
    const user = userEvent.setup();
    mockOnConfirm.mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );

    render(
      <MoveDialog
        file={mockFile}
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    const saveButton = screen.getByRole("button", { name: "Save" });
    await user.click(saveButton);

    expect(screen.getByText("Saving…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Saving…" })).toBeDisabled();
  });

  it("displays error message on failure", async () => {
    const user = userEvent.setup();
    const errorMessage = "Failed to update file";
    mockOnConfirm.mockRejectedValue(new Error(errorMessage));

    render(
      <MoveDialog
        file={mockFile}
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    const saveButton = screen.getByRole("button", { name: "Save" });
    await user.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText(`Error: ${errorMessage}`)).toBeInTheDocument();
    });
    expect(mockOnClose).not.toHaveBeenCalled();
  });

  it("calls onClose when cancel button is clicked", async () => {
    const user = userEvent.setup();
    render(
      <MoveDialog
        file={mockFile}
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    const cancelButton = screen.getByRole("button", { name: "Cancel" });
    await user.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalledTimes(1);
    expect(mockOnConfirm).not.toHaveBeenCalled();
  });

  it("calls onClose when backdrop is clicked", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <MoveDialog
        file={mockFile}
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    const backdrop = container.firstChild as HTMLElement;
    await user.click(backdrop);

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it("does not close when dialog content is clicked", async () => {
    const user = userEvent.setup();
    render(
      <MoveDialog
        file={mockFile}
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    const heading = screen.getByText("Rename / Move");
    await user.click(heading);

    expect(mockOnClose).not.toHaveBeenCalled();
  });

  it("closes on Escape key press", async () => {
    const user = userEvent.setup();
    render(
      <MoveDialog
        file={mockFile}
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    await user.keyboard("{Escape}");

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it("submits form on Enter key press", async () => {
    const user = userEvent.setup();
    render(
      <MoveDialog
        file={mockFile}
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    const filenameInput = screen.getByDisplayValue("test-file.jpg");
    await user.type(filenameInput, "{Enter}");

    await waitFor(() => {
      expect(mockOnConfirm).toHaveBeenCalled();
    });
  });

  it("has correct accessibility labels", () => {
    render(
      <MoveDialog
        file={mockFile}
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByText("Filename")).toBeInTheDocument();
    expect(screen.getByText("Directory")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(".")).toBeInTheDocument();
  });
});
