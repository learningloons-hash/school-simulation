import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Sparkline } from "./Sparkline";
import {
  createExperiment,
  experimentExportJsonUrl,
  experimentExportZipUrl,
  fetchExperiment,
  getSimulation,
  listExperiments,
  type ExperimentDetail,
  type ExperimentListItem,
  type ExperimentRunRow,
  type RunEconomics,
  type ScenarioCatalogItem,
  type SimulationStatus,
} from "../lib/api";
import { shortStatusLabel } from "../lib/runStatusCopy";
import { FONT, emptyStateCardStyle } from "../lib/theme";

const sectionHeadingStyle: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  color: "#6B7280",
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  marginBottom: 12,
};

const STRATEGY_LABELS: Record<string, string> = {
  full_census: "All participants speak",
  role_stratified: "By role group",
  hybrid_core_remainder: "Core group + random fill",
  posture_maxvar: "Maximum diversity",
  network_centrality: "By network influence",
};

function strategyLabel(s: string | null | undefined): string {
  if (s == null || s === "") return "—";
  return STRATEGY_LABELS[s] ?? s;
}

const SAMPLING_STRATEGIES = [
  "full_census",
  "role_stratified",
  "hybrid_core_remainder",
  "posture_maxvar",
  "network_centrality",
] as const;

const LINE_COLORS = ["#2563eb", "#16a34a", "#c026d3", "#ea580c", "#0891b2"];

type ComparisonMetricKey =
  | "implementation_readiness"
  | "alignment_index"
  | "adoption_momentum"
  | "conflict_events"
  | "consistency_index"
  | "convergence_delta";

const COMPARISON_METRIC_OPTIONS: { value: ComparisonMetricKey; label: string }[] = [
  { value: "implementation_readiness", label: "Readiness to adopt" },
  { value: "alignment_index", label: "Level of agreement" },
  { value: "adoption_momentum", label: "Adoption momentum" },
  { value: "conflict_events", label: "Disagreements" },
  { value: "consistency_index", label: "Consistency" },
  { value: "convergence_delta", label: "Opinion change rate" },
];

type RunRowForm = { label: string; sampling_strategy: string };

type Props = {
  scenarioChoices: ScenarioCatalogItem[];
};

function fmtMetric(v: number | undefined): string {
  if (typeof v !== "number" || Number.isNaN(v)) return "—";
  return v.toFixed(2);
}

function comparisonMetricLabel(key: ComparisonMetricKey): string {
  return COMPARISON_METRIC_OPTIONS.find((o) => o.value === key)?.label ?? key;
}

/** Table header + compact lines — align with Run Details AI usage (App.tsx). */
function formatTokensCost(e: RunEconomics | null | undefined): string {
  if (!e) return "";
  const total = (e.total_input_tokens ?? 0) + (e.total_output_tokens ?? 0);
  const costPart =
    e.estimated_cost_usd != null && e.estimated_cost_usd > 0
      ? `$${e.estimated_cost_usd.toFixed(4)}`
      : e.llm_provider === "lmstudio" || e.llm_provider === ""
        ? "Free (local model)"
        : "—";
  return `Tokens: ${total.toLocaleString()} · ${costPart}`;
}

function experimentRunTokenTotal(r: ExperimentRunRow): number {
  const tin = r.total_input_tokens ?? r.economics?.total_input_tokens ?? 0;
  const tout = r.total_output_tokens ?? r.economics?.total_output_tokens ?? 0;
  return tin + tout;
}

function experimentRunEconomicsSuffix(r: ExperimentRunRow): string {
  if (!r.economics) return "";
  const total = experimentRunTokenTotal(r);
  const costPart =
    r.economics.estimated_cost_usd != null && r.economics.estimated_cost_usd > 0
      ? `$${r.economics.estimated_cost_usd.toFixed(4)}`
      : r.economics.llm_provider === "lmstudio" || r.economics.llm_provider === ""
        ? "Free (local model)"
        : "—";
  return `~${total.toLocaleString()} tokens · ${costPart}`;
}

export function ExperimentConsole({ scenarioChoices }: Props) {
  const [expName, setExpName] = useState("Strategy sweep");
  const [scenarioId, setScenarioId] = useState(scenarioChoices[0]?.id ?? "psle_reform_mvp");
  const [randomSeed, setRandomSeed] = useState(42);
  const [totalRounds, setTotalRounds] = useState(2);
  const [agentLimit, setAgentLimit] = useState(3);
  const [runRows, setRunRows] = useState<RunRowForm[]>([
    { label: "A", sampling_strategy: "full_census" },
    { label: "B", sampling_strategy: "role_stratified" },
  ]);
  const [expConvThreshold, setExpConvThreshold] = useState<string>("");
  const [expConvPatience, setExpConvPatience] = useState<number>(2);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastExperimentId, setLastExperimentId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ExperimentDetail | null>(null);
  const [expList, setExpList] = useState<ExperimentListItem[]>([]);
  const [listErr, setListErr] = useState<string | null>(null);

  const [compareIdA, setCompareIdA] = useState("");
  const [compareIdB, setCompareIdB] = useState("");
  const [compareA, setCompareA] = useState<SimulationStatus | null>(null);
  const [compareB, setCompareB] = useState<SimulationStatus | null>(null);
  const [compareError, setCompareError] = useState<string | null>(null);

  const [comparisonMetric, setComparisonMetric] = useState<ComparisonMetricKey>("implementation_readiness");
  const [elapsedSec, setElapsedSec] = useState(0);
  const abortRef = useRef<AbortController | null>(null);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearTick = useCallback(() => {
    if (tickRef.current) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
  }, []);

  const refreshList = useCallback(async () => {
    try {
      setListErr(null);
      setExpList(await listExperiments(40));
    } catch (e) {
      setListErr(String((e as Error)?.message ?? e));
    }
  }, []);

  useEffect(() => {
    void refreshList();
  }, [refreshList]);

  useEffect(() => () => clearTick(), [clearTick]);

  const loadDetail = useCallback(async (id: string) => {
    setError(null);
    try {
      setDetail(await fetchExperiment(id));
    } catch (e) {
      setError(String((e as Error)?.message ?? e));
    }
  }, []);

  useEffect(() => {
    if (lastExperimentId) void loadDetail(lastExperimentId);
  }, [lastExperimentId, loadDetail]);

  async function onSubmitExperiment() {
    abortRef.current?.abort();
    clearTick();
    const ac = new AbortController();
    abortRef.current = ac;
    setElapsedSec(0);
    setError(null);
    setBusy(true);
    tickRef.current = setInterval(() => setElapsedSec((s) => s + 1), 1000);
    try {
      const ect = expConvThreshold.trim();
      const expConv =
        ect !== "" && Number.isFinite(Number(ect))
          ? { convergence_threshold: Number(ect), convergence_patience: expConvPatience }
          : {};
      const res = await createExperiment(
        {
          name: expName.trim() || "Experiment",
          scenario_id: scenarioId,
          random_seed: randomSeed,
          total_rounds: totalRounds,
          agent_limit: agentLimit,
          ...expConv,
          runs: runRows.map((r) => ({
            label: r.label.trim() || undefined,
            sampling_strategy: r.sampling_strategy,
          })),
        },
        ac.signal,
      );
      setLastExperimentId(res.experiment_id);
      await refreshList();
      await loadDetail(res.experiment_id);
    } catch (e: unknown) {
      const name = e && typeof e === "object" && "name" in e ? String((e as { name: string }).name) : "";
      if (name === "AbortError") {
        setError("Cancelled (request aborted — server may still finish in-flight child runs).");
      } else {
        setError(String((e as Error)?.message ?? e));
      }
    } finally {
      clearTick();
      setBusy(false);
      abortRef.current = null;
    }
  }

  function onCancelExperiment() {
    abortRef.current?.abort();
  }

  function addRow() {
    setRunRows((rows) => [
      ...rows,
      { label: String.fromCharCode(65 + rows.length), sampling_strategy: "full_census" },
    ]);
  }

  function removeRow(i: number) {
    setRunRows((rows) => rows.filter((_, j) => j !== i));
  }

  async function onCompare() {
    setCompareError(null);
    setCompareA(null);
    setCompareB(null);
    const a = compareIdA.trim();
    const b = compareIdB.trim();
    if (!a || !b) {
      setCompareError("Enter two run IDs.");
      return;
    }
    try {
      const [ra, rb] = await Promise.all([getSimulation(a), getSimulation(b)]);
      setCompareA(ra);
      setCompareB(rb);
    } catch (e) {
      setCompareError(String((e as Error)?.message ?? e));
    }
  }

  const metricSeriesByLabel = useMemo(() => {
    if (!detail?.comparison?.length) return new Map<string, number[]>();
    const keys = new Set<string>();
    for (const row of detail.comparison) {
      Object.keys(row.by_run ?? {}).forEach((k) => keys.add(k));
    }
    const m = new Map<string, number[]>();
    for (const k of keys) {
      const vals: number[] = [];
      for (const row of detail.comparison) {
        const raw = row.by_run[k]?.[comparisonMetric];
        const v = typeof raw === "number" && !Number.isNaN(raw) ? raw : 0;
        vals.push(v);
      }
      m.set(k, vals);
    }
    return m;
  }, [detail, comparisonMetric]);

  const tableSeriesKeys = useMemo(() => {
    if (!detail?.comparison?.length) return [];
    const s = new Set<string>();
    for (const row of detail.comparison) {
      Object.keys(row.by_run ?? {}).forEach((k) => s.add(k));
    }
    return Array.from(s);
  }, [detail]);

  return (
    <div style={{ display: "grid", gap: 24, maxWidth: 920 }}>
      <section style={{ padding: 12, border: "1px solid #E5E3DC", borderRadius: 8 }}>
        <div style={{ ...sectionHeadingStyle, marginTop: 0 }}>New comparison run</div>
        <p style={{ fontSize: 14, opacity: 0.85, marginTop: 0 }}>
          Run the same scenario with different participant-selection strategies side by side. Each row is one run — all
          share the same scenario and seed. Runs complete one after another.
        </p>
        <div style={{ display: "grid", gap: 10, maxWidth: 480 }}>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Comparison name</span>
            <input value={expName} onChange={(e) => setExpName(e.target.value)} style={{ padding: 8 }} />
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Policy scenario</span>
            <select value={scenarioId} onChange={(e) => setScenarioId(e.target.value)} style={{ padding: 8 }}>
              {scenarioChoices.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Reproducibility seed</span>
            <input type="number" value={randomSeed} onChange={(e) => setRandomSeed(Number(e.target.value))} style={{ padding: 8 }} />
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Discussion rounds</span>
            <input
              type="number"
              min={1}
              max={25}
              value={totalRounds}
              onChange={(e) => setTotalRounds(Number(e.target.value))}
              style={{ padding: 8 }}
            />
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Number of participants</span>
            <input
              type="number"
              min={1}
              max={300}
              value={agentLimit}
              onChange={(e) => setAgentLimit(Number(e.target.value))}
              style={{ padding: 8 }}
            />
          </label>
          <div style={{ display: "grid", gap: 8, padding: 10, background: "#f8fafc", borderRadius: 6 }}>
            <div style={{ fontSize: 12, fontWeight: 600 }}>Auto-stop settings (optional — applies to all runs)</div>
            <label style={{ display: "grid", gap: 4 }}>
              <span>Sensitivity (0.01 = very sensitive, 0.1 = loose)</span>
              <input
                type="text"
                inputMode="decimal"
                placeholder="e.g. 0.01"
                value={expConvThreshold}
                onChange={(e) => setExpConvThreshold(e.target.value)}
                style={{ padding: 8, maxWidth: 200 }}
              />
            </label>
            <label style={{ display: "grid", gap: 4 }}>
              <span>Rounds to confirm consensus</span>
              <input
                type="number"
                min={1}
                max={25}
                value={expConvPatience}
                onChange={(e) => setExpConvPatience(Number(e.target.value))}
                style={{ padding: 8, maxWidth: 120 }}
              />
            </label>
          </div>
        </div>

        <div style={{ ...sectionHeadingStyle, marginTop: 18 }}>Runs to compare</div>
        {runRows.map((row, i) => (
          <div key={i} style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 8, alignItems: "center" }}>
            <input
              placeholder="Run label (e.g. A)"
              value={row.label}
              onChange={(e) => {
                const v = e.target.value;
                setRunRows((rs) => rs.map((r, j) => (j === i ? { ...r, label: v } : r)));
              }}
              style={{ padding: 6, width: 80 }}
            />
            <select
              value={row.sampling_strategy}
              onChange={(e) => {
                const v = e.target.value;
                setRunRows((rs) => rs.map((r, j) => (j === i ? { ...r, sampling_strategy: v } : r)));
              }}
              style={{ padding: 6, minWidth: 200 }}
            >
              {SAMPLING_STRATEGIES.map((s) => (
                <option key={s} value={s}>
                  {strategyLabel(s)}
                </option>
              ))}
            </select>
            <button type="button" onClick={() => removeRow(i)} disabled={runRows.length <= 1}>
              Remove
            </button>
          </div>
        ))}
        <button type="button" onClick={addRow} style={{ marginRight: 8 }}>
          Add run
        </button>
        <button type="button" disabled={busy} onClick={() => void onSubmitExperiment()} style={{ padding: "10px 16px" }}>
          {busy ? "Running…" : "Start comparison"}
        </button>
        {busy ? (
          <button type="button" onClick={onCancelExperiment} style={{ marginLeft: 8, padding: "10px 16px" }}>
            Cancel
          </button>
        ) : null}
        {busy ? (
          <span style={{ marginLeft: 12, fontSize: 13, opacity: 0.85 }}>
            Elapsed: <strong>{elapsedSec}s</strong>
          </span>
        ) : null}
        {error ? <div style={{ color: "#E05252", marginTop: 8 }}>{error}</div> : null}
        {lastExperimentId ? (
          <div style={{ marginTop: 10, fontSize: 13 }}>
            Comparison ID:{" "}
            <span style={{ fontFamily: FONT.mono, fontSize: 12 }}>{lastExperimentId.slice(0, 14)}…</span>
          </div>
        ) : null}
      </section>

      <section style={{ padding: 12, border: "1px solid #E5E3DC", borderRadius: 8 }}>
        <div style={{ ...sectionHeadingStyle, marginTop: 0 }}>Metric trends</div>
        {!detail ? (
          <div style={{ opacity: 0.75 }}>Start or load a comparison above to see metrics here.</div>
        ) : (
          <div style={{ display: "grid", gap: 12 }}>
            <div style={{ fontSize: 13, opacity: 0.85 }}>
              Run group {detail.experiment.id.slice(0, 10)}… · {shortStatusLabel(detail.experiment.status)}
              {typeof detail.total_estimated_cost_usd === "number" ? (
                <span style={{ marginLeft: 8 }}>
                  · Total est. cost (USD): <strong>{detail.total_estimated_cost_usd.toFixed(4)}</strong>
                </span>
              ) : null}
            </div>
            <label style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", fontSize: 14 }}>
              <span>Chart by</span>
              <select
                value={comparisonMetric}
                onChange={(e) => setComparisonMetric(e.target.value as ComparisonMetricKey)}
                style={{ padding: 6 }}
              >
                {COMPARISON_METRIC_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "flex-end" }}>
              {Array.from(metricSeriesByLabel.entries()).map(([label, vals], idx) => (
                <div key={label} style={{ border: "1px solid #E5E3DC", borderRadius: 8, padding: 10 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>{label}</div>
                  <Sparkline values={vals} width={160} height={40} color={LINE_COLORS[idx % LINE_COLORS.length]} />
                  <div style={{ fontSize: 11, opacity: 0.75, marginTop: 4 }}>{comparisonMetricLabel(comparisonMetric)}</div>
                </div>
              ))}
            </div>
            <details style={{ fontSize: 13 }}>
              <summary style={{ cursor: "pointer" }}>All metrics by round</summary>
              <div style={{ overflowX: "auto", marginTop: 8 }}>
                <table style={{ borderCollapse: "collapse", fontSize: 12, minWidth: 480 }}>
                  <thead>
                    <tr>
                      <th style={{ border: "1px solid #E5E3DC", padding: 6, textAlign: "left" }}>Round</th>
                      {tableSeriesKeys.map((sk) => (
                        <th key={sk} style={{ border: "1px solid #E5E3DC", padding: 6, textAlign: "left" }}>
                          {sk}
                          {(() => {
                            const runRow = detail.runs.find((x) => x.series_key === sk);
                            const e = runRow?.economics;
                            if (!e) return null;
                            const line = formatTokensCost(e);
                            return line ? (
                              <div style={{ fontWeight: 400, fontSize: 10, opacity: 0.8, marginTop: 4 }}>{line}</div>
                            ) : null;
                          })()}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {detail.comparison.map((row) => (
                      <tr key={row.round_number}>
                        <td style={{ border: "1px solid #E5E3DC", padding: 6 }}>{row.round_number}</td>
                        {tableSeriesKeys.map((sk) => {
                          const met = row.by_run[sk];
                          return (
                            <td
                              key={sk}
                              style={{ border: "1px solid #E5E3DC", padding: 6, fontSize: 11, fontFamily: FONT.mono }}
                            >
                              {met ? (
                                <>
                                  <div>Readiness: {fmtMetric(met.implementation_readiness)}</div>
                                  <div>Agreement: {fmtMetric(met.alignment_index)}</div>
                                  <div>Adoption: {fmtMetric(met.adoption_momentum)}</div>
                                  <div>Disagreements: {met.conflict_events ?? "—"}</div>
                                  <div>Consistency: {fmtMetric(met.consistency_index)}</div>
                                  <div>Opinion change: {fmtMetric(met.convergence_delta)}</div>
                                </>
                              ) : (
                                "—"
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              <a
                href={experimentExportZipUrl(detail.experiment.id)}
                download
                style={{ padding: "8px 12px", border: "1px solid #E5E3DC", borderRadius: 6 }}
              >
                Download experiment ZIP
              </a>
              <a
                href={experimentExportJsonUrl(detail.experiment.id)}
                target="_blank"
                rel="noreferrer"
                style={{ padding: "8px 12px", border: "1px solid #E5E3DC", borderRadius: 6 }}
              >
                Open experiment JSON
              </a>
            </div>
          </div>
        )}
      </section>

      <section style={{ padding: 12, border: "1px solid #E5E3DC", borderRadius: 8 }}>
        <div style={{ ...sectionHeadingStyle, marginTop: 0 }}>Run results</div>
        {!detail ? (
          <div style={{ opacity: 0.75 }}>Load a comparison to see per-run results.</div>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 8 }}>
            {detail.runs.map((r) => (
              <li key={r.simulation_id} style={{ border: "1px solid #E5E3DC", borderRadius: 8, padding: 10, fontSize: 13 }}>
                <strong>{r.series_key}</strong> · {strategyLabel(r.sampling_strategy)} · {shortStatusLabel(r.status)}
                {r.status === "completed" ? (
                  <span style={{ opacity: 0.85 }}>
                    {" "}
                    ·{" "}
                    {typeof r.converged_at_round === "number"
                      ? `Consensus at Round ${r.converged_at_round}`
                      : `All ${r.total_rounds} rounds`}
                  </span>
                ) : null}
                {r.economics ? (
                  <span style={{ opacity: 0.85, marginLeft: 6 }}>· {experimentRunEconomicsSuffix(r)}</span>
                ) : null}
                <div style={{ fontFamily: FONT.mono, fontSize: 11, marginTop: 4 }}>{r.simulation_id}</div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section style={{ padding: 12, border: "1px solid #E5E3DC", borderRadius: 8 }}>
        <div style={{ ...sectionHeadingStyle, marginTop: 0 }}>Previous comparisons</div>
        <button type="button" onClick={() => void refreshList()} style={{ marginBottom: 8 }}>
          Refresh
        </button>
        {listErr ? <div style={{ color: "#E05252" }}>{listErr}</div> : null}
        {expList.length === 0 ? (
          <div style={{ ...emptyStateCardStyle, textAlign: "left", padding: "14px 16px" }}>
            No previous comparisons. Set up a new one above to get started.
          </div>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, display: "grid", gap: 8 }}>
            {expList.map((e) => (
              <li
                key={e.id}
                style={{
                  border: "1px solid #E5E3DC",
                  borderRadius: 8,
                  padding: 10,
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 8,
                  alignItems: "center",
                }}
              >
                <span style={{ fontWeight: 600 }}>{e.name}</span>
                <span style={{ opacity: 0.8 }}>{shortStatusLabel(e.status)}</span>
                {typeof e.run_count === "number" ? <span style={{ fontSize: 12, opacity: 0.75 }}>{e.run_count} runs</span> : null}
                <span style={{ fontFamily: FONT.mono, fontSize: 11, color: "#6B7280" }}>{e.id.slice(0, 10)}…</span>
                <button type="button" onClick={() => setLastExperimentId(e.id)}>
                  Load
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section style={{ padding: 12, border: "1px solid #E5E3DC", borderRadius: 8 }}>
        <div style={{ ...sectionHeadingStyle, marginTop: 0 }}>Compare two individual runs</div>
        <p style={{ fontSize: 14, opacity: 0.85 }}>Paste two run IDs to compare their outcomes side by side.</p>
        <div style={{ display: "grid", gap: 8, maxWidth: 520 }}>
          <input placeholder="First run ID" value={compareIdA} onChange={(e) => setCompareIdA(e.target.value)} style={{ padding: 8 }} />
          <input placeholder="Second run ID" value={compareIdB} onChange={(e) => setCompareIdB(e.target.value)} style={{ padding: 8 }} />
          <button type="button" onClick={() => void onCompare()}>
            Compare
          </button>
        </div>
        {compareError ? <div style={{ color: "#E05252", marginTop: 8 }}>{compareError}</div> : null}
        {compareA && compareB ? (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 6 }}>Run A · {compareA.id.slice(0, 8)}…</div>
              <div style={{ fontSize: 13 }}>Status: {shortStatusLabel(compareA.status)}</div>
              {(compareA.outcome_indicators ?? []).map((o) => (
                <div key={`a-${o.round_number}`} style={{ fontSize: 12, marginTop: 6 }}>
                  Round {o.round_number}: Adoption {o.adoption_momentum.toFixed(2)} · Disagreements {o.conflict_events} ·
                  Consistency {o.consistency_index.toFixed(2)}
                </div>
              ))}
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 6 }}>Run B · {compareB.id.slice(0, 8)}…</div>
              <div style={{ fontSize: 13 }}>Status: {shortStatusLabel(compareB.status)}</div>
              {(compareB.outcome_indicators ?? []).map((o) => (
                <div key={`b-${o.round_number}`} style={{ fontSize: 12, marginTop: 6 }}>
                  Round {o.round_number}: Adoption {o.adoption_momentum.toFixed(2)} · Disagreements {o.conflict_events} ·
                  Consistency {o.consistency_index.toFixed(2)}
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
