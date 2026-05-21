import logging
import os

import aiosqlite

logger = logging.getLogger("mirofish_backend.db")


async def init_db(sqlite_path: str) -> None:
    db_dir = os.path.dirname(sqlite_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    # Ensure directory exists (sqlite_path may be nested)
    # Use aiosqlite for consistent async behavior.
    async with aiosqlite.connect(sqlite_path) as db:
        await db.execute("PRAGMA journal_mode=WAL;")

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS simulation_runs (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              scenario_id TEXT NOT NULL,
              status TEXT NOT NULL,
              total_rounds INTEGER NOT NULL,
              current_round INTEGER NOT NULL,
              random_seed INTEGER NOT NULL,
              prompt_version TEXT NOT NULL,
              model_used TEXT NOT NULL,
              config_snapshot TEXT,
              failure_reason TEXT,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              completed_at TIMESTAMP
            );
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_turns (
              id TEXT PRIMARY KEY,
              simulation_id TEXT NOT NULL REFERENCES simulation_runs(id),
              round_number INTEGER NOT NULL,
              turn_index INTEGER NOT NULL,
              agent_id TEXT NOT NULL,
              agent_role TEXT NOT NULL,
              agent_name TEXT NOT NULL,
              interaction_type TEXT NOT NULL DEFAULT 'broadcast',
              target_scope TEXT NOT NULL DEFAULT 'all',
              target_agent_id TEXT,
              target_agent_name TEXT,
              intent_tag TEXT,
              raw_prompt TEXT NOT NULL,
              raw_response TEXT NOT NULL,
              latency_ms INTEGER,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_state_snapshots (
              id TEXT PRIMARY KEY,
              simulation_id TEXT NOT NULL REFERENCES simulation_runs(id),
              round_number INTEGER NOT NULL,
              agent_id TEXT NOT NULL,
              agent_role TEXT NOT NULL,
              agent_name TEXT NOT NULL,
              age INTEGER,
              sex TEXT,
              ethnicity TEXT,
              ses TEXT,
              support_level REAL NOT NULL,
              resistance_level REAL NOT NULL,
              workload_stress REAL NOT NULL,
              belief_posture TEXT NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS global_state_snapshots (
              id TEXT PRIMARY KEY,
              simulation_id TEXT NOT NULL REFERENCES simulation_runs(id),
              round_number INTEGER NOT NULL,
              implementation_readiness REAL NOT NULL,
              alignment_index REAL NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS round_outcomes (
              id TEXT PRIMARY KEY,
              simulation_id TEXT NOT NULL REFERENCES simulation_runs(id),
              round_number INTEGER NOT NULL,
              adoption_momentum REAL NOT NULL,
              conflict_events INTEGER NOT NULL,
              consistency_index REAL NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS round_summaries (
              simulation_id TEXT NOT NULL,
              round_number  INTEGER NOT NULL,
              summary_text  TEXT NOT NULL,
              created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (simulation_id, round_number)
            );
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_scenarios (
              scenario_id TEXT PRIMARY KEY,
              display_name TEXT NOT NULL,
              document_json TEXT NOT NULL,
              scenario_doc_version TEXT NOT NULL DEFAULT '1',
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS validity_notes (
              id TEXT PRIMARY KEY,
              simulation_id TEXT NOT NULL REFERENCES simulation_runs(id),
              round_number INTEGER,
              rater_id TEXT,
              face_score REAL,
              face_rubric TEXT,
              construct_score REAL,
              construct_rubric TEXT,
              predictive_score REAL,
              predictive_rubric TEXT,
              notes TEXT,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS experiments (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              scenario_id TEXT NOT NULL,
              base_random_seed INTEGER NOT NULL,
              base_total_rounds INTEGER NOT NULL,
              status TEXT NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              completed_at TIMESTAMP
            );
            """
        )

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS experiment_runs (
              experiment_id TEXT NOT NULL,
              step_index INTEGER NOT NULL,
              simulation_id TEXT NOT NULL,
              run_label TEXT,
              PRIMARY KEY (experiment_id, step_index)
            );
            """
        )
        await db.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_experiment_runs_simulation_id
            ON experiment_runs(simulation_id);
            """
        )

        # Backward-compatible migration for databases created before interaction metadata.
        await _ensure_column(db, "simulation_runs", "config_snapshot", "TEXT")
        await _ensure_column(db, "simulation_runs", "failure_reason", "TEXT")
        await _ensure_column(db, "agent_turns", "interaction_type", "TEXT NOT NULL DEFAULT 'broadcast'")
        await _ensure_column(db, "agent_turns", "target_scope", "TEXT NOT NULL DEFAULT 'all'")
        await _ensure_column(db, "agent_turns", "target_agent_id", "TEXT")
        await _ensure_column(db, "agent_turns", "target_agent_name", "TEXT")
        await _ensure_column(db, "agent_turns", "intent_tag", "TEXT")
        await _ensure_column(db, "agent_turns", "group_ids", "TEXT")
        await _ensure_column(db, "agent_turns", "effective_provider", "TEXT")
        await _ensure_column(db, "agent_turns", "effective_model", "TEXT")
        await _ensure_column(db, "agent_turns", "fidelity_tier", "INTEGER NOT NULL DEFAULT 1")
        await _ensure_column(db, "agent_state_snapshots", "group_ids", "TEXT")
        await _ensure_column(db, "agent_state_snapshots", "spoke_this_round", "INTEGER")
        await _ensure_column(db, "agent_state_snapshots", "attribute_sections_json", "TEXT")
        await _ensure_column(db, "simulation_runs", "experiment_id", "TEXT")
        await _ensure_column(db, "global_state_snapshots", "convergence_delta", "REAL")
        await _ensure_column(db, "simulation_runs", "converged_at_round", "INTEGER")
        await _ensure_column(db, "simulation_runs", "total_input_tokens", "INTEGER")
        await _ensure_column(db, "simulation_runs", "total_output_tokens", "INTEGER")
        await _ensure_column(db, "agent_turns", "input_tokens", "INTEGER")
        await _ensure_column(db, "agent_turns", "output_tokens", "INTEGER")
        await _ensure_column(db, "agent_turns", "effective_profile_id", "TEXT")
        await _ensure_column(db, "agent_turns", "state_update_source", "TEXT")

        await db.commit()
        logger.info("SQLite schema initialized")


async def _ensure_column(db: aiosqlite.Connection, table_name: str, column_name: str, ddl: str) -> None:
    cursor = await db.execute(f"PRAGMA table_info({table_name});")
    columns = await cursor.fetchall()
    existing = {row[1] for row in columns}
    if column_name in existing:
        return
    await db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl};")

