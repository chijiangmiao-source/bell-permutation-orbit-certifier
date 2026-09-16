import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "../../src/App";
import type { VerifyResponse } from "../../src/lib/types";

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  };
}

const collision: VerifyResponse = {
  status: "fail",
  outcome: "collision",
  bells: 4,
  block_size: 1,
  repeats: 3,
  total_steps: 3,
  block_order: 2,
  witness: { first_step: 0, second_step: 2, row: [1, 2, 3, 4] },
  final_row: null,
};

const notHome: VerifyResponse = {
  status: "fail",
  outcome: "not_home",
  bells: 4,
  block_size: 1,
  repeats: 1,
  total_steps: 1,
  block_order: 3,
  witness: null,
  final_row: [2, 3, 1, 4],
};

const trillionPass: VerifyResponse = {
  status: "pass",
  outcome: null,
  bells: 4,
  block_size: 2,
  repeats: 1_000_000_000_000,
  total_steps: 2_000_000_000_000,
  block_order: 2,
  witness: null,
  final_row: null,
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("App verification flow", () => {
  it("shows block order, total steps and the repeat witness on collision", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(collision)));
    render(<App />);

    fireEvent.change(screen.getByLabelText(/钟数/), { target: { value: "4" } });
    fireEvent.change(screen.getByLabelText(/重复次数/), { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: "开始验真" }));

    await waitFor(() =>
      expect(screen.getByTestId("result-status")).toHaveTextContent("失败")
    );
    expect(screen.getByTestId("fact-order")).toHaveTextContent("2");
    expect(screen.getByTestId("fact-total")).toHaveTextContent("3");
    expect(screen.getByTestId("witness-first")).toHaveTextContent("0");
    expect(screen.getByTestId("witness-second")).toHaveTextContent("2");
    expect(screen.getByTestId("witness-row")).toHaveTextContent("1 2 3 4");
    expect(screen.queryByTestId("final-row")).toBeNull();
  });

  it("a later invalid input clears the stale result and locates the first bad row", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(collision)));
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "开始验真" }));
    await screen.findByTestId("result-panel");

    // Introduce a malformed second change; the old result must disappear.
    const textarea = screen.getByLabelText(/block/);
    fireEvent.change(textarea, {
      target: { value: "2 1 3 4\n9 9 9 9" },
    });
    fireEvent.click(screen.getByRole("button", { name: "开始验真" }));

    await waitFor(() =>
      expect(screen.queryByTestId("result-panel")).toBeNull()
    );
    const error = screen.getByTestId("error");
    expect(error.textContent).toContain("block[1]");
    expect(textarea).toHaveFocus();
  });

  it("shows canonical not-home failure evidence with the final row only", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(notHome)));
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "开始验真" }));

    await screen.findByTestId("result-panel");
    expect(screen.getByTestId("result-outcome")).toHaveTextContent("未回到初始行");
    expect(screen.getByTestId("final-row")).toHaveTextContent("2 3 1 4");
    expect(screen.queryByTestId("witness")).toBeNull();
  });

  it("displays success for a one-trillion-repeat exact verification", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(trillionPass)));
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "开始验真" }));

    await screen.findByTestId("result-panel");
    expect(screen.getByTestId("result-status")).toHaveTextContent("通过");
    expect(screen.getByTestId("fact-total")).toHaveTextContent("2,000,000,000,000");
    expect(screen.getByTestId("trillion-note")).toHaveTextContent(
      "1,000,000,000,000"
    );
    expect(screen.queryByTestId("witness")).toBeNull();
    expect(screen.queryByTestId("final-row")).toBeNull();
  });

  it("a 422 API error clears the previous result and shows the located field", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(collision))
      .mockResolvedValueOnce(
        jsonResponse(
          { error: { message: "must be a permutation", field: "block[0]" } },
          422
        )
      );
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "开始验真" }));
    await screen.findByTestId("result-panel");

    fireEvent.click(screen.getByRole("button", { name: "开始验真" }));
    await waitFor(() =>
      expect(screen.queryByTestId("result-panel")).toBeNull()
    );
    expect(screen.getByTestId("error").textContent).toContain("block[0]");
  });

  it("local validation errors never call the API", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    fireEvent.change(screen.getByLabelText(/钟数/), { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: "开始验真" }));
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByTestId("error").textContent).toContain("bells");
  });
});
