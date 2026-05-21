import React, { useEffect, useState } from "react";

export type ScenarioPick = {
  id: string;
  name: string;
  rag_enabled: boolean;
  source: string;
};

export type ScenarioSelectorProps = {
  scenarios: ScenarioPick[];
  selected: string;
  onChange: (id: string) => void;
};

const BUILTIN_DESCRIPTIONS: Record<string, string> = {
  psle_reform_mvp:
    "Simulate a stakeholder discussion about reforming the Primary School Leaving Examination — exploring how teachers, principals, and policymakers respond to proposed changes.",
  fsbb_comparator:
    "Explore how education stakeholders deliberate on Full Subject-Based Banding, a policy that allows students to take subjects at different levels based on ability.",
};

const FALLBACK_DESCRIPTION = "A custom scenario. Run the simulation to see how participants deliberate on this policy.";

function descriptionFor(id: string): string {
  return BUILTIN_DESCRIPTIONS[id] ?? FALLBACK_DESCRIPTION;
}

export function ScenarioSelector({ scenarios, selected, onChange }: ScenarioSelectorProps) {
  const [wide, setWide] = useState(() => (typeof window !== "undefined" ? window.innerWidth > 700 : true));

  useEffect(() => {
    const onResize = () => setWide(window.innerWidth > 700);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: wide ? "repeat(2, minmax(0, 1fr))" : "1fr",
        gap: 12,
      }}
    >
      {scenarios.map((s) => {
        const isSelected = s.id === selected;
        return (
          <button
            key={s.id}
            type="button"
            onClick={() => onChange(s.id)}
            style={{
              textAlign: "left",
              background: isSelected ? "#EEF3FA" : "#FFFFFF",
              border: isSelected ? "2px solid #4A6FA5" : "1px solid #E5E3DC",
              borderRadius: 10,
              padding: "14px 16px",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
              <div style={{ fontSize: 15, fontWeight: 600, color: "#1A1A1A" }}>{s.name}</div>
              {isSelected ? (
                <span
                  style={{
                    borderRadius: 999,
                    background: "#4A6FA5",
                    color: "#FFFFFF",
                    fontSize: 11,
                    padding: "2px 8px",
                    flexShrink: 0,
                  }}
                >
                  Selected
                </span>
              ) : null}
            </div>
            <div style={{ fontSize: 13, color: "#6B7280", marginTop: 4, lineHeight: 1.5 }}>{descriptionFor(s.id)}</div>
          </button>
        );
      })}
    </div>
  );
}
