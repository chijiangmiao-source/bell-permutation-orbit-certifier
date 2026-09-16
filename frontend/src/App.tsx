import { useRef, useState } from "react";
import { verifyComposition } from "./lib/api";
import {
  MAX_REPEATS,
  parseInput,
  type InputError,
} from "./lib/parse";
import type { VerifyResponse } from "./lib/types";
import { ResultPanel } from "./components/ResultPanel";

const BLOCK_LINE_RE = /block\[(\d+)\]/;

export default function App() {
  const [bells, setBells] = useState("4");
  const [repeats, setRepeats] = useState("2");
  const [blockText, setBlockText] = useState("2 1 3 4");
  const [result, setResult] = useState<VerifyResponse | null>(null);
  const [error, setError] = useState<InputError | null>(null);
  const [loading, setLoading] = useState(false);

  const bellsRef = useRef<HTMLInputElement>(null);
  const repeatsRef = useRef<HTMLInputElement>(null);
  const blockRef = useRef<HTMLTextAreaElement>(null);

  function locateError(field: string) {
    if (field === "bells") {
      bellsRef.current?.focus();
      bellsRef.current?.select();
      return;
    }
    if (field === "repeats") {
      repeatsRef.current?.focus();
      repeatsRef.current?.select();
      return;
    }
    const area = blockRef.current;
    if (area) {
      area.focus();
      const match = BLOCK_LINE_RE.exec(field);
      if (match) {
        const lines = area.value.split(/\r?\n/);
        const index = Number(match[1]);
        let start = 0;
        for (let i = 0; i < index && i < lines.length; i++) {
          start += lines[i].length + 1;
        }
        const end = start + (lines[Math.min(index, lines.length - 1)]?.length ?? 0);
        area.setSelectionRange(start, end);
      }
    }
  }

  function showError(next: InputError) {
    // Errors must clear any stale result so only canonical evidence remains.
    setResult(null);
    setError(next);
    locateError(next.field);
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const parsed = parseInput(bells, repeats, blockText);
    if (!parsed.ok) {
      showError(parsed.error);
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const response = await verifyComposition(parsed.request);
      setResult(response);
      setError(null);
    } catch (err) {
      const apiError = err as InputError;
      showError({
        message: apiError.message ?? "请求失败",
        field: apiError.field ?? "",
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <h1>换位块真值验真</h1>
      <p className="semantics">
        行从升序钟号开始，每步按换位 p 令新行第 i 位取旧行第 p[i] 位，依 block
        循环 N = 块长 × repeats 步；仅比较第 0 至 N-1 步，第 N 步只用于归位判定。
      </p>

      <form onSubmit={handleSubmit} noValidate className="form">
        <label className={error?.field === "bells" ? "field invalid" : "field"}>
          <span>钟数 bells（4–12）</span>
          <input
            ref={bellsRef}
            type="text"
            inputMode="numeric"
            value={bells}
            aria-invalid={error?.field === "bells"}
            onChange={(e) => setBells(e.target.value)}
          />
        </label>

        <label
          className={error?.field === "repeats" ? "field invalid" : "field"}
        >
          <span>重复次数 repeats（1–{MAX_REPEATS.toLocaleString("en-US")}）</span>
          <input
            ref={repeatsRef}
            type="text"
            inputMode="numeric"
            value={repeats}
            aria-invalid={error?.field === "repeats"}
            onChange={(e) => setRepeats(e.target.value)}
          />
        </label>

        <label
          className={
            error?.field === "block" || BLOCK_LINE_RE.test(error?.field ?? "")
              ? "field invalid"
              : "field"
          }
        >
          <span>
            block：共 1–5000 行，每行一个长度为 bells 的置换（恰含 1..bells）
          </span>
          <textarea
            ref={blockRef}
            rows={8}
            spellCheck={false}
            value={blockText}
            aria-invalid={error?.field.startsWith("block")}
            onChange={(e) => setBlockText(e.target.value)}
          />
        </label>

        {error && (
          <p className="error" data-testid="error" role="alert">
            <strong>{error.field || "请求错误"}：</strong>
            {error.message}
          </p>
        )}

        <button type="submit" disabled={loading}>
          {loading ? "验真中…" : "开始验真"}
        </button>
      </form>

      {result !== null && <ResultPanel result={result} />}
    </main>
  );
}
