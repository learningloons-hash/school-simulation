import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  startSimulation,
  getSimulation,
  listSimulations,
  exportZipUrl,
  downloadExportJson,
  samplingReportUrl,
  createValidityNote,
  fetchScenarioCatalog,
  type SimulationTurn,
  type SimulationListItem,
  type SimulationStatus,
  type ValidityNoteCreate,
  type ScenarioCatalogItem,
  type RunEconomics,
} from "./lib/api";
import { AgentConsole } from "./components/AgentConsole";
import { ExperimentConsole } from "./components/ExperimentConsole";
import { LiveRunDashboard } from "./components/LiveRunDashboard";
import { ScenarioWizard } from "./components/ScenarioWizard";

/** Faster refresh while a run is in progress (Iteration 8). */
const POLL_MS_WHILE_RUNNING = 750;

type TabId =
  | "controls"
  | "agent"
  | "live"
  | "transcript"
  | "outcomes"
  | "state"
  | "metadata"
  | "validity"
  | "experiments"
  | "scenarios";

const FALLBACK_SCENARIO_CATALOG: ScenarioCatalogItem[] = [
  { id: "psle_reform_mvp", name: "PSLE Reform (MVP)", rag_enabled: false, source: "builtin" },
  { id: "fsbb_comparator", name: "FSBB Comparator (MVP)", rag_enabled: true, source: "builtin" },
];

export default function App() {

  const [scenarioId, setScenarioId] = useState<string>("psle_reform_mvp");
  const [scenarioCatalog, setScenarioCatalog] = useState<ScenarioCatalogItem[] | null>(null);

  const refreshScenarioCatalog = useCallback(async () => {
    try {
      setScenarioCatalog(await fetchScenarioCatalog());
    } catch {
      setScenarioCatalog(null);
    }
  }, []);

  useEffect(() => {
    void refreshScenarioCatalog();
  }, [refreshScenarioCatalog]);

  const runScenarioChoices = scenarioCatalog ?? FALLBACK_SCENARIO_CATALOG;
  const [totalRounds, setTotalRounds] = useState<number>(4);
  const [agentLimit, setAgentLimit] = useState<number>(3);
  const [rosterCsv, setRosterCsv] = useState<string>("");
  const [populationCsv, setPopulationCsv] = useState<string>("");
  const [populationSampleMode, setPopulationSampleMode] = useState<string>("weighted");
  const [randomSeed, setRandomSeed] = useState<number>(42);
  /** Empty = server default */
  const [llmProviderChoice, setLlmProviderChoice] = useState<string>("");
  const [simulationMode, setSimulationMode] = useState<string>("full_round_robin");
  const [speakersPerRound, setSpeakersPerRound] = useState<number>(2);
  /** Iteration 28: empty = disabled */
  const [convergenceThreshold, setConvergenceThreshold] = useState<string>("");
  const [convergencePatience, setConvergencePatience] = useState<number>(2);

  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("idle");
  const [currentRound, setCurrentRound] = useState<number>(0);
  const [failureReason, setFailureReason] = useState<string | null>(null);
  const [configSnapshot, setConfigSnapshot] = useState<Record<string, unknown> | null>(null);
  const [transcript, setTranscript] = useState<SimulationTurn[]>([]);
  const [stateTimeline, setStateTimeline] = useState<SimulationStatus["state_timeline"]>([]);
  const [outcomeIndicators, setOutcomeIndicators] = useState<SimulationStatus["outcome_indicators"]>([]);
  const [validityNotes, setValidityNotes] = useState<NonNullable<SimulationStatus["validity_notes"]>>([]);

  const [runList, setRunList] = useState<SimulationListItem[]>([]);
  const [listError, setListError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("controls");

  const [vnRound, setVnRound] = useState<string>("");
  const [vnRater, setVnRater] = useState<string>("");
  const [vnFaceScore, setVnFaceScore] = useState<string>("");
  const [vnFaceRubric, setVnFaceRubric] = useState<string>("");
  const [vnConstructScore, setVnConstructScore] = useState<string>("");
  const [vnConstructRubric, setVnConstructRubric] = useState<string>("");
  const [vnPredictiveScore, setVnPredictiveScore] = useState<string>("");
  const [vnPredictiveRubric, setVnPredictiveRubric] = useState<string>("");
  const [vnNotes, setVnNotes] = useState<string>("");
  const [vnSaving, setVnSaving] = useState(false);
  const [vnError, setVnError] = useState<string | null>(null);
  /** From POST /simulations/run (Iteration 12), e.g. unknown roster/population group_ids */
  const [runStartWarnings, setRunStartWarnings] = useState<string[] | null>(null);
  const [convergedAtRound, setConvergedAtRound] = useState<number | null>(null);
  const [runEconomics, setRunEconomics] = useState<RunEconomics | null>(null);

  const refreshRuns = useCallback(async () => {
    try {
      setListError(null);
      const rows = await listSimulations(50);
      setRunList(rows);
    } catch (e) {
      setListError(String((e as Error)?.message ?? e));
    }
  }, []);

  useEffect(() => {
    void refreshRuns();
  }, [refreshRuns]);

  async function poll(simId: string) {
    setStatus("running");
    setFailureReason(null);
    for (let attempt = 0; attempt < 240; attempt++) {
      const res = await getSimulation(simId);
      setStatus(res.status);
      setCurrentRound(res.current_round);
      setTranscript(res.transcript ?? []);
      setStateTimeline(res.state_timeline ?? []);
      setOutcomeIndicators(res.outcome_indicators ?? []);
      setValidityNotes(res.validity_notes ?? []);
      setFailureReason(res.failure_reason ?? null);
      setConfigSnapshot((res.config_snapshot as Record<string, unknown>) ?? null);
      setConvergedAtRound(typeof res.converged_at_round === "number" ? res.converged_at_round : null);
      setRunEconomics(res.economics ?? null);
      if (res.status === "completed" || res.status === "failed") {
        void refreshRuns();
        return;
      }
      await new Promise((r) => setTimeout(r, POLL_MS_WHILE_RUNNING));
    }
    setStatus("timeout");
    void refreshRuns();
  }

  async function onStart() {
    setRunId(null);
    setTranscript([]);
    setStateTimeline([]);
    setOutcomeIndicators([]);
    setValidityNotes([]);
    setFailureReason(null);
    setConfigSnapshot(null);
    setRunStartWarnings(null);
    setConvergedAtRound(null);
    setRunEconomics(null);
    setStatus("starting");

    try {
      const ctRaw = convergenceThreshold.trim();
      const convOpts =
        ctRaw !== "" && Number.isFinite(Number(ctRaw))
          ? { convergence_threshold: Number(ctRaw), convergence_patience: convergencePatience }
          : {};
      const { id, warnings } = await startSimulation({
        scenario_id: scenarioId,
        total_rounds: totalRounds,
        agent_limit: agentLimit,
        random_seed: randomSeed,
        ...(llmProviderChoice ? { llm_provider: llmProviderChoice } : {}),
        ...(rosterCsv.trim() ? { roster_csv: rosterCsv.trim() } : {}),
        ...(populationCsv.trim()
          ? {
              population_csv: populationCsv.trim(),
              population_sample_mode: populationSampleMode,
            }
          : {}),
        simulation_mode: simulationMode,
        speakers_per_round: speakersPerRound,
        ...convOpts,
      });
      if (!id) {
        setStatus("error: missing run id from server");
        return;
      }
      setRunId(id);
      if (warnings && warnings.length > 0) {
        setRunStartWarnings(warnings);
      }
      poll(id).catch((e) => {
        setStatus(`error: ${String((e as Error)?.message ?? e)}`);
      });
    } catch (e) {
      setStatus(`error: ${String((e as Error)?.message ?? e)}`);
    }
  }

  async function loadRunById(id: string) {
    const trimmed = id.trim();
    if (!trimmed) return;
    try {
      const res = await getSimulation(trimmed);
      setRunId(res.id);
      setStatus(res.status);
      setCurrentRound(res.current_round);
      setTranscript(res.transcript ?? []);
      setStateTimeline(res.state_timeline ?? []);
      setOutcomeIndicators(res.outcome_indicators ?? []);
      setValidityNotes(res.validity_notes ?? []);
      setFailureReason(res.failure_reason ?? null);
      setConfigSnapshot((res.config_snapshot as Record<string, unknown>) ?? null);
      setConvergedAtRound(typeof res.converged_at_round === "number" ? res.converged_at_round : null);
      setRunEconomics(res.economics ?? null);
    } catch (e) {
      setStatus(`error: ${String((e as Error)?.message ?? e)}`);
    }
  }

  async function onSaveValidityNote() {
    setVnError(null);
    if (!runId) {
      setVnError("Load or start a run first.");
      return;
    }
    const body: ValidityNoteCreate = {};
    const rt = vnRound.trim();
    if (rt !== "") {
      const n = parseInt(rt, 10);
      if (Number.isNaN(n)) {
        setVnError("Round must be a number or empty (run-level).");
        return;
      }
      body.round_number = n;
    }
    if (vnRater.trim()) body.rater_id = vnRater.trim();
    const parseOptFloat = (s: string) => {
      const t = s.trim();
      if (!t) return undefined;
      const x = parseFloat(t);
      return Number.isNaN(x) ? undefined : x;
    };
    const fs = parseOptFloat(vnFaceScore);
    const cs = parseOptFloat(vnConstructScore);
    const ps = parseOptFloat(vnPredictiveScore);
    if (fs !== undefined) body.face_score = fs;
    if (cs !== undefined) body.construct_score = cs;
    if (ps !== undefined) body.predictive_score = ps;
    if (vnFaceRubric.trim()) body.face_rubric = vnFaceRubric.trim();
    if (vnConstructRubric.trim()) body.construct_rubric = vnConstructRubric.trim();
    if (vnPredictiveRubric.trim()) body.predictive_rubric = vnPredictiveRubric.trim();
    if (vnNotes.trim()) body.notes = vnNotes.trim();
    const hasAny =
      body.round_number !== undefined ||
      body.rater_id !== undefined ||
      body.face_score !== undefined ||
      body.construct_score !== undefined ||
      body.predictive_score !== undefined ||
      body.face_rubric !== undefined ||
      body.construct_rubric !== undefined ||
      body.predictive_rubric !== undefined ||
      body.notes !== undefined;
    if (!hasAny) {
      setVnError("Add at least one score, rubric, rater, round, or notes.");
      return;
    }
    setVnSaving(true);
    try {
      await createValidityNote(runId, body);
      const res = await getSimulation(runId);
      setValidityNotes(res.validity_notes ?? []);
      setRunEconomics(res.economics ?? null);
    } catch (e) {
      setVnError(String((e as Error)?.message ?? e));
    } finally {
      setVnSaving(false);
    }
  }

  const tabStyle = (id: TabId) => ({
    padding: "8px 12px",
    borderRadius: 6,
    border: "1px solid #ccc",
    background: activeTab === id ? "#eef" : "#fff",
    cursor: "pointer" as const,
  });

  /** Keep tab content mounted so form state, polls, and in-flight fetches survive tab switches. */
  const tabPanelStyle = (id: TabId): React.CSSProperties => ({
    display: activeTab === id ? "block" : "none",
  });

  const tabPanelHidden = (id: TabId) => activeTab !== id;

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: 24, fontFamily: "system-ui" }}>
      <h1>MiroFish MVP Simulation</h1>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
        {(
          [
            ["controls", "Run"],
            ["agent", "Agent"],
            ["live", "Live"],
            ["transcript", "Transcript"],
            ["outcomes", "Outcomes"],
            ["state", "State"],
            ["metadata", "Run metadata"],
            ["validity", "Validity"],
            ["experiments", "Experiments"],
            ["scenarios", "Scenarios"],
          ] as const
        ).map(([id, label]) => (
          <button key={id} type="button" style={tabStyle(id)} onClick={() => setActiveTab(id)}>
            {label}
          </button>
        ))}
      </div>

      <div style={tabPanelStyle("controls")} aria-hidden={tabPanelHidden("controls")}>
          <section style={{ display: "grid", gap: 12, padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
            <label style={{ display: "grid", gap: 6 }}>
              <span>Scenario</span>
              <select value={scenarioId} onChange={(e) => setScenarioId(e.target.value)}>
                {runScenarioChoices.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.source}
                    {s.rag_enabled ? ", RAG" : ""})
                  </option>
                ))}
              </select>
            </label>

            <label style={{ display: "grid", gap: 6 }}>
              <span>Total rounds</span>
              <input
                type="number"
                value={totalRounds}
                min={1}
                max={25}
                onChange={(e) => setTotalRounds(Number(e.target.value))}
              />
            </label>

            <div style={{ display: "grid", gap: 8, padding: 10, background: "#f8fafc", borderRadius: 8 }}>
              <div style={{ fontSize: 13, fontWeight: 600 }}>Convergence stop (optional, Iteration 28)</div>
              <label style={{ display: "grid", gap: 6 }}>
                <span>Threshold (0–1, empty = off)</span>
                <input
                  type="text"
                  inputMode="decimal"
                  placeholder="e.g. 0.01"
                  value={convergenceThreshold}
                  onChange={(e) => setConvergenceThreshold(e.target.value)}
                  style={{ maxWidth: 200 }}
                />
                <span style={{ fontSize: 12, opacity: 0.8 }}>
                  Stops when mean population abs change in support / resistance / workload stays below this for N
                  consecutive rounds.
                </span>
              </label>
              <label style={{ display: "grid", gap: 6 }}>
                <span>Patience (consecutive rounds)</span>
                <input
                  type="number"
                  value={convergencePatience}
                  min={1}
                  max={25}
                  onChange={(e) => setConvergencePatience(Number(e.target.value))}
                  style={{ maxWidth: 120 }}
                />
              </label>
            </div>

            <label style={{ display: "grid", gap: 6 }}>
              <span>Agent limit</span>
              <input
                type="number"
                value={agentLimit}
                min={1}
                max={50}
                onChange={(e) => setAgentLimit(Number(e.target.value))}
              />
              <span style={{ fontSize: 12, opacity: 0.8 }}>
                API cap 50 (Iteration 9). Scale / cost notes: <code>docs/plans/SCALE_LIMITS_AND_COST.md</code>
              </span>
              {agentLimit > 20 ? (
                <span style={{ fontSize: 12, color: "#a60" }}>
                  Heads-up: runs with many agents are sequential LLM calls — expect long wall-clock time.
                </span>
              ) : null}
            </label>

            <label style={{ display: "grid", gap: 6 }}>
              <span>
                Roster CSV (optional) —{" "}
                <a href="/simulations/roster-csv-template" target="_blank" rel="noreferrer">
                  download template
                </a>
              </span>
              <textarea
                value={rosterCsv}
                onChange={(e) => setRosterCsv(e.target.value)}
                rows={5}
                placeholder="slot,persona_id,role,name,role_level,style_cues,beliefs_json,groups"
                style={{ fontFamily: "monospace", fontSize: 12 }}
              />
            </label>

            <label style={{ display: "grid", gap: 6 }}>
              <span>
                Population pool CSV (optional, Iteration 11) —{" "}
                <a href="/simulations/population-csv-template" target="_blank" rel="noreferrer">
                  download template
                </a>
              </span>
              <textarea
                value={populationCsv}
                onChange={(e) => setPopulationCsv(e.target.value)}
                rows={5}
                placeholder="persona_id,sampling_weight,stratum,age,sex,ethnicity,ses,name,groups"
                style={{ fontFamily: "monospace", fontSize: 12 }}
              />
              <span style={{ fontSize: 12, opacity: 0.8 }}>
                Draws <code>agent_limit</code> rows from the pool (no replacement) using <code>random_seed</code>.
                Optional roster CSV merges on top per slot after the draw.
              </span>
            </label>

            {populationCsv.trim() ? (
              <label style={{ display: "grid", gap: 6 }}>
                <span>Population sample mode</span>
                <select
                  value={populationSampleMode}
                  onChange={(e) => setPopulationSampleMode(e.target.value)}
                >
                  <option value="weighted">Weighted (within full pool)</option>
                  <option value="stratified">Stratified (by stratum column)</option>
                </select>
              </label>
            ) : null}

            <label style={{ display: "grid", gap: 6 }}>
              <span>Random seed</span>
              <input type="number" value={randomSeed} onChange={(e) => setRandomSeed(Number(e.target.value))} />
            </label>

            <label style={{ display: "grid", gap: 6 }}>
              <span>Interaction mode</span>
              <select value={simulationMode} onChange={(e) => setSimulationMode(e.target.value)}>
                <option value="full_round_robin">Full round-robin (each agent speaks every round)</option>
                <option value="sample_k_per_round">Sample K speakers per round (seed-stable)</option>
              </select>
              <span style={{ fontSize: 12, opacity: 0.8 }}>
                Iteration 10. Non-sampled agents keep state; global metrics still use the full roster.
              </span>
            </label>

            {simulationMode === "sample_k_per_round" ? (
              <label style={{ display: "grid", gap: 6 }}>
                <span>Speakers per round (K)</span>
                <input
                  type="number"
                  value={speakersPerRound}
                  min={1}
                  max={50}
                  onChange={(e) => setSpeakersPerRound(Number(e.target.value))}
                />
              </label>
            ) : null}

            <label style={{ display: "grid", gap: 6 }}>
              <span>LLM routing (optional)</span>
              <select value={llmProviderChoice} onChange={(e) => setLlmProviderChoice(e.target.value)}>
                <option value="">Server default</option>
                <option value="lmstudio">lmstudio (local)</option>
                <option value="anthropic">anthropic</option>
                <option value="hybrid">hybrid (frontier on first turn of each round)</option>
              </select>
            </label>

            <button onClick={onStart} disabled={status === "running" || status === "starting"} style={{ padding: 10 }}>
              {status === "starting" ? "Starting..." : "Start simulation"}
            </button>

            {runStartWarnings && runStartWarnings.length > 0 ? (
              <div
                style={{
                  marginTop: 12,
                  padding: 10,
                  background: "#fff8e6",
                  border: "1px solid #e6d08c",
                  borderRadius: 6,
                  fontSize: 13,
                }}
              >
                <strong>Warnings from server</strong> (run was still started; check <code>config_snapshot</code> for
                full detail):
                <ul style={{ margin: "6px 0 0 18px" }}>
                  {runStartWarnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>

          <section style={{ marginTop: 18 }}>
            <h2>Current run</h2>
            <div>Status: {status}</div>
            <div>Progress (rounds completed): {currentRound}</div>
            <div style={{ fontSize: 13, opacity: 0.85, maxWidth: 520 }}>
              This counter moves after each round completes (after all <strong>scheduled</strong> turns in that
              round). In sample-K mode, fewer turns run per round. While it stays at 0, the model is still
              working — open the{" "}
              <strong>Transcript</strong> tab to see each turn appear as it completes.
            </div>
            {status === "running" || status === "starting" ? (
              <div style={{ fontSize: 13, marginTop: 6 }}>
                Turns in transcript: {transcript.length} · polling ~{POLL_MS_WHILE_RUNNING}ms while running — open{" "}
                <button type="button" style={{ border: "none", background: "none", color: "#22c", cursor: "pointer", padding: 0, textDecoration: "underline" }} onClick={() => setActiveTab("live")}>
                  Live
                </button>{" "}
                for charts
              </div>
            ) : null}
            {runId && status !== "running" && status !== "starting" ? (
              <button type="button" style={{ marginTop: 8, padding: "6px 10px", borderRadius: 6, border: "1px solid #ccc", background: "#fff" }} onClick={() => setActiveTab("live")}>
                Open Live dashboard
              </button>
            ) : null}
            <div style={{ fontSize: 12, opacity: 0.8 }}>Run id: {runId ?? "(none)"}</div>
            {failureReason ? (
              <div style={{ marginTop: 8, padding: 8, background: "#ffecec", borderRadius: 6 }}>
                <strong>Failure</strong>: {failureReason}
              </div>
            ) : null}
            {runId && (status === "completed" || status === "failed" || status === "running") ? (
              <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
                <a href={exportZipUrl(runId)} download style={{ padding: "8px 12px", border: "1px solid #999", borderRadius: 6 }}>
                  Download ZIP (CSVs)
                </a>
                <button
                  type="button"
                  style={{ padding: "8px 12px", border: "1px solid #999", borderRadius: 6, background: "#fff" }}
                  onClick={() => downloadExportJson(runId).catch((e) => setStatus(`error: ${String(e)}`))}
                >
                  Download JSON
                </button>
                {status === "completed" || status === "failed" ? (
                  <a
                    href={samplingReportUrl(runId)}
                    target="_blank"
                    rel="noreferrer"
                    style={{ padding: "8px 12px", border: "1px solid #999", borderRadius: 6 }}
                  >
                    Sampling report (JSON)
                  </a>
                ) : null}
              </div>
            ) : null}
          </section>

          <section style={{ marginTop: 18 }}>
            <h2>Recent runs</h2>
            <button type="button" onClick={() => void refreshRuns()} style={{ marginBottom: 8 }}>
              Refresh list
            </button>
            {listError ? <div style={{ color: "coral" }}>{listError}</div> : null}
            {runList.length === 0 ? (
              <div>No runs in database yet.</div>
            ) : (
              <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 8 }}>
                {runList.map((r) => (
                  <li
                    key={r.id}
                    style={{ border: "1px solid #eee", borderRadius: 8, padding: 10, display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}
                  >
                    <span style={{ fontFamily: "monospace", fontSize: 12 }}>{r.id.slice(0, 12)}…</span>
                    <span>{r.status}</span>
                    <span>
                      {r.scenario_id} · r{r.current_round}/{r.total_rounds}
                      {r.experiment_id ? (
                        <span style={{ marginLeft: 6, fontSize: 11, opacity: 0.75 }}>
                          · exp {String(r.experiment_id).slice(0, 8)}…
                        </span>
                      ) : null}
                    </span>
                    <button type="button" onClick={() => void loadRunById(r.id)}>
                      Load in UI
                    </button>
                    <a href={exportZipUrl(r.id)} download style={{ fontSize: 13 }}>
                      ZIP
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section style={{ marginTop: 18 }}>
            <h2>Open run by ID</h2>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <input placeholder="simulation id" style={{ flex: "1 1 240px", padding: 8 }} id="open-run-id" />
              <button
                type="button"
                onClick={() => {
                  const el = document.getElementById("open-run-id") as HTMLInputElement | null;
                  void loadRunById(el?.value ?? "");
                }}
              >
                Load
              </button>
            </div>
          </section>
      </div>

      <section style={tabPanelStyle("live")} aria-hidden={tabPanelHidden("live")}>
          <h2>Live run dashboard</h2>
          {!runId ? (
            <div>Start a run or load one from the Run tab to see live metrics.</div>
          ) : (
            <LiveRunDashboard
              status={status}
              currentRound={currentRound}
              transcriptLength={transcript.length}
              stateTimeline={stateTimeline}
              outcomeIndicators={outcomeIndicators}
              configSnapshot={configSnapshot}
              runId={runId}
              convergedAtRound={convergedAtRound}
              pollIntervalMs={status === "running" || status === "starting" ? POLL_MS_WHILE_RUNNING : undefined}
            />
          )}
      </section>

      <section style={tabPanelStyle("transcript")} aria-hidden={tabPanelHidden("transcript")}>
          <h2>Transcript</h2>
          {transcript.length === 0 ? (
            <div>No turns loaded. Start a run or load one from the Run tab.</div>
          ) : (
            <div style={{ display: "grid", gap: 12 }}>
              {transcript.map((t, idx) => (
                <div key={`${t.id ?? "turn"}-${idx}`} style={{ border: "1px solid #eee", borderRadius: 8, padding: 12 }}>
                  <div style={{ fontSize: 12, opacity: 0.8 }}>
                    Round {t.round_number} - {t.agent_role} ({t.agent_name})
                  </div>
                  <div style={{ fontSize: 12, opacity: 0.8 }}>
                    {t.interaction_type} to {t.target_agent_name ?? t.target_scope} · intent {t.intent_tag ?? "unspecified"}
                    {" · "}
                    fidelity tier {t.fidelity_tier ?? 1}
                  </div>
                  {t.effective_provider || t.effective_model ? (
                    <div style={{ fontSize: 11, opacity: 0.75, marginTop: 4 }}>
                      LLM: {t.effective_provider ?? "?"} / {t.effective_model ?? "?"}
                    </div>
                  ) : null}
                  <pre style={{ whiteSpace: "pre-wrap", margin: "8px 0 0 0" }}>{t.raw_response}</pre>
                </div>
              ))}
            </div>
          )}
      </section>

      <section style={tabPanelStyle("outcomes")} aria-hidden={tabPanelHidden("outcomes")}>
          <h2>Outcome indicators</h2>
          {outcomeIndicators.length === 0 ? (
            <div>No outcomes loaded.</div>
          ) : (
            <div style={{ display: "grid", gap: 8 }}>
              {outcomeIndicators.map((o, idx) => (
                <div key={`outcome-${idx}`} style={{ border: "1px solid #eee", borderRadius: 8, padding: 10 }}>
                  Round {o.round_number}: adoption={o.adoption_momentum.toFixed(2)} · conflicts={o.conflict_events} ·
                  consistency={o.consistency_index.toFixed(2)}
                </div>
              ))}
            </div>
          )}
      </section>

      <section style={tabPanelStyle("state")} aria-hidden={tabPanelHidden("state")}>
          <h2>State timeline</h2>
          {stateTimeline.length === 0 ? (
            <div>No state timeline loaded.</div>
          ) : (
            <div style={{ display: "grid", gap: 12 }}>
              {stateTimeline.map((round) => (
                <div key={`state-${round.round_number}`} style={{ border: "1px solid #eee", borderRadius: 8, padding: 12 }}>
                  <div style={{ fontWeight: 600 }}>Round {round.round_number}</div>
                  <div style={{ fontSize: 12, opacity: 0.85 }}>
                    Global readiness: {(round.global_state?.implementation_readiness ?? 0).toFixed(2)} · alignment:{" "}
                    {(round.global_state?.alignment_index ?? 0).toFixed(2)}
                  </div>
                  <div style={{ marginTop: 8, display: "grid", gap: 6 }}>
                    {(round.agents ?? []).map((agent) => (
                      <div key={`${round.round_number}-${agent.agent_id}`} style={{ fontSize: 12 }}>
                        {agent.agent_name} ({agent.agent_role}) [{agent.demographics?.age ?? "?"}/{agent.demographics?.sex ?? "?"}/
                        {agent.demographics?.ethnicity ?? "?"}/{agent.demographics?.ses ?? "?"}] support={agent.support_level.toFixed(2)}{" "}
                        resistance={agent.resistance_level.toFixed(2)} workload={agent.workload_stress.toFixed(2)} posture={agent.belief_posture}
                        {agent.attribute_sections &&
                        (Object.keys(agent.attribute_sections.identity ?? {}).length > 0 ||
                          Object.keys(agent.attribute_sections.attitudes ?? {}).length > 0 ||
                          Object.keys(agent.attribute_sections.personal_history ?? {}).length > 0) ? (
                          <pre
                            style={{
                              marginTop: 6,
                              fontSize: 11,
                              opacity: 0.88,
                              whiteSpace: "pre-wrap",
                              background: "#fafafa",
                              padding: 6,
                              borderRadius: 4,
                            }}
                          >
                            {JSON.stringify(agent.attribute_sections, null, 2)}
                          </pre>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
      </section>

      <section style={tabPanelStyle("metadata")} aria-hidden={tabPanelHidden("metadata")}>
          <h2>Run metadata</h2>
          <div style={{ fontSize: 12, opacity: 0.85 }}>Run id: {runId ?? "(none)"}</div>
          <div style={{ fontSize: 12, opacity: 0.85 }}>Status: {status}</div>
          {runId && (status === "completed" || status === "failed") ? (
            <div style={{ fontSize: 12, marginTop: 8 }}>
              <a href={samplingReportUrl(runId)} target="_blank" rel="noreferrer">
                Open sampling report (JSON)
              </a>
              <span style={{ opacity: 0.75 }}> — tier / role / posture breakdown from persisted audit</span>
            </div>
          ) : null}
          {failureReason ? (
            <div style={{ marginTop: 8, padding: 8, background: "#ffecec", borderRadius: 6 }}>Failure: {failureReason}</div>
          ) : null}
          {runEconomics ? (
            <div style={{ marginTop: 14, padding: 12, background: "#f0fdf4", borderRadius: 8, fontSize: 13 }}>
              <h3 style={{ marginTop: 0, marginBottom: 8 }}>Run economics</h3>
              <div>
                Tokens in / out: {runEconomics.total_input_tokens ?? "—"} / {runEconomics.total_output_tokens ?? "—"}
              </div>
              <div>Estimated cost (USD): {runEconomics.estimated_cost_usd ?? "—"}</div>
              <div style={{ opacity: 0.85 }}>Provider (request): {runEconomics.llm_provider ?? "—"}</div>
              {runEconomics.tier_breakdown ? (
                <div style={{ marginTop: 6, fontFamily: "monospace", fontSize: 12 }}>
                  Tier turns — T1 {runEconomics.tier_breakdown.tier_1_turns ?? 0}, T2{" "}
                  {runEconomics.tier_breakdown.tier_2_turns ?? 0}, T3 {runEconomics.tier_breakdown.tier_3_turns ?? 0}
                </div>
              ) : null}
            </div>
          ) : (
            <p style={{ fontSize: 12, opacity: 0.75, marginTop: 12 }}>
              Run economics (tokens + estimated cost) appear here after the backend records usage (Iteration 29).
            </p>
          )}
          <h3 style={{ marginTop: 16 }}>Config snapshot</h3>
          {configSnapshot ? (
            <pre style={{ whiteSpace: "pre-wrap", background: "#f7f7f7", padding: 12, borderRadius: 8 }}>
              {JSON.stringify(configSnapshot, null, 2)}
            </pre>
          ) : (
            <div>No config snapshot loaded (start or load a run).</div>
          )}
          {configSnapshot && "state_audit_enabled" in configSnapshot ? (
            <p style={{ fontSize: 13, opacity: 0.85 }}>
              <code>state_audit_enabled</code> (reserved for future second-pass audit):{" "}
              {String(configSnapshot.state_audit_enabled)}
            </p>
          ) : null}
      </section>

      <section style={tabPanelStyle("validity")} aria-hidden={tabPanelHidden("validity")}>
          <h2>Validity notes</h2>
          <p style={{ fontSize: 14, opacity: 0.85, maxWidth: 640 }}>
            Manual face / construct / predictive coding per run or per round. Saved notes appear in{" "}
            <code>GET /simulations/{"{id}"}</code>, export JSON (<code>export_version</code> 4), and ZIP{" "}
            <code>validity_notes.csv</code>.
          </p>
          <div style={{ fontSize: 13, marginBottom: 12 }}>Run id: {runId ?? "(none — load a run first)"}</div>
          {vnError ? <div style={{ color: "coral", marginBottom: 8 }}>{vnError}</div> : null}
          <div
            style={{
              display: "grid",
              gap: 10,
              maxWidth: 560,
              marginBottom: 20,
              padding: 12,
              border: "1px solid #ddd",
              borderRadius: 8,
            }}
          >
            <label style={{ display: "grid", gap: 4 }}>
              <span>Round (empty = whole run)</span>
              <input value={vnRound} onChange={(e) => setVnRound(e.target.value)} placeholder="e.g. 2" style={{ padding: 8 }} />
            </label>
            <label style={{ display: "grid", gap: 4 }}>
              <span>Rater id (optional)</span>
              <input value={vnRater} onChange={(e) => setVnRater(e.target.value)} placeholder="analyst_id" style={{ padding: 8 }} />
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
              <label style={{ display: "grid", gap: 4 }}>
                <span>Face score</span>
                <input value={vnFaceScore} onChange={(e) => setVnFaceScore(e.target.value)} placeholder="0–1" style={{ padding: 8 }} />
              </label>
              <label style={{ display: "grid", gap: 4 }}>
                <span>Construct score</span>
                <input
                  value={vnConstructScore}
                  onChange={(e) => setVnConstructScore(e.target.value)}
                  placeholder="0–1"
                  style={{ padding: 8 }}
                />
              </label>
              <label style={{ display: "grid", gap: 4 }}>
                <span>Predictive score</span>
                <input
                  value={vnPredictiveScore}
                  onChange={(e) => setVnPredictiveScore(e.target.value)}
                  placeholder="0–1"
                  style={{ padding: 8 }}
                />
              </label>
            </div>
            <label style={{ display: "grid", gap: 4 }}>
              <span>Face rubric / notes</span>
              <textarea value={vnFaceRubric} onChange={(e) => setVnFaceRubric(e.target.value)} rows={2} style={{ padding: 8 }} />
            </label>
            <label style={{ display: "grid", gap: 4 }}>
              <span>Construct rubric / notes</span>
              <textarea
                value={vnConstructRubric}
                onChange={(e) => setVnConstructRubric(e.target.value)}
                rows={2}
                style={{ padding: 8 }}
              />
            </label>
            <label style={{ display: "grid", gap: 4 }}>
              <span>Predictive rubric / notes</span>
              <textarea
                value={vnPredictiveRubric}
                onChange={(e) => setVnPredictiveRubric(e.target.value)}
                rows={2}
                style={{ padding: 8 }}
              />
            </label>
            <label style={{ display: "grid", gap: 4 }}>
              <span>General notes</span>
              <textarea value={vnNotes} onChange={(e) => setVnNotes(e.target.value)} rows={2} style={{ padding: 8 }} />
            </label>
            <button type="button" disabled={vnSaving || !runId} onClick={() => void onSaveValidityNote()} style={{ padding: 10 }}>
              {vnSaving ? "Saving…" : "Save validity note"}
            </button>
          </div>
          <h3>Saved notes</h3>
          {validityNotes.length === 0 ? (
            <div>None yet for this run.</div>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, display: "grid", gap: 10 }}>
              {validityNotes.map((n) => (
                <li key={n.id} style={{ border: "1px solid #eee", borderRadius: 8, padding: 10, fontSize: 13 }}>
                  <div>
                    <strong>{n.round_number == null ? "Run-level" : `Round ${n.round_number}`}</strong>
                    {n.rater_id ? ` · rater ${n.rater_id}` : ""}
                    {n.created_at ? ` · ${n.created_at}` : ""}
                  </div>
                  <div>face: {n.face_score ?? "—"} / {n.face_rubric ?? "—"}</div>
                  <div>construct: {n.construct_score ?? "—"} / {n.construct_rubric ?? "—"}</div>
                  <div>predictive: {n.predictive_score ?? "—"} / {n.predictive_rubric ?? "—"}</div>
                  {n.notes ? <div style={{ marginTop: 6 }}>notes: {n.notes}</div> : null}
                </li>
              ))}
            </ul>
          )}
      </section>

      <section style={tabPanelStyle("experiments")} aria-hidden={tabPanelHidden("experiments")}>
        <h2 style={{ marginTop: 0 }}>Experiments</h2>
        <ExperimentConsole scenarioChoices={runScenarioChoices} />
      </section>

      <section
        style={{
          ...tabPanelStyle("agent"),
          padding: "4px 0 24px",
        }}
        aria-hidden={tabPanelHidden("agent")}
      >
        <h2 style={{ marginTop: 0 }}>Agent (plan / run / analyze)</h2>
        <AgentConsole />
      </section>

      <div style={tabPanelStyle("scenarios")} aria-hidden={tabPanelHidden("scenarios")}>
        <ScenarioWizard onCatalogRefresh={refreshScenarioCatalog} />
      </div>
    </div>
  );
}
