import React from "react";
import { classifyRunStatusTone, getRunStatusLabel, RUN_STATUS_PILL_STYLES } from "../lib/runStatusCopy";

export type SennaHeaderProps = {
  status: string;
  currentRound: number;
  totalRounds: number;
  convergedAtRound: number | null;
};

export function SennaHeader({ status, currentRound, totalRounds, convergedAtRound }: SennaHeaderProps) {
  const tone = classifyRunStatusTone(status);
  const pillLabel = getRunStatusLabel(status, { currentRound, totalRounds, convergedAtRound });

  return (
    <header
      style={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: 16,
        marginBottom: 20,
        paddingBottom: 12,
        borderBottom: "1px solid #E5E3DC",
        background: "#F7F6F2",
      }}
    >
      <div style={{ display: "flex", gap: 10, alignItems: "flex-start", minWidth: 0 }}>
        <div
          style={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: "#4A6FA5",
            marginTop: 8,
            flexShrink: 0,
          }}
          aria-hidden
        />
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
              fontSize: 22,
              fontWeight: 600,
              color: "#1A1A1A",
              letterSpacing: "-0.3px",
              lineHeight: 1.2,
            }}
          >
            Senna
          </div>
          <div style={{ fontSize: 13, color: "#595F6B", fontWeight: 400, marginTop: 2 }}>
            Policy simulation platform
          </div>
        </div>
      </div>
      <div
        style={{
          ...RUN_STATUS_PILL_STYLES[tone],
          borderRadius: 999,
          padding: "3px 10px",
          fontSize: 12,
          fontWeight: 500,
          maxWidth: "min(420px, 52vw)",
          textAlign: "right",
          lineHeight: 1.35,
          flexShrink: 0,
        }}
      >
        {pillLabel}
      </div>
    </header>
  );
}
