import React from "react";
import type { AgentRunReport } from "../lib/api";

const cardStyle: React.CSSProperties = {
  padding: 10,
  border: "1px solid #e0e0e0",
  borderRadius: 6,
  background: "#fafafa",
};

type Props = {
  run: AgentRunReport;
};

/** Shared per-run display for `/agent/ask` and `/agent/execute` responses (Iteration 18 architect review). */
export function RunResultCard({ run }: Props) {
  return (
    <div style={cardStyle}>
      <div style={{ fontWeight: 600, marginBottom: 6 }}>
        {run.label} — <code>{run.status}</code>
        {run.simulation_id ? (
          <>
            {" "}
            · sim <code>{run.simulation_id}</code>
          </>
        ) : null}
      </div>
      {run.failure_reason ? (
        <div style={{ color: "#a30", fontSize: 13, marginBottom: 6 }}>Failure: {run.failure_reason}</div>
      ) : null}
      {run.analysis_error ? (
        <div style={{ color: "#a30", fontSize: 13, marginBottom: 8 }}>{run.analysis_error}</div>
      ) : null}
      {run.queue_warnings && run.queue_warnings.length > 0 ? (
        <div style={{ fontSize: 12, marginBottom: 8, opacity: 0.9 }}>
          <strong>Queue warnings</strong>
          <ul style={{ margin: "4px 0 0 18px" }}>
            {run.queue_warnings.map((w, j) => (
              <li key={j}>{w}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {run.generate_warnings && run.generate_warnings.length > 0 ? (
        <div style={{ fontSize: 12, marginBottom: 8, opacity: 0.9 }}>
          <strong>Generate warnings</strong>
          <ul style={{ margin: "4px 0 0 18px" }}>
            {run.generate_warnings.map((w, j) => (
              <li key={j}>{w}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {run.analysis?.key_findings?.length ? (
        <div style={{ fontSize: 14 }}>
          <strong>Key findings</strong>
          <ul style={{ margin: "6px 0 0 18px" }}>
            {run.analysis.key_findings.map((k, j) => (
              <li key={j}>{k}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {run.analysis?.trajectory_narrative ? (
        <div style={{ fontSize: 14, marginTop: 8 }}>
          <strong>Narrative</strong>
          <p style={{ margin: "6px 0 0", whiteSpace: "pre-wrap" }}>{run.analysis.trajectory_narrative}</p>
        </div>
      ) : null}
      {run.analysis?.suggested_follow_ups?.length ? (
        <div style={{ fontSize: 13, marginTop: 8, opacity: 0.9 }}>
          <strong>Follow-ups</strong>
          <ul style={{ margin: "4px 0 0 18px" }}>
            {run.analysis.suggested_follow_ups.map((u, j) => (
              <li key={j}>{u}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
