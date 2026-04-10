import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  agentAsk,
  agentExecute,
  agentPlan,
  type AgentAskResponse,
  type ExecutionPlan,
} from "../lib/api";
import { RunResultCard } from "./RunResultCard";

function prettyJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function isAbortError(e: unknown): boolean {
  if (e instanceof DOMException && e.name === "AbortError") return true;
  if (e instanceof Error && e.name === "AbortError") return true;
  return false;
}

function useElapsedSeconds(active: boolean): number {
  const [sec, setSec] = useState(0);
  useEffect(() => {
    if (!active) {
      setSec(0);
      return;
    }
    setSec(0);
    const t0 = Date.now();
    const id = window.setInterval(() => setSec(Math.floor((Date.now() - t0) / 1000)), 500);
    return () => window.clearInterval(id);
  }, [active]);
  return sec;
}

const QUESTION_PLACEHOLDER =
  "e.g. Plan and run a 1-round PSLE reform simulation and summarize key tensions.";

export function AgentConsole() {
  const [question, setQuestion] = useState("");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [constraints, setConstraints] = useState("");
  const [waitTimeoutSeconds, setWaitTimeoutSeconds] = useState(900);
  const [planTemperature, setPlanTemperature] = useState<string>("");
  const [planMaxTokens, setPlanMaxTokens] = useState<string>("");

  const abortRef = useRef<AbortController | null>(null);

  const [askLoading, setAskLoading] = useState(false);
  const [askError, setAskError] = useState<string | null>(null);
  const [lastAsk, setLastAsk] = useState<AgentAskResponse | null>(null);
  const [planDetailsOpen, setPlanDetailsOpen] = useState(false);

  const [planOnlyLoading, setPlanOnlyLoading] = useState(false);
  const [planOnlyError, setPlanOnlyError] = useState<string | null>(null);
  const [lastPlanOnly, setLastPlanOnly] = useState<ExecutionPlan | null>(null);

  const [executeJson, setExecuteJson] = useState("");
  const [executeLoading, setExecuteLoading] = useState(false);
  const [executeError, setExecuteError] = useState<string | null>(null);
  const [lastExecute, setLastExecute] = useState<{ runs: AgentAskResponse["runs"] } | null>(null);

  const anyLoading = askLoading || planOnlyLoading || executeLoading;
  const elapsedSec = useElapsedSeconds(anyLoading);

  const planOpts = useMemo(() => {
    const pt = planTemperature.trim();
    const pm = planMaxTokens.trim();
    const t = pt === "" ? NaN : Number(pt);
    const m = pm === "" ? NaN : Number(pm);
    return {
      plan_temperature: Number.isFinite(t) ? t : undefined,
      plan_max_tokens: Number.isFinite(m) ? m : undefined,
    };
  }, [planTemperature, planMaxTokens]);

  const advancedTuningInvalid = useMemo(() => {
    const pt = planTemperature.trim();
    if (pt !== "") {
      const t = Number(pt);
      if (!Number.isFinite(t) || t < 0 || t > 2) return true;
    }
    const pm = planMaxTokens.trim();
    if (pm !== "") {
      const m = Number(pm);
      if (!Number.isFinite(m) || !Number.isInteger(m) || m < 256 || m > 4096) return true;
    }
    return false;
  }, [planTemperature, planMaxTokens]);

  const attachAbortController = useCallback(() => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    return ac;
  }, []);

  const cancelAgentRequest = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const onAsk = useCallback(async () => {
    setAskError(null);
    const ac = attachAbortController();
    setAskLoading(true);
    setPlanOnlyLoading(false);
    setExecuteLoading(false);
    setLastAsk(null);
    setPlanDetailsOpen(false);
    try {
      const res = await agentAsk(
        {
          question: question.trim(),
          constraints: constraints.trim() || undefined,
          wait_timeout_seconds: waitTimeoutSeconds,
          ...(planOpts.plan_temperature !== undefined ? { plan_temperature: planOpts.plan_temperature } : {}),
          ...(planOpts.plan_max_tokens !== undefined ? { plan_max_tokens: planOpts.plan_max_tokens } : {}),
        },
        { signal: ac.signal },
      );
      setLastAsk(res);
      setLastPlanOnly(res.plan);
      setExecuteJson(prettyJson(res.plan));
    } catch (e) {
      if (isAbortError(e)) {
        setAskError(null);
        return;
      }
      setAskError(String((e as Error)?.message ?? e));
    } finally {
      setAskLoading(false);
      if (abortRef.current === ac) abortRef.current = null;
    }
  }, [question, constraints, waitTimeoutSeconds, planOpts, attachAbortController]);

  const onPlanOnly = useCallback(async () => {
    setPlanOnlyError(null);
    const ac = attachAbortController();
    setPlanOnlyLoading(true);
    setAskLoading(false);
    setExecuteLoading(false);
    try {
      const { plan } = await agentPlan(
        {
          question: question.trim(),
          constraints: constraints.trim() || undefined,
          ...(planOpts.plan_temperature !== undefined ? { plan_temperature: planOpts.plan_temperature } : {}),
          ...(planOpts.plan_max_tokens !== undefined ? { plan_max_tokens: planOpts.plan_max_tokens } : {}),
        },
        { signal: ac.signal },
      );
      setLastPlanOnly(plan);
      setExecuteJson(prettyJson(plan));
    } catch (e) {
      if (isAbortError(e)) {
        setPlanOnlyError(null);
        return;
      }
      setPlanOnlyError(String((e as Error)?.message ?? e));
    } finally {
      setPlanOnlyLoading(false);
      if (abortRef.current === ac) abortRef.current = null;
    }
  }, [question, constraints, planOpts, attachAbortController]);

  const onExecute = useCallback(async () => {
    setExecuteError(null);
    const ac = attachAbortController();
    setExecuteLoading(true);
    setAskLoading(false);
    setPlanOnlyLoading(false);
    setLastExecute(null);
    try {
      const parsed = JSON.parse(executeJson) as ExecutionPlan;
      if (!parsed || !Array.isArray(parsed.runs)) {
        throw new Error("JSON must be an object with a runs[] array (ExecutionPlan).");
      }
      const { runs } = await agentExecute(parsed, { signal: ac.signal });
      setLastExecute({ runs });
    } catch (e) {
      if (isAbortError(e)) {
        setExecuteError(null);
        return;
      }
      if (e instanceof SyntaxError) {
        setExecuteError(`Invalid JSON: ${e.message}`);
      } else {
        setExecuteError(String((e as Error)?.message ?? e));
      }
    } finally {
      setExecuteLoading(false);
      if (abortRef.current === ac) abortRef.current = null;
    }
  }, [executeJson, attachAbortController]);

  const sectionStyle: React.CSSProperties = {
    display: "grid",
    gap: 12,
    padding: 12,
    border: "1px solid #ddd",
    borderRadius: 8,
    marginBottom: 16,
  };

  const askDisabled = askLoading || question.trim().length < 8 || advancedTuningInvalid;
  const planOnlyDisabled = planOnlyLoading || question.trim().length < 8 || advancedTuningInvalid;
  const executeDisabled = executeLoading || !executeJson.trim() || advancedTuningInvalid;

  return (
    <div>
      <p style={{ fontSize: 14, opacity: 0.85, maxWidth: 640, marginBottom: 16 }}>
        Describe what you want in plain language. The server plans the run, executes simulations, and returns structured
        analysis. Use <strong>Advanced</strong> to tune timeouts, planner temperature, or run <strong>Plan</strong> /{" "}
        <strong>Execute</strong> separately.
      </p>

      <section style={sectionStyle}>
        <label style={{ display: "grid", gap: 6 }}>
          <span>Research question (min. 8 characters)</span>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={4}
            placeholder={QUESTION_PLACEHOLDER}
            style={{ fontFamily: "system-ui", fontSize: 14 }}
          />
        </label>

        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 10 }}>
          <button
            type="button"
            onClick={() => void onAsk()}
            disabled={askDisabled}
            style={{ padding: "10px 16px", fontWeight: 600 }}
          >
            {askLoading ? "Running (plan + execute)…" : "Ask"}
          </button>
          {anyLoading ? (
            <>
              <button type="button" onClick={cancelAgentRequest} style={{ padding: "10px 14px" }}>
                Cancel request
              </button>
              <span style={{ fontSize: 13, opacity: 0.85 }}>
                Elapsed: <strong>{elapsedSec}s</strong>
              </span>
            </>
          ) : null}
        </div>
        {question.trim().length > 0 && question.trim().length < 8 ? (
          <span style={{ fontSize: 12, color: "#a60" }}>Question must be at least 8 characters for the API.</span>
        ) : null}
        {askError ? (
          <div
            style={{
              padding: 10,
              background: "#ffecec",
              border: "1px solid #e6a0a0",
              borderRadius: 6,
              fontSize: 13,
              whiteSpace: "pre-wrap",
            }}
          >
            {askError}
          </div>
        ) : null}
      </section>

      {lastAsk ? (
        <section style={sectionStyle}>
          <h2 style={{ margin: 0 }}>Results</h2>
          {lastAsk.runs.map((run, i) => (
            <RunResultCard key={`${run.label}-${i}`} run={run} />
          ))}

          <button
            type="button"
            onClick={() => setPlanDetailsOpen((o) => !o)}
            style={{ padding: "6px 12px", alignSelf: "start" }}
          >
            {planDetailsOpen ? "Hide" : "Show"} execution plan (JSON)
          </button>
          {planDetailsOpen ? (
            <pre
              style={{
                margin: 0,
                padding: 12,
                background: "#f4f4f4",
                borderRadius: 6,
                fontSize: 12,
                overflow: "auto",
                maxHeight: 360,
              }}
            >
              {prettyJson(lastAsk.plan)}
            </pre>
          ) : null}
        </section>
      ) : null}

      <section style={{ ...sectionStyle, marginTop: 8 }}>
        <button
          type="button"
          onClick={() => setAdvancedOpen((o) => !o)}
          style={{ padding: "8px 12px", justifySelf: "start" }}
        >
          {advancedOpen ? "▼ Hide advanced" : "▶ Advanced (constraints, plan/execute, tuning)"}
        </button>

        {advancedOpen ? (
          <>
            <label style={{ display: "grid", gap: 6 }}>
              <span>Constraints (optional)</span>
              <textarea
                value={constraints}
                onChange={(e) => setConstraints(e.target.value)}
                rows={3}
                placeholder="Extra instructions for the planner…"
                style={{ fontFamily: "system-ui", fontSize: 14 }}
              />
            </label>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <label style={{ display: "grid", gap: 6 }}>
                <span>Wait timeout per run (seconds)</span>
                <input
                  type="number"
                  min={30}
                  max={7200}
                  value={waitTimeoutSeconds}
                  onChange={(e) => setWaitTimeoutSeconds(Number(e.target.value))}
                />
                <span style={{ fontSize: 11, opacity: 0.75 }}>Applied each simulation wait; multi-run asks sum wall-clock.</span>
              </label>
              <label style={{ display: "grid", gap: 6 }}>
                <span>Planner temperature (optional, 0–2)</span>
                <input
                  type="number"
                  inputMode="decimal"
                  min={0}
                  max={2}
                  step="any"
                  placeholder="default 0.35"
                  value={planTemperature}
                  onChange={(e) => setPlanTemperature(e.target.value)}
                />
                {planTemperature.trim() !== "" &&
                (() => {
                  const t = Number(planTemperature.trim());
                  return !Number.isFinite(t) || t < 0 || t > 2;
                })() ? (
                  <span style={{ fontSize: 12, color: "#a60" }}>Must be a number between 0 and 2 (or leave empty).</span>
                ) : null}
              </label>
            </div>

            <label style={{ display: "grid", gap: 6 }}>
              <span>Plan max tokens (optional, 256–4096)</span>
              <input
                type="number"
                inputMode="numeric"
                min={256}
                max={4096}
                step={1}
                placeholder="default 2048"
                value={planMaxTokens}
                onChange={(e) => setPlanMaxTokens(e.target.value)}
              />
              {planMaxTokens.trim() !== "" &&
              (() => {
                const m = Number(planMaxTokens.trim());
                return !Number.isFinite(m) || !Number.isInteger(m) || m < 256 || m > 4096;
              })() ? (
                <span style={{ fontSize: 12, color: "#a60" }}>Must be a whole number from 256 to 4096 (or leave empty).</span>
              ) : null}
            </label>

            {advancedTuningInvalid ? (
              <span style={{ fontSize: 12, color: "#a60" }}>
                Fix advanced tuning values above before Ask / Plan / Execute.
              </span>
            ) : null}

            <div style={{ borderTop: "1px solid #eee", paddingTop: 12, display: "grid", gap: 10 }}>
              <div style={{ fontWeight: 600 }}>Plan only</div>
              <span style={{ fontSize: 13, opacity: 0.85 }}>
                Calls <code>POST /agent/plan</code> with the question above. Fills the execute JSON box below.
              </span>
              <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 10 }}>
                <button
                  type="button"
                  onClick={() => void onPlanOnly()}
                  disabled={planOnlyDisabled}
                  style={{ padding: 8, justifySelf: "start" }}
                >
                  {planOnlyLoading ? "Planning…" : "Run plan only"}
                </button>
                {planOnlyLoading ? (
                  <span style={{ fontSize: 13, opacity: 0.85 }}>
                    Elapsed: <strong>{elapsedSec}s</strong>
                  </span>
                ) : null}
              </div>
              {planOnlyError ? (
                <div style={{ fontSize: 13, color: "#a30", whiteSpace: "pre-wrap" }}>{planOnlyError}</div>
              ) : null}
            </div>

            <div style={{ borderTop: "1px solid #eee", paddingTop: 12, display: "grid", gap: 10 }}>
              <div style={{ fontWeight: 600 }}>Execute plan</div>
              <span style={{ fontSize: 13, opacity: 0.85 }}>
                Paste an <code>ExecutionPlan</code> JSON (<code>runs</code> array). Calls <code>POST /agent/execute</code>.
              </span>
              <textarea
                value={executeJson}
                onChange={(e) => setExecuteJson(e.target.value)}
                rows={12}
                style={{ fontFamily: "monospace", fontSize: 12 }}
              />
              <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 10 }}>
                <button
                  type="button"
                  onClick={() => void onExecute()}
                  disabled={executeDisabled}
                  style={{ padding: 8, justifySelf: "start" }}
                >
                  {executeLoading ? "Executing…" : "Execute JSON plan"}
                </button>
                {executeLoading ? (
                  <span style={{ fontSize: 13, opacity: 0.85 }}>
                    Elapsed: <strong>{elapsedSec}s</strong>
                  </span>
                ) : null}
              </div>
              {executeError ? (
                <div style={{ fontSize: 13, color: "#a30", whiteSpace: "pre-wrap" }}>{executeError}</div>
              ) : null}
            </div>

            {lastExecute ? (
              <div style={{ marginTop: 8 }}>
                <strong>Execute results</strong>
                <div style={{ display: "grid", gap: 10, marginTop: 8 }}>
                  {lastExecute.runs.map((run, i) => (
                    <RunResultCard key={`${run.label}-ex-${i}`} run={run} />
                  ))}
                </div>
              </div>
            ) : null}

            {lastPlanOnly && !lastAsk ? (
              <p style={{ fontSize: 12, opacity: 0.8, margin: 0 }}>
                Last plan loaded — use <strong>Execute JSON plan</strong> to run it without re-planning.
              </p>
            ) : null}
          </>
        ) : null}
      </section>
    </div>
  );
}
