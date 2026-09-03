import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import FolderCard from "@/components/drive/FolderCard";

describe("FolderCard", () => {
  const mockOnClick = jest.fn();
  const mockOnMove = jest.fn();
  const mockOnDelete = jest.fn();

  const defaultProps = {
    name: "My Folder",
    onClick: mockOnClick,
    onMove: mockOnMove,
    onDelete: mockOnDelete,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders folder name correctly", () => {
    render(<FolderCard {...defaultProps} name="My Folder" />);

    expect(screen.getByText("My Folder")).toBeInTheDocument();
  });

  it("renders folder icon", () => {
    const { container } = render(<FolderCard {...defaultProps} />);

    const svgs = container.querySelectorAll("svg");
    expect(svgs.length).toBeGreaterThan(0);
    const folderSvg = container.querySelector("svg.text-neon-blue");
    expect(folderSvg).toBeInTheDocument();
  });

  it("calls onClick when card is clicked", async () => {
    const user = userEvent.setup();
    render(<FolderCard {...defaultProps} name="Test" />);

    const buttons = screen.getAllByRole("button");
    const cardButton = buttons[0]!;
    await user.click(cardButton);

    expect(mockOnClick).toHaveBeenCalledTimes(1);
  });

  it("calls onMove when rename/move button is clicked", async () => {
    const user = userEvent.setup();
    render(<FolderCard {...defaultProps} />);

    const moveButton = screen.getByTitle("Rename / Move");
    await user.click(moveButton);

    expect(mockOnMove).toHaveBeenCalledTimes(1);
    expect(mockOnClick).not.toHaveBeenCalled();
  });

  it("calls onDelete when delete button is clicked", async () => {
    const user = userEvent.setup();
    render(<FolderCard {...defaultProps} />);

    const deleteButton = screen.getByTitle("Delete");
    await user.click(deleteButton);

    expect(mockOnDelete).toHaveBeenCalledTimes(1);
    expect(mockOnClick).not.toHaveBeenCalled();
  });

  it("renders rename/move and delete action buttons", () => {
    render(<FolderCard {...defaultProps} />);

    expect(screen.getByTitle("Rename / Move")).toBeInTheDocument();
    expect(screen.getByTitle("Delete")).toBeInTheDocument();
  });

  it("truncates long folder names", () => {
    const longName = "This is a very long folder name that should be truncated";
    render(<FolderCard {...defaultProps} name={longName} />);

    const text = screen.getByText(longName);
    expect(text).toHaveClass("truncate");
  });

  it("shows full name in title attribute", () => {
    const folderName = "Important Documents";
    render(<FolderCard {...defaultProps} name={folderName} />);

    const text = screen.getByText(folderName);
    expect(text).toHaveAttribute("title", folderName);
  });

  it("has correct styling classes", () => {
    render(<FolderCard {...defaultProps} name="Test" />);

    const buttons = screen.getAllByRole("button");
    const cardButton = buttons[0]!;
    expect(cardButton).toHaveClass("group", "flex", "flex-col", "items-center");
    expect(cardButton).toHaveClass("hover:bg-background-secondary");
  });

  it("has focus-visible ring for accessibility", () => {
    render(<FolderCard {...defaultProps} name="Test" />);

    const buttons = screen.getAllByRole("button");
    const cardButton = buttons[0]!;
    expect(cardButton).toHaveClass("focus-visible:ring-2");
    expect(cardButton).toHaveClass("focus-visible:ring-border-accent");
  });

  it("handles special characters in folder name", () => {
    const specialName = "Folder-with_special.chars!@#";
    render(<FolderCard {...defaultProps} name={specialName} />);

    expect(screen.getByText(specialName)).toBeInTheDocument();
  });
});
