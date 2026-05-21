import React from "react";
import { getRunStatusLabel } from "../lib/runStatusCopy";

export type RunStatusCardProps = {
  status: string;
  runId: string | null;
  currentRound: number;
  totalRounds: number;
  convergedAtRound: number | null;
  transcriptLength: number;
  failureReason: string | null;
  onOpenLive: () => void;
  onOpenConversation: () => void;
};

const secondaryBtn: React.CSSProperties = {
  background: "#FFFFFF",
  color: "#1A1A1A",
  border: "1px solid #E5E3DC",
  borderRadius: 8,
  padding: "8px 14px",
  fontSize: 14,
  cursor: "pointer",
  fontFamily: "inherit",
  textDecoration: "none",
  display: "inline-block",
};

export function RunStatusCard({
  status,
  runId,
  currentRound,
  totalRounds,
  convergedAtRound,
  transcriptLength,
  failureReason,
  onOpenLive,
  onOpenConversation,
}: RunStatusCardProps) {
  const empty = runId === null && status === "idle";

  if (empty) {
    return (
      <div
        style={{
          background: "#FFFFFF",
          border: "1px solid #E5E3DC",
          borderRadius: 10,
          padding: 24,
          textAlign: "center",
          fontSize: 14,
          color: "#6B7280",
        }}
      >
        No discussion running yet.
        <br />
        Set up your parameters above and press &quot;Start discussion&quot; to begin.
      </div>
    );
  }

  const barPct = totalRounds > 0 ? Math.round((currentRound / totalRounds) * 100) : 0;
  const barColor = status === "completed" ? "#4CAF82" : "#4A6FA5";

  return (
    <div
      style={{
        background: "#FFFFFF",
        border: "1px solid #E5E3DC",
        borderRadius: 10,
        padding: 24,
      }}
    >
      <div style={{ fontSize: 15, color: "#1A1A1A", lineHeight: 1.45 }}>
        {getRunStatusLabel(status, { currentRound, totalRounds, convergedAtRound })}
      </div>

      {runId ? (
        <div style={{ margin: "12px 0" }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#6B7280", marginBottom: 4 }}>
            <span>Progress</span>
            <span>
              Round {currentRound} of {totalRounds}
            </span>
          </div>
          <div style={{ background: "#E5E3DC", borderRadius: 999, height: 6, overflow: "hidden" }}>
            <div
              style={{
                background: barColor,
                borderRadius: 999,
                height: "100%",
                width: `${barPct}%`,
                transition: "width 0.4s ease",
              }}
            />
          </div>
        </div>
      ) : null}

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
        <button type="button" style={secondaryBtn} onClick={onOpenLive}>
          Watch Live
        </button>
        {transcriptLength > 0 ? (
          <button type="button" style={secondaryBtn} onClick={onOpenConversation}>
            View Conversation
          </button>
        ) : null}
      </div>

      {failureReason ? (
        <div style={{ marginTop: 12, padding: 12, background: "#FEE2E2", borderRadius: 8, fontSize: 13, color: "#991B1B" }}>
          <strong>Something went wrong:</strong> {failureReason}
        </div>
      ) : null}
    </div>
  );
}
