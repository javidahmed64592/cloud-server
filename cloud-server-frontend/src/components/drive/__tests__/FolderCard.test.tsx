import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import FolderCard from "@/components/drive/FolderCard";

describe("FolderCard", () => {
  const mockOnClick = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders folder name correctly", () => {
    render(<FolderCard name="My Folder" onClick={mockOnClick} />);

    expect(screen.getByText("My Folder")).toBeInTheDocument();
  });

  it("renders folder icon", () => {
    const { container } = render(
      <FolderCard name="Test" onClick={mockOnClick} />
    );

    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveClass("text-neon-blue");
  });

  it("calls onClick when clicked", async () => {
    const user = userEvent.setup();
    render(<FolderCard name="Test" onClick={mockOnClick} />);

    const button = screen.getByRole("button");
    await user.click(button);

    expect(mockOnClick).toHaveBeenCalledTimes(1);
  });

  it("truncates long folder names", () => {
    const longName = "This is a very long folder name that should be truncated";
    render(<FolderCard name={longName} onClick={mockOnClick} />);

    const text = screen.getByText(longName);
    expect(text).toHaveClass("truncate");
  });

  it("shows full name in title attribute", () => {
    const folderName = "Important Documents";
    render(<FolderCard name={folderName} onClick={mockOnClick} />);

    const text = screen.getByText(folderName);
    expect(text).toHaveAttribute("title", folderName);
  });

  it("has correct styling classes", () => {
    render(<FolderCard name="Test" onClick={mockOnClick} />);

    const button = screen.getByRole("button");
    expect(button).toHaveClass("group", "flex", "flex-col", "items-center");
    expect(button).toHaveClass("hover:bg-background-secondary");
  });

  it("has focus-visible ring for accessibility", () => {
    render(<FolderCard name="Test" onClick={mockOnClick} />);

    const button = screen.getByRole("button");
    expect(button).toHaveClass("focus-visible:ring-2");
    expect(button).toHaveClass("focus-visible:ring-border-accent");
  });

  it("handles special characters in folder name", () => {
    const specialName = "Folder-with_special.chars!@#";
    render(<FolderCard name={specialName} onClick={mockOnClick} />);

    expect(screen.getByText(specialName)).toBeInTheDocument();
  });
});
