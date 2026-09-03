import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import FolderDialog from "@/components/drive/FolderDialog";

describe("FolderDialog", () => {
  const mockOnConfirm = jest.fn();
  const mockOnClose = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockOnConfirm.mockResolvedValue(undefined);
  });

  it("renders with initial folder name and parent split correctly", () => {
    render(
      <FolderDialog
        folderPath="photos/2023"
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByDisplayValue("2023")).toBeInTheDocument();
    expect(screen.getByDisplayValue("photos")).toBeInTheDocument();
  });

  it("uses '.' as parent for top-level folder", () => {
    render(
      <FolderDialog
        folderPath="documents"
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    expect(screen.getByDisplayValue("documents")).toBeInTheDocument();
    expect(screen.getByDisplayValue(".")).toBeInTheDocument();
  });

  it("calls onConfirm with new name and parent on submit", async () => {
    const user = userEvent.setup();
    render(
      <FolderDialog
        folderPath="photos/2023"
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    const nameInput = screen.getByDisplayValue("2023");
    await user.clear(nameInput);
    await user.type(nameInput, "archive");

    await user.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(mockOnConfirm).toHaveBeenCalledWith("archive", "photos");
    });
  });

  it("closes dialog after successful confirm", async () => {
    const user = userEvent.setup();
    render(
      <FolderDialog
        folderPath="myfolder"
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    await user.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });
  });

  it("calls onClose when cancel button is clicked", async () => {
    const user = userEvent.setup();
    render(
      <FolderDialog
        folderPath="myfolder"
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    await user.click(screen.getByRole("button", { name: /cancel/i }));

    expect(mockOnClose).toHaveBeenCalledTimes(1);
    expect(mockOnConfirm).not.toHaveBeenCalled();
  });

  it("shows error message when confirm throws", async () => {
    const user = userEvent.setup();
    mockOnConfirm.mockRejectedValue(new Error("Move failed"));
    render(
      <FolderDialog
        folderPath="myfolder"
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    await user.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(screen.getByText("Error: Move failed")).toBeInTheDocument();
    });
    expect(mockOnClose).not.toHaveBeenCalled();
  });

  it("disables Save button when name is empty", async () => {
    const user = userEvent.setup();
    render(
      <FolderDialog
        folderPath="myfolder"
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    const nameInput = screen.getByDisplayValue("myfolder");
    await user.clear(nameInput);

    expect(screen.getByRole("button", { name: /save/i })).toBeDisabled();
  });

  it("closes on Escape key", async () => {
    const user = userEvent.setup();
    render(
      <FolderDialog
        folderPath="myfolder"
        onConfirm={mockOnConfirm}
        onClose={mockOnClose}
      />
    );

    await user.keyboard("{Escape}");

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });
});
