import type { VerifyRequest } from "./types";

export const MIN_BELLS = 4;
export const MAX_BELLS = 12;
export const MIN_BLOCK_SIZE = 1;
export const MAX_BLOCK_SIZE = 5000;
export const MIN_REPEATS = 1;
export const MAX_REPEATS = 1_000_000_000_000;

export interface InputError {
  message: string;
  field: string; // "bells" | "repeats" | "block" | "block[i]"
}

export type ParseResult =
  | { ok: true; request: VerifyRequest }
  | { ok: false; error: InputError };

const INTEGER_RE = /^\d+$/;

function parseStrictInteger(text: string, field: string): number | InputError {
  const trimmed = text.trim();
  if (!INTEGER_RE.test(trimmed)) {
    return { message: `${field} 必须是整数`, field };
  }
  return Number(trimmed); // exact for values up to 10**12
}

/**
 * Parse and validate the whole form. On failure the error points at the
 * first offending item: scalar fields by name, the first bad change row by
 * block[index].
 */
export function parseInput(
  bellsText: string,
  repeatsText: string,
  blockText: string
): ParseResult {
  const bellsParsed = parseStrictInteger(bellsText, "bells");
  if (typeof bellsParsed !== "number") {
    return { ok: false, error: { ...bellsParsed, message: "钟数必须是整数" } };
  }
  const bells = bellsParsed;
  if (bells < MIN_BELLS || bells > MAX_BELLS) {
    return {
      ok: false,
      error: {
        message: `钟数必须在 ${MIN_BELLS} 至 ${MAX_BELLS} 之间`,
        field: "bells",
      },
    };
  }

  const repeatsParsed = parseStrictInteger(repeatsText, "repeats");
  if (typeof repeatsParsed !== "number") {
    return {
      ok: false,
      error: { message: "重复次数必须是整数", field: "repeats" },
    };
  }
  const repeats = repeatsParsed;
  if (repeats < MIN_REPEATS || repeats > MAX_REPEATS) {
    return {
      ok: false,
      error: {
        message: `重复次数必须在 ${MIN_REPEATS} 至 ${MAX_REPEATS.toLocaleString(
          "en-US"
        )} 之间`,
        field: "repeats",
      },
    };
  }

  const lines = blockText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  if (lines.length < MIN_BLOCK_SIZE) {
    return {
      ok: false,
      error: { message: "block 至少包含 1 个换位", field: "block" },
    };
  }
  if (lines.length > MAX_BLOCK_SIZE) {
    return {
      ok: false,
      error: {
        message: `block 至多包含 ${MAX_BLOCK_SIZE.toLocaleString("en-US")} 个换位`,
        field: "block",
      },
    };
  }

  const required = new Set<number>();
  for (let i = 1; i <= bells; i++) required.add(i);
  const block: number[][] = [];

  for (let index = 0; index < lines.length; index++) {
    const tokens = lines[index].split(/[\s,]+/).filter((t) => t.length > 0);
    const row: number[] = [];
    let bad = false;
    for (const token of tokens) {
      if (!INTEGER_RE.test(token)) {
        bad = true;
        break;
      }
      row.push(Number(token));
    }
    if (bad || row.length !== bells || new Set(row).size !== bells) {
      return {
        ok: false,
        error: {
          message: `block[${index}] 必须是 1..${bells} 的置换（${bells} 个互不重复的钟号）`,
          field: `block[${index}]`,
        },
      };
    }
    for (const bell of row) {
      if (!required.has(bell)) {
        return {
          ok: false,
          error: {
            message: `block[${index}] 必须恰含 1..${bells} 的每个钟号`,
            field: `block[${index}]`,
          },
        };
      }
    }
    block.push(row);
  }

  return { ok: true, request: { bells, repeats, block } };
}

export function formatRow(row: number[]): string {
  return row.join(" ");
}

export function formatInteger(value: number): string {
  return value.toLocaleString("en-US");
}
