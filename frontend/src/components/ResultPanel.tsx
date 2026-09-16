import type { VerifyResponse } from "../lib/types";
import { formatInteger, formatRow } from "../lib/parse";

interface ResultPanelProps {
  result: VerifyResponse;
}

export function ResultPanel({ result }: ResultPanelProps) {
  const passed = result.status === "pass";
  return (
    <section
      className={`result ${passed ? "result-pass" : "result-fail"}`}
      data-testid="result-panel"
      aria-live="assertive"
    >
      <h2 data-testid="result-status">
        {passed ? "通过：全程无重复且归位" : "失败"}
      </h2>
      {!passed && result.outcome === "collision" && (
        <p className="outcome" data-testid="result-outcome">
          跨轮或同轮撞回旧行
        </p>
      )}
      {!passed && result.outcome === "not_home" && (
        <p className="outcome" data-testid="result-outcome">
          无重复，但第 N 步未回到初始行
        </p>
      )}

      <dl className="facts">
        <div>
          <dt>块置换阶</dt>
          <dd data-testid="fact-order">{formatInteger(result.block_order)}</dd>
        </div>
        <div>
          <dt>总步数 N</dt>
          <dd data-testid="fact-total">{formatInteger(result.total_steps)}</dd>
        </div>
      </dl>

      {result.witness !== null && (
        <div className="witness" data-testid="witness">
          <h3>重复见证</h3>
          <p>
            第{" "}
            <strong data-testid="witness-second">
              {formatInteger(result.witness.second_step)}
            </strong>{" "}
            步与第{" "}
            <strong data-testid="witness-first">
              {formatInteger(result.witness.first_step)}
            </strong>{" "}
            步同行（先按第二次步号最小、再按第一次步号最小选取）：
          </p>
          <pre data-testid="witness-row">
            {formatRow(result.witness.row)}
          </pre>
        </div>
      )}

      {result.final_row !== null && (
        <div className="final-row" data-testid="final-row">
          <h3>末行（第 N 步）</h3>
          <pre>{formatRow(result.final_row)}</pre>
        </div>
      )}

      {passed && (
        <p className="trillion-note" data-testid="trillion-note">
          已在至多 {formatInteger(result.repeats)} 次重复内完成精确判据：无冲突且归位。
        </p>
      )}
    </section>
  );
}
