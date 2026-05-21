import type { CSSProperties } from "react";

// ── Palette ──────────────────────────────────────────────
export const COLOR = {
  bg: "#F7F6F2", // page background
  card: "#FFFFFF", // card / panel surface
  textPrimary: "#1A1A1A",
  textSecondary: "#595F6B",
  accent: "#4A6FA5", // interactive, active states
  accentLight: "#EEF3FA", // active tab bg, hover bg
  border: "#E5E3DC",
  success: "#4CAF82",
  successBg: "#D1FAE5",
  successText: "#065F46",
  successBorder: "#A7F3D0",
  warning: "#F59E0B",
  warningBg: "#FEF3C7",
  warningText: "#92400E",
  error: "#E05252",
  errorBg: "#FEE2E2",
  errorText: "#991B1B",
  errorBorder: "#FECACA",
} as const;

export const FONT = {
  system: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  mono: '"SF Mono", "Fira Code", "Fira Mono", "Roboto Mono", ui-monospace, monospace',
} as const;

// ── Shared component styles ───────────────────────────────
export const cardStyle: CSSProperties = {
  background: COLOR.card,
  border: `1px solid ${COLOR.border}`,
  borderRadius: 10,
  padding: 20,
};

export const emptyStateCardStyle: CSSProperties = {
  background: COLOR.card,
  border: `1px solid ${COLOR.border}`,
  borderRadius: 10,
  padding: 24,
  textAlign: "center",
  fontSize: 14,
  color: "#6B7280",
};

export const sectionHeadingStyle: CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  color: COLOR.textSecondary,
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  marginBottom: 12,
};

export const secondaryBtnStyle: CSSProperties = {
  background: COLOR.card,
  color: COLOR.textPrimary,
  border: `1px solid ${COLOR.border}`,
  borderRadius: 8,
  padding: "8px 14px",
  fontSize: 14,
  cursor: "pointer",
  fontFamily: FONT.system,
  textDecoration: "none",
  display: "inline-block",
};

export const primaryBtnStyle: CSSProperties = {
  background: COLOR.accent,
  color: "#FFFFFF",
  border: "none",
  borderRadius: 8,
  padding: "10px 18px",
  fontWeight: 600,
  fontSize: 15,
  cursor: "pointer",
  fontFamily: FONT.system,
};
