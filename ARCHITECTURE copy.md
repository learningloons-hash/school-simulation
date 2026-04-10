# MiroFish Policy Simulation Engine — System Architecture

**Version**: 0.1 (Draft)
**Date**: 2026-03-28
**Author**: Mark Lee Ser Ming / Claude (Architect)

---

## 1. Design Principles

1. **Methodological Transparency** — Every agent decision, prompt, and orchestration step is logged and auditable. Thesis examiners can trace any simulation output back to its causal chain.
2. **Model Agnosticism** — The engine runs the same simulation scenarios against local fine-tuned models (Ollama) AND frontier models (Claude API), enabling direct comparison — this IS the Phase 1/2 research finding.
3. **Cultural Grounding** — Agent personas are grounded in Singapore education policy context through fine-tuning, RAG, or hybrid approaches. The grounding method is a variable, not a fixed design choice.
4. **Reproducibility** — Fixed random seeds, versioned prompts, deterministic turn order. Any simulation run can be exactly replicated.
5. **Extensibility** — Built for PSLE Reform and Full SBB cases first, but architecturally generalizable to any policy domain.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                         │
│  ┌──────────┐ ┌──────────────┐ ┌────────────┐ ┌─────────────┐  │
│  │Simulation│ │  Agent Chat  │ │  Validity  │ │   Policy    │  │
│  │Dashboard │ │   Viewer     │ │ Assessment │ │  Document   │  │
│  │          │ │              │ │  Dashboard │ │  Manager    │  │
│  └──────────┘ └──────────────┘ └────────────┘ └─────────────┘  │
│                          Port 3000                              │
└─────────────────────┬───────────────────────────────────────────┘
                      │ REST + WebSocket
┌─────────────────────┴───────────────────────────────────────────┐
│                      API LAYER (FastAPI)                         │
│                          Port 8000                               │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────────┐  │
│  │ /simulations │ │   /agents    │ │    /validity            │  │
│  │ CRUD + Run   │ │ Persona CRUD │ │    Assessment endpoints │  │
│  └──────────────┘ └──────────────┘ └─────────────────────────┘  │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────────┐  │
│  │  /policies   │ │   /models    │ │    /ws/simulation       │  │
│  │  Doc mgmt    │ │ Config/swap  │ │    Real-time stream     │  │
│  └──────────────┘ └──────────────┘ └─────────────────────────┘  │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                    SIMULATION ENGINE (Python)                     │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    ORCHESTRATOR                              │ │
│  │  - Manages simulation lifecycle (init → rounds → complete)  │ │
│  │  - Controls turn order (sequential / parallel / random)     │ │
│  │  - Injects policy events at specified rounds                │ │
│  │  - Tracks global simulation state                           │ │
│  └──────────┬──────────────────────────────┬───────────────────┘ │
│             │                              │                     │
│  ┌──────────┴──────────┐    ┌──────────────┴────────────────┐   │
│  │    AGENT MANAGER    │    │       INTERACTION ENGINE       │   │
│  │                     │    │                                │   │
│  │  - Loads personas   │    │  - Generates conversation      │   │
│  │  - Manages memory   │    │    contexts per round          │   │
│  │  - Tracks beliefs,  │    │  - Routes to appropriate LLM   │   │
│  │    attitudes, state │    │  - Processes agent responses    │   │
│  │  - Role hierarchy:  │    │  - Manages multi-agent          │   │
│  │    Principal →       │    │    dialogues (1:1, group,      │   │
│  │    Middle Mgr →      │    │    broadcast)                  │   │
│  │    Teacher           │    │                                │   │
│  └─────────────────────┘    └────────────────────────────────┘   │
│             │                              │                     │
│  ┌──────────┴──────────────────────────────┴───────────────────┐ │
│  │                     LLM ROUTER                              │ │
│  │                                                             │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │ │
│  │  │   Ollama    │  │  Claude API  │  │   OpenAI-compat   │  │ │
│  │  │  Connector  │  │  Connector   │  │    Connector      │  │ │
│  │  │             │  │              │  │                   │  │ │
│  │  │ Qwen 7B    │  │ Sonnet/Opus  │  │  Any OpenAI-API   │  │ │
│  │  │ Mistral 7B │  │              │  │  compatible model  │  │ │
│  │  │ (LoRA)     │  │              │  │                   │  │ │
│  │  └─────────────┘  └──────────────┘  └───────────────────┘  │ │
│  │                                                             │ │
│  │  Model selection per agent configurable:                    │ │
│  │  - "all_local": Every agent uses Ollama                     │ │
│  │  - "all_frontier": Every agent uses Claude                  │ │
│  │  - "hybrid": Persona responses via local, orchestration     │ │
│  │              via Claude                                     │ │
│  │  - "comparison": Run same scenario on both, compare         │ │
│  │  - "pipeline": Local generates → Claude refines             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌───────────────────────────┴─────────────────────────────────┐ │
│  │                   MEMORY SYSTEM                             │ │
│  │                                                             │ │
│  │  Per-Agent Memory:                                          │ │
│  │  ├── Short-term: Current round context (conversation buf)   │ │
│  │  ├── Working: Active beliefs, attitudes, emotional state    │ │
│  │  └── Long-term: Accumulated experiences, relationship map   │ │
│  │                                                             │ │
│  │  Global Memory:                                             │ │
│  │  ├── Policy state: Current policy parameters + changes      │ │
│  │  ├── School state: Org structure, resources, constraints    │ │
│  │  └── Event log: All interactions, decisions, outcomes       │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌───────────────────────────┴─────────────────────────────────┐ │
│  │                   RAG PIPELINE                              │ │
│  │                                                             │ │
│  │  Policy Document Store → Chunking → Embedding → Vector DB   │ │
│  │                                                             │ │
│  │  Used for:                                                  │ │
│  │  - Grounding agent responses in actual policy text          │ │
│  │  - Injecting MOE circulars, press releases, Hansard         │ │
│  │  - Providing context for Singapore education system         │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────────┐
│                      DATA LAYER                                  │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │   SQLite     │  │ ChromaDB     │  │   File Storage         │ │
│  │              │  │ (Vector DB)  │  │                        │ │
│  │ - Sim runs   │  │              │  │ - Policy PDFs          │ │
│  │ - Agent logs │  │ - Policy doc │  │ - Fine-tune datasets   │ │
│  │ - Validity   │  │   embeddings │  │ - Simulation exports   │ │
│  │   scores     │  │ - Agent      │  │ - Prompt version       │ │
│  │ - Config     │  │   memory     │  │   history              │ │
│  │   snapshots  │  │   embeddings │  │                        │ │
│  └──────────────┘  └──────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                VALIDITY ASSESSMENT MODULE                         │
│                                                                   │
│  ┌─────────────────┐ ┌─────────────────┐ ┌───────────────────┐  │
│  │ Face Validity   │ │Construct Validity│ │Predictive Validity│  │
│  │                 │ │                  │ │                   │  │
│  │ - Expert review │ │ - Lipsky align-  │ │ - Compare sim     │  │
│  │   interface     │ │   ment scoring   │ │   outcomes to     │  │
│  │ - Plausibility  │ │ - Spillane dist  │ │   known policy    │  │
│  │   rubrics       │ │   leadership     │ │   outcomes (PSLE  │  │
│  │ - Comparison to │ │   metrics        │ │   reform, FSBB)   │  │
│  │   practitioner  │ │ - Trinidad org   │ │ - Statistical     │  │
│  │   knowledge     │ │   sociology      │ │   comparison      │  │
│  │                 │ │   alignment      │ │   framework       │  │
│  └─────────────────┘ └─────────────────┘ └───────────────────┘  │
│                                                                   │
│  Output: Validity Score Card per simulation run                   │
│  - Aggregated scores across all three dimensions                  │
│  - Confidence intervals                                           │
│  - Comparison across model configurations                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Details

### 3.1 Simulation Engine — Orchestrator

The orchestrator is the central control loop. It manages the simulation lifecycle:

```
INIT
 │
 ├── Load scenario config (policy case, agent roster, round count)
 ├── Initialize agents from persona templates
 ├── Load policy documents into RAG pipeline
 ├── Set random seed for reproducibility
 │
 ▼
ROUND LOOP (for each round 1..N)
 │
 ├── Check for policy events (e.g., "Round 5: MOE announces PSLE changes")
 ├── Update global state
 ├── For each agent (in configured turn order):
 │    ├── Build context: agent memory + global state + policy docs (RAG)
 │    ├── Route to LLM (based on model allocation config)
 │    ├── Parse response: extract actions, beliefs, communications
 │    ├── Update agent memory and state
 │    └── Log everything to database
 ├── Process inter-agent interactions (meetings, informal chats)
 ├── Run validity checks (if configured for real-time assessment)
 │
 ▼
COMPLETE
 │
 ├── Generate simulation summary
 ├── Run full validity assessment
 ├── Export all data (conversations, state changes, scores)
 └── Archive simulation run
```

### 3.2 Agent Persona System

Each agent is defined by a **Persona Template** — a structured specification:

```yaml
# Example: Secondary School Teacher persona
persona:
  id: "teacher_001"
  role: "teacher"
  role_level: 3  # 1=Principal, 2=Middle Manager, 3=Teacher

  demographics:
    age_range: "30-40"
    experience_years: "8-12"
    subject: "Mathematics"
    school_type: "neighbourhood_secondary"

  psychological_profile:
    openness_to_change: 0.4        # 0-1 scale
    policy_compliance_tendency: 0.7
    professional_identity_strength: 0.8
    risk_aversion: 0.6
    workload_sensitivity: 0.7

  beliefs:
    streaming_effectiveness: "mixed"     # believes streaming has pros and cons
    student_ability_fixed_vs_growth: 0.6 # leans growth mindset
    trust_in_moe_policy: 0.5            # moderate trust
    peer_influence_weight: 0.7           # influenced by colleagues

  context:
    school_banding: "mid"
    department_size: 12
    union_membership: false
    years_to_retirement: 20

  grounding_method: "lora|rag|prompt|hybrid"  # configurable per experiment
```

**Role Hierarchy** (from the GABM prototype):
- **Principal** (1 per school): Interprets policy, sets school-level strategy, manages resources
- **Middle Manager / HoD** (2-4 per school): Translates principal's direction into department practices, mediates between leadership and teachers
- **Teacher** (8-20 per school): Street-level bureaucrat (Lipsky). Exercises discretion in classroom implementation. Where policy meets reality.

### 3.3 LLM Router — Model Allocation Strategy

The LLM Router supports five configuration modes, reflecting the thesis research design:

| Mode | Agent Responses | Orchestration | Use Case |
|------|----------------|---------------|----------|
| `all_local` | Ollama (Qwen/Mistral 7B, LoRA fine-tuned) | Python logic | Phase 2: Test fine-tuned model capability |
| `all_frontier` | Claude Sonnet 4.6 | Claude Opus 4.6 | Phase 1: Baseline with best reasoning |
| `hybrid` | Ollama for persona responses | Claude for orchestration + analysis | Phase 2: Two-tier architecture test |
| `comparison` | Both (parallel runs) | Both | Phase 1-2: Direct model comparison |
| `pipeline` | Ollama generates draft → Claude refines | Claude | Phase 2: Fine-tune → prompt pipeline |

**Cost management**: Each run logs token usage per model. The comparison mode doubles cost but produces the core Phase 1-2 finding.

### 3.4 Memory System

Inspired by Park et al. (2023) Generative Agents but simplified for policy context:

**Per-Agent Memory** (3 layers):
1. **Short-term** (current round): Conversation buffer, immediate context. Cleared each round.
2. **Working memory**: Active beliefs, current attitudes toward policy, emotional state, recent interactions. Updated each round. This is where Lipsky's discretion lives.
3. **Long-term**: Accumulated experiences, relationship quality with other agents, belief trajectory over time. Persists across rounds. Enables "memory" of how policy was communicated, who said what.

**Memory Retrieval**: When building agent context for LLM call, retrieve:
- All working memory (always included)
- Top-K relevant long-term memories (by recency + importance + relevance)
- Relevant policy document chunks (from RAG)

### 3.5 RAG Pipeline

**Purpose**: Ground agent responses in actual Singapore education policy documents.

**Document Types**:
- MOE press releases and circulars on PSLE reform / FSBB
- Parliamentary Hansard debates on education policy
- Singapore Curriculum Planning & Development Division documents
- School-level implementation guidelines
- Media coverage and public discourse

**Pipeline**:
```
PDF/Text → Chunking (500 tokens, 100 overlap)
         → Embedding (all-MiniLM-L6-v2 or similar)
         → ChromaDB vector store
         → Retrieval at query time (top-5 chunks per agent context)
```

### 3.6 Validity Assessment Module

This is the methodological heart of the thesis. Three dimensions:

**Face Validity**:
- Structured rubric for expert reviewers (MOE practitioners, education researchers)
- Agent response samples rated on plausibility, realism, contextual appropriateness
- Inter-rater reliability scoring
- Automated pre-screening: coherence checks, role-consistency checks

**Construct Validity**:
- Does the principal agent behave like a principal? Measured against Lipsky, Spillane, Trinidad frameworks
- Alignment scoring: map agent actions to theoretical constructs
- Example: Teacher exercises discretion (Lipsky) → system detects and scores this
- Distributed leadership patterns (Spillane) → do middle managers actually mediate?

**Predictive Validity**:
- The retrospective test: simulate PSLE reform rollout, compare simulation trajectory to what actually happened
- Metrics: implementation timeline, stakeholder resistance patterns, adaptation strategies, outcome alignment
- Statistical framework: correlation, pattern matching, process tracing alignment

---

## 4. Tech Stack

### Backend (Python 3.11+)
| Component | Library | Rationale |
|-----------|---------|-----------|
| API Server | FastAPI | Async, WebSocket support, auto-docs |
| LLM - Anthropic | anthropic SDK | Claude API access |
| LLM - Local | ollama-python | Ollama API for local models |
| LLM - Generic | litellm | Unified interface across providers |
| RAG - Embeddings | sentence-transformers | Local embedding models |
| RAG - Vector DB | ChromaDB | Simple, file-based, no infra needed |
| Database | SQLite + SQLAlchemy | Lightweight, portable, thesis-friendly |
| Data Processing | pandas, numpy | Analysis and export |
| Task Queue | (optional) Celery + Redis | For parallel simulation runs |
| Config | pydantic-settings + YAML | Type-safe configuration |
| Testing | pytest | Standard |

### Frontend (React + TypeScript)
| Component | Library | Rationale |
|-----------|---------|-----------|
| Framework | React 18 + Vite | Fast dev, modern tooling |
| UI Components | shadcn/ui + Tailwind | Professional, thesis-presentable |
| Charts | Recharts or Plotly.js | Validity score visualization |
| Real-time | WebSocket (native) | Simulation streaming |
| State | Zustand | Lightweight state management |
| API Client | TanStack Query | Caching, loading states |

### Infrastructure
| Component | Tool | Rationale |
|-----------|------|-----------|
| Local LLMs | Ollama | Already installed on Mark's M4 Mac Mini |
| Fine-tuning | MLX (Apple Silicon) or Unsloth | LoRA fine-tuning on 32GB M4 |
| Containerization | Docker Compose | Reproducible deployment |
| Version Control | Git | Full history of system evolution |

---

## 5. Data Model (SQLite Schema — Core Tables)

```sql
-- Simulation runs
CREATE TABLE simulation_runs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    scenario_id TEXT NOT NULL,
    model_config TEXT NOT NULL,        -- json: which LLM mode
    status TEXT DEFAULT 'pending',     -- pending, running, completed, failed
    total_rounds INTEGER,
    current_round INTEGER DEFAULT 0,
    random_seed INTEGER,
    config_snapshot TEXT,               -- json: full config at time of run
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Agent instances (per simulation run)
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    simulation_id TEXT REFERENCES simulation_runs(id),
    persona_template_id TEXT,
    role TEXT NOT NULL,                 -- principal, middle_manager, teacher
    name TEXT,
    initial_state TEXT,                 -- json: starting beliefs, attitudes
    current_state TEXT,                 -- json: current beliefs, attitudes
    model_used TEXT                     -- which LLM served this agent
);

-- Round-by-round agent actions and responses
CREATE TABLE agent_turns (
    id TEXT PRIMARY KEY,
    simulation_id TEXT REFERENCES simulation_runs(id),
    agent_id TEXT REFERENCES agents(id),
    round_number INTEGER,
    context_provided TEXT,              -- json: what the agent "saw"
    raw_prompt TEXT,                    -- full prompt sent to LLM
    raw_response TEXT,                  -- full LLM response
    parsed_actions TEXT,               -- json: extracted actions
    parsed_beliefs TEXT,               -- json: belief updates
    parsed_communications TEXT,        -- json: messages to other agents
    token_count_input INTEGER,
    token_count_output INTEGER,
    model_used TEXT,
    latency_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Policy events injected during simulation
CREATE TABLE policy_events (
    id TEXT PRIMARY KEY,
    simulation_id TEXT REFERENCES simulation_runs(id),
    round_number INTEGER,
    event_type TEXT,                    -- announcement, circular, meeting, media
    content TEXT,
    source TEXT                         -- MOE, school_leadership, media, etc.
);

-- Validity assessment scores
CREATE TABLE validity_scores (
    id TEXT PRIMARY KEY,
    simulation_id TEXT REFERENCES simulation_runs(id),
    dimension TEXT,                     -- face, construct, predictive
    metric TEXT,                        -- specific metric name
    score REAL,
    confidence REAL,
    evidence TEXT,                      -- json: supporting data
    assessed_by TEXT,                   -- automated, expert_reviewer_id
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scenarios (reusable across runs)
CREATE TABLE scenarios (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    policy_case TEXT,                   -- psle_reform, fsbb, australian_comparator
    agent_roster TEXT,                  -- json: how many of each role
    round_count INTEGER,
    policy_events TEXT,                 -- json: scheduled events
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 6. Project Structure

```
mirofish/
├── README.md
├── pyproject.toml                  # Python project config (uv/pip)
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── config.py               # Pydantic settings
│   │   │
│   │   ├── api/                    # API routes
│   │   │   ├── simulations.py
│   │   │   ├── agents.py
│   │   │   ├── policies.py
│   │   │   ├── validity.py
│   │   │   └── websocket.py
│   │   │
│   │   ├── engine/                 # Core simulation engine
│   │   │   ├── orchestrator.py     # Main simulation loop
│   │   │   ├── agent_manager.py    # Agent lifecycle
│   │   │   ├── interaction.py      # Agent-agent interaction logic
│   │   │   ├── memory.py           # Memory system (3 layers)
│   │   │   └── state.py            # Global state management
│   │   │
│   │   ├── llm/                    # LLM integration
│   │   │   ├── router.py           # Model routing logic
│   │   │   ├── ollama_client.py    # Ollama connector
│   │   │   ├── claude_client.py    # Anthropic API connector
│   │   │   ├── litellm_client.py   # Generic connector
│   │   │   └── prompts/            # Versioned prompt templates
│   │   │       ├── persona_system.py
│   │   │       ├── round_context.py
│   │   │       └── analysis.py
│   │   │
│   │   ├── rag/                    # RAG pipeline
│   │   │   ├── ingest.py           # Document processing
│   │   │   ├── embeddings.py       # Embedding generation
│   │   │   ├── retrieval.py        # Vector search
│   │   │   └── store.py            # ChromaDB interface
│   │   │
│   │   ├── validity/               # Validity assessment
│   │   │   ├── face.py             # Face validity metrics
│   │   │   ├── construct.py        # Construct validity scoring
│   │   │   ├── predictive.py       # Predictive validity comparison
│   │   │   └── scorecard.py        # Aggregated reporting
│   │   │
│   │   ├── personas/               # Persona templates
│   │   │   ├── principal.yaml
│   │   │   ├── middle_manager.yaml
│   │   │   ├── teacher.yaml
│   │   │   └── loader.py
│   │   │
│   │   ├── scenarios/              # Scenario definitions
│   │   │   ├── psle_reform.yaml
│   │   │   ├── fsbb.yaml
│   │   │   └── australian_comparator.yaml
│   │   │
│   │   └── db/                     # Database layer
│   │       ├── models.py           # SQLAlchemy models
│   │       ├── migrations/
│   │       └── database.py         # Connection management
│   │
│   ├── tests/
│   │   ├── test_orchestrator.py
│   │   ├── test_agent_manager.py
│   │   ├── test_llm_router.py
│   │   ├── test_memory.py
│   │   └── test_validity.py
│   │
│   └── data/
│       ├── policy_documents/       # PDFs for RAG
│       ├── fine_tune/              # Training data for LoRA
│       └── simulation_outputs/     # Exported results
│
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx       # Simulation overview
│   │   │   ├── SimulationView.tsx  # Live/replay simulation
│   │   │   ├── AgentInspector.tsx  # Deep dive into agent state
│   │   │   ├── ValidityReport.tsx  # Validity assessment results
│   │   │   └── PolicyManager.tsx   # Document upload and management
│   │   ├── components/
│   │   │   ├── AgentCard.tsx
│   │   │   ├── ConversationThread.tsx
│   │   │   ├── BeliefTracker.tsx   # Visualize belief changes over time
│   │   │   ├── ValidityScoreCard.tsx
│   │   │   └── SimulationControls.tsx
│   │   └── lib/
│   │       ├── api.ts              # API client
│   │       └── websocket.ts        # WebSocket connection
│   └── public/
│
├── fine_tuning/                    # LoRA fine-tuning pipeline
│   ├── prepare_data.py             # Convert training data to format
│   ├── train_lora.py               # MLX/Unsloth training script
│   ├── evaluate_model.py           # Test fine-tuned model quality
│   └── datasets/
│       ├── sg_education_conversations/
│       └── policy_response_pairs/
│
└── docs/
    ├── methodology.md              # For thesis documentation
    ├── prompt_registry.md          # All prompts, versioned
    ├── validity_framework.md       # Scoring rubrics
    └── benchmarks/                 # MiroFish comparison results
```

---

## 7. Thesis Phase Mapping

| Phase | Engine Components Used | Key Config |
|-------|----------------------|------------|
| **Phase 1**: Retrospective Validation | Orchestrator, Agent Manager, LLM Router (`all_frontier` + `comparison`), Validity Module, RAG Pipeline | PSLE Reform + FSBB scenarios. Compare sim outputs to known outcomes. |
| **Phase 2**: Fine-Tuning Local Model | Fine-tuning pipeline, LLM Router (`all_local`, `hybrid`, `pipeline`), RAG Pipeline | Train LoRA models on SG education data. Compare all 5 model modes. |
| **Phase 3**: Simulating Evaluations | Full engine + Validity Module extended for evaluation design simulation | Simulate RCTs, quasi-experiments, realist evaluation in synthetic policy environments. |

---

## 8. Build Sequence (Recommended)

### Sprint 1 (Week 1-2): Foundation
- [ ] Project scaffolding (Python backend, React frontend, Docker)
- [ ] Database schema + SQLAlchemy models
- [ ] Basic FastAPI routes (CRUD for simulations, agents, scenarios)
- [ ] LLM Router with Claude connector (frontier-first)
- [ ] Basic orchestrator: single round, single agent

### Sprint 2 (Week 3-4): Core Engine
- [ ] Multi-agent orchestrator with turn management
- [ ] Memory system (3 layers)
- [ ] Agent persona loader from YAML
- [ ] Inter-agent interaction (meetings, communications)
- [ ] Policy event injection system
- [ ] Ollama connector

### Sprint 3 (Week 5-6): RAG + Scenarios
- [ ] RAG pipeline (ChromaDB + sentence-transformers)
- [ ] Policy document ingestion
- [ ] PSLE Reform scenario definition
- [ ] FSBB scenario definition
- [ ] Full simulation run: multi-round, multi-agent, with RAG

### Sprint 4 (Week 7-8): Frontend + Validity
- [ ] React dashboard (simulation list, create, run)
- [ ] Agent conversation viewer
- [ ] Belief trajectory visualization
- [ ] Validity assessment module (face + construct + predictive)
- [ ] Validity scorecard UI

### Sprint 5 (Week 9-10): Fine-Tuning + Comparison
- [ ] LoRA fine-tuning pipeline (MLX)
- [ ] Training data preparation
- [ ] Model comparison framework (`comparison` mode)
- [ ] Benchmark: local vs frontier vs hybrid

### Sprint 6 (Week 11-12): Polish + Documentation
- [ ] Full methodology documentation
- [ ] Prompt registry
- [ ] Reproducibility verification
- [ ] Docker Compose for full-stack deployment
- [ ] MiroFish benchmark comparison

---

## 9. Key Architectural Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Database | SQLite (not Postgres) | Portability, no infra, thesis-friendly. Can migrate later. |
| Vector DB | ChromaDB (not Pinecone/Weaviate) | Local, file-based, no cloud dependency. Sufficient for policy doc corpus. |
| Memory | Custom 3-layer (not Zep) | Full transparency and control. MiroFish uses Zep — we need to show we understand the design. |
| Agent framework | Custom (not LangChain/CrewAI) | Methodological transparency. No black-box abstractions. Every decision documented. |
| Frontend | React (not Streamlit) | Professional presentation for thesis defense. Reusable. Open-source deliverable quality. |
| Config | YAML + Pydantic | Human-readable scenarios, type-safe in code. Examiners can read the YAML. |
| LLM abstraction | LiteLLM for generic + direct SDKs | Flexibility to add models. Direct SDKs for fine control over Anthropic/Ollama. |

---

## 10. Comparison: MiroFish (Original) vs Our System

| Aspect | MiroFish | Our System |
|--------|----------|------------|
| Agent Engine | OASIS (CAMEL-AI) | Custom (full transparency) |
| Knowledge Graph | GraphRAG | ChromaDB RAG (simpler, sufficient) |
| Memory | Zep Cloud | Custom 3-layer (thesis-documented) |
| Frontend | Vue.js | React |
| Backend | FastAPI | FastAPI |
| Models | Qwen-Plus (cloud) | Ollama local + Claude API (dual) |
| Scale | Thousands of agents | 10-30 per school (realistic) |
| Focus | General policy simulation | Education policy validation |
| Validation | Not primary focus | Core research contribution |
| Open Source | Yes | Yes (thesis deliverable) |
