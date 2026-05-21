import type { CSSProperties } from "react";

/** Plain-English run status for UI (Senna Arc 1 — senna-iter-4 / senna-iter-5). */

export type RunStatusPillTone = "idle" | "active" | "success" | "danger";

/** Shared pill colours for status badges (header, run history, etc.). */
export const RUN_STATUS_PILL_STYLES: Record<RunStatusPillTone, CSSProperties> = {
  idle: { background: "#E5E3DC", color: "#1A1A1A" },
  active: { background: "#FEF3C7", color: "#92400E" },
  success: { background: "#D1FAE5", color: "#065F46" },
  danger: { background: "#FEE2E2", color: "#991B1B" },
};

/** Short label for compact history / list badges. */
export function shortStatusLabel(status: string): string {
  if (status === "completed") return "Finished";
  if (status === "running") return "In progress";
  if (status === "failed") return "Failed";
  if (status === "starting") return "Starting";
  if (status.startsWith("error:")) return "Error";
  return status;
}

export function classifyRunStatusTone(status: string): RunStatusPillTone {
  if (status === "completed") return "success";
  if (status === "failed" || status === "timeout" || status.startsWith("error:")) return "danger";
  if (status === "running" || status === "starting") return "active";
  return "idle";
}

export function getRunStatusLabel(
  status: string,
  opts: { currentRound: number; totalRounds: number; convergedAtRound: number | null },
): string {
  const { currentRound, totalRounds, convergedAtRound } = opts;
  if (status === "idle") return "Ready to start a new discussion.";
  if (status === "starting") return "Starting up…";
  if (status === "running") {
    return `Discussion in progress — Round ${currentRound} of ${totalRounds} underway.`;
  }
  if (status === "completed") {
    if (typeof convergedAtRound === "number") {
      return `Finished! Consensus reached at Round ${convergedAtRound}.`;
    }
    return `Finished! All ${totalRounds} rounds completed.`;
  }
  if (status === "failed") return "Something went wrong. See Run Details for more information.";
  if (status === "timeout") {
    return "The run timed out after too long without a response. Check your AI model connection.";
  }
  if (status.startsWith("error:")) {
    const rest = status.slice("error:".length).trim();
    return `Error: ${rest}.`;
  }
  return status;
}

export function getProgressLine(status: string, currentRound: number, totalRounds: number): string {
  if (status === "idle" && currentRound === 0) return "Not started yet";
  return `Round ${currentRound} of ${totalRounds} complete`;
}
