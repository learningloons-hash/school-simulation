import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  cloneScenario,
  fetchBundledRagPaths,
  fetchScenarioCatalog,
  fetchScenarioDocument,
  generateScenarioFromBrief,
  llmFillPersona,
  saveUserScenario,
  scenarioExportYamlUrl,
  type ScenarioCatalogItem,
} from "../lib/api";

type PolicyRow = { round: number; text: string };
type SectionMap = Record<string, string>;
type PersonaRow = {
  persona_id: string;
  role: string;
  name: string;
  role_level: number;
  style_cues: string;
  beliefs_json: string;
  /** Iteration 14: structured attribute sections */
  identity: SectionMap;
  attitudes: SectionMap;
  personal_history: SectionMap;
};
type GroupRow = { group_id: string; name: string; description: string };

const STEPS = ["Basics", "Policy rounds", "Personas", "Groups", "RAG", "Review"] as const;

const SECTION_LABELS: Record<string, string> = {
  identity: "Identity",
  attitudes: "Attitudes / Stance",
  personal_history: "Personal History",
};

function emptyPersona(): PersonaRow {
  return {
    persona_id: "",
    role: "teacher",
    name: "",
    role_level: 3,
    style_cues: "",
    beliefs_json: "{}",
    identity: {},
    attitudes: {},
    personal_history: {},
  };
}

/** Convert a raw Record<string, unknown> from the server to SectionMap (string values). */
function toSectionMap(raw: unknown): SectionMap {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return {};
  const out: SectionMap = {};
  for (const [k, v] of Object.entries(raw as Record<string, unknown>)) {
    out[k] = String(v ?? "");
  }
  return out;
}

/** Constrained randomize: generate plausible values for each section based on role. */
function randomizeSections(role: string): { identity: SectionMap; attitudes: SectionMap; personal_history: SectionMap } {
  const ethnicities = ["Chinese", "Malay", "Indian", "Eurasian", "Other"];
  const nationalities = ["Singaporean", "Malaysian", "Filipino", "Other"];
  const stances = ["cautiously_supportive", "neutral", "skeptical", "strongly_supportive", "resistant"];
  const readiness = ["low", "medium", "high"];
  const postings = ["school_based", "MOE_HQ_secondment", "cluster_office", "NIE_attached"];
  const quals = ["bachelor_of_education", "PGDE", "master_in_education", "PhD"];
  const randStr = (arr: string[]): string => arr[Math.floor(Math.random() * arr.length)];
  const randInt = (min: number, max: number) => Math.floor(Math.random() * (max - min + 1)) + min;

  return {
    identity: {
      nationality: randStr(nationalities),
      ethnicity: randStr(ethnicities),
      gender_identity: randStr(["man", "woman", "non-binary"]),
    },
    attitudes: {
      policy_stance: randStr(stances),
      change_readiness: randStr(readiness),
      trust_in_leadership: String((Math.random() * 0.5 + 0.3).toFixed(2)),
      workload_sensitivity: randStr(["low", "medium", "high"]),
    },
    personal_history: {
      years_in_role: String(randInt(role === "principal" ? 3 : 1, role === "principal" ? 20 : 15)),
      prior_posting: randStr(postings),
      highest_qualification: randStr(quals),
    },
  };
}

type Props = {
  onCatalogRefresh: () => void;
};

export function ScenarioWizard({ onCatalogRefresh }: Props) {
  const [step, setStep] = useState(0);
  const [catalog, setCatalog] = useState<ScenarioCatalogItem[]>([]);
  const [ragPaths, setRagPaths] = useState<string[]>([]);
  const [scenarioId, setScenarioId] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [policyRows, setPolicyRows] = useState<PolicyRow[]>([{ round: 1, text: "" }]);
  const [personas, setPersonas] = useState<PersonaRow[]>([emptyPersona()]);
  const [groups, setGroups] = useState<GroupRow[]>([]);
  const [ragEnabled, setRagEnabled] = useState(false);
  const [selectedRagPaths, setSelectedRagPaths] = useState<Set<string>>(new Set());
  const [loadTemplateId, setLoadTemplateId] = useState("psle_reform_mvp");
  const [cloneTemplateId, setCloneTemplateId] = useState("psle_reform_mvp");
  const [cloneNewId, setCloneNewId] = useState("");
  const [cloneDisplayName, setCloneDisplayName] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [saveMode, setSaveMode] = useState<"create" | "update">("create");
  const [fillLoadingIdx, setFillLoadingIdx] = useState<number | null>(null);
  const [expandedSections, setExpandedSections] = useState<Record<number, boolean>>({});
  const [briefText, setBriefText] = useState("");
  const [briefLoading, setBriefLoading] = useState(false);

  const userScenarioIds = useMemo(() => catalog.filter((c) => c.source === "user").map((c) => c.id), [catalog]);

  const refreshLocal = useCallback(async () => {
    try {
      const [cat, paths] = await Promise.all([fetchScenarioCatalog(), fetchBundledRagPaths()]);
      setCatalog(cat);
      setRagPaths(paths);
    } catch (e) {
      setError(String((e as Error)?.message ?? e));
    }
  }, []);

  useEffect(() => {
    void refreshLocal();
  }, [refreshLocal]);

  function hydrateFromDocument(doc: Record<string, unknown>) {
    setScenarioId(String(doc.scenario_id ?? ""));
    setDisplayName(String(doc.name ?? ""));
    const pe = doc.policy_events as Record<string, string> | undefined;
    if (pe && typeof pe === "object") {
      const rows = Object.entries(pe)
        .map(([k, v]) => ({ round: Number(k), text: String(v) }))
        .sort((a, b) => a.round - b.round);
      setPolicyRows(rows.length ? rows : [{ round: 1, text: "" }]);
    }
    const pl = doc.personas as unknown[];
    if (Array.isArray(pl) && pl.length) {
      setPersonas(
        pl.map((p) => {
          const x = p as Record<string, unknown>;
          return {
            persona_id: String(x.persona_id ?? ""),
            role: String(x.role ?? "teacher"),
            name: String(x.name ?? ""),
            role_level: Number(x.role_level ?? 3),
            style_cues: String(x.style_cues ?? ""),
            beliefs_json: JSON.stringify(x.beliefs && typeof x.beliefs === "object" ? x.beliefs : {}, null, 2),
            identity: toSectionMap(x.identity),
            attitudes: toSectionMap(x.attitudes),
            personal_history: toSectionMap(x.personal_history),
          };
        }),
      );
    } else {
      setPersonas([emptyPersona()]);
    }
    const gr = doc.groups as unknown[];
    if (Array.isArray(gr)) {
      setGroups(
        gr.map((g) => {
          const x = g as Record<string, unknown>;
          return {
            group_id: String(x.group_id ?? ""),
            name: String(x.name ?? ""),
            description: String(x.description ?? ""),
          };
        }),
      );
    } else {
      setGroups([]);
    }
    const re = Boolean(doc.rag_enabled);
    setRagEnabled(re);
    const rp = doc.rag_corpus_paths as string[] | undefined;
    if (Array.isArray(rp)) {
      setSelectedRagPaths(new Set(rp.map(String)));
    } else {
      setSelectedRagPaths(new Set());
    }
  }

  async function onLoadTemplate() {
    setError(null);
    setMessage(null);
    try {
      const doc = await fetchScenarioDocument(loadTemplateId);
      hydrateFromDocument(doc);
      setSaveMode("create");
      setStep(0);
      setMessage(`Loaded template ${loadTemplateId} into editor (save as a new scenario_id).`);
    } catch (e) {
      setError(String((e as Error)?.message ?? e));
    }
  }

  async function onGenerateFromBrief() {
    const b = briefText.trim();
    if (b.length < 20) {
      setError("Brief must be at least 20 characters (server validation).");
      return;
    }
    setBriefLoading(true);
    setError(null);
    setMessage(null);
    try {
      const res = await generateScenarioFromBrief(b);
      hydrateFromDocument(res.document);
      setWarnings(res.warnings ?? []);
      setSaveMode("create");
      setStep(0);
      setMessage("Generated scenario from brief — review fields, then save as a new scenario_id.");
    } catch (e) {
      setError(String((e as Error)?.message ?? e));
    } finally {
      setBriefLoading(false);
    }
  }

  async function onClone() {
    setError(null);
    setMessage(null);
    try {
      const res = await cloneScenario(cloneTemplateId, cloneNewId.trim(), cloneDisplayName.trim() || undefined);
      setWarnings(res.warnings ?? []);
      setMessage(`Cloned to ${res.id}.`);
      await refreshLocal();
      onCatalogRefresh();
      const doc = await fetchScenarioDocument(res.id);
      hydrateFromDocument(doc);
      setSaveMode("update");
    } catch (e) {
      setError(String((e as Error)?.message ?? e));
    }
  }

  function buildDocument(): Record<string, unknown> {
    const policy_events: Record<string, string> = {};
    for (const r of policyRows) {
      policy_events[String(r.round)] = r.text;
    }
    const personaObjs = personas.map((p) => {
      let beliefs: Record<string, unknown> = {};
      try {
        beliefs = JSON.parse(p.beliefs_json || "{}") as Record<string, unknown>;
      } catch {
        throw new Error(`Invalid JSON in persona ${p.persona_id || "?"} beliefs`);
      }
      const obj: Record<string, unknown> = {
        persona_id: p.persona_id.trim(),
        role: p.role.trim(),
        name: p.name.trim(),
        role_level: p.role_level,
        style_cues: p.style_cues.trim(),
        beliefs,
      };
      if (Object.keys(p.identity).length) obj.identity = p.identity;
      if (Object.keys(p.attitudes).length) obj.attitudes = p.attitudes;
      if (Object.keys(p.personal_history).length) obj.personal_history = p.personal_history;
      return obj;
    });
    const groupObjs = groups
      .filter((g) => g.group_id.trim() && g.name.trim())
      .map((g) => ({
        group_id: g.group_id.trim(),
        name: g.name.trim(),
        description: g.description.trim(),
      }));
    const doc: Record<string, unknown> = {
      scenario_id: scenarioId.trim(),
      name: displayName.trim() || scenarioId.trim(),
      policy_events,
      personas: personaObjs,
    };
    if (groupObjs.length) doc.groups = groupObjs;
    if (ragEnabled) {
      doc.rag_enabled = true;
      doc.rag_corpus_paths = Array.from(selectedRagPaths);
    }
    return doc;
  }

  async function onLlmFill(personaIdx: number) {
    const p = personas[personaIdx];
    setFillLoadingIdx(personaIdx);
    setError(null);
    try {
      const res = await llmFillPersona(scenarioId.trim() || "psle_reform_mvp", {
        persona_id: p.persona_id || "persona",
        role: p.role,
        name: p.name,
        style_cues: p.style_cues,
      });
      const n = [...personas];
      n[personaIdx] = {
        ...p,
        identity: { ...p.identity, ...toSectionMap(res.identity) },
        attitudes: { ...p.attitudes, ...toSectionMap(res.attitudes) },
        personal_history: { ...p.personal_history, ...toSectionMap(res.personal_history) },
      };
      setPersonas(n);
      setExpandedSections((prev) => ({ ...prev, [personaIdx]: true }));
    } catch (e) {
      setError(String((e as Error)?.message ?? e));
    } finally {
      setFillLoadingIdx(null);
    }
  }

  function onRandomizeSections(personaIdx: number) {
    const p = personas[personaIdx];
    const generated = randomizeSections(p.role);
    const n = [...personas];
    n[personaIdx] = {
      ...p,
      identity: { ...p.identity, ...generated.identity },
      attitudes: { ...p.attitudes, ...generated.attitudes },
      personal_history: { ...p.personal_history, ...generated.personal_history },
    };
    setPersonas(n);
    setExpandedSections((prev) => ({ ...prev, [personaIdx]: true }));
  }

  async function onSave() {
    setError(null);
    setMessage(null);
    setWarnings([]);
    try {
      const doc = buildDocument();
      const body = { document: doc, display_name: displayName.trim() || undefined };
      const res =
        saveMode === "create"
          ? await saveUserScenario(body, "POST")
          : await saveUserScenario(body, "PUT", scenarioId.trim());
      setWarnings(res.warnings ?? []);
      setMessage(`Saved scenario ${res.id}.`);
      setSaveMode("update");
      await refreshLocal();
      onCatalogRefresh();
    } catch (e) {
      setError(String((e as Error)?.message ?? e));
    }
  }

  function toggleRagPath(p: string) {
    const next = new Set(selectedRagPaths);
    if (next.has(p)) next.delete(p);
    else next.add(p);
    setSelectedRagPaths(next);
  }

  return (
    <section style={{ display: "grid", gap: 16, padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
      <div style={{ fontSize: 14, opacity: 0.85 }}>
        Create or edit <strong>user</strong> scenarios stored in SQLite. Built-in YAML scenarios are read-only; clone
        or load as template. See <code>docs/plans/scenario-wizard-design.md</code>.
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
        {STEPS.map((label, i) => (
          <button
            key={label}
            type="button"
            onClick={() => setStep(i)}
            style={{
              padding: "6px 10px",
              borderRadius: 6,
              border: "1px solid #ccc",
              background: step === i ? "#eef" : "#fff",
            }}
          >
            {i + 1}. {label}
          </button>
        ))}
      </div>

      <div style={{ border: "1px solid #eee", borderRadius: 6, padding: 12 }}>
        <strong>Load / clone</strong>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 8, alignItems: "flex-end" }}>
          <label style={{ display: "grid", gap: 4 }}>
            <span style={{ fontSize: 12 }}>Load template into editor</span>
            <select value={loadTemplateId} onChange={(e) => setLoadTemplateId(e.target.value)}>
              {catalog.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.source})
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={() => void onLoadTemplate()}>
            Load
          </button>
        </div>
        <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
          <span style={{ fontSize: 12, fontWeight: 600 }}>Generate from brief (LLM)</span>
          <textarea
            value={briefText}
            onChange={(e) => setBriefText(e.target.value)}
            placeholder="Describe the policy context, stakeholders, and what should happen across rounds (20+ characters). The server validates the result."
            rows={4}
            style={{ width: "100%", maxWidth: 560, fontFamily: "inherit", fontSize: 13 }}
          />
          <button type="button" disabled={briefLoading} onClick={() => void onGenerateFromBrief()}>
            {briefLoading ? "Generating…" : "Generate from brief"}
          </button>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 12, alignItems: "flex-end" }}>
          <label style={{ display: "grid", gap: 4 }}>
            <span style={{ fontSize: 12 }}>Clone template → new id</span>
            <select value={cloneTemplateId} onChange={(e) => setCloneTemplateId(e.target.value)}>
              {catalog.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span style={{ fontSize: 12 }}>new_scenario_id (slug)</span>
            <input
              value={cloneNewId}
              onChange={(e) => setCloneNewId(e.target.value)}
              placeholder="analyst_my_run"
              style={{ fontFamily: "monospace", width: 180 }}
            />
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span style={{ fontSize: 12 }}>Display name</span>
            <input value={cloneDisplayName} onChange={(e) => setCloneDisplayName(e.target.value)} style={{ width: 160 }} />
          </label>
          <button type="button" onClick={() => void onClone()}>
            Clone
          </button>
        </div>
      </div>

      {step === 0 && (
        <div style={{ display: "grid", gap: 10 }}>
          <label style={{ display: "grid", gap: 4 }}>
            <span>scenario_id (lowercase slug, e.g. analyst_case_a)</span>
            <input
              value={scenarioId}
              onChange={(e) => setScenarioId(e.target.value)}
              style={{ fontFamily: "monospace" }}
              disabled={saveMode === "update"}
            />
          </label>
          <label style={{ display: "grid", gap: 4 }}>
            <span>Display name</span>
            <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          </label>
          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="radio"
              checked={saveMode === "create"}
              onChange={() => setSaveMode("create")}
            />
            New scenario (POST)
            <input
              type="radio"
              checked={saveMode === "update"}
              onChange={() => setSaveMode("update")}
            />
            Update existing user scenario
          </label>
          {saveMode === "update" ? (
            <label style={{ display: "grid", gap: 4 }}>
              <span>Pick user scenario to edit</span>
              <select
                value={scenarioId}
                onChange={async (e) => {
                  const id = e.target.value;
                  setScenarioId(id);
                  try {
                    const doc = await fetchScenarioDocument(id);
                    hydrateFromDocument(doc);
                  } catch (err) {
                    setError(String((err as Error)?.message ?? err));
                  }
                }}
              >
                <option value="">— select —</option>
                {userScenarioIds.map((id) => (
                  <option key={id} value={id}>
                    {id}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
        </div>
      )}

      {step === 1 && (
        <div style={{ display: "grid", gap: 8 }}>
          {policyRows.map((row, i) => (
            <div key={i} style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-start" }}>
              <label>
                Round
                <input
                  type="number"
                  min={1}
                  max={25}
                  value={row.round}
                  onChange={(e) => {
                    const next = [...policyRows];
                    next[i] = { ...row, round: Number(e.target.value) };
                    setPolicyRows(next);
                  }}
                  style={{ width: 64 }}
                />
              </label>
              <label style={{ flex: 1, minWidth: 200, display: "grid", gap: 4 }}>
                Policy text
                <textarea
                  rows={3}
                  value={row.text}
                  onChange={(e) => {
                    const next = [...policyRows];
                    next[i] = { ...row, text: e.target.value };
                    setPolicyRows(next);
                  }}
                />
              </label>
              <button
                type="button"
                onClick={() => setPolicyRows(policyRows.filter((_, j) => j !== i))}
                disabled={policyRows.length <= 1}
              >
                Remove
              </button>
            </div>
          ))}
          <button type="button" onClick={() => setPolicyRows([...policyRows, { round: policyRows.length + 1, text: "" }])}>
            Add round
          </button>
        </div>
      )}

      {step === 2 && (
        <div style={{ display: "grid", gap: 12 }}>
          {personas.map((p, i) => (
            <div key={i} style={{ border: "1px solid #dde", padding: 10, borderRadius: 6, display: "grid", gap: 8 }}>
              {/* Core fields */}
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                <input
                  placeholder="persona_id"
                  value={p.persona_id}
                  onChange={(e) => { const n = [...personas]; n[i] = { ...p, persona_id: e.target.value }; setPersonas(n); }}
                  style={{ fontFamily: "monospace", width: 140 }}
                />
                <input
                  placeholder="name"
                  value={p.name}
                  onChange={(e) => { const n = [...personas]; n[i] = { ...p, name: e.target.value }; setPersonas(n); }}
                  style={{ width: 120 }}
                />
                <select
                  value={p.role}
                  onChange={(e) => { const n = [...personas]; n[i] = { ...p, role: e.target.value }; setPersonas(n); }}
                >
                  <option value="principal">principal</option>
                  <option value="middle_manager">middle_manager</option>
                  <option value="teacher">teacher</option>
                </select>
                <label style={{ fontSize: 12 }}>
                  role_level
                  <input
                    type="number" min={1} max={3} value={p.role_level}
                    onChange={(e) => { const n = [...personas]; n[i] = { ...p, role_level: Number(e.target.value) }; setPersonas(n); }}
                    style={{ width: 48 }}
                  />
                </label>
              </div>
              <textarea
                placeholder="style_cues"
                rows={2}
                value={p.style_cues}
                onChange={(e) => { const n = [...personas]; n[i] = { ...p, style_cues: e.target.value }; setPersonas(n); }}
              />
              <textarea
                placeholder='beliefs JSON e.g. {"key": 0.5}'
                rows={2}
                value={p.beliefs_json}
                onChange={(e) => { const n = [...personas]; n[i] = { ...p, beliefs_json: e.target.value }; setPersonas(n); }}
                style={{ fontFamily: "monospace", fontSize: 12 }}
              />

              {/* Attribute sections */}
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <strong style={{ fontSize: 13 }}>Structured attributes</strong>
                <button
                  type="button"
                  onClick={() => setExpandedSections((prev) => ({ ...prev, [i]: !prev[i] }))}
                  style={{ fontSize: 12, padding: "2px 8px" }}
                >
                  {expandedSections[i] ? "Hide" : "Show / Edit"}
                </button>
                <button
                  type="button"
                  onClick={() => onRandomizeSections(i)}
                  style={{ fontSize: 12, padding: "2px 8px" }}
                  title="Fill with random plausible values based on role"
                >
                  Randomize
                </button>
                <button
                  type="button"
                  disabled={fillLoadingIdx === i}
                  onClick={() => void onLlmFill(i)}
                  style={{ fontSize: 12, padding: "2px 8px" }}
                  title="Ask LLM to suggest attribute values based on this persona's role and style cues"
                >
                  {fillLoadingIdx === i ? "Filling…" : "LLM Fill"}
                </button>
                {(Object.keys(p.identity).length + Object.keys(p.attitudes).length + Object.keys(p.personal_history).length) > 0 && (
                  <span style={{ fontSize: 11, opacity: 0.7 }}>
                    {Object.keys(p.identity).length + Object.keys(p.attitudes).length + Object.keys(p.personal_history).length} keys set
                  </span>
                )}
              </div>

              {expandedSections[i] && (
                <div style={{ display: "grid", gap: 8, paddingLeft: 8, borderLeft: "3px solid #eef" }}>
                  {(["identity", "attitudes", "personal_history"] as const).map((sec) => (
                    <div key={sec}>
                      <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4 }}>{SECTION_LABELS[sec]}</div>
                      {Object.entries(p[sec]).map(([k, v]) => (
                        <div key={k} style={{ display: "flex", gap: 6, marginBottom: 4, alignItems: "center" }}>
                          <input
                            value={k}
                            onChange={(e) => {
                              const newKey = e.target.value;
                              const n = [...personas];
                              const updated = { ...p[sec] };
                              delete updated[k];
                              if (newKey) updated[newKey] = v;
                              n[i] = { ...p, [sec]: updated };
                              setPersonas(n);
                            }}
                            style={{ fontFamily: "monospace", width: 140, fontSize: 12 }}
                            placeholder="key"
                          />
                          <span style={{ opacity: 0.5 }}>=</span>
                          <input
                            value={v}
                            onChange={(e) => {
                              const n = [...personas];
                              n[i] = { ...p, [sec]: { ...p[sec], [k]: e.target.value } };
                              setPersonas(n);
                            }}
                            style={{ flex: 1, fontSize: 12 }}
                            placeholder="value"
                          />
                          <button
                            type="button"
                            onClick={() => {
                              const n = [...personas];
                              const updated = { ...p[sec] };
                              delete updated[k];
                              n[i] = { ...p, [sec]: updated };
                              setPersonas(n);
                            }}
                            style={{ fontSize: 11, padding: "1px 6px" }}
                          >
                            ×
                          </button>
                        </div>
                      ))}
                      <button
                        type="button"
                        onClick={() => {
                          const n = [...personas];
                          const newKey = `new_key_${Date.now()}`;
                          n[i] = { ...p, [sec]: { ...p[sec], [newKey]: "" } };
                          setPersonas(n);
                        }}
                        style={{ fontSize: 11, padding: "2px 8px" }}
                      >
                        + Add {SECTION_LABELS[sec]} key
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <button type="button" onClick={() => setPersonas(personas.filter((_, j) => j !== i))} disabled={personas.length <= 1}>
                Remove persona
              </button>
            </div>
          ))}
          <button type="button" onClick={() => setPersonas([...personas, emptyPersona()])}>
            Add persona
          </button>
        </div>
      )}

      {step === 3 && (
        <div style={{ display: "grid", gap: 8 }}>
          {groups.map((g, i) => (
            <div key={i} style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <input
                placeholder="group_id"
                value={g.group_id}
                onChange={(e) => {
                  const n = [...groups];
                  n[i] = { ...g, group_id: e.target.value };
                  setGroups(n);
                }}
                style={{ fontFamily: "monospace" }}
              />
              <input
                placeholder="name"
                value={g.name}
                onChange={(e) => {
                  const n = [...groups];
                  n[i] = { ...g, name: e.target.value };
                  setGroups(n);
                }}
              />
              <input
                placeholder="description"
                value={g.description}
                onChange={(e) => {
                  const n = [...groups];
                  n[i] = { ...g, description: e.target.value };
                  setGroups(n);
                }}
                style={{ flex: 1, minWidth: 160 }}
              />
              <button type="button" onClick={() => setGroups(groups.filter((_, j) => j !== i))}>
                Remove
              </button>
            </div>
          ))}
          <button type="button" onClick={() => setGroups([...groups, { group_id: "", name: "", description: "" }])}>
            Add group
          </button>
        </div>
      )}

      {step === 4 && (
        <div style={{ display: "grid", gap: 8 }}>
          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input type="checkbox" checked={ragEnabled} onChange={(e) => setRagEnabled(e.target.checked)} />
            Enable RAG (bundled corpus paths only)
          </label>
          <div style={{ fontSize: 12, opacity: 0.8 }}>Select files under scenarios/data (server-enumerated).</div>
          <div style={{ display: "grid", gap: 4, maxHeight: 200, overflow: "auto" }}>
            {ragPaths.map((p) => (
              <label key={p} style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <input type="checkbox" checked={selectedRagPaths.has(p)} onChange={() => toggleRagPath(p)} />
                <code style={{ fontSize: 11 }}>{p}</code>
              </label>
            ))}
          </div>
        </div>
      )}

      {step === 5 && (
        <div style={{ display: "grid", gap: 8 }}>
          <pre style={{ fontSize: 11, overflow: "auto", maxHeight: 240, background: "#f8f8f8", padding: 8 }}>
            {JSON.stringify(buildDocument(), null, 2)}
          </pre>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            <button type="button" onClick={() => void onSave()}>
              {saveMode === "create" ? "Save (create)" : "Save (update)"}
            </button>
            {scenarioId.trim() ? (
              <a href={scenarioExportYamlUrl(scenarioId.trim())} target="_blank" rel="noreferrer">
                Export YAML
              </a>
            ) : null}
          </div>
        </div>
      )}

      {message ? <div style={{ color: "#059669" }}>{message}</div> : null}
      {error ? <div style={{ color: "#b91c1c" }}>{error}</div> : null}
      {warnings.length ? (
        <div style={{ fontSize: 13, color: "#a60" }}>
          <strong>Warnings:</strong>
          <ul style={{ margin: "4px 0 0 16px" }}>
            {warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
