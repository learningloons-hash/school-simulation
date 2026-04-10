import React, { useMemo } from "react";
import { Sparkline } from "./Sparkline";
import type { SimulationStatus } from "../lib/api";

type Timeline = SimulationStatus["state_timeline"];
type Outcomes = SimulationStatus["outcome_indicators"];

type Props = {
  status: string;
  currentRound: number;
  transcriptLength: number;
  stateTimeline: Timeline;
  outcomeIndicators: Outcomes;
  configSnapshot: Record<string, unknown> | null;
  runId: string | null;
  /** Iteration 28: early stop round when convergence criterion met */
  convergedAtRound?: number | null;
  pollIntervalMs?: number;
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
  runId,
  convergedAtRound,
  pollIntervalMs,
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
  const populationSchema =
    typeof configSnapshot?.population_schema_version === "string"
      ? (configSnapshot.population_schema_version as string)
      : undefined;
  const populationPool =
    typeof configSnapshot?.population_pool_row_count === "number"
      ? configSnapshot.population_pool_row_count
      : undefined;
  const populationMode =
    typeof configSnapshot?.population_sample_mode === "string"
      ? (configSnapshot.population_sample_mode as string)
      : undefined;

  const lastRound = stateTimeline?.[stateTimeline.length - 1];
  const convThreshold =
    typeof configSnapshot?.convergence_threshold === "number"
      ? (configSnapshot.convergence_threshold as number)
      : undefined;

  return (
    <section style={{ display: "grid", gap: 20 }}>
      {convergedAtRound != null ? (
        <div
          style={{
            padding: "10px 14px",
            borderRadius: 8,
            background: "#ecfdf5",
            border: "1px solid #6ee7b7",
            fontSize: 14,
          }}
        >
          Converged at round <strong>{convergedAtRound}</strong>
          {convThreshold != null ? (
            <span style={{ opacity: 0.85, marginLeft: 8 }}>
              (threshold {convThreshold.toFixed(4)}, patience{" "}
              {typeof configSnapshot?.convergence_patience === "number"
                ? configSnapshot.convergence_patience
                : "—"}
              )
            </span>
          ) : null}
        </div>
      ) : null}
      <div style={{ fontSize: 14, opacity: 0.85, maxWidth: 720 }}>
        Data updates from the same <code>GET /simulations/{"{id}"}</code> payload as other tabs
        {pollIntervalMs ? ` (~${pollIntervalMs}ms poll while running).` : "."} See{" "}
        <code>docs/plans/iteration-8-live-dashboard-design.md</code> for scale and streaming notes.
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: 12,
        }}
      >
        <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: 12 }}>
          <div style={{ fontSize: 12, opacity: 0.75 }}>Status</div>
          <div style={{ fontWeight: 600 }}>{status}</div>
          <div style={{ fontSize: 12, marginTop: 6 }}>Run id</div>
          <div style={{ fontFamily: "monospace", fontSize: 11, wordBreak: "break-all" }}>{runId ?? "—"}</div>
        </div>
        <div style={{ border: "1px solid #ddd", borderRadius: 8, padding: 12 }}>
          <div style={{ fontSize: 12, opacity: 0.75 }}>Progress</div>
          <div>
            Rounds completed: <strong>{currentRound}</strong>
            {totalRounds != null ? ` / ${totalRounds}` : ""}
          </div>
          <div style={{ fontSize: 12, marginTop: 6 }}>Transcript turns</div>
          <div style={{ fontWeight: 600 }}>{transcriptLength}</div>
          {agentLimit != null ? (
            <div style={{ fontSize: 12, marginTop: 6, opacity: 0.8 }}>
              agent_limit (config): {agentLimit}
            </div>
          ) : null}
          {simulationMode ? (
            <div style={{ fontSize: 12, marginTop: 6, opacity: 0.8 }}>
              simulation_mode: {simulationMode}
              {simulationMode === "sample_k_per_round" && speakersPerRound != null ? ` · K=${speakersPerRound}` : ""}
            </div>
          ) : null}
          {populationApplied ? (
            <div style={{ fontSize: 12, marginTop: 6, opacity: 0.8 }}>
              population: schema v{populationSchema ?? "?"} · pool {populationPool ?? "—"} rows · {populationMode ?? "—"}
            </div>
          ) : null}
        </div>
      </div>

      <div>
        <h3 style={{ margin: "0 0 8px 0" }}>Global state (by completed round)</h3>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 20, alignItems: "flex-end" }}>
          <div>
            <div style={{ fontSize: 12, opacity: 0.75 }}>Implementation readiness</div>
            <Sparkline values={readiness} color="#059669" label="implementation_readiness" />
          </div>
          <div>
            <div style={{ fontSize: 12, opacity: 0.75 }}>Alignment index</div>
            <Sparkline values={alignment} color="#7c3aed" label="alignment_index" />
          </div>
          <div>
            <div style={{ fontSize: 12, opacity: 0.75 }} title="Mean population abs Δ (support/resistance/workload); round 1 omitted">
              Convergence δ (rounds 2+)
            </div>
            <Sparkline values={convDeltas} color="#0e7490" width={160} height={36} label="convergence_delta" />
          </div>
        </div>
      </div>

      <div>
        <h3 style={{ margin: "0 0 8px 0" }}>Round outcomes</h3>
        {outcomeIndicators.length === 0 ? (
          <div style={{ fontSize: 13, opacity: 0.8 }}>No outcome rows yet (first row appears after round 1 completes).</div>
        ) : (
          <>
            <div style={{ marginBottom: 8 }}>
              <span style={{ fontSize: 12, opacity: 0.75 }}>Adoption momentum</span>
              <Sparkline values={adoption} color="#d97706" width={180} height={40} label="adoption_momentum" />
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ borderCollapse: "collapse", fontSize: 13, minWidth: 360 }}>
                <thead>
                  <tr style={{ textAlign: "left", borderBottom: "1px solid #ccc" }}>
                    <th style={{ padding: "6px 8px" }}>Round</th>
                    <th style={{ padding: "6px 8px" }}>Adoption</th>
                    <th style={{ padding: "6px 8px" }}>Conflicts</th>
                    <th style={{ padding: "6px 8px" }}>Consistency</th>
                  </tr>
                </thead>
                <tbody>
                  {outcomeIndicators.map((o) => (
                    <tr key={o.round_number} style={{ borderBottom: "1px solid #eee" }}>
                      <td style={{ padding: "6px 8px" }}>{o.round_number}</td>
                      <td style={{ padding: "6px 8px", fontFamily: "monospace" }}>{o.adoption_momentum.toFixed(3)}</td>
                      <td style={{ padding: "6px 8px" }}>{o.conflict_events}</td>
                      <td style={{ padding: "6px 8px", fontFamily: "monospace" }}>{o.consistency_index.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      <div>
        <h3 style={{ margin: "0 0 8px 0" }}>Agents (latest round snapshot + series)</h3>
        {agentIds.length === 0 ? (
          <div style={{ fontSize: 13, opacity: 0.8 }}>No agent state until at least one round completes.</div>
        ) : (
          <div style={{ display: "grid", gap: 10 }}>
            {agentIds.map((id) => {
              const agent = lastRound?.agents?.find((a) => a.agent_id === id);
              return (
                <div
                  key={id}
                  style={{
                    border: "1px solid #e5e5e5",
                    borderRadius: 8,
                    padding: 10,
                    display: "grid",
                    gap: 8,
                  }}
                >
                  <div style={{ fontWeight: 600 }}>
                    {agent?.agent_name ?? id}{" "}
                    <span style={{ fontWeight: 400, opacity: 0.75, fontSize: 12 }}>({agent?.agent_role ?? "?"})</span>
                  </div>
                  <div style={{ fontSize: 12, fontFamily: "monospace" }}>
                    Latest: support {agent?.support_level.toFixed(2)} · resistance {agent?.resistance_level.toFixed(2)} ·
                    workload {agent?.workload_stress.toFixed(2)} · {agent?.belief_posture}
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center" }}>
                    <span style={{ fontSize: 11, opacity: 0.7 }}>support</span>
                    <Sparkline values={seriesForAgent(stateTimeline, id, "support_level")} color="#059669" />
                    <span style={{ fontSize: 11, opacity: 0.7 }}>resistance</span>
                    <Sparkline values={seriesForAgent(stateTimeline, id, "resistance_level")} color="#dc2626" />
                    <span style={{ fontSize: 11, opacity: 0.7 }}>workload</span>
                    <Sparkline values={seriesForAgent(stateTimeline, id, "workload_stress")} color="#ca8a04" />
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
