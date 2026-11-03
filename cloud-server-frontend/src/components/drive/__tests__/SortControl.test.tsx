import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import SortControl from "@/components/drive/SortControl";

describe("SortControl", () => {
  it("changes the sort key", async () => {
    const onChange = jest.fn();
    render(
      <SortControl
        value={{ key: "name", direction: "asc" }}
        onChange={onChange}
      />
    );
    await userEvent.selectOptions(screen.getByLabelText("Sort by"), "created");
    expect(onChange).toHaveBeenCalledWith({ key: "created", direction: "asc" });
  });

  it("toggles the direction", async () => {
    const onChange = jest.fn();
    render(
      <SortControl
        value={{ key: "created", direction: "asc" }}
        onChange={onChange}
      />
    );
    await userEvent.click(screen.getByRole("button", { name: "Ascending" }));
    expect(onChange).toHaveBeenCalledWith({
      key: "created",
      direction: "desc",
    });
  });
});
