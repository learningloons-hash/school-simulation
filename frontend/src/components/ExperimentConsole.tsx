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
  type ScenarioCatalogItem,
  type SimulationStatus,
} from "../lib/api";

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
  { value: "implementation_readiness", label: "implementation_readiness" },
  { value: "alignment_index", label: "alignment_index" },
  { value: "adoption_momentum", label: "adoption_momentum" },
  { value: "conflict_events", label: "conflict_events" },
  { value: "consistency_index", label: "consistency_index" },
  { value: "convergence_delta", label: "convergence_delta" },
];

type RunRowForm = { label: string; sampling_strategy: string };

type Props = {
  scenarioChoices: ScenarioCatalogItem[];
};

function fmtMetric(v: number | undefined): string {
  if (typeof v !== "number" || Number.isNaN(v)) return "—";
  return v.toFixed(2);
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
      <section style={{ padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
        <h2 style={{ marginTop: 0 }}>Create experiment</h2>
        <p style={{ fontSize: 14, opacity: 0.85, marginTop: 0 }}>
          Same scenario and seed; each row queues a simulation with a different <code>sampling_strategy</code>. Runs
          execute <strong>sequentially</strong> on the server (one finishes before the next starts).
        </p>
        <div style={{ display: "grid", gap: 10, maxWidth: 480 }}>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Name</span>
            <input value={expName} onChange={(e) => setExpName(e.target.value)} style={{ padding: 8 }} />
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Scenario</span>
            <select value={scenarioId} onChange={(e) => setScenarioId(e.target.value)} style={{ padding: 8 }}>
              {scenarioChoices.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Random seed</span>
            <input type="number" value={randomSeed} onChange={(e) => setRandomSeed(Number(e.target.value))} style={{ padding: 8 }} />
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Total rounds</span>
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
            <span>Agent limit</span>
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
            <div style={{ fontSize: 12, fontWeight: 600 }}>Convergence (optional — same for every run)</div>
            <label style={{ display: "grid", gap: 4 }}>
              <span>Threshold (0–1, empty = off)</span>
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
              <span>Patience (rounds)</span>
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

        <h3 style={{ marginTop: 18 }}>Runs</h3>
        {runRows.map((row, i) => (
          <div key={i} style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 8, alignItems: "center" }}>
            <input
              placeholder="label"
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
                  {s}
                </option>
              ))}
            </select>
            <button type="button" onClick={() => removeRow(i)} disabled={runRows.length <= 1}>
              Remove
            </button>
          </div>
        ))}
        <button type="button" onClick={addRow} style={{ marginRight: 8 }}>
          Add run row
        </button>
        <button type="button" disabled={busy} onClick={() => void onSubmitExperiment()} style={{ padding: "10px 16px" }}>
          {busy ? "Running experiment…" : "Start experiment"}
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
        {error ? <div style={{ color: "coral", marginTop: 8 }}>{error}</div> : null}
        {lastExperimentId ? (
          <div style={{ marginTop: 10, fontSize: 13 }}>
            Last experiment id: <code>{lastExperimentId}</code>
          </div>
        ) : null}
      </section>

      <section style={{ padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
        <h2 style={{ marginTop: 0 }}>Comparison chart</h2>
        {!detail ? (
          <div style={{ opacity: 0.75 }}>Create or load an experiment to see metrics by round.</div>
        ) : (
          <div style={{ display: "grid", gap: 12 }}>
            <div style={{ fontSize: 13, opacity: 0.85 }}>
              Experiment <code>{detail.experiment.id.slice(0, 12)}…</code> — status {detail.experiment.status}
              {typeof detail.total_estimated_cost_usd === "number" ? (
                <span style={{ marginLeft: 8 }}>
                  · Total est. cost (USD): <strong>{detail.total_estimated_cost_usd.toFixed(4)}</strong>
                </span>
              ) : null}
            </div>
            <label style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", fontSize: 14 }}>
              <span>Sparkline metric</span>
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
                <div key={label} style={{ border: "1px solid #eee", borderRadius: 8, padding: 10 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>{label}</div>
                  <Sparkline values={vals} width={160} height={40} color={LINE_COLORS[idx % LINE_COLORS.length]} />
                  <div style={{ fontSize: 11, opacity: 0.75, marginTop: 4 }}>{comparisonMetric}</div>
                </div>
              ))}
            </div>
            <details style={{ fontSize: 13 }}>
              <summary style={{ cursor: "pointer" }}>All metrics by round (table)</summary>
              <div style={{ overflowX: "auto", marginTop: 8 }}>
                <table style={{ borderCollapse: "collapse", fontSize: 12, minWidth: 480 }}>
                  <thead>
                    <tr>
                      <th style={{ border: "1px solid #ddd", padding: 6, textAlign: "left" }}>Round</th>
                      {tableSeriesKeys.map((sk) => (
                        <th key={sk} style={{ border: "1px solid #ddd", padding: 6, textAlign: "left" }}>
                          {sk}
                          {(() => {
                            const runRow = detail.runs.find((x) => x.series_key === sk);
                            const e = runRow?.economics;
                            if (!e) return null;
                            return (
                              <div style={{ fontWeight: 400, fontSize: 10, opacity: 0.8, marginTop: 4 }}>
                                in/out {e.total_input_tokens ?? "—"}/{e.total_output_tokens ?? "—"} · ${Number(e.estimated_cost_usd ?? 0).toFixed(4)}
                              </div>
                            );
                          })()}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {detail.comparison.map((row) => (
                      <tr key={row.round_number}>
                        <td style={{ border: "1px solid #ddd", padding: 6 }}>{row.round_number}</td>
                        {tableSeriesKeys.map((sk) => {
                          const met = row.by_run[sk];
                          return (
                            <td
                              key={sk}
                              style={{ border: "1px solid #ddd", padding: 6, fontFamily: "monospace", fontSize: 11 }}
                            >
                              {met ? (
                                <>
                                  ir {fmtMetric(met.implementation_readiness)} · al {fmtMetric(met.alignment_index)} · am{" "}
                                  {fmtMetric(met.adoption_momentum)} · ce {met.conflict_events ?? "—"} · ci{" "}
                                  {fmtMetric(met.consistency_index)}
                                  {" · cd "}
                                  {fmtMetric(met.convergence_delta)}
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
              <a href={experimentExportZipUrl(detail.experiment.id)} download style={{ padding: "8px 12px", border: "1px solid #999", borderRadius: 6 }}>
                Download experiment ZIP
              </a>
              <a
                href={experimentExportJsonUrl(detail.experiment.id)}
                target="_blank"
                rel="noreferrer"
                style={{ padding: "8px 12px", border: "1px solid #999", borderRadius: 6 }}
              >
                Open experiment JSON
              </a>
            </div>
          </div>
        )}
      </section>

      <section style={{ padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
        <h2 style={{ marginTop: 0 }}>Per-run status</h2>
        {!detail ? (
          <div style={{ opacity: 0.75 }}>No experiment loaded.</div>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 8 }}>
            {detail.runs.map((r) => (
              <li key={r.simulation_id} style={{ border: "1px solid #eee", borderRadius: 8, padding: 10, fontSize: 13 }}>
                <strong>{r.series_key}</strong> · {r.sampling_strategy ?? "?"} · {r.status}
                {r.status === "completed" ? (
                  <span style={{ opacity: 0.85 }}>
                    {" "}
                    ·{" "}
                    {typeof r.converged_at_round === "number"
                      ? `Converged R${r.converged_at_round}`
                      : `Full ${r.total_rounds} rounds`}
                  </span>
                ) : null}
                {r.economics ? (
                  <span style={{ opacity: 0.85, marginLeft: 6 }}>
                    · Tokens {r.total_input_tokens ?? r.economics.total_input_tokens ?? "—"}/
                    {r.total_output_tokens ?? r.economics.total_output_tokens ?? "—"} · est. $
                    {Number(r.economics.estimated_cost_usd ?? 0).toFixed(4)}
                  </span>
                ) : null}
                <div style={{ fontFamily: "monospace", fontSize: 11, marginTop: 4 }}>{r.simulation_id}</div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section style={{ padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
        <h2 style={{ marginTop: 0 }}>Recent experiments</h2>
        <button type="button" onClick={() => void refreshList()} style={{ marginBottom: 8 }}>
          Refresh
        </button>
        {listErr ? <div style={{ color: "coral" }}>{listErr}</div> : null}
        {expList.length === 0 ? (
          <div>None yet.</div>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, display: "grid", gap: 8 }}>
            {expList.map((e) => (
              <li key={e.id} style={{ border: "1px solid #eee", borderRadius: 8, padding: 10, display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
                <span style={{ fontWeight: 600 }}>{e.name}</span>
                <span style={{ opacity: 0.8 }}>{e.status}</span>
                {typeof e.run_count === "number" ? <span style={{ fontSize: 12, opacity: 0.75 }}>{e.run_count} runs</span> : null}
                <code style={{ fontSize: 11 }}>{e.id.slice(0, 14)}…</code>
                <button type="button" onClick={() => setLastExperimentId(e.id)}>
                  Load detail
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section style={{ padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
        <h2 style={{ marginTop: 0 }}>Compare two runs (by ID)</h2>
        <p style={{ fontSize: 14, opacity: 0.85 }}>Side-by-side outcome indicators from <code>GET /simulations/{"{id}"}</code>.</p>
        <div style={{ display: "grid", gap: 8, maxWidth: 520 }}>
          <input placeholder="Run ID A" value={compareIdA} onChange={(e) => setCompareIdA(e.target.value)} style={{ padding: 8 }} />
          <input placeholder="Run ID B" value={compareIdB} onChange={(e) => setCompareIdB(e.target.value)} style={{ padding: 8 }} />
          <button type="button" onClick={() => void onCompare()}>
            Compare
          </button>
        </div>
        {compareError ? <div style={{ color: "coral", marginTop: 8 }}>{compareError}</div> : null}
        {compareA && compareB ? (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
            <div>
              <h3>A: {compareA.id.slice(0, 8)}…</h3>
              <div style={{ fontSize: 13 }}>Status: {compareA.status}</div>
              {(compareA.outcome_indicators ?? []).map((o) => (
                <div key={`a-${o.round_number}`} style={{ fontSize: 12, marginTop: 6 }}>
                  R{o.round_number}: adoption {o.adoption_momentum.toFixed(2)}, conflicts {o.conflict_events}, consistency{" "}
                  {o.consistency_index.toFixed(2)}
                </div>
              ))}
            </div>
            <div>
              <h3>B: {compareB.id.slice(0, 8)}…</h3>
              <div style={{ fontSize: 13 }}>Status: {compareB.status}</div>
              {(compareB.outcome_indicators ?? []).map((o) => (
                <div key={`b-${o.round_number}`} style={{ fontSize: 12, marginTop: 6 }}>
                  R{o.round_number}: adoption {o.adoption_momentum.toFixed(2)}, conflicts {o.conflict_events}, consistency{" "}
                  {o.consistency_index.toFixed(2)}
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
