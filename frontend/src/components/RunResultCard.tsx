import React from "react";
import type { AgentRunReport } from "../lib/api";
import { shortStatusLabel, classifyRunStatusTone, RUN_STATUS_PILL_STYLES } from "../lib/runStatusCopy";
import { COLOR, FONT, cardStyle, sectionHeadingStyle } from "../lib/theme";

type Props = {
  run: AgentRunReport;
};

const errorPanelStyle: React.CSSProperties = {
  padding: "10px 12px",
  background: COLOR.errorBg,
  border: `1px solid ${COLOR.errorBorder}`,
  borderRadius: 8,
  fontSize: 13,
  color: COLOR.errorText,
  marginBottom: 8,
};

/** Shared per-run display for `/agent/ask` and `/agent/execute` responses (Iteration 18 architect review). */
export function RunResultCard({ run }: Props) {
  const queueWarnings = run.queue_warnings ?? [];
  const generateWarnings = run.generate_warnings ?? [];
  const hasWarnings = queueWarnings.length > 0 || generateWarnings.length > 0;

  return (
    <div style={cardStyle}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 8,
          marginBottom: 10,
        }}
      >
        <div style={{ fontWeight: 600, fontSize: 15, color: COLOR.textPrimary }}>{run.label || "Run"}</div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            style={{
              ...RUN_STATUS_PILL_STYLES[classifyRunStatusTone(run.status)],
              borderRadius: 999,
              padding: "3px 10px",
              fontSize: 12,
              fontWeight: 500,
            }}
          >
            {shortStatusLabel(run.status)}
          </span>
          {run.simulation_id ? (
            <span style={{ fontFamily: FONT.mono, fontSize: 11, color: COLOR.textSecondary }}>
              {run.simulation_id.slice(0, 10)}…
            </span>
          ) : null}
        </div>
      </div>
      {run.failure_reason ? (
        <div style={errorPanelStyle}>
          <strong>Something went wrong:</strong> {run.failure_reason}
        </div>
      ) : null}
      {run.analysis_error ? (
        <div style={errorPanelStyle}>
          <strong>Something went wrong:</strong> {run.analysis_error}
        </div>
      ) : null}
      {hasWarnings ? (
        <div style={{ marginBottom: 8 }}>
          <div style={sectionHeadingStyle}>Warnings</div>
          <ul
            style={{
              margin: 0,
              paddingLeft: 18,
              fontSize: 12,
              color: COLOR.textPrimary,
              lineHeight: 1.45,
            }}
          >
            {queueWarnings.map((w, j) => (
              <li key={`q-${j}`}>{w}</li>
            ))}
            {generateWarnings.map((w, j) => (
              <li key={`g-${j}`}>{w}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {run.analysis?.key_findings?.length ? (
        <div style={{ fontSize: 14, marginTop: hasWarnings || run.failure_reason || run.analysis_error ? 4 : 0 }}>
          <div style={{ fontWeight: 600, fontSize: 14, color: COLOR.textPrimary, marginBottom: 6 }}>Key findings</div>
          <ul
            style={{
              margin: 0,
              paddingLeft: 18,
              color: COLOR.textPrimary,
              fontSize: 14,
              lineHeight: 1.5,
            }}
          >
            {run.analysis.key_findings.map((k, j) => (
              <li key={j}>{k}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {run.analysis?.trajectory_narrative ? (
        <div style={{ fontSize: 14, marginTop: 8 }}>
          <div style={{ fontWeight: 600, fontSize: 14, color: COLOR.textPrimary, marginBottom: 6 }}>Summary</div>
          <p style={{ margin: "6px 0 0", whiteSpace: "pre-wrap", color: COLOR.textPrimary }}>{run.analysis.trajectory_narrative}</p>
        </div>
      ) : null}
      {run.analysis?.suggested_follow_ups?.length ? (
        <div style={{ fontSize: 13, marginTop: 8 }}>
          <div style={{ fontWeight: 600, fontSize: 13, color: COLOR.textSecondary, marginBottom: 4 }}>
            Suggested next questions
          </div>
          <ul
            style={{
              margin: 0,
              paddingLeft: 18,
              color: COLOR.textPrimary,
              fontSize: 13,
              lineHeight: 1.45,
            }}
          >
            {run.analysis.suggested_follow_ups.map((u, j) => (
              <li key={j}>{u}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
