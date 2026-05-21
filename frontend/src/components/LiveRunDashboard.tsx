import React, { useMemo } from "react";
import { Sparkline } from "./Sparkline";
import type { SimulationStatus } from "../lib/api";
import { getRunStatusLabel } from "../lib/runStatusCopy";
import { FONT } from "../lib/theme";

type Timeline = SimulationStatus["state_timeline"];
type Outcomes = SimulationStatus["outcome_indicators"];

const emptyStateCardStyle: React.CSSProperties = {
  background: "#FFFFFF",
  border: "1px solid #E5E3DC",
  borderRadius: 10,
  padding: 24,
  textAlign: "center",
  fontSize: 14,
  color: "#6B7280",
};

type Props = {
  status: string;
  currentRound: number;
  transcriptLength: number;
  stateTimeline: Timeline;
  outcomeIndicators: Outcomes;
  configSnapshot: Record<string, unknown> | null;
  /** Iteration 28: early stop round when convergence criterion met */
  convergedAtRound?: number | null;
};

function readinessSeries(timeline: Timeline): number[] {
  return (timeline ?? []).map((r) => r.global_state?.implementation_readiness ?? 0);
}

function alignmentSeries(timeline: Timeline): number[] {
  return (timeline ?? []).map((r) => r.global_state?.alignment_index ?? 0);
}

/** Rounds 2+ only — mean population convergence delta (aligned to timeline order, skips round 1). */
function convergenceDeltaSeries(timeline: Timeline): number[] {
  return (timeline ?? [])
    .map((r) => r.global_state?.convergence_delta)
    .filter((v): v is number => typeof v === "number");
}

function adoptionSeries(outcomes: Outcomes): number[] {
  return (outcomes ?? []).map((o) => o.adoption_momentum);
}

function agentIdsFromTimeline(timeline: Timeline): string[] {
  const last = timeline?.[timeline.length - 1];
  if (!last?.agents?.length) return [];
  return last.agents.map((a) => a.agent_id);
}

function seriesForAgent(timeline: Timeline, agentId: string, key: "support_level" | "resistance_level" | "workload_stress"): number[] {
  const out: number[] = [];
  for (const round of timeline ?? []) {
    const a = round.agents?.find((x) => x.agent_id === agentId);
    if (a) out.push(a[key]);
  }
  return out;
}

export function LiveRunDashboard({
  status,
  currentRound,
  transcriptLength,
  stateTimeline,
  outcomeIndicators,
  configSnapshot,
  convergedAtRound,
}: Props) {
  const agentIds = useMemo(() => agentIdsFromTimeline(stateTimeline), [stateTimeline]);
  const readiness = useMemo(() => readinessSeries(stateTimeline), [stateTimeline]);
  const alignment = useMemo(() => alignmentSeries(stateTimeline), [stateTimeline]);
  const adoption = useMemo(() => adoptionSeries(outcomeIndicators), [outcomeIndicators]);
  const convDeltas = useMemo(() => convergenceDeltaSeries(stateTimeline), [stateTimeline]);

  const totalRounds = typeof configSnapshot?.total_rounds === "number" ? configSnapshot.total_rounds : undefined;
  const agentLimit = typeof configSnapshot?.agent_limit === "number" ? configSnapshot.agent_limit : undefined;
  const simulationMode =
    typeof configSnapshot?.simulation_mode === "string" ? (configSnapshot.simulation_mode as string) : undefined;
  const speakersPerRound =
    typeof configSnapshot?.speakers_per_round === "number" ? (configSnapshot.speakers_per_round as number) : undefined;
  const populationApplied = configSnapshot?.population_csv_applied === true;
  const populationPool =
    typeof configSnapshot?.population_pool_row_count === "number"
      ? configSnapshot.population_pool_row_count
      : undefined;
  const populationMode =
    typeof configSnapshot?.population_sample_mode === "string"
      ? (configSnapshot.population_sample_mode as string)
      : undefined;

  const lastRound = stateTimeline?.[stateTimeline.length - 1];

  const totalRoundsForStatus =
    typeof configSnapshot?.total_rounds === "number" ? configSnapshot.total_rounds : 1;
  const statusLabel = getRunStatusLabel(status, {
    currentRound,
    totalRounds: totalRoundsForStatus,
    convergedAtRound: convergedAtRound ?? null,
  });

  const populationPoolSummary = (() => {
    if (!populationApplied || populationPool == null) return null;
    if (populationMode === "weighted") {
      return `Participant pool: ${populationPool} people, weighted sampling`;
    }
    if (populationMode === "stratified") {
      return `Participant pool: ${populationPool} people, stratified by group`;
    }
    return `Participant pool: ${populationPool} people`;
  })();

  return (
    <section style={{ display: "grid", gap: 20 }}>
      {convergedAtRound != null ? (
        <div
          style={{
            padding: "10px 14px",
            borderRadius: 8,
            background: "#ECFDF5",
            border: "1px solid #6EE7B7",
            fontSize: 14,
            marginBottom: 12,
          }}
        >
          ✓ Consensus reached at Round <strong>{convergedAtRound}</strong> — the discussion stabilised and stopped early.
        </div>
      ) : null}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: 12,
        }}
      >
        <div style={{ border: "1px solid #E5E3DC", borderRadius: 8, padding: 12, background: "#FFFFFF" }}>
          <div style={{ fontSize: 12, color: "#6B7280" }}>Discussion status</div>
          <div style={{ fontWeight: 600, marginTop: 4 }}>{statusLabel}</div>
        </div>
        <div style={{ border: "1px solid #E5E3DC", borderRadius: 8, padding: 12, background: "#FFFFFF" }}>
          <div style={{ fontSize: 12, color: "#6B7280" }}>Rounds completed</div>
          <div style={{ marginTop: 4 }}>
            <strong>{currentRound}</strong>
            {totalRounds != null ? ` of ${totalRounds}` : ""}
          </div>
          <div style={{ fontSize: 12, marginTop: 6, color: "#6B7280" }}>Exchanges so far</div>
          <div style={{ fontWeight: 600 }}>{transcriptLength}</div>
          {agentLimit != null ? (
            <div style={{ fontSize: 12, marginTop: 6, color: "#6B7280" }}>
              Participants: {agentLimit}
            </div>
          ) : null}
          {simulationMode === "full_round_robin" ? (
            <div style={{ fontSize: 12, marginTop: 6, color: "#6B7280" }}>Turn style: Everyone speaks each round</div>
          ) : simulationMode === "sample_k_per_round" ? (
            <div style={{ fontSize: 12, marginTop: 6, color: "#6B7280" }}>
              Turn style: Rotating speakers
              {speakersPerRound != null ? ` (${speakersPerRound} per round)` : ""}
            </div>
          ) : simulationMode ? (
            <div style={{ fontSize: 12, marginTop: 6, color: "#6B7280" }}>Turn style: {simulationMode}</div>
          ) : null}
          {populationPoolSummary ? (
            <div style={{ fontSize: 12, marginTop: 6, color: "#6B7280" }}>{populationPoolSummary}</div>
          ) : null}
        </div>
      </div>

      <div>
        <h3 style={{ margin: "0 0 8px 0" }}>Opinion trends by round</h3>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 20, alignItems: "flex-end" }}>
          <div>
            <div style={{ fontSize: 12, color: "#6B7280" }}>Readiness to adopt</div>
            <Sparkline values={readiness} color="#059669" label="Readiness to adopt" />
          </div>
          <div>
            <div style={{ fontSize: 12, color: "#6B7280" }}>Level of agreement</div>
            <Sparkline values={alignment} color="#7c3aed" label="Level of agreement" />
          </div>
          <div>
            <div style={{ fontSize: 12, color: "#6B7280" }}>Opinion change rate</div>
            <Sparkline values={convDeltas} color="#0e7490" width={160} height={36} label="Opinion change rate" />
          </div>
        </div>
      </div>

      <div>
        <h3 style={{ margin: "0 0 8px 0" }}>Round-by-round outcomes</h3>
        {outcomeIndicators.length === 0 ? (
          <div style={emptyStateCardStyle}>Outcomes will appear after the first round completes.</div>
        ) : (
          <>
            <div style={{ marginBottom: 8 }}>
              <span style={{ fontSize: 12, color: "#6B7280" }}>Adoption momentum</span>
              <Sparkline values={adoption} color="#d97706" width={180} height={40} label="Adoption momentum" />
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ borderCollapse: "collapse", fontSize: 13, minWidth: 360 }}>
                <thead>
                  <tr style={{ textAlign: "left", borderBottom: "1px solid #ccc" }}>
                    <th style={{ padding: "6px 8px" }}>Round</th>
                    <th style={{ padding: "6px 8px" }}>Adoption score</th>
                    <th style={{ padding: "6px 8px" }}>Disagreements</th>
                    <th style={{ padding: "6px 8px" }}>Consistency score</th>
                  </tr>
                </thead>
                <tbody>
                  {outcomeIndicators.map((o) => (
                    <tr key={o.round_number} style={{ borderBottom: "1px solid #eee" }}>
                      <td style={{ padding: "6px 8px" }}>{o.round_number}</td>
                      <td style={{ padding: "6px 8px", color: "#1A1A1A", fontFamily: FONT.mono, fontSize: 13 }}>
                        {o.adoption_momentum.toFixed(3)}
                      </td>
                      <td style={{ padding: "6px 8px", color: "#1A1A1A", fontFamily: FONT.mono, fontSize: 13 }}>
                        {o.conflict_events}
                      </td>
                      <td style={{ padding: "6px 8px", color: "#1A1A1A", fontFamily: FONT.mono, fontSize: 13 }}>
                        {o.consistency_index.toFixed(3)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      <div>
        <h3 style={{ margin: "0 0 8px 0" }}>Participants</h3>
        {agentIds.length === 0 ? (
          <div style={emptyStateCardStyle}>Participant data will appear after the first round completes.</div>
        ) : (
          <div style={{ display: "grid", gap: 10 }}>
            {agentIds.map((id) => {
              const agent = lastRound?.agents?.find((a) => a.agent_id === id);
              return (
                <div
                  key={id}
                  style={{
                    border: "1px solid #E5E3DC",
                    borderRadius: 8,
                    padding: 10,
                    display: "grid",
                    gap: 8,
                    background: "#FFFFFF",
                  }}
                >
                  <div style={{ fontWeight: 600 }}>
                    {agent?.agent_name ?? id}{" "}
                    <span style={{ fontWeight: 400, color: "#6B7280", fontSize: 12 }}>({agent?.agent_role ?? "?"})</span>
                  </div>
                  <div style={{ fontSize: 12, color: "#6B7280" }}>
                    Support: {((agent?.support_level ?? 0) * 100).toFixed(0)}% &nbsp;·&nbsp; Resistance:{" "}
                    {((agent?.resistance_level ?? 0) * 100).toFixed(0)}% &nbsp;·&nbsp; Workload:{" "}
                    {((agent?.workload_stress ?? 0) * 100).toFixed(0)}% &nbsp;·&nbsp; Stance: {agent?.belief_posture ?? "unknown"}
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center" }}>
                    <span style={{ fontSize: 11, color: "#6B7280" }}>Support</span>
                    <Sparkline
                      values={seriesForAgent(stateTimeline, id, "support_level")}
                      color="#059669"
                      label="Support"
                    />
                    <span style={{ fontSize: 11, color: "#6B7280" }}>Resistance</span>
                    <Sparkline
                      values={seriesForAgent(stateTimeline, id, "resistance_level")}
                      color="#dc2626"
                      label="Resistance"
                    />
                    <span style={{ fontSize: 11, color: "#6B7280" }}>Workload</span>
                    <Sparkline
                      values={seriesForAgent(stateTimeline, id, "workload_stress")}
                      color="#ca8a04"
                      label="Workload"
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
