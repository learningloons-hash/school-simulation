import React from "react";

type SparklineProps = {
  values: number[];
  width?: number;
  height?: number;
  color?: string;
  label?: string;
};

/** Minimal SVG sparkline — no chart library dependency. */
export function Sparkline({ values, width = 140, height = 36, color = "#2563eb", label }: SparklineProps) {
  if (values.length === 0) {
    return <span style={{ opacity: 0.45, fontSize: 12 }}>—</span>;
  }
  if (values.length === 1) {
    return (
      <span style={{ fontSize: 12, fontFamily: "monospace" }} title={label}>
        {values[0].toFixed(2)}
      </span>
    );
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pad = 2;
  const w = width - 2 * pad;
  const h = height - 2 * pad;
  const pts = values
    .map((v, i) => {
      const x = pad + (i / (values.length - 1)) * w;
      const y = pad + h - ((v - min) / span) * h;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg width={width} height={height} style={{ verticalAlign: "middle", display: "inline-block" }} aria-hidden title={label}>
      <polyline fill="none" stroke={color} strokeWidth="2" points={pts} />
    </svg>
  );
}
