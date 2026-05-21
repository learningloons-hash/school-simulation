import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  startSimulation,
  preflightSimulation,
  getSimulation,
  listSimulations,
  exportZipUrl,
  downloadExportJson,
  samplingReportUrl,
  createValidityNote,
  fetchScenarioCatalog,
  fetchCapabilities,
  modelChoicesFromCapabilities,
  modelChoiceToRunRequest,
  FALLBACK_MODEL_CHOICES,
  type SimulationTurn,
  type SimulationListItem,
  type SimulationStatus,
  type ValidityNoteCreate,
  type ScenarioCatalogItem,
  type RunEconomics,
  type ModelChoiceOption,
  type PreflightSummary,
} from "./lib/api";
import { AgentConsole } from "./components/AgentConsole";
import { ExperimentConsole } from "./components/ExperimentConsole";
import { LiveRunDashboard } from "./components/LiveRunDashboard";
import { ScenarioWizard } from "./components/ScenarioWizard";
import { SennaHeader } from "./components/SennaHeader";
import { ScenarioSelector } from "./components/ScenarioSelector";
import { RunStatusCard } from "./components/RunStatusCard";
import { ConversationView } from "./components/ConversationView";
import {
  classifyRunStatusTone,
  getRunStatusLabel,
  RUN_STATUS_PILL_STYLES,
  shortStatusLabel,
} from "./lib/runStatusCopy";
import { FONT, secondaryBtnStyle } from "./lib/theme";

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

const PRIMARY_TABS = [
  ["controls", "Set Up & Run"],
  ["live", "Watch Live"],
  ["transcript", "Conversation"],
  ["outcomes", "Results"],
  ["state", "Attitudes"],
] as const satisfies [TabId, string][];

const SECONDARY_TABS = [
  ["experiments", "Compare Runs"],
  ["agent", "Assistant"],
  ["scenarios", "Policy Scenarios"],
  ["validity", "Quality Notes"],
  ["metadata", "Run Details"],
] as const satisfies [TabId, string][];

const FALLBACK_SCENARIO_CATALOG: ScenarioCatalogItem[] = [
  { id: "psle_reform_mvp", name: "PSLE Reform", rag_enabled: false, source: "builtin" },
  { id: "fsbb_comparator", name: "FSBB Comparator", rag_enabled: true, source: "builtin" },
];

const sectionHeadingStyle: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  color: "#595F6B",
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  marginBottom: 12,
};

const cardStyle: React.CSSProperties = {
  background: "#FFFFFF",
  border: "1px solid #E5E3DC",
  borderRadius: 10,
  padding: 20,
};

const emptyStateCardStyle: React.CSSProperties = {
  background: "#FFFFFF",
  border: "1px solid #E5E3DC",
  borderRadius: 10,
  padding: 24,
  textAlign: "center",
  fontSize: 14,
  color: "#6B7280",
};

function FieldDivider() {
  return <hr style={{ border: "none", borderTop: "1px solid #F0EEE8", margin: "4px 0" }} />;
}

function PreflightSetupPanel({
  preflight,
  warnings,
}: {
  preflight: PreflightSummary;
  warnings: string[];
}) {
  const cost = preflight.estimated_cost_usd ?? 0;
  const pressure = preflight.context_pressure_ratio;
  return (
    <div
      style={{
        marginTop: 12,
        padding: 12,
        background: "#F7F6F2",
        border: "1px solid #E5E3DC",
        borderRadius: 8,
        fontSize: 13,
      }}
    >
      <strong style={{ display: "block", marginBottom: 6 }}>Run estimate (preflight)</strong>
      <ul style={{ margin: "0 0 8px 18px", padding: 0, color: "#1A1A1A" }}>
        <li>
          ~{preflight.total_speaking_turns ?? 0} speaking turns ({preflight.llm_turns ?? 0} LLM,{" "}
          {preflight.heuristic_turns ?? 0} heuristic)
        </li>
        <li>
          Estimated cost envelope: {cost > 0 ? `~$${cost.toFixed(2)}` : "$0 (local / unpaid path)"}
        </li>
        {pressure != null ? (
          <li>Context pressure vs model window: ~{Math.round(pressure * 100)}%</li>
        ) : null}
      </ul>
      {warnings.length > 0 ? (
        <div
          style={{
            padding: 10,
            background: "#fff8e6",
            border: "1px solid #e6d08c",
            borderRadius: 6,
          }}
        >
          <strong>Preflight warnings</strong> (you can still start the run):
          <ul style={{ margin: "6px 0 0 18px" }}>
            {warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function formatRunDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - d.getTime()) / 86_400_000);
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

function readinessLevel(v: number | null): string {
  if (v === null) return "unknown";
  if (v < 0.33) return "low";
  if (v < 0.66) return "moderate";
  return "high";
}

export default function App() {

  const [scenarioId, setScenarioId] = useState<string>("psle_reform_mvp");
  const [scenarioCatalog, setScenarioCatalog] = useState<ScenarioCatalogItem[] | null>(null);
  /** Empty = server default; profile id, __hybrid__, or legacy lmstudio/anthropic/hybrid */
  const [modelChoice, setModelChoice] = useState<string>("");
  const [modelChoiceOptions, setModelChoiceOptions] = useState<ModelChoiceOption[]>(FALLBACK_MODEL_CHOICES);

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

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const cap = await fetchCapabilities();
        if (!cancelled) {
          setModelChoiceOptions(modelChoicesFromCapabilities(cap));
        }
      } catch {
        if (!cancelled) {
          setModelChoiceOptions(FALLBACK_MODEL_CHOICES);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const runScenarioChoices = scenarioCatalog ?? FALLBACK_SCENARIO_CATALOG;
  const runModelChoices = modelChoiceOptions;
  const [totalRounds, setTotalRounds] = useState<number>(4);
  const [agentLimit, setAgentLimit] = useState<number>(3);
  const [rosterCsv, setRosterCsv] = useState<string>("");
  const [populationCsv, setPopulationCsv] = useState<string>("");
  const [populationSampleMode, setPopulationSampleMode] = useState<string>("weighted");
  const [randomSeed, setRandomSeed] = useState<number>(42);
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
  const [setupPreflight, setSetupPreflight] = useState<{
    warnings: string[];
    preflight: PreflightSummary;
  } | null>(null);
  const [setupPreflightLoading, setSetupPreflightLoading] = useState(false);
  const [setupPreflightError, setSetupPreflightError] = useState<string | null>(null);
  const [convergedAtRound, setConvergedAtRound] = useState<number | null>(null);
  const [runEconomics, setRunEconomics] = useState<RunEconomics | null>(null);
  const [openRunIdInput, setOpenRunIdInput] = useState("");

  const [viewportWidth, setViewportWidth] = useState(() =>
    typeof window !== "undefined" ? window.innerWidth : 1200,
  );

  useEffect(() => {
    const onResize = () => setViewportWidth(window.innerWidth);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const isWideLayout = viewportWidth >= 700;

  const discussionSummaryStats = useMemo(() => {
    const firstState = stateTimeline[0]?.global_state;
    const lastState = stateTimeline[stateTimeline.length - 1]?.global_state;
    return {
      firstReadiness: firstState?.implementation_readiness ?? null,
      lastReadiness: lastState?.implementation_readiness ?? null,
      firstAlignment: firstState?.alignment_index ?? null,
      lastAlignment: lastState?.alignment_index ?? null,
      totalConflicts: outcomeIndicators.reduce((sum, o) => sum + (o.conflict_events ?? 0), 0),
      totalRoundsCompleted: stateTimeline.length,
    };
  }, [stateTimeline, outcomeIndicators]);

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

  useEffect(() => {
    if (activeTab === "controls") void refreshRuns();
  }, [activeTab, refreshRuns]);

  useEffect(() => {
    if (activeTab !== "controls") return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      void (async () => {
        setSetupPreflightLoading(true);
        setSetupPreflightError(null);
        try {
          const ctRaw = convergenceThreshold.trim();
          const convOpts =
            ctRaw !== "" && Number.isFinite(Number(ctRaw))
              ? { convergence_threshold: Number(ctRaw), convergence_patience: convergencePatience }
              : {};
          const result = await preflightSimulation(
            {
              scenario_id: scenarioId,
              total_rounds: totalRounds,
              agent_limit: agentLimit,
              random_seed: randomSeed,
              ...modelChoiceToRunRequest(modelChoice, runModelChoices),
              simulation_mode: simulationMode,
              speakers_per_round: speakersPerRound,
              ...convOpts,
            },
            controller.signal,
          );
          setSetupPreflight(result);
        } catch (e) {
          if ((e as Error).name === "AbortError") return;
          setSetupPreflight(null);
          setSetupPreflightError(String((e as Error)?.message ?? e));
        } finally {
          setSetupPreflightLoading(false);
        }
      })();
    }, 450);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [
    activeTab,
    scenarioId,
    totalRounds,
    agentLimit,
    randomSeed,
    modelChoice,
    runModelChoices,
    simulationMode,
    speakersPerRound,
    convergenceThreshold,
    convergencePatience,
  ]);

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
        ...modelChoiceToRunRequest(modelChoice, runModelChoices),
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

  async function loadRunById(id: string, opts?: { switchTab?: boolean }) {
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
      if (opts?.switchTab) {
        if (res.status === "running" || res.status === "starting") setActiveTab("live");
        else if (res.status === "completed") setActiveTab("transcript");
      }
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
      setVnError("Add at least one score or note before saving.");
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

  const tabStyle = (id: TabId): React.CSSProperties => {
    const active = activeTab === id;
    return {
      padding: "7px 12px",
      borderRadius: 8,
      border: active ? "1px solid #4A6FA5" : "1px solid #E5E3DC",
      background: active ? "#EEF3FA" : "#FFFFFF",
      cursor: "pointer",
      fontFamily: "inherit",
      fontSize: 13,
      fontWeight: active ? 500 : 400,
      color: active ? "#4A6FA5" : "#1A1A1A",
      whiteSpace: "nowrap",
      flexShrink: 0,
      transition: "background 0.1s ease, border-color 0.1s ease",
    };
  };

  /** Keep tab content mounted so form state, polls, and in-flight fetches survive tab switches. */
  const tabPanelStyle = (id: TabId): React.CSSProperties => ({
    display: activeTab === id ? "block" : "none",
  });

  const tabPanelHidden = (id: TabId) => activeTab !== id;

  return (
    <div
      style={{
        maxWidth: 1100,
        margin: "0 auto",
        padding: 24,
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        background: "#F7F6F2",
        minHeight: "100vh",
      }}
    >
      <SennaHeader
        status={status}
        currentRound={currentRound}
        totalRounds={totalRounds}
        convergedAtRound={convergedAtRound}
      />

      <main>
      <div style={{ position: "relative", marginBottom: 16 }}>
        <div
          role="tablist"
          aria-label="Navigation"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            overflowX: "auto",
            scrollbarWidth: "none",
            msOverflowStyle: "none",
            paddingBottom: 2,
          }}
        >
          {PRIMARY_TABS.map(([id, label]) => (
            <button
              key={id}
              id={`tab-${id}`}
              type="button"
              role="tab"
              aria-selected={activeTab === id}
              aria-controls={`panel-${id}`}
              style={tabStyle(id)}
              onClick={() => setActiveTab(id)}
            >
              {label}
            </button>
          ))}
          <div
            style={{
              width: 1,
              alignSelf: "stretch",
              minHeight: 28,
              background: "#E5E3DC",
              margin: "0 4px",
              flexShrink: 0,
            }}
            aria-hidden
          />
          {SECONDARY_TABS.map(([id, label]) => (
            <button
              key={id}
              id={`tab-${id}`}
              type="button"
              role="tab"
              aria-selected={activeTab === id}
              aria-controls={`panel-${id}`}
              style={tabStyle(id)}
              onClick={() => setActiveTab(id)}
            >
              {label}
            </button>
          ))}
        </div>
        <div
          aria-hidden
          style={{
            position: "absolute",
            top: 0,
            right: 0,
            width: 32,
            height: "100%",
            background: "linear-gradient(to right, transparent, #F7F6F2)",
            pointerEvents: "none",
          }}
        />
      </div>

      <section
        id="panel-controls"
        role="tabpanel"
        aria-labelledby="tab-controls"
        style={tabPanelStyle("controls")}
        aria-hidden={tabPanelHidden("controls")}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: isWideLayout ? "minmax(0, 1fr) minmax(0, 1fr)" : "1fr",
            gap: 24,
            alignItems: "start",
          }}
        >
          <div>
            <div style={sectionHeadingStyle}>Set up your discussion</div>
            <section style={{ ...cardStyle, display: "grid", gap: 20 }}>
              <div>
                <div style={sectionHeadingStyle}>Policy scenario</div>
                <ScenarioSelector
                  scenarios={runScenarioChoices}
                  selected={scenarioId}
                  onChange={setScenarioId}
                />
              </div>

              <FieldDivider />

              <label style={{ display: "grid", gap: 6 }}>
                <span>Discussion rounds</span>
                <input
                  type="number"
                  value={totalRounds}
                  min={1}
                  max={25}
                  onChange={(e) => setTotalRounds(Number(e.target.value))}
                />
                <span style={{ fontSize: 12, color: "#6B7280" }}>
                  Each round, participants share their views. More rounds = richer deliberation.
                </span>
              </label>

              <FieldDivider />

              <label style={{ display: "grid", gap: 6 }}>
                <span>How participants take turns</span>
                <select value={simulationMode} onChange={(e) => setSimulationMode(e.target.value)}>
                  <option value="full_round_robin">Everyone speaks each round</option>
                  <option value="sample_k_per_round">Rotating speakers</option>
                </select>
                <span style={{ fontSize: 12, color: "#6B7280" }}>
                  Participants who do not speak in a round keep their current views. Summary scores still reflect the full
                  group.
                </span>
              </label>

              {simulationMode === "sample_k_per_round" ? (
                <label style={{ display: "grid", gap: 6 }}>
                  <span>Speakers per round</span>
                  <input
                    type="number"
                    value={speakersPerRound}
                    min={1}
                    max={50}
                    onChange={(e) => setSpeakersPerRound(Number(e.target.value))}
                  />
                  <span style={{ fontSize: 12, color: "#6B7280" }}>
                    How many participants speak in each round when using rotating mode.
                  </span>
                </label>
              ) : null}

              <FieldDivider />

              <label style={{ display: "grid", gap: 6 }}>
                <span>Number of participants</span>
                <input
                  type="number"
                  value={agentLimit}
                  min={1}
                  max={50}
                  onChange={(e) => setAgentLimit(Number(e.target.value))}
                />
                <span style={{ fontSize: 12, color: "#6B7280" }}>How many participants take part in the simulation.</span>
                {agentLimit > 20 ? (
                  <span style={{ fontSize: 12, color: "#92400E" }}>
                    For large simulations (over 20 participants), expect longer run times.
                  </span>
                ) : null}
              </label>

              <FieldDivider />

              <label style={{ display: "grid", gap: 6 }}>
                <span>AI model</span>
                <select value={modelChoice} onChange={(e) => setModelChoice(e.target.value)}>
                  {runModelChoices.map((opt) => (
                    <option key={opt.value || "__default__"} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>

              <FieldDivider />

              <details style={{ border: "1px solid #E5E3DC", borderRadius: 8, padding: "8px 12px", background: "#F7F6F2" }}>
                <summary
                  style={{
                    cursor: "pointer",
                    fontSize: 13,
                    color: "#4A6FA5",
                    fontWeight: 500,
                    listStyle: "none",
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                  }}
                >
                  ▸ Advanced options
                </summary>
                <div style={{ display: "grid", gap: 12, marginTop: 12 }}>
                  <label style={{ display: "grid", gap: 6 }}>
                    <span>Reproducibility seed</span>
                    <input type="number" value={randomSeed} onChange={(e) => setRandomSeed(Number(e.target.value))} />
                  </label>

                  <label style={{ display: "grid", gap: 6 }}>
                    <span>
                      Custom participant list (CSV) —{" "}
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
                    <span style={{ fontSize: 12, color: "#6B7280" }}>
                      Optional. Upload a CSV to specify exactly who participates.
                    </span>
                  </label>

                  <label style={{ display: "grid", gap: 6 }}>
                    <span>
                      Participant pool (CSV) —{" "}
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
                    <span style={{ fontSize: 12, color: "#6B7280" }}>
                      Optional. Upload a pool of participants for Senna to sample from. Senna draws up to your
                      participant count from the pool (no duplicates). Optional roster data can still be merged per slot
                      after the draw.
                    </span>
                  </label>

                  {populationCsv.trim() ? (
                    <label style={{ display: "grid", gap: 6 }}>
                      <span>How to select participants</span>
                      <select
                        value={populationSampleMode}
                        onChange={(e) => setPopulationSampleMode(e.target.value)}
                      >
                        <option value="weighted">Weighted random</option>
                        <option value="stratified">Stratified by group</option>
                      </select>
                    </label>
                  ) : null}

                  <div style={{ display: "grid", gap: 8, padding: 10, background: "#fff", borderRadius: 8 }}>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>Auto-stop when consensus is reached</div>
                    <label style={{ display: "grid", gap: 6 }}>
                      <span>Sensitivity (0.01 = very sensitive, 0.1 = loose)</span>
                      <input
                        type="text"
                        inputMode="decimal"
                        placeholder="e.g. 0.01"
                        value={convergenceThreshold}
                        onChange={(e) => setConvergenceThreshold(e.target.value)}
                        style={{ maxWidth: 200 }}
                      />
                      <span style={{ fontSize: 12, color: "#6B7280" }}>
                        Leave blank to run all rounds regardless of consensus.
                      </span>
                    </label>
                    <label style={{ display: "grid", gap: 6 }}>
                      <span>Rounds to confirm consensus</span>
                      <input
                        type="number"
                        value={convergencePatience}
                        min={1}
                        max={25}
                        onChange={(e) => setConvergencePatience(Number(e.target.value))}
                        style={{ maxWidth: 120 }}
                      />
                      <span style={{ fontSize: 12, color: "#6B7280" }}>
                        Senna will stop after this many rounds of stable opinion.
                      </span>
                    </label>
                  </div>
                </div>
              </details>

              {setupPreflightLoading ? (
                <p style={{ fontSize: 13, color: "#6B7280", margin: "8px 0 0 0" }}>Estimating run scale…</p>
              ) : setupPreflightError ? (
                <p style={{ fontSize: 13, color: "#B45309", margin: "8px 0 0 0" }}>
                  Could not estimate this setup: {setupPreflightError}
                </p>
              ) : setupPreflight ? (
                <PreflightSetupPanel preflight={setupPreflight.preflight} warnings={setupPreflight.warnings} />
              ) : null}

              <button
                type="button"
                onClick={() => void onStart()}
                disabled={status === "running" || status === "starting"}
                style={{
                  background: status === "running" || status === "starting" ? "#9BAFC7" : "#4A6FA5",
                  color: "#FFFFFF",
                  border: "none",
                  borderRadius: 8,
                  padding: "12px 24px",
                  fontWeight: 600,
                  fontSize: 15,
                  cursor: status === "running" || status === "starting" ? "not-allowed" : "pointer",
                  width: "100%",
                  marginTop: 4,
                  fontFamily: "inherit",
                  transition: "background 0.15s ease",
                }}
              >
                {status === "starting" ? "Starting…" : status === "running" ? "Running…" : "Start discussion"}
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
                  <strong>Warnings from server</strong> (the run still started):
                  <ul style={{ margin: "6px 0 0 18px" }}>
                    {runStartWarnings.map((w) => (
                      <li key={w}>{w}</li>
                    ))}
                  </ul>
                  <p style={{ margin: "8px 0 0 0", fontSize: 12, color: "#6B7280" }}>
                    The run started, but check Run Details for the full configuration.
                  </p>
                </div>
              ) : null}
            </section>
          </div>

          <div>
            <div style={sectionHeadingStyle}>Current discussion</div>
            <RunStatusCard
              status={status}
              runId={runId}
              currentRound={currentRound}
              totalRounds={totalRounds}
              convergedAtRound={convergedAtRound}
              transcriptLength={transcript.length}
              failureReason={failureReason}
              onOpenLive={() => setActiveTab("live")}
              onOpenConversation={() => setActiveTab("transcript")}
            />

            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 12,
                marginTop: 28,
                flexWrap: "wrap",
              }}
            >
              <div style={{ ...sectionHeadingStyle, marginBottom: 0 }}>Recent discussions</div>
              <button
                type="button"
                aria-label="Refresh run list"
                onClick={() => void refreshRuns()}
                style={{ fontSize: 12, color: "#595F6B", background: "none", border: "none", cursor: "pointer" }}
              >
                ↻ Refresh
              </button>
            </div>
            {listError ? <div style={{ color: "#E05252", marginTop: 8 }}>{listError}</div> : null}
            {runList.length === 0 ? (
              <div style={{ ...emptyStateCardStyle, marginTop: 8 }}>No previous discussions yet. Start one above.</div>
            ) : (
              <ul style={{ listStyle: "none", padding: 0, margin: "8px 0 0 0", display: "grid", gap: 10 }}>
                {runList.map((r) => {
                  const scenarioName =
                    runScenarioChoices.find((s) => s.id === r.scenario_id)?.name ?? r.scenario_id;
                  const tone = classifyRunStatusTone(r.status);
                  const pillStyle = RUN_STATUS_PILL_STYLES[tone];
                  const dateLabel = formatRunDate(r.created_at);
                  return (
                    <li
                      key={r.id}
                      style={{
                        ...cardStyle,
                        padding: 16,
                        display: "grid",
                        gap: 10,
                      }}
                    >
                      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                        <div style={{ fontSize: 15, fontWeight: 600, color: "#1A1A1A" }}>{scenarioName}</div>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span style={{ ...pillStyle, borderRadius: 999, padding: "3px 10px", fontSize: 12, fontWeight: 500 }}>
                            ● {shortStatusLabel(r.status)}
                          </span>
                          {dateLabel ? (
                            <span style={{ fontSize: 13, color: "#6B7280" }}>{dateLabel}</span>
                          ) : null}
                        </div>
                      </div>
                      <div style={{ fontSize: 13, color: "#6B7280" }}>
                        {r.current_round} of {r.total_rounds} rounds
                        {r.experiment_id ? (
                          <span style={{ marginLeft: 8, fontSize: 12, color: "#6B7280" }}>· part of a comparison run</span>
                        ) : null}
                      </div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                        <button
                          type="button"
                          title="Load this discussion"
                          style={{
                            background: "#FFFFFF",
                            color: "#1A1A1A",
                            border: "1px solid #E5E3DC",
                            borderRadius: 8,
                            padding: "8px 14px",
                            fontSize: 14,
                            cursor: "pointer",
                            fontFamily: "inherit",
                          }}
                          onClick={() => void loadRunById(r.id, { switchTab: true })}
                        >
                          Open
                        </button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}

            <div style={{ marginTop: 20 }}>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: "#595F6B",
                  marginBottom: 12,
                }}
              >
                Load a previous discussion by ID
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                <input
                  value={openRunIdInput}
                  onChange={(e) => setOpenRunIdInput(e.target.value)}
                  placeholder="Paste a run ID to reload a previous session"
                  style={{
                    flex: "1 1 240px",
                    padding: "8px 12px",
                    border: "1px solid #E5E3DC",
                    borderRadius: 8,
                    fontFamily: "inherit",
                  }}
                />
                <button
                  type="button"
                  disabled={!openRunIdInput.trim()}
                  style={{
                    ...secondaryBtnStyle,
                    opacity: openRunIdInput.trim() ? 1 : 0.5,
                  }}
                  onClick={() => void loadRunById(openRunIdInput)}
                >
                  Load
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section
        id="panel-live"
        role="tabpanel"
        aria-labelledby="tab-live"
        style={{ ...tabPanelStyle("live"), paddingTop: 4 }}
        aria-hidden={tabPanelHidden("live")}
      >
        {!runId ? (
          <div style={emptyStateCardStyle}>
            Start a discussion from the Set Up &amp; Run tab to see live charts here.
          </div>
        ) : status === "starting" ? (
          <div style={emptyStateCardStyle}>
            Starting up — charts will appear once the first round begins.
          </div>
        ) : (
          <LiveRunDashboard
            status={status}
            currentRound={currentRound}
            transcriptLength={transcript.length}
            stateTimeline={stateTimeline}
            outcomeIndicators={outcomeIndicators}
            configSnapshot={configSnapshot}
            convergedAtRound={convergedAtRound}
          />
        )}
      </section>

      <section
        id="panel-transcript"
        role="tabpanel"
        aria-labelledby="tab-transcript"
        style={{ ...tabPanelStyle("transcript"), paddingTop: 4 }}
        aria-hidden={tabPanelHidden("transcript")}
      >
        {transcript.length === 0 ? (
          <div style={emptyStateCardStyle}>
            No conversation yet. Start a discussion and exchanges will appear here as they happen.
          </div>
        ) : (
          <ConversationView turns={transcript} />
        )}
      </section>

      <section
        id="panel-outcomes"
        role="tabpanel"
        aria-labelledby="tab-outcomes"
        style={{ ...tabPanelStyle("outcomes"), paddingTop: 4 }}
        aria-hidden={tabPanelHidden("outcomes")}
      >
        {stateTimeline.length === 0 && outcomeIndicators.length === 0 ? (
          <div style={emptyStateCardStyle}>Results will appear here once a discussion is complete.</div>
        ) : (
          <>
            {stateTimeline.length > 0 ? (
              <div
                style={{
                  ...cardStyle,
                  padding: "18px 20px",
                  marginBottom: outcomeIndicators.length > 0 ? 20 : 0,
                  lineHeight: 1.7,
                  fontSize: 14,
                  color: "#1A1A1A",
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 15 }}>Discussion summary</div>
                <p style={{ margin: "0 0 8px 0" }}>
                  After <strong>{discussionSummaryStats.totalRoundsCompleted}</strong>{" "}
                  {discussionSummaryStats.totalRoundsCompleted === 1 ? "round" : "rounds"} of discussion
                  {convergedAtRound != null ? (
                    <>
                      {", the group reached consensus at Round "}
                      <strong>{convergedAtRound}</strong>
                      {" and the discussion stopped early"}
                    </>
                  ) : null}
                  {", readiness to adopt the policy "}
                  {discussionSummaryStats.firstReadiness !== null && discussionSummaryStats.lastReadiness !== null ? (
                    <>
                      moved from <strong>{readinessLevel(discussionSummaryStats.firstReadiness)}</strong> to{" "}
                      <strong>{readinessLevel(discussionSummaryStats.lastReadiness)}</strong>.
                    </>
                  ) : (
                    "was tracked across all rounds."
                  )}
                </p>
                {discussionSummaryStats.firstAlignment !== null && discussionSummaryStats.lastAlignment !== null ? (
                  <p style={{ margin: "0 0 8px 0" }}>
                    Group agreement{" "}
                    {discussionSummaryStats.lastAlignment > discussionSummaryStats.firstAlignment
                      ? "rose"
                      : discussionSummaryStats.lastAlignment < discussionSummaryStats.firstAlignment
                        ? "fell"
                        : "held steady"}{" "}
                    from <strong>{Math.round(discussionSummaryStats.firstAlignment * 100)}%</strong> to{" "}
                    <strong>{Math.round(discussionSummaryStats.lastAlignment * 100)}%</strong>.
                  </p>
                ) : null}
                {discussionSummaryStats.totalConflicts > 0 ? (
                  <p style={{ margin: 0 }}>
                    There {discussionSummaryStats.totalConflicts === 1 ? "was" : "were"}{" "}
                    <strong>{discussionSummaryStats.totalConflicts}</strong> moment
                    {discussionSummaryStats.totalConflicts !== 1 ? "s" : ""} of disagreement across the discussion.
                  </p>
                ) : null}
              </div>
            ) : null}
            {outcomeIndicators.length > 0 ? (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: "2px solid #E5E3DC" }}>
                      <th style={{ padding: "8px 12px", textAlign: "left", color: "#6B7280", fontWeight: 600 }}>
                        Round
                      </th>
                      <th style={{ padding: "8px 12px", textAlign: "left", color: "#6B7280", fontWeight: 600 }}>
                        Adoption score
                      </th>
                      <th style={{ padding: "8px 12px", textAlign: "left", color: "#6B7280", fontWeight: 600 }}>
                        Disagreements
                      </th>
                      <th style={{ padding: "8px 12px", textAlign: "left", color: "#6B7280", fontWeight: 600 }}>
                        Consistency score
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {outcomeIndicators.map((o) => (
                      <tr key={o.round_number} style={{ borderBottom: "1px solid #F0EEE8" }}>
                        <td style={{ padding: "8px 12px", color: "#1A1A1A" }}>{o.round_number}</td>
                        <td style={{ padding: "8px 12px", color: "#1A1A1A", fontFamily: FONT.mono, fontSize: 13 }}>
                          {o.adoption_momentum.toFixed(2)}
                        </td>
                        <td style={{ padding: "8px 12px", color: "#1A1A1A", fontFamily: FONT.mono, fontSize: 13 }}>
                          {o.conflict_events}
                        </td>
                        <td style={{ padding: "8px 12px", color: "#1A1A1A", fontFamily: FONT.mono, fontSize: 13 }}>
                          {o.consistency_index.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </>
        )}
      </section>

      <section
        id="panel-state"
        role="tabpanel"
        aria-labelledby="tab-state"
        style={{ ...tabPanelStyle("state"), paddingTop: 4 }}
        aria-hidden={tabPanelHidden("state")}
      >
        {stateTimeline.length === 0 ? (
          <div style={emptyStateCardStyle}>
            Attitude data will appear here as the discussion progresses.
          </div>
        ) : (
          <div style={{ display: "grid", gap: 16 }}>
            {stateTimeline.map((round) => (
              <div key={`state-${round.round_number}`} style={{ ...cardStyle, padding: 16 }}>
                <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 15, color: "#1A1A1A" }}>
                  Round {round.round_number}
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 16, marginBottom: 12 }}>
                  <div>
                    <div
                      style={{
                        fontSize: 11,
                        color: "#6B7280",
                        fontWeight: 500,
                        textTransform: "uppercase",
                        letterSpacing: "0.4px",
                      }}
                    >
                      Readiness to adopt
                    </div>
                    <div style={{ fontSize: 20, fontWeight: 600, color: "#1A1A1A" }}>
                      {Math.round((round.global_state?.implementation_readiness ?? 0) * 100)}%
                    </div>
                  </div>
                  <div>
                    <div
                      style={{
                        fontSize: 11,
                        color: "#6B7280",
                        fontWeight: 500,
                        textTransform: "uppercase",
                        letterSpacing: "0.4px",
                      }}
                    >
                      Level of agreement
                    </div>
                    <div style={{ fontSize: 20, fontWeight: 600, color: "#1A1A1A" }}>
                      {Math.round((round.global_state?.alignment_index ?? 0) * 100)}%
                    </div>
                  </div>
                  {round.global_state?.convergence_delta != null ? (
                    <div>
                      <div
                        style={{
                          fontSize: 11,
                          color: "#6B7280",
                          fontWeight: 500,
                          textTransform: "uppercase",
                          letterSpacing: "0.4px",
                        }}
                      >
                        Opinion change rate
                      </div>
                      <div style={{ fontSize: 20, fontWeight: 600, color: "#1A1A1A" }}>
                        {round.global_state.convergence_delta.toFixed(3)}
                      </div>
                    </div>
                  ) : null}
                </div>
                <div style={{ display: "grid", gap: 10 }}>
                  {(round.agents ?? []).map((agent) => (
                    <div
                      key={`${round.round_number}-${agent.agent_id}`}
                      style={{
                        background: "#F7F6F2",
                        borderRadius: 8,
                        padding: "10px 12px",
                        fontSize: 13,
                      }}
                    >
                      <div style={{ fontWeight: 600, color: "#1A1A1A", marginBottom: 6 }}>
                        {agent.agent_name}
                        <span style={{ fontWeight: 400, color: "#6B7280", marginLeft: 6 }}>
                          {agent.agent_role.replace(/_/g, " ")}
                        </span>
                      </div>
                      <div
                        style={{
                          display: "flex",
                          flexWrap: "wrap",
                          gap: 16,
                          fontSize: 12,
                          color: "#6B7280",
                        }}
                      >
                        <span>
                          Support <strong style={{ color: "#1A1A1A" }}>{Math.round(agent.support_level * 100)}%</strong>
                        </span>
                        <span>
                          Resistance{" "}
                          <strong style={{ color: "#1A1A1A" }}>{Math.round(agent.resistance_level * 100)}%</strong>
                        </span>
                        <span>
                          Workload <strong style={{ color: "#1A1A1A" }}>{Math.round(agent.workload_stress * 100)}%</strong>
                        </span>
                        <span>
                          Stance <strong style={{ color: "#1A1A1A" }}>{agent.belief_posture ?? "—"}</strong>
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section
        id="panel-metadata"
        role="tabpanel"
        aria-labelledby="tab-metadata"
        style={tabPanelStyle("metadata")}
        aria-hidden={tabPanelHidden("metadata")}
      >
        <div style={{ fontSize: 18, fontWeight: 600, color: "#1A1A1A", marginBottom: 20, marginTop: 0 }}>Run Details</div>
        {runId && (status === "completed" || status === "failed" || status === "running") ? (
          <div style={{ marginBottom: 0 }}>
            <div style={sectionHeadingStyle}>Download</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              <a
                href={exportZipUrl(runId)}
                download
                style={{
                  background: "#4A6FA5",
                  color: "#FFFFFF",
                  border: "none",
                  borderRadius: 8,
                  padding: "10px 18px",
                  fontWeight: 600,
                  fontSize: 14,
                  textDecoration: "none",
                  display: "inline-block",
                  cursor: "pointer",
                }}
              >
                Download full report
              </a>
              <button
                type="button"
                style={{
                  background: "#FFFFFF",
                  color: "#1A1A1A",
                  border: "1px solid #E5E3DC",
                  borderRadius: 8,
                  padding: "10px 18px",
                  fontSize: 14,
                  cursor: "pointer",
                  fontFamily: "inherit",
                }}
                onClick={() => {
                  void downloadExportJson(runId).catch((e) => setStatus(`error: ${String(e)}`));
                }}
              >
                Export as JSON
              </button>
            </div>
            <div style={{ fontSize: 12, color: "#595F6B", marginTop: 6 }}>
              Full report includes conversation transcript, participant attitudes, outcomes, and cost data.
            </div>
          </div>
        ) : null}
        <div style={{ fontSize: 12, color: "#595F6B", marginTop: 16 }}>
          Session ID: <span style={{ fontFamily: "monospace" }}>{runId ?? "—"}</span>
        </div>
        <div style={{ fontSize: 12, color: "#595F6B", marginTop: 8 }}>
          {getRunStatusLabel(status, { currentRound, totalRounds, convergedAtRound })}
        </div>
        {failureReason ? (
          <div style={{ marginTop: 8, padding: 8, background: "#ffecec", borderRadius: 6 }}>
            <strong>Something went wrong:</strong> {failureReason}
          </div>
        ) : null}
        {runEconomics ? (
          <div
            style={{
              background: "#F0FDF4",
              border: "1px solid #BBF7D0",
              borderRadius: 10,
              padding: "14px 16px",
              marginTop: 16,
            }}
          >
            <div style={{ fontWeight: 600, fontSize: 14, color: "#1A1A1A", marginBottom: 10 }}>AI usage</div>
            <div style={{ display: "grid", gap: 6, fontSize: 13, color: "#1A1A1A" }}>
              <div>
                Tokens used: ~
                {((runEconomics.total_input_tokens ?? 0) + (runEconomics.total_output_tokens ?? 0)).toLocaleString()}
              </div>
              <div>
                Estimated cost:{" "}
                {runEconomics.estimated_cost_usd != null && runEconomics.estimated_cost_usd > 0
                  ? `$${runEconomics.estimated_cost_usd.toFixed(4)}`
                  : runEconomics.llm_provider === "lmstudio" || runEconomics.llm_provider === ""
                    ? "Free (local model)"
                    : "—"}
              </div>
              {runEconomics.tier_breakdown ? (
                <div style={{ color: "#6B7280", fontSize: 12, marginTop: 4 }}>
                  Full AI turns: {runEconomics.tier_breakdown.tier_1_turns ?? 0} &nbsp;·&nbsp; Simplified turns:{" "}
                  {runEconomics.tier_breakdown.tier_2_turns ?? 0} &nbsp;·&nbsp; Rule-based turns:{" "}
                  {runEconomics.tier_breakdown.tier_3_turns ?? 0}
                </div>
              ) : null}
            </div>
          </div>
        ) : runId ? (
          <p style={{ fontSize: 12, opacity: 0.75, marginTop: 12 }}>
            Token and cost figures appear here after the backend records usage for this run.
          </p>
        ) : null}
        <details style={{ marginTop: 20 }}>
          <summary
            style={{
              cursor: "pointer",
              fontSize: 13,
              color: "#4A6FA5",
              fontWeight: 500,
              listStyle: "none",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            ▸ Technical configuration
          </summary>
          <div style={{ marginTop: 10 }}>
            {configSnapshot ? (
              <pre
                style={{
                  whiteSpace: "pre-wrap",
                  background: "#F7F6F2",
                  padding: 12,
                  borderRadius: 8,
                  fontSize: 12,
                  color: "#1A1A1A",
                  overflowX: "auto",
                }}
              >
                {JSON.stringify(configSnapshot, null, 2)}
              </pre>
            ) : (
              <div style={{ fontSize: 13, color: "#595F6B" }}>No configuration loaded.</div>
            )}
            {runId && (status === "completed" || status === "failed") ? (
              <div style={{ marginTop: 10, fontSize: 12 }}>
                <a href={samplingReportUrl(runId)} target="_blank" rel="noreferrer" style={{ color: "#4A6FA5" }}>
                  Sampling report
                </a>
                <span style={{ color: "#595F6B" }}> — tier, role, and posture breakdown</span>
              </div>
            ) : null}
          </div>
        </details>
      </section>

      <section
        id="panel-validity"
        role="tabpanel"
        aria-labelledby="tab-validity"
        style={tabPanelStyle("validity")}
        aria-hidden={tabPanelHidden("validity")}
      >
        <div style={{ fontSize: 18, fontWeight: 600, color: "#1A1A1A", marginBottom: 16 }}>Quality notes</div>
        <p style={{ fontSize: 14, color: "#595F6B", maxWidth: 560, marginBottom: 20 }}>
          Rate how realistic and useful this discussion felt — for the whole run or for individual rounds. Notes are saved
          with the run and included in all exports.
        </p>
        {runId ? (
          <div style={{ fontSize: 13, color: "#595F6B", marginBottom: 12 }}>
            Noting quality for session:{" "}
            <span style={{ fontFamily: "monospace", fontSize: 12 }}>{runId.slice(0, 12)}…</span>
          </div>
        ) : (
          <div style={{ fontSize: 13, color: "#595F6B", marginBottom: 12 }}>Load a run first to add notes.</div>
        )}
        {vnError ? <div style={{ color: "#E05252", marginBottom: 8 }}>{vnError}</div> : null}
        <div
          style={{
            display: "grid",
            gap: 10,
            maxWidth: 560,
            marginBottom: 20,
            padding: 20,
            border: "1px solid #E5E3DC",
            borderRadius: 10,
            background: "#FFFFFF",
          }}
        >
          <label style={{ display: "grid", gap: 4 }}>
            <span>Round (leave blank for whole run)</span>
            <input value={vnRound} onChange={(e) => setVnRound(e.target.value)} placeholder="e.g. 2" style={{ padding: 8 }} />
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Your name or ID (optional)</span>
            <input
              value={vnRater}
              onChange={(e) => setVnRater(e.target.value)}
              placeholder="e.g. mark, reviewer-1"
              style={{ padding: 8 }}
            />
          </label>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
            <label style={{ display: "grid", gap: 4 }}>
              <span>Realism score</span>
              <input
                value={vnFaceScore}
                onChange={(e) => setVnFaceScore(e.target.value)}
                placeholder="0.0 – 1.0"
                style={{ padding: 8 }}
              />
            </label>
            <label style={{ display: "grid", gap: 4 }}>
              <span>Accuracy score</span>
              <input
                value={vnConstructScore}
                onChange={(e) => setVnConstructScore(e.target.value)}
                placeholder="0.0 – 1.0"
                style={{ padding: 8 }}
              />
            </label>
            <label style={{ display: "grid", gap: 4 }}>
              <span>Predictive score</span>
              <input
                value={vnPredictiveScore}
                onChange={(e) => setVnPredictiveScore(e.target.value)}
                placeholder="0.0 – 1.0"
                style={{ padding: 8 }}
              />
            </label>
          </div>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Realism notes</span>
            <textarea value={vnFaceRubric} onChange={(e) => setVnFaceRubric(e.target.value)} rows={2} style={{ padding: 8 }} />
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Accuracy notes</span>
            <textarea
              value={vnConstructRubric}
              onChange={(e) => setVnConstructRubric(e.target.value)}
              rows={2}
              style={{ padding: 8 }}
            />
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Predictive notes</span>
            <textarea
              value={vnPredictiveRubric}
              onChange={(e) => setVnPredictiveRubric(e.target.value)}
              rows={2}
              style={{ padding: 8 }}
            />
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Other notes</span>
            <textarea value={vnNotes} onChange={(e) => setVnNotes(e.target.value)} rows={2} style={{ padding: 8 }} />
          </label>
          <button type="button" disabled={vnSaving || !runId} onClick={() => void onSaveValidityNote()} style={{ padding: 10 }}>
            {vnSaving ? "Saving…" : "Save quality note"}
          </button>
        </div>
        <div style={sectionHeadingStyle}>Saved notes</div>
        {validityNotes.length === 0 ? (
          <div style={emptyStateCardStyle}>No quality notes yet for this run.</div>
        ) : (
          <ul style={{ listStyle: "none", padding: 0, display: "grid", gap: 10 }}>
            {validityNotes.map((n) => (
              <li key={n.id} style={{ border: "1px solid #E5E3DC", borderRadius: 8, padding: 10, fontSize: 13 }}>
                <div>
                  <strong>{n.round_number == null ? "Whole run" : `Round ${n.round_number}`}</strong>
                  {n.rater_id ? ` · ${n.rater_id}` : ""}
                  {n.created_at ? ` · ${formatRunDate(n.created_at)}` : ""}
                </div>
                {n.face_score != null || n.face_rubric ? (
                  <div>
                    Realism: {n.face_score ?? "—"}
                    {n.face_rubric ? ` — ${n.face_rubric}` : ""}
                  </div>
                ) : null}
                {n.construct_score != null || n.construct_rubric ? (
                  <div>
                    Accuracy: {n.construct_score ?? "—"}
                    {n.construct_rubric ? ` — ${n.construct_rubric}` : ""}
                  </div>
                ) : null}
                {n.predictive_score != null || n.predictive_rubric ? (
                  <div>
                    Predictive: {n.predictive_score ?? "—"}
                    {n.predictive_rubric ? ` — ${n.predictive_rubric}` : ""}
                  </div>
                ) : null}
                {n.notes ? <div style={{ marginTop: 6 }}>Other notes: {n.notes}</div> : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section
        id="panel-experiments"
        role="tabpanel"
        aria-labelledby="tab-experiments"
        style={{ ...tabPanelStyle("experiments"), paddingTop: 4 }}
        aria-hidden={tabPanelHidden("experiments")}
      >
        <ExperimentConsole scenarioChoices={runScenarioChoices} />
      </section>

      <section
        id="panel-agent"
        role="tabpanel"
        aria-labelledby="tab-agent"
        style={{
          ...tabPanelStyle("agent"),
          padding: "4px 0 24px",
        }}
        aria-hidden={tabPanelHidden("agent")}
      >
        <AgentConsole />
      </section>

      <section
        id="panel-scenarios"
        role="tabpanel"
        aria-labelledby="tab-scenarios"
        style={tabPanelStyle("scenarios")}
        aria-hidden={tabPanelHidden("scenarios")}
      >
        <ScenarioWizard onCatalogRefresh={refreshScenarioCatalog} />
      </section>
      </main>
    </div>
  );
}
