import { describe, expect, it } from "vitest";
import { parseInput } from "../../src/lib/parse";

describe("parseInput", () => {
  it("accepts a valid request", () => {
    const result = parseInput("4", "2", "2 1 3 4");
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.request).toEqual({
        bells: 4,
        repeats: 2,
        block: [[2, 1, 3, 4]],
      });
    }
  });

  it("accepts comma and whitespace separated bells and multiple lines", () => {
    const result = parseInput("5", "3", "2 1 3 5 4\n1,2,4,3,5");
    expect(result.ok).toBe(true);
  });

  it("accepts repeats up to one trillion exactly", () => {
    const result = parseInput("4", "1000000000000", "2 1 3 4");
    expect(result.ok).toBe(true);
  });

  it("rejects non-integer bells and points at bells field", () => {
    const result = parseInput("4.5", "2", "2 1 3 4");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.field).toBe("bells");
  });

  it("rejects bells below 4", () => {
    const result = parseInput("3", "2", "2 1 3");
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.field).toBe("bells");
    }
  });

  it("rejects bells above 12", () => {
    const row = Array.from({ length: 13 }, (_, i) => i + 1).join(" ");
    const result = parseInput("13", "2", row);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.field).toBe("bells");
  });

  it("rejects zero repeats", () => {
    const result = parseInput("4", "0", "2 1 3 4");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.field).toBe("repeats");
  });

  it("rejects repeats above one trillion", () => {
    const result = parseInput("4", "1000000000001", "2 1 3 4");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.field).toBe("repeats");
  });

  it("rejects an empty block", () => {
    const result = parseInput("4", "2", "  \n  ");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.field).toBe("block");
  });

  it("locates the first bad row by index for wrong length", () => {
    const result = parseInput("4", "2", "2 1 3 4\n2 1 4");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.field).toBe("block[1]");
  });

  it("locates the first bad row by index for duplicate bells", () => {
    const result = parseInput("4", "2", "2 2 3 4");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.field).toBe("block[0]");
  });

  it("locates the first bad row for out-of-range bells", () => {
    const result = parseInput("4", "2", "5 1 3 4");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.field).toBe("block[0]");
  });

  it("stops at the first invalid row even when later rows are also bad", () => {
    const result = parseInput("4", "2", "1 1 1 1\n9");
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.field).toBe("block[0]");
  });
});
