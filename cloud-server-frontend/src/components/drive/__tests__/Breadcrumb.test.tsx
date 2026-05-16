import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import Breadcrumb from "@/components/drive/Breadcrumb";

describe("Breadcrumb", () => {
  const mockOnNavigate = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders root path correctly", () => {
    render(<Breadcrumb path="." onNavigate={mockOnNavigate} />);

    const driveButton = screen.getByRole("button", { name: "Drive" });
    expect(driveButton).toBeInTheDocument();
    expect(driveButton).toHaveClass("font-semibold", "text-text-primary");
  });

  it("renders single-level path correctly", () => {
    render(<Breadcrumb path="folder1" onNavigate={mockOnNavigate} />);

    expect(screen.getByRole("button", { name: "Drive" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "folder1" })).toBeInTheDocument();
    expect(screen.getAllByText("/")).toHaveLength(1);
  });

  it("renders multi-level path correctly", () => {
    render(
      <Breadcrumb path="folder1/subfolder/deep" onNavigate={mockOnNavigate} />
    );

    expect(screen.getByRole("button", { name: "Drive" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "folder1" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "subfolder" })
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "deep" })).toBeInTheDocument();
    expect(screen.getAllByText("/")).toHaveLength(3);
  });

  it("highlights last segment in path", () => {
    render(<Breadcrumb path="folder1/folder2" onNavigate={mockOnNavigate} />);

    const folder1 = screen.getByRole("button", { name: "folder1" });
    const folder2 = screen.getByRole("button", { name: "folder2" });

    expect(folder1).toHaveClass("text-text-secondary");
    expect(folder2).toHaveClass("font-semibold", "text-text-primary");
  });

  it("calls onNavigate with root path when Drive is clicked", async () => {
    const user = userEvent.setup();
    render(<Breadcrumb path="folder1/folder2" onNavigate={mockOnNavigate} />);

    const driveButton = screen.getByRole("button", { name: "Drive" });
    await user.click(driveButton);

    expect(mockOnNavigate).toHaveBeenCalledWith(".");
    expect(mockOnNavigate).toHaveBeenCalledTimes(1);
  });

  it("calls onNavigate with correct path when intermediate segment is clicked", async () => {
    const user = userEvent.setup();
    render(
      <Breadcrumb path="folder1/folder2/folder3" onNavigate={mockOnNavigate} />
    );

    const folder2Button = screen.getByRole("button", { name: "folder2" });
    await user.click(folder2Button);

    expect(mockOnNavigate).toHaveBeenCalledWith("folder1/folder2");
    expect(mockOnNavigate).toHaveBeenCalledTimes(1);
  });

  it("calls onNavigate when last segment is clicked", async () => {
    const user = userEvent.setup();
    render(<Breadcrumb path="folder1/folder2" onNavigate={mockOnNavigate} />);

    const folder2Button = screen.getByRole("button", { name: "folder2" });
    await user.click(folder2Button);

    expect(mockOnNavigate).toHaveBeenCalledWith("folder1/folder2");
    expect(mockOnNavigate).toHaveBeenCalledTimes(1);
  });

  it("applies correct hover styles to segments", () => {
    render(<Breadcrumb path="folder1" onNavigate={mockOnNavigate} />);

    const driveButton = screen.getByRole("button", { name: "Drive" });
    const folder1Button = screen.getByRole("button", { name: "folder1" });

    expect(driveButton).toHaveClass("hover:text-text-primary");
    expect(folder1Button).toHaveClass("hover:text-text-primary");
  });

  it("has correct aria-label for navigation", () => {
    const { container } = render(
      <Breadcrumb path="folder1" onNavigate={mockOnNavigate} />
    );

    const nav = container.querySelector("nav");
    expect(nav).toHaveAttribute("aria-label", "Directory path");
  });
});
