import { afterEach, describe, expect, it, vi } from "vitest";
import { verifyComposition } from "../../src/lib/api";
import type { VerifyResponse } from "../../src/lib/types";

const okResponse: VerifyResponse = {
  status: "pass",
  outcome: null,
  bells: 4,
  block_size: 1,
  repeats: 2,
  total_steps: 2,
  block_order: 2,
  witness: null,
  final_row: null,
};

afterEach(() => vi.restoreAllMocks());

describe("verifyComposition", () => {
  it("POSTs JSON to /api/verify and parses the response", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: () => Promise.resolve(okResponse),
    }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await verifyComposition({ bells: 4, repeats: 2, block: [[2, 1, 3, 4]] });
    expect(result).toEqual(okResponse);
    expect(fetchMock).toHaveBeenCalledOnce();
    const call = fetchMock.mock.calls[0] as unknown as [
      string,
      { method: string; headers: Record<string, string>; body: string },
    ];
    const [url, init] = call;
    expect(url).toBe("/api/verify");
    expect(init.method).toBe("POST");
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(init.body)).toEqual({
      bells: 4,
      repeats: 2,
      block: [[2, 1, 3, 4]],
    });
  });

  it("maps a 422 body to an error carrying message and field", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: false,
      status: 422,
      json: () =>
        Promise.resolve({
          error: { message: "bad permutation", field: "block[2]" },
        }),
    })));
    await expect(
      verifyComposition({ bells: 4, repeats: 1, block: [[2, 1, 3, 4]] })
    ).rejects.toEqual({ message: "bad permutation", field: "block[2]" });
  });

  it("falls back to a generic message for a non-JSON error response", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error("not json")),
    })));
    await expect(
      verifyComposition({ bells: 4, repeats: 1, block: [[2, 1, 3, 4]] })
    ).rejects.toMatchObject({ message: /HTTP 500/, field: "" });
  });
});
