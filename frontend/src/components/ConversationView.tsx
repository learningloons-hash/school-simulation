import React, { useState } from "react";
import type { SimulationTurn } from "../lib/api";

const ROLE_COLORS: Record<string, string> = {
  teacher: "#4A90D9",
  principal: "#7B68EE",
  ministry_official: "#E8A838",
  ministry: "#E8A838",
  parent: "#52C278",
  researcher: "#E06666",
  academic: "#E06666",
  default: "#8B8FA8",
};

function roleColor(role: string): string {
  const key = role.toLowerCase().replace(/\s+/g, "_");
  return ROLE_COLORS[key] ?? ROLE_COLORS.default;
}

function initials(name: string): string {
  const trimmed = name.trim();
  if (!trimmed) return "?";
  return trimmed
    .split(/\s+/)
    .map((w) => w[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export type ConversationViewProps = {
  turns: SimulationTurn[];
};

function TurnBubble({
  turn,
  color,
  avatarInitials,
}: {
  turn: SimulationTurn;
  color: string;
  avatarInitials: string;
}) {
  const [open, setOpen] = useState(false);

  const roleDisplay = turn.agent_role
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div
      style={{
        background: "#FFFFFF",
        border: "1px solid #E5E3DC",
        borderRadius: 12,
        padding: "16px 20px",
        borderLeft: `4px solid ${color}`,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 8,
          marginBottom: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: "50%",
              background: color,
              color: "#FFFFFF",
              fontSize: 12,
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            {avatarInitials}
          </div>
          <span style={{ fontWeight: 600, fontSize: 15, color: "#1A1A1A" }}>{turn.agent_name}</span>
          <span
            style={{
              fontSize: 11,
              fontWeight: 500,
              color,
              background: `${color}18`,
              borderRadius: 999,
              padding: "2px 8px",
            }}
          >
            {roleDisplay}
          </span>
        </div>
        <span style={{ fontSize: 12, color: "#6B7280", flexShrink: 0 }}>Round {turn.round_number}</span>
      </div>

      <div style={{ fontSize: 15, color: "#1A1A1A", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
        {turn.raw_response}
      </div>

      <button
        type="button"
        aria-label={open ? "Hide turn details" : "Show turn details"}
        onClick={() => setOpen((v) => !v)}
        style={{
          marginTop: 12,
          fontSize: 12,
          color: "#6B7280",
          background: "none",
          border: "none",
          cursor: "pointer",
          padding: 0,
          display: "flex",
          alignItems: "center",
          gap: 4,
          fontFamily: "inherit",
        }}
      >
        {open ? "▾" : "▸"} Details
      </button>

      {open ? (
        <div
          style={{
            marginTop: 8,
            fontSize: 12,
            color: "#6B7280",
            display: "grid",
            gap: 4,
            padding: "10px 12px",
            background: "#F7F6F2",
            borderRadius: 8,
          }}
        >
          {turn.interaction_type ? (
            <div>Interaction: {turn.interaction_type.replace(/_/g, " ")}</div>
          ) : null}
          {turn.target_agent_name ?? turn.target_scope ? (
            <div>Directed to: {turn.target_agent_name ?? turn.target_scope}</div>
          ) : null}
          {turn.intent_tag ? <div>Intent: {turn.intent_tag.replace(/_/g, " ")}</div> : null}
          {turn.fidelity_tier != null ? <div>Detail level: {turn.fidelity_tier}</div> : null}
          {turn.effective_provider || turn.effective_model ? (
            <div>AI model: {[turn.effective_provider, turn.effective_model].filter(Boolean).join(" / ")}</div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function ConversationView({ turns }: ConversationViewProps) {
  if (!turns || turns.length === 0) return null;

  return (
    <div style={{ display: "grid", gap: 16 }}>
      {turns.map((t, idx) => {
        const color = roleColor(t.agent_role);
        const avatarInitials = initials(t.agent_name);
        return <TurnBubble key={`${t.id ?? "turn"}-${idx}`} turn={t} color={color} avatarInitials={avatarInitials} />;
      })}
    </div>
  );
}
