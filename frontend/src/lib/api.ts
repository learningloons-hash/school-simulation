export type StartSimulationRequest = {
  scenario_id: string;
  total_rounds: number;
  agent_limit: number;
  random_seed: number;
  /** Optional override; server default is typically 1024 */
  max_tokens?: number;
  /** lmstudio | anthropic — omit to use server default */
  llm_provider?: string;
  /** Force RAG on/off; omit to use server flag and scenario rag_enabled */
  rag_enabled?: boolean;
  /** Optional CSV roster (1-based slot); merges onto scenario personas */
  roster_csv?: string;
  /** Optional population pool CSV (Iteration 11); draws agent_limit rows without replacement */
  population_csv?: string;
  /** weighted | stratified — used with population_csv */
  population_sample_mode?: string;
  /** full_round_robin | sample_k_per_round (Iteration 10) */
  simulation_mode?: string;
  /** When sample_k_per_round; default 2 on server */
  speakers_per_round?: number;
  /** Iteration 28: omit to run full total_rounds; 0–1 mean population attitude change threshold */
  convergence_threshold?: number;
  /** Iteration 28: consecutive sub-threshold rounds (default 2 on server) */
  convergence_patience?: number;
};

export type SimulationTurn = {
  id?: string;
  round_number: number;
  turn_index: number;
  agent_id: string;
  agent_role: string;
  agent_name: string;
  interaction_type: string;
  target_scope: string;
  target_agent_id?: string | null;
  target_agent_name?: string | null;
  intent_tag?: string | null;
  raw_response: string;
  latency_ms?: number | null;
  group_ids?: string[];
  /** Iteration 12: which LLM backend served this turn (hybrid resolves per turn). */
  effective_provider?: string | null;
  effective_model?: string | null;
  /** Iteration 23: sampling fidelity tier (1=full LLM, 2=simplified prompt, 3=no LLM placeholder). */
  fidelity_tier?: number | null;
  /** Iteration 29: LLM usage when available; Tier-3/heuristic rows use 0. */
  input_tokens?: number | null;
  output_tokens?: number | null;
};

/** Iteration 29 — token totals + thesis cost estimate (Anthropic-priced turns only in hybrid/local runs). */
export type RunEconomics = {
  total_input_tokens?: number | null;
  total_output_tokens?: number | null;
  estimated_cost_usd?: number;
  llm_provider?: string;
  tier_breakdown?: {
    tier_1_turns?: number;
    tier_2_turns?: number;
    tier_3_turns?: number;
  };
};

export type SimulationListItem = {
  id: string;
  name: string;
  scenario_id: string;
  status: string;
  current_round: number;
  total_rounds: number;
  created_at?: string | null;
  completed_at?: string | null;
  /** Iteration 27: set when run was queued as part of an experiment */
  experiment_id?: string | null;
};

export type SimulationStatus = {
  id: string;
  status: string;
  current_round: number;
  total_rounds: number;
  failure_reason?: string | null;
  /** Iteration 28: set when run stopped early on convergence criterion */
  converged_at_round?: number | null;
  config_snapshot?: Record<string, unknown> | null;
  transcript: SimulationTurn[];
  state_timeline: Array<{
    round_number: number;
    global_state: {
      implementation_readiness?: number;
      alignment_index?: number;
      /** Iteration 28: mean population abs attitude change vs prior round; absent on round 1 */
      convergence_delta?: number;
    };
    agents: Array<{
      agent_id: string;
      agent_role: string;
      agent_name: string;
      demographics: {
        age?: number | null;
        sex?: string | null;
        ethnicity?: string | null;
        ses?: string | null;
      };
      support_level: number;
      resistance_level: number;
      workload_stress: number;
      belief_posture: string;
      group_ids?: string[];
      /** Iteration 13: identity / attitudes / personal_history maps when non-empty */
      attribute_sections?: {
        identity?: Record<string, unknown>;
        attitudes?: Record<string, unknown>;
        personal_history?: Record<string, unknown>;
      };
    }>;
  }>;
  outcome_indicators: Array<{
    round_number: number;
    adoption_momentum: number;
    conflict_events: number;
    consistency_index: number;
  }>;
  /** Iteration 29 */
  economics?: RunEconomics | null;
  validity_notes?: Array<{
    id: string;
    simulation_id: string;
    round_number: number | null;
    rater_id: string | null;
    face_score: number | null;
    face_rubric: string | null;
    construct_score: number | null;
    construct_rubric: string | null;
    predictive_score: number | null;
    predictive_rubric: string | null;
    notes: string | null;
    created_at: string | null;
  }>;
};

export type ValidityNoteCreate = {
  round_number?: number | null;
  rater_id?: string | null;
  face_score?: number | null;
  face_rubric?: string | null;
  construct_score?: number | null;
  construct_rubric?: string | null;
  predictive_score?: number | null;
  predictive_rubric?: string | null;
  notes?: string | null;
};

export async function listSimulations(limit = 50): Promise<SimulationListItem[]> {
  const res = await fetch(`/simulations?limit=${encodeURIComponent(String(limit))}`);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`List simulations failed: ${res.status} ${text}`);
  }
  return (await res.json()) as SimulationListItem[];
}

/** Iteration 27 — persisted multi-run experiment */
export type ExperimentListItem = {
  id: string;
  name: string;
  scenario_id: string;
  base_random_seed: number;
  base_total_rounds: number;
  status: string;
  created_at?: string | null;
  completed_at?: string | null;
  /** Child runs linked via `experiment_runs` */
  run_count?: number;
};

export type ExperimentRunRow = {
  step_index: number;
  simulation_id: string;
  run_label: string | null;
  series_key: string;
  sampling_strategy: string | null;
  status: string;
  current_round: number;
  total_rounds: number;
  failure_reason: string | null;
  /** Iteration 28: early convergence round, if any */
  converged_at_round?: number | null;
  /** Iteration 29 */
  total_input_tokens?: number | null;
  total_output_tokens?: number | null;
  economics?: RunEconomics | null;
};

export type ExperimentComparisonRound = {
  round_number: number;
  by_run: Record<
    string,
    {
      implementation_readiness?: number;
      alignment_index?: number;
      adoption_momentum?: number;
      conflict_events?: number;
      consistency_index?: number;
      convergence_delta?: number;
    }
  >;
};

export type ExperimentDetail = {
  experiment: ExperimentListItem;
  runs: ExperimentRunRow[];
  comparison: ExperimentComparisonRound[];
  export_version: string;
  /** Iteration 29: sum of per-run estimated_cost_usd */
  total_estimated_cost_usd?: number;
};

export type CreateExperimentRequest = {
  name: string;
  scenario_id: string;
  random_seed: number;
  total_rounds: number;
  agent_limit?: number;
  roster_csv?: string | null;
  population_csv?: string | null;
  population_sample_mode?: string;
  simulation_mode?: string;
  speakers_per_round?: number;
  convergence_threshold?: number;
  convergence_patience?: number;
  runs: Array<{ label?: string; sampling_strategy: string; agent_limit?: number }>;
};

export async function listExperiments(limit = 50): Promise<ExperimentListItem[]> {
  const res = await fetch(`/experiments?limit=${encodeURIComponent(String(limit))}`);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`List experiments failed: ${res.status} ${text}`);
  }
  return (await res.json()) as ExperimentListItem[];
}

export async function createExperiment(
  body: CreateExperimentRequest,
  signal?: AbortSignal,
): Promise<{ experiment_id: string; simulation_ids: string[] }> {
  const res = await fetch("/experiments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  const text = await res.text().catch(() => "");
  if (!res.ok) {
    throw new Error(`Create experiment failed: ${res.status} ${text}`);
  }
  return JSON.parse(text) as { experiment_id: string; simulation_ids: string[] };
}

export async function fetchExperiment(experimentId: string): Promise<ExperimentDetail> {
  const res = await fetch(`/experiments/${encodeURIComponent(experimentId)}`);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Get experiment failed: ${res.status} ${text}`);
  }
  return (await res.json()) as ExperimentDetail;
}

export function experimentExportZipUrl(experimentId: string): string {
  return `/experiments/${encodeURIComponent(experimentId)}/export.zip`;
}

export function experimentExportJsonUrl(experimentId: string): string {
  return `/experiments/${encodeURIComponent(experimentId)}/export.json`;
}

export function exportZipUrl(simId: string): string {
  return `/simulations/${encodeURIComponent(simId)}/export.zip`;
}

export function exportJsonUrl(simId: string): string {
  return `/simulations/${encodeURIComponent(simId)}/export.json`;
}

/** Iteration 26: researcher-readable tier/posture view of persisted `sampling_audit` (JSON). */
export function samplingReportUrl(simId: string): string {
  return `/simulations/${encodeURIComponent(simId)}/sampling-report`;
}

export async function downloadExportJson(simId: string, filename?: string): Promise<void> {
  const res = await fetch(exportJsonUrl(simId));
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Export JSON failed: ${res.status} ${text}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename ?? `mirofish_run_${simId}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export async function startSimulation(
  req: StartSimulationRequest,
): Promise<{ id: string; warnings?: string[] }> {
  const res = await fetch("/simulations/run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Start simulation failed: ${res.status} ${text}`);
  }

  const json = (await res.json()) as {
    id?: string;
    sim_id?: string;
    simulation_id?: string;
    warnings?: string[];
  };
  return {
    id: json.id ?? json.sim_id ?? json.simulation_id ?? "",
    warnings: json.warnings,
  };
}

export async function getSimulation(simId: string): Promise<SimulationStatus> {
  const res = await fetch(`/simulations/${encodeURIComponent(simId)}`, {
    method: "GET",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Get simulation failed: ${res.status} ${text}`);
  }
  return (await res.json()) as SimulationStatus;
}

export type ScenarioCatalogItem = {
  id: string;
  name: string;
  rag_enabled: boolean;
  source: string;
};

export async function fetchScenarioCatalog(): Promise<ScenarioCatalogItem[]> {
  const res = await fetch("/scenarios");
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Scenario catalog failed: ${res.status} ${text}`);
  }
  return (await res.json()) as ScenarioCatalogItem[];
}

/** Iteration 16: runtime capability surface (enums, versions, bundled paths). */
export async function fetchCapabilities(): Promise<Record<string, unknown>> {
  const res = await fetch("/capabilities");
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Capabilities failed: ${res.status} ${text}`);
  }
  return (await res.json()) as Record<string, unknown>;
}

/** Iteration 16: plain-English brief → validated scenario document (LLM). */
export async function generateScenarioFromBrief(
  brief: string,
  options?: { max_tokens?: number },
): Promise<{ document: Record<string, unknown>; warnings: string[] }> {
  const res = await fetch("/scenarios/generate-from-brief", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ brief, max_tokens: options?.max_tokens ?? null }),
  });
  const text = await res.text().catch(() => "");
  if (!res.ok) {
    throw new Error(`Generate from brief failed: ${res.status} ${text}`);
  }
  return JSON.parse(text) as { document: Record<string, unknown>; warnings: string[] };
}

export async function fetchBundledRagPaths(): Promise<string[]> {
  const res = await fetch("/scenarios/bundled-rag-paths");
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Bundled RAG paths failed: ${res.status} ${text}`);
  }
  const j = (await res.json()) as { paths?: string[] };
  return j.paths ?? [];
}

export async function fetchScenarioDocument(scenarioId: string): Promise<Record<string, unknown>> {
  const res = await fetch(`/scenarios/${encodeURIComponent(scenarioId)}/document`);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Scenario document failed: ${res.status} ${text}`);
  }
  return (await res.json()) as Record<string, unknown>;
}

export async function saveUserScenario(
  body: { document: Record<string, unknown>; display_name?: string },
  method: "POST" | "PUT",
  scenarioId?: string,
): Promise<{ id: string; warnings: string[] }> {
  const url = method === "POST" ? "/scenarios" : `/scenarios/${encodeURIComponent(scenarioId ?? "")}`;
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await res.text().catch(() => "");
  if (!res.ok) {
    throw new Error(`Save scenario failed: ${res.status} ${text}`);
  }
  return JSON.parse(text) as { id: string; warnings: string[] };
}

export async function cloneScenario(
  templateId: string,
  newScenarioId: string,
  displayName?: string,
): Promise<{ id: string; warnings: string[] }> {
  const res = await fetch("/scenarios/clone", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      template_id: templateId,
      new_scenario_id: newScenarioId,
      display_name: displayName || null,
    }),
  });
  const text = await res.text().catch(() => "");
  if (!res.ok) {
    throw new Error(`Clone scenario failed: ${res.status} ${text}`);
  }
  return JSON.parse(text) as { id: string; warnings: string[] };
}

export function scenarioExportYamlUrl(scenarioId: string): string {
  return `/scenarios/${encodeURIComponent(scenarioId)}/export.yaml`;
}

export type LlmFillRequest = {
  persona_id: string;
  role: string;
  name?: string;
  style_cues?: string;
  beliefs_summary?: string;
  sections?: string[];
};

export type LlmFillResponse = {
  identity: Record<string, unknown>;
  attitudes: Record<string, unknown>;
  personal_history: Record<string, unknown>;
  raw_llm_text?: string;
};

/** Iteration 14: Call LLM to suggest attribute sections for a persona stub. */
export async function llmFillPersona(
  scenarioId: string,
  body: LlmFillRequest,
): Promise<LlmFillResponse> {
  const res = await fetch(`/scenarios/${encodeURIComponent(scenarioId)}/llm-fill`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await res.text().catch(() => "");
  if (!res.ok) {
    throw new Error(`LLM fill failed: ${res.status} ${text}`);
  }
  return JSON.parse(text) as LlmFillResponse;
}

// --- Iteration 18: agent orchestration (/agent/*)

export type AgentPlanSimulation = Record<string, unknown>;

export type AgentPlanRunStep = {
  label?: string | null;
  research_question: string;
  scenario_id?: string | null;
  scenario_brief?: string | null;
  simulation?: AgentPlanSimulation;
};

export type ExecutionPlan = {
  runs: AgentPlanRunStep[];
};

export type AgentRunReport = {
  label: string;
  scenario_id?: string | null;
  simulation_id?: string | null;
  status: string;
  failure_reason?: string | null;
  queue_warnings?: string[];
  generate_warnings?: string[];
  analysis?: {
    key_findings?: string[];
    per_agent_summary?: Record<string, string>;
    trajectory_narrative?: string;
    suggested_follow_ups?: string[];
  } | null;
  analysis_error?: string | null;
};

export type AgentAskResponse = {
  plan: ExecutionPlan;
  runs: AgentRunReport[];
};

export type AgentPlanRequest = {
  question: string;
  constraints?: string | null;
  plan_max_tokens?: number | null;
  plan_temperature?: number | null;
};

export type AgentFetchInit = { signal?: AbortSignal };

export async function agentPlan(
  body: AgentPlanRequest,
  init?: AgentFetchInit,
): Promise<{ plan: ExecutionPlan }> {
  const res = await fetch("/agent/plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: body.question,
      constraints: body.constraints ?? null,
      plan_max_tokens: body.plan_max_tokens ?? null,
      plan_temperature: body.plan_temperature ?? null,
    }),
    signal: init?.signal,
  });
  const text = await res.text().catch(() => "");
  if (!res.ok) {
    throw new Error(`Agent plan failed: ${res.status} ${text}`);
  }
  return JSON.parse(text) as { plan: ExecutionPlan };
}

export async function agentExecute(
  plan: ExecutionPlan,
  init?: AgentFetchInit,
): Promise<{ runs: AgentRunReport[] }> {
  const res = await fetch("/agent/execute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(plan),
    signal: init?.signal,
  });
  const text = await res.text().catch(() => "");
  if (!res.ok) {
    throw new Error(`Agent execute failed: ${res.status} ${text}`);
  }
  return JSON.parse(text) as { runs: AgentRunReport[] };
}

export type AgentAskRequest = {
  question: string;
  constraints?: string | null;
  plan_max_tokens?: number | null;
  plan_temperature?: number | null;
  wait_timeout_seconds?: number;
};

export async function agentAsk(body: AgentAskRequest, init?: AgentFetchInit): Promise<AgentAskResponse> {
  const res = await fetch("/agent/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: body.question,
      constraints: body.constraints ?? null,
      plan_max_tokens: body.plan_max_tokens ?? null,
      plan_temperature: body.plan_temperature ?? null,
      wait_timeout_seconds: body.wait_timeout_seconds ?? 900,
    }),
    signal: init?.signal,
  });
  const text = await res.text().catch(() => "");
  if (!res.ok) {
    throw new Error(`Agent ask failed: ${res.status} ${text}`);
  }
  return JSON.parse(text) as AgentAskResponse;
}

export async function createValidityNote(simId: string, body: ValidityNoteCreate): Promise<{ id: string }> {
  const res = await fetch(`/simulations/${encodeURIComponent(simId)}/validity-notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Save validity note failed: ${res.status} ${text}`);
  }
  return (await res.json()) as { id: string };
}
