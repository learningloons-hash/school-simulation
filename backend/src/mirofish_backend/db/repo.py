import aiosqlite
from typing import Any
import json
import uuid

from mirofish_backend.simulation.economics import build_run_economics_payload


def _parse_group_ids_column(raw: str | None) -> list[str]:
    if raw is None or raw == "":
        return []
    try:
        v = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    return []


async def create_simulation_run(
    sqlite_path: str,
    *,
    name: str,
    scenario_id: str,
    status: str,
    total_rounds: int,
    random_seed: int,
    prompt_version: str,
    model_used: str,
    config_snapshot: dict[str, Any] | None = None,
    experiment_id: str | None = None,
) -> str:
    sim_id = uuid.uuid4().hex
    current_round = 0
    config_snapshot_json = json.dumps(config_snapshot, sort_keys=True) if config_snapshot is not None else None

    async with aiosqlite.connect(sqlite_path) as db:
        await db.execute(
            """
            INSERT INTO simulation_runs (
              id, name, scenario_id, status, total_rounds, current_round,
              random_seed, prompt_version, model_used, config_snapshot, experiment_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                sim_id,
                name,
                scenario_id,
                status,
                total_rounds,
                current_round,
                random_seed,
                prompt_version,
                model_used,
                config_snapshot_json,
                experiment_id,
            ),
        )
        await db.commit()
    return sim_id


async def set_simulation_status(
    sqlite_path: str,
    *,
    simulation_id: str,
    status: str,
    current_round: int,
    failure_reason: str | None = None,
    converged_at_round: int | None = None,
    record_converged_at_round: bool = False,
) -> None:
    async with aiosqlite.connect(sqlite_path) as db:
        if status == "completed":
            if record_converged_at_round:
                await db.execute(
                    """
                    UPDATE simulation_runs
                    SET status = ?, current_round = ?, completed_at = CURRENT_TIMESTAMP, failure_reason = NULL,
                        converged_at_round = ?
                    WHERE id = ?;
                    """,
                    (status, current_round, converged_at_round, simulation_id),
                )
            else:
                await db.execute(
                    """
                    UPDATE simulation_runs
                    SET status = ?, current_round = ?, completed_at = CURRENT_TIMESTAMP, failure_reason = NULL
                    WHERE id = ?;
                    """,
                    (status, current_round, simulation_id),
                )
        elif status == "failed":
            await db.execute(
                """
                UPDATE simulation_runs
                SET status = ?, current_round = ?, completed_at = CURRENT_TIMESTAMP, failure_reason = ?
                WHERE id = ?;
                """,
                (status, current_round, failure_reason, simulation_id),
            )
        else:
            await db.execute(
                """
                UPDATE simulation_runs
                SET status = ?, current_round = ?, failure_reason = NULL
                WHERE id = ?;
                """,
                (status, current_round, simulation_id),
            )
        await db.commit()


async def update_simulation_token_totals(
    sqlite_path: str,
    *,
    simulation_id: str,
    total_input_tokens: int,
    total_output_tokens: int,
) -> None:
    """Cumulative token counts for a run (Iteration 29); updated after each round."""
    async with aiosqlite.connect(sqlite_path) as db:
        await db.execute(
            """
            UPDATE simulation_runs
            SET total_input_tokens = ?, total_output_tokens = ?
            WHERE id = ?;
            """,
            (total_input_tokens, total_output_tokens, simulation_id),
        )
        await db.commit()


async def merge_simulation_config_snapshot(
    sqlite_path: str,
    *,
    simulation_id: str,
    updates: dict[str, Any],
) -> None:
    """Shallow-merge ``updates`` into the run's stored ``config_snapshot`` JSON (Iteration 28)."""
    async with aiosqlite.connect(sqlite_path) as db:
        cur = await db.execute(
            "SELECT config_snapshot FROM simulation_runs WHERE id = ?;",
            (simulation_id,),
        )
        row = await cur.fetchone()
        if row is None:
            return
        raw = row[0]
        cfg: dict[str, Any] = json.loads(raw) if raw else {}
        cfg.update(updates)
        await db.execute(
            """
            UPDATE simulation_runs SET config_snapshot = ? WHERE id = ?;
            """,
            (json.dumps(cfg, sort_keys=True), simulation_id),
        )
        await db.commit()


async def insert_agent_turn(
    sqlite_path: str,
    *,
    simulation_id: str,
    round_number: int,
    turn_index: int,
    agent_id: str,
    agent_role: str,
    agent_name: str,
    interaction_type: str,
    target_scope: str,
    target_agent_id: str | None,
    target_agent_name: str | None,
    intent_tag: str | None,
    raw_prompt: str,
    raw_response: str,
    latency_ms: int | None = None,
    group_ids: tuple[str, ...] | list[str] | None = None,
    effective_provider: str | None = None,
    effective_model: str | None = None,
    effective_profile_id: str | None = None,
    fidelity_tier: int = 1,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    state_update_source: str | None = None,
) -> str:
    turn_id = uuid.uuid4().hex
    gid = list(group_ids) if group_ids else []
    group_ids_json = json.dumps(gid)
    async with aiosqlite.connect(sqlite_path) as db:
        await db.execute(
            """
            INSERT INTO agent_turns (
              id, simulation_id, round_number, turn_index,
              agent_id, agent_role, agent_name,
              interaction_type, target_scope, target_agent_id, target_agent_name, intent_tag,
              raw_prompt, raw_response, latency_ms, group_ids,
              effective_provider, effective_model, effective_profile_id, fidelity_tier,
              input_tokens, output_tokens, state_update_source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                turn_id,
                simulation_id,
                round_number,
                turn_index,
                agent_id,
                agent_role,
                agent_name,
                interaction_type,
                target_scope,
                target_agent_id,
                target_agent_name,
                intent_tag,
                raw_prompt,
                raw_response,
                latency_ms,
                group_ids_json,
                effective_provider,
                effective_model,
                effective_profile_id,
                fidelity_tier,
                input_tokens,
                output_tokens,
                state_update_source,
            ),
        )
        await db.commit()
    return turn_id


async def get_simulation_status_with_transcript(
    sqlite_path: str,
    *,
    simulation_id: str,
) -> dict[str, Any] | None:
    async with aiosqlite.connect(sqlite_path) as db:
        cursor = await db.execute(
            """
            SELECT
              id, status, current_round, total_rounds, config_snapshot, failure_reason, converged_at_round,
              total_input_tokens, total_output_tokens
            FROM simulation_runs
            WHERE id = ?;
            """,
            (simulation_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None

        (
            sim_id,
            status,
            current_round,
            total_rounds,
            config_snapshot_json,
            failure_reason,
            converged_at_round_raw,
            total_input_tokens_raw,
            total_output_tokens_raw,
        ) = row
        cfg_parsed = json.loads(config_snapshot_json) if config_snapshot_json else None
        llm_pv = str((cfg_parsed or {}).get("llm_provider") or "lmstudio")
        turns_cursor = await db.execute(
            """
            SELECT
              id, round_number, turn_index,
              agent_id, agent_role, agent_name,
              interaction_type, target_scope, target_agent_id, target_agent_name, intent_tag,
              raw_response, latency_ms, group_ids,
              effective_provider, effective_model, effective_profile_id, fidelity_tier,
              input_tokens, output_tokens, state_update_source
            FROM agent_turns
            WHERE simulation_id = ?
            ORDER BY round_number ASC, turn_index ASC;
            """,
            (simulation_id,),
        )
        turns = []
        async for t in turns_cursor:
            (
                turn_id,
                round_number,
                turn_index,
                agent_id,
                agent_role,
                agent_name,
                interaction_type,
                target_scope,
                target_agent_id,
                target_agent_name,
                intent_tag,
                raw_response,
                latency_ms,
                group_ids_raw,
                eff_prov,
                eff_model,
                eff_profile,
                fid_tier,
                in_tok,
                out_tok,
                state_src,
            ) = t
            turns.append(
                {
                    "id": turn_id,
                    "round_number": round_number,
                    "turn_index": turn_index,
                    "agent_id": agent_id,
                    "agent_role": agent_role,
                    "agent_name": agent_name,
                    "interaction_type": interaction_type,
                    "target_scope": target_scope,
                    "target_agent_id": target_agent_id,
                    "target_agent_name": target_agent_name,
                    "intent_tag": intent_tag,
                    "raw_response": raw_response,
                    "latency_ms": latency_ms,
                    "group_ids": _parse_group_ids_column(group_ids_raw),
                    "effective_provider": eff_prov,
                    "effective_model": eff_model,
                    "effective_profile_id": eff_profile,
                    "fidelity_tier": int(fid_tier) if fid_tier is not None else 1,
                    "input_tokens": int(in_tok) if in_tok is not None else None,
                    "output_tokens": int(out_tok) if out_tok is not None else None,
                    "state_update_source": state_src,
                }
            )

        tin = int(total_input_tokens_raw) if total_input_tokens_raw is not None else None
        tout = int(total_output_tokens_raw) if total_output_tokens_raw is not None else None
        economics = build_run_economics_payload(
            turns,
            total_input_tokens=tin,
            total_output_tokens=tout,
            llm_provider=llm_pv,
        )

        return {
            "id": sim_id,
            "status": status,
            "current_round": current_round,
            "total_rounds": total_rounds,
            "config_snapshot": cfg_parsed,
            "failure_reason": failure_reason,
            "converged_at_round": int(converged_at_round_raw) if converged_at_round_raw is not None else None,
            "transcript": turns,
            "state_timeline": await _get_state_timeline(db, simulation_id=simulation_id),
            "outcome_indicators": await _get_outcome_indicators(db, simulation_id=simulation_id),
            "validity_notes": await _get_validity_notes(db, simulation_id=simulation_id),
            "economics": economics,
        }


async def get_simulation_status_and_config_snapshot(
    sqlite_path: str,
    *,
    simulation_id: str,
) -> dict[str, Any] | None:
    """Light row for sampling report: status + parsed ``config_snapshot`` only."""
    async with aiosqlite.connect(sqlite_path) as db:
        cursor = await db.execute(
            """
            SELECT status, config_snapshot
            FROM simulation_runs
            WHERE id = ?;
            """,
            (simulation_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        status, raw = row[0], row[1]
        return {
            "status": str(status or ""),
            "config_snapshot": json.loads(raw) if raw else None,
        }


async def get_simulation_run_status_only(
    sqlite_path: str,
    *,
    simulation_id: str,
) -> dict[str, Any] | None:
    """Lightweight poll row for orchestration wait loops (no transcript)."""
    async with aiosqlite.connect(sqlite_path) as db:
        cursor = await db.execute(
            """
            SELECT id, status, current_round, total_rounds, failure_reason, converged_at_round,
              total_input_tokens, total_output_tokens
            FROM simulation_runs
            WHERE id = ?;
            """,
            (simulation_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "status": row[1],
            "current_round": row[2],
            "total_rounds": row[3],
            "failure_reason": row[4],
            "converged_at_round": int(row[5]) if row[5] is not None else None,
            "total_input_tokens": int(row[6]) if row[6] is not None else None,
            "total_output_tokens": int(row[7]) if row[7] is not None else None,
        }


async def get_last_agent_responses(
    sqlite_path: str,
    *,
    simulation_id: str,
    agent_id: str,
    last_k: int,
) -> list[str]:
    async with aiosqlite.connect(sqlite_path) as db:
        cursor = await db.execute(
            """
            SELECT raw_response
            FROM agent_turns
            WHERE simulation_id = ? AND agent_id = ?
            ORDER BY round_number DESC, turn_index DESC
            LIMIT ?;
            """,
            (simulation_id, agent_id, last_k),
        )
        rows = await cursor.fetchall()
        # rows are newest->oldest; reverse to oldest->newest for readability.
        return [r[0] for r in rows][::-1]


async def get_recent_interactions(
    sqlite_path: str,
    *,
    simulation_id: str,
    last_k: int,
) -> list[dict[str, Any]]:
    async with aiosqlite.connect(sqlite_path) as db:
        cursor = await db.execute(
            """
            SELECT
              round_number,
              turn_index,
              agent_id,
              agent_name,
              interaction_type,
              target_scope,
              target_agent_name,
              raw_response
            FROM agent_turns
            WHERE simulation_id = ?
            ORDER BY round_number DESC, turn_index DESC
            LIMIT ?;
            """,
            (simulation_id, last_k),
        )
        rows = await cursor.fetchall()

    # rows are newest->oldest; reverse to oldest->newest for readability.
    ordered = rows[::-1]
    return [
        {
            "round_number": int(row[0]),
            "turn_index": int(row[1]),
            "agent_id": str(row[2]),
            "agent_name": row[3],
            "interaction_type": row[4],
            "target_scope": row[5],
            "target_agent_name": row[6] or "all",
            "raw_response": row[7],
        }
        for row in ordered
    ]


async def insert_agent_state_snapshot(
    sqlite_path: str,
    *,
    simulation_id: str,
    round_number: int,
    agent_id: str,
    agent_role: str,
    agent_name: str,
    age: int | None,
    sex: str | None,
    ethnicity: str | None,
    ses: str | None,
    support_level: float,
    resistance_level: float,
    workload_stress: float,
    belief_posture: str,
    group_ids: tuple[str, ...] | list[str] | None = None,
    spoke_this_round: bool = True,
    attribute_sections_json: str | None = None,
) -> str:
    snapshot_id = uuid.uuid4().hex
    gid = list(group_ids) if group_ids else []
    group_ids_json = json.dumps(gid)
    spoke_int = 1 if spoke_this_round else 0
    asj = attribute_sections_json if attribute_sections_json is not None else "{}"
    async with aiosqlite.connect(sqlite_path) as db:
        await db.execute(
            """
            INSERT INTO agent_state_snapshots (
              id, simulation_id, round_number, agent_id, agent_role, agent_name,
              age, sex, ethnicity, ses,
              support_level, resistance_level, workload_stress, belief_posture, group_ids,
              spoke_this_round, attribute_sections_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                snapshot_id,
                simulation_id,
                round_number,
                agent_id,
                agent_role,
                agent_name,
                age,
                sex,
                ethnicity,
                ses,
                support_level,
                resistance_level,
                workload_stress,
                belief_posture,
                group_ids_json,
                spoke_int,
                asj,
            ),
        )
        await db.commit()
    return snapshot_id


async def insert_global_state_snapshot(
    sqlite_path: str,
    *,
    simulation_id: str,
    round_number: int,
    implementation_readiness: float,
    alignment_index: float,
    convergence_delta: float | None = None,
) -> str:
    snapshot_id = uuid.uuid4().hex
    async with aiosqlite.connect(sqlite_path) as db:
        await db.execute(
            """
            INSERT INTO global_state_snapshots (
              id, simulation_id, round_number, implementation_readiness, alignment_index, convergence_delta
            )
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (snapshot_id, simulation_id, round_number, implementation_readiness, alignment_index, convergence_delta),
        )
        await db.commit()
    return snapshot_id


async def insert_round_outcome(
    sqlite_path: str,
    *,
    simulation_id: str,
    round_number: int,
    adoption_momentum: float,
    conflict_events: int,
    consistency_index: float,
) -> str:
    outcome_id = uuid.uuid4().hex
    async with aiosqlite.connect(sqlite_path) as db:
        await db.execute(
            """
            INSERT INTO round_outcomes (
              id, simulation_id, round_number, adoption_momentum, conflict_events, consistency_index
            )
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (outcome_id, simulation_id, round_number, adoption_momentum, conflict_events, consistency_index),
        )
        await db.commit()
    return outcome_id


async def _get_state_timeline(
    db: aiosqlite.Connection,
    *,
    simulation_id: str,
) -> list[dict[str, Any]]:
    global_cursor = await db.execute(
        """
        SELECT round_number, implementation_readiness, alignment_index, convergence_delta
        FROM global_state_snapshots
        WHERE simulation_id = ?
        ORDER BY round_number ASC;
        """,
        (simulation_id,),
    )
    global_rows = await global_cursor.fetchall()

    by_round: dict[int, dict[str, Any]] = {}
    for row in global_rows:
        round_number = int(row[0])
        gs: dict[str, Any] = {
            "implementation_readiness": float(row[1]),
            "alignment_index": float(row[2]),
        }
        if row[3] is not None:
            gs["convergence_delta"] = float(row[3])
        by_round[round_number] = {
            "round_number": round_number,
            "global_state": gs,
            "agents": [],
        }

    agent_cursor = await db.execute(
        """
        SELECT
          round_number, agent_id, agent_role, agent_name, age, sex, ethnicity, ses,
          support_level, resistance_level, workload_stress, belief_posture, group_ids,
          spoke_this_round, attribute_sections_json
        FROM agent_state_snapshots
        WHERE simulation_id = ?
        ORDER BY round_number ASC, agent_name ASC;
        """,
        (simulation_id,),
    )
    agent_rows = await agent_cursor.fetchall()
    for row in agent_rows:
        round_number = int(row[0])
        if round_number not in by_round:
            by_round[round_number] = {
                "round_number": round_number,
                "global_state": {},
                "agents": [],
            }
        raw_spoke = row[13]
        spoke_val: bool | None
        if raw_spoke is None:
            spoke_val = None
        else:
            spoke_val = bool(int(raw_spoke))
        attr_sections: dict[str, Any] = {}
        raw_attr = row[14]
        if raw_attr:
            try:
                parsed = json.loads(raw_attr)
                if isinstance(parsed, dict):
                    attr_sections = parsed
            except json.JSONDecodeError:
                pass
        agent_entry: dict[str, Any] = {
            "agent_id": row[1],
            "agent_role": row[2],
            "agent_name": row[3],
            "demographics": {
                "age": row[4],
                "sex": row[5],
                "ethnicity": row[6],
                "ses": row[7],
            },
            "support_level": float(row[8]),
            "resistance_level": float(row[9]),
            "workload_stress": float(row[10]),
            "belief_posture": row[11],
            "group_ids": _parse_group_ids_column(row[12]),
            "spoke_this_round": spoke_val,
        }
        if attr_sections:
            agent_entry["attribute_sections"] = attr_sections
        by_round[round_number]["agents"].append(agent_entry)

    return [by_round[k] for k in sorted(by_round.keys())]


async def _get_outcome_indicators(
    db: aiosqlite.Connection,
    *,
    simulation_id: str,
) -> list[dict[str, Any]]:
    cursor = await db.execute(
        """
        SELECT round_number, adoption_momentum, conflict_events, consistency_index
        FROM round_outcomes
        WHERE simulation_id = ?
        ORDER BY round_number ASC;
        """,
        (simulation_id,),
    )
    rows = await cursor.fetchall()
    return [
        {
            "round_number": int(r[0]),
            "adoption_momentum": float(r[1]),
            "conflict_events": int(r[2]),
            "consistency_index": float(r[3]),
        }
        for r in rows
    ]


async def _get_validity_notes(db: aiosqlite.Connection, *, simulation_id: str) -> list[dict[str, Any]]:
    cursor = await db.execute(
        """
        SELECT
          id, simulation_id, round_number, rater_id,
          face_score, face_rubric, construct_score, construct_rubric,
          predictive_score, predictive_rubric, notes, created_at
        FROM validity_notes
        WHERE simulation_id = ?
        ORDER BY datetime(created_at) ASC, id ASC;
        """,
        (simulation_id,),
    )
    rows = await cursor.fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": r[0],
                "simulation_id": r[1],
                "round_number": r[2],
                "rater_id": r[3],
                "face_score": float(r[4]) if r[4] is not None else None,
                "face_rubric": r[5],
                "construct_score": float(r[6]) if r[6] is not None else None,
                "construct_rubric": r[7],
                "predictive_score": float(r[8]) if r[8] is not None else None,
                "predictive_rubric": r[9],
                "notes": r[10],
                "created_at": r[11],
            }
        )
    return out


async def simulation_exists(sqlite_path: str, simulation_id: str) -> bool:
    async with aiosqlite.connect(sqlite_path) as db:
        cur = await db.execute("SELECT 1 FROM simulation_runs WHERE id = ? LIMIT 1;", (simulation_id,))
        row = await cur.fetchone()
    return row is not None


async def get_simulation_total_rounds(sqlite_path: str, simulation_id: str) -> int | None:
    async with aiosqlite.connect(sqlite_path) as db:
        cur = await db.execute("SELECT total_rounds FROM simulation_runs WHERE id = ?;", (simulation_id,))
        row = await cur.fetchone()
    if row is None:
        return None
    return int(row[0])


async def insert_validity_note(
    sqlite_path: str,
    *,
    simulation_id: str,
    round_number: int | None,
    rater_id: str | None,
    face_score: float | None,
    face_rubric: str | None,
    construct_score: float | None,
    construct_rubric: str | None,
    predictive_score: float | None,
    predictive_rubric: str | None,
    notes: str | None,
) -> str:
    note_id = uuid.uuid4().hex
    async with aiosqlite.connect(sqlite_path) as db:
        await db.execute(
            """
            INSERT INTO validity_notes (
              id, simulation_id, round_number, rater_id,
              face_score, face_rubric, construct_score, construct_rubric,
              predictive_score, predictive_rubric, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                note_id,
                simulation_id,
                round_number,
                rater_id,
                face_score,
                face_rubric,
                construct_score,
                construct_rubric,
                predictive_score,
                predictive_rubric,
                notes,
            ),
        )
        await db.commit()
    return note_id


async def list_simulation_runs(sqlite_path: str, *, limit: int = 50) -> list[dict[str, Any]]:
    async with aiosqlite.connect(sqlite_path) as db:
        cursor = await db.execute(
            """
            SELECT id, name, scenario_id, status, current_round, total_rounds, created_at, completed_at, experiment_id
            FROM simulation_runs
            ORDER BY datetime(created_at) DESC
            LIMIT ?;
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
    return [
        {
            "id": r[0],
            "name": r[1],
            "scenario_id": r[2],
            "status": r[3],
            "current_round": r[4],
            "total_rounds": r[5],
            "created_at": r[6],
            "completed_at": r[7],
            "experiment_id": r[8],
        }
        for r in rows
    ]


async def get_simulation_export_bundle(sqlite_path: str, *, simulation_id: str) -> dict[str, Any] | None:
    """
    Full export payload: run row, flat tables, plus derived state_timeline / outcome_indicators for JSON consumers.
    """
    async with aiosqlite.connect(sqlite_path) as db:
        cursor = await db.execute(
            """
            SELECT
              id, name, scenario_id, status, total_rounds, current_round, random_seed,
              prompt_version, model_used, config_snapshot, failure_reason, created_at, completed_at, experiment_id,
              converged_at_round, total_input_tokens, total_output_tokens
            FROM simulation_runs
            WHERE id = ?;
            """,
            (simulation_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None

        (
            sim_id,
            name,
            scenario_id,
            status,
            total_rounds,
            current_round,
            random_seed,
            prompt_version,
            model_used,
            config_snapshot_json,
            failure_reason,
            created_at,
            completed_at,
            experiment_id,
            converged_at_round_raw,
            total_input_tokens_raw,
            total_output_tokens_raw,
        ) = row

        cfg_run = json.loads(config_snapshot_json) if config_snapshot_json else None
        llm_pv = str((cfg_run or {}).get("llm_provider") or "lmstudio")
        tin_run = int(total_input_tokens_raw) if total_input_tokens_raw is not None else None
        tout_run = int(total_output_tokens_raw) if total_output_tokens_raw is not None else None

        run: dict[str, Any] = {
            "id": sim_id,
            "name": name,
            "scenario_id": scenario_id,
            "status": status,
            "total_rounds": total_rounds,
            "current_round": current_round,
            "random_seed": random_seed,
            "prompt_version": prompt_version,
            "model_used": model_used,
            "config_snapshot": cfg_run,
            "failure_reason": failure_reason,
            "created_at": created_at,
            "completed_at": completed_at,
            "experiment_id": experiment_id,
            "converged_at_round": int(converged_at_round_raw) if converged_at_round_raw is not None else None,
            "total_input_tokens": tin_run,
            "total_output_tokens": tout_run,
        }

        turns_cursor = await db.execute(
            """
            SELECT
              id, simulation_id, round_number, turn_index,
              agent_id, agent_role, agent_name,
              interaction_type, target_scope, target_agent_id, target_agent_name, intent_tag,
              raw_prompt, raw_response, latency_ms, group_ids,
              effective_provider, effective_model, effective_profile_id, fidelity_tier, created_at,
              input_tokens, output_tokens, state_update_source
            FROM agent_turns
            WHERE simulation_id = ?
            ORDER BY round_number ASC, turn_index ASC;
            """,
            (simulation_id,),
        )
        transcript: list[dict[str, Any]] = []
        async for t in turns_cursor:
            transcript.append(
                {
                    "id": t[0],
                    "simulation_id": t[1],
                    "round_number": t[2],
                    "turn_index": t[3],
                    "agent_id": t[4],
                    "agent_role": t[5],
                    "agent_name": t[6],
                    "interaction_type": t[7],
                    "target_scope": t[8],
                    "target_agent_id": t[9],
                    "target_agent_name": t[10],
                    "intent_tag": t[11],
                    "raw_prompt": t[12],
                    "raw_response": t[13],
                    "latency_ms": t[14],
                    "group_ids": _parse_group_ids_column(t[15]),
                    "effective_provider": t[16],
                    "effective_model": t[17],
                    "effective_profile_id": t[18],
                    "fidelity_tier": int(t[19]) if t[19] is not None else 1,
                    "created_at": t[20],
                    "input_tokens": int(t[21]) if t[21] is not None else None,
                    "output_tokens": int(t[22]) if t[22] is not None else None,
                    "state_update_source": t[23],
                }
            )

        run["economics"] = build_run_economics_payload(
            transcript,
            total_input_tokens=tin_run,
            total_output_tokens=tout_run,
            llm_provider=llm_pv,
        )

        snap_cursor = await db.execute(
            """
            SELECT
              id, simulation_id, round_number, agent_id, agent_role, agent_name,
              age, sex, ethnicity, ses,
              support_level, resistance_level, workload_stress, belief_posture, group_ids,
              spoke_this_round, attribute_sections_json, created_at
            FROM agent_state_snapshots
            WHERE simulation_id = ?
            ORDER BY round_number ASC, agent_name ASC;
            """,
            (simulation_id,),
        )
        agent_state_snapshots: list[dict[str, Any]] = []
        async for s in snap_cursor:
            raw_spoke = s[15]
            spoke_out: bool | None
            if raw_spoke is None:
                spoke_out = None
            else:
                spoke_out = bool(int(raw_spoke))
            attr_snap: dict[str, Any] | None = None
            raw_asj = s[16]
            if raw_asj:
                try:
                    p = json.loads(raw_asj)
                    if isinstance(p, dict) and p:
                        attr_snap = p
                except json.JSONDecodeError:
                    pass
            row_dict: dict[str, Any] = {
                "id": s[0],
                "simulation_id": s[1],
                "round_number": s[2],
                "agent_id": s[3],
                "agent_role": s[4],
                "agent_name": s[5],
                "age": s[6],
                "sex": s[7],
                "ethnicity": s[8],
                "ses": s[9],
                "support_level": float(s[10]),
                "resistance_level": float(s[11]),
                "workload_stress": float(s[12]),
                "belief_posture": s[13],
                "group_ids": _parse_group_ids_column(s[14]),
                "spoke_this_round": spoke_out,
                "created_at": s[17],
            }
            if attr_snap is not None:
                row_dict["attribute_sections"] = attr_snap
            agent_state_snapshots.append(row_dict)

        g_cursor = await db.execute(
            """
            SELECT id, simulation_id, round_number, implementation_readiness, alignment_index, convergence_delta, created_at
            FROM global_state_snapshots
            WHERE simulation_id = ?
            ORDER BY round_number ASC;
            """,
            (simulation_id,),
        )
        global_state_snapshots: list[dict[str, Any]] = []
        async for g in g_cursor:
            gdict: dict[str, Any] = {
                "id": g[0],
                "simulation_id": g[1],
                "round_number": g[2],
                "implementation_readiness": float(g[3]),
                "alignment_index": float(g[4]),
                "created_at": g[6],
            }
            if g[5] is not None:
                gdict["convergence_delta"] = float(g[5])
            global_state_snapshots.append(gdict)

        o_cursor = await db.execute(
            """
            SELECT id, simulation_id, round_number, adoption_momentum, conflict_events, consistency_index, created_at
            FROM round_outcomes
            WHERE simulation_id = ?
            ORDER BY round_number ASC;
            """,
            (simulation_id,),
        )
        round_outcomes: list[dict[str, Any]] = []
        async for o in o_cursor:
            round_outcomes.append(
                {
                    "id": o[0],
                    "simulation_id": o[1],
                    "round_number": o[2],
                    "adoption_momentum": float(o[3]),
                    "conflict_events": int(o[4]),
                    "consistency_index": float(o[5]),
                    "created_at": o[6],
                }
            )

        state_timeline = await _get_state_timeline(db, simulation_id=simulation_id)
        outcome_indicators = await _get_outcome_indicators(db, simulation_id=simulation_id)
        validity_notes = await _get_validity_notes(db, simulation_id=simulation_id)

    return {
        "run": run,
        "transcript": transcript,
        "agent_state_snapshots": agent_state_snapshots,
        "global_state_snapshots": global_state_snapshots,
        "round_outcomes": round_outcomes,
        "state_timeline": state_timeline,
        "outcome_indicators": outcome_indicators,
        "validity_notes": validity_notes,
    }


async def upsert_user_scenario(
    sqlite_path: str,
    *,
    scenario_id: str,
    display_name: str,
    document_json: str,
    scenario_doc_version: str = "1",
) -> None:
    async with aiosqlite.connect(sqlite_path) as db:
        await db.execute(
            """
            INSERT INTO user_scenarios (scenario_id, display_name, document_json, scenario_doc_version, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(scenario_id) DO UPDATE SET
              display_name = excluded.display_name,
              document_json = excluded.document_json,
              scenario_doc_version = excluded.scenario_doc_version,
              updated_at = CURRENT_TIMESTAMP;
            """,
            (scenario_id, display_name, document_json, scenario_doc_version),
        )
        await db.commit()


async def get_user_scenario_json(sqlite_path: str, *, scenario_id: str) -> str | None:
    async with aiosqlite.connect(sqlite_path) as db:
        cursor = await db.execute(
            "SELECT document_json FROM user_scenarios WHERE scenario_id = ?;",
            (scenario_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return str(row[0])


async def get_user_scenario_row(sqlite_path: str, *, scenario_id: str) -> dict[str, Any] | None:
    async with aiosqlite.connect(sqlite_path) as db:
        cursor = await db.execute(
            """
            SELECT scenario_id, display_name, document_json, scenario_doc_version, updated_at
            FROM user_scenarios WHERE scenario_id = ?;
            """,
            (scenario_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return {
            "scenario_id": row[0],
            "display_name": row[1],
            "document_json": row[2],
            "scenario_doc_version": row[3],
            "updated_at": row[4],
        }


async def list_user_scenario_rows(sqlite_path: str) -> list[dict[str, Any]]:
    async with aiosqlite.connect(sqlite_path) as db:
        cursor = await db.execute(
            """
            SELECT scenario_id, display_name, document_json, scenario_doc_version, updated_at
            FROM user_scenarios ORDER BY scenario_id ASC;
            """,
        )
        rows = await cursor.fetchall()
    return [
        {
            "scenario_id": r[0],
            "display_name": r[1],
            "document_json": r[2],
            "scenario_doc_version": r[3],
            "updated_at": r[4],
        }
        for r in rows
    ]


async def user_scenario_exists(sqlite_path: str, *, scenario_id: str) -> bool:
    async with aiosqlite.connect(sqlite_path) as db:
        cursor = await db.execute(
            "SELECT 1 FROM user_scenarios WHERE scenario_id = ? LIMIT 1;",
            (scenario_id,),
        )
        row = await cursor.fetchone()
        return row is not None


# --- Experiments (Iteration 27) ---


async def create_experiment(
    sqlite_path: str,
    *,
    name: str,
    scenario_id: str,
    base_random_seed: int,
    base_total_rounds: int,
    status: str = "pending",
) -> str:
    exp_id = uuid.uuid4().hex
    async with aiosqlite.connect(sqlite_path) as db:
        await db.execute(
            """
            INSERT INTO experiments (id, name, scenario_id, base_random_seed, base_total_rounds, status)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (exp_id, name, scenario_id, base_random_seed, base_total_rounds, status),
        )
        await db.commit()
    return exp_id


async def set_experiment_status(
    sqlite_path: str,
    *,
    experiment_id: str,
    status: str,
) -> None:
    async with aiosqlite.connect(sqlite_path) as db:
        if status in ("completed", "failed"):
            await db.execute(
                """
                UPDATE experiments SET status = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?;
                """,
                (status, experiment_id),
            )
        else:
            await db.execute(
                "UPDATE experiments SET status = ? WHERE id = ?;",
                (status, experiment_id),
            )
        await db.commit()


async def get_experiment_row(sqlite_path: str, *, experiment_id: str) -> dict[str, Any] | None:
    async with aiosqlite.connect(sqlite_path) as db:
        cur = await db.execute(
            """
            SELECT id, name, scenario_id, base_random_seed, base_total_rounds, status, created_at, completed_at
            FROM experiments WHERE id = ?;
            """,
            (experiment_id,),
        )
        row = await cur.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "name": row[1],
        "scenario_id": row[2],
        "base_random_seed": int(row[3]),
        "base_total_rounds": int(row[4]),
        "status": row[5],
        "created_at": row[6],
        "completed_at": row[7],
    }


async def list_experiments(sqlite_path: str, *, limit: int = 50) -> list[dict[str, Any]]:
    async with aiosqlite.connect(sqlite_path) as db:
        cur = await db.execute(
            """
            SELECT
              e.id, e.name, e.scenario_id, e.base_random_seed, e.base_total_rounds,
              e.status, e.created_at, e.completed_at,
              (SELECT COUNT(*) FROM experiment_runs er WHERE er.experiment_id = e.id) AS run_count
            FROM experiments e
            ORDER BY datetime(e.created_at) DESC
            LIMIT ?;
            """,
            (limit,),
        )
        rows = await cur.fetchall()
    return [
        {
            "id": r[0],
            "name": r[1],
            "scenario_id": r[2],
            "base_random_seed": int(r[3]),
            "base_total_rounds": int(r[4]),
            "status": r[5],
            "created_at": r[6],
            "completed_at": r[7],
            "run_count": int(r[8] or 0),
        }
        for r in rows
    ]


async def insert_experiment_run_link(
    sqlite_path: str,
    *,
    experiment_id: str,
    step_index: int,
    simulation_id: str,
    run_label: str | None,
) -> None:
    async with aiosqlite.connect(sqlite_path) as db:
        await db.execute(
            """
            INSERT INTO experiment_runs (experiment_id, step_index, simulation_id, run_label)
            VALUES (?, ?, ?, ?);
            """,
            (experiment_id, step_index, simulation_id, run_label),
        )
        await db.commit()


async def list_experiment_run_links(
    sqlite_path: str,
    *,
    experiment_id: str,
) -> list[dict[str, Any]]:
    async with aiosqlite.connect(sqlite_path) as db:
        cur = await db.execute(
            """
            SELECT step_index, simulation_id, run_label
            FROM experiment_runs
            WHERE experiment_id = ?
            ORDER BY step_index ASC;
            """,
            (experiment_id,),
        )
        rows = await cur.fetchall()
    return [
        {"step_index": int(r[0]), "simulation_id": r[1], "run_label": r[2]} for r in rows
    ]


async def get_simulation_economics_summary(
    sqlite_path: str,
    *,
    simulation_id: str,
) -> dict[str, Any] | None:
    """Token totals + tier/cost breakdown without loading full transcript bodies (Iteration 29)."""
    async with aiosqlite.connect(sqlite_path) as db:
        cur = await db.execute(
            """
            SELECT config_snapshot, total_input_tokens, total_output_tokens
            FROM simulation_runs WHERE id = ?;
            """,
            (simulation_id,),
        )
        row = await cur.fetchone()
        if row is None:
            return None
        cfg_raw, tin, tout = row[0], row[1], row[2]
        cfg_parsed = json.loads(cfg_raw) if cfg_raw else {}
        llm_pv = str((cfg_parsed or {}).get("llm_provider") or "lmstudio")
        tin_i = int(tin) if tin is not None else None
        tout_i = int(tout) if tout is not None else None
        tcur = await db.execute(
            """
            SELECT fidelity_tier, effective_provider, input_tokens, output_tokens
            FROM agent_turns
            WHERE simulation_id = ?
            ORDER BY round_number ASC, turn_index ASC;
            """,
            (simulation_id,),
        )
        rows = await tcur.fetchall()
    transcript_minimal: list[dict[str, Any]] = []
    for r in rows:
        fid = r[0]
        try:
            ft = int(fid) if fid is not None else 1
        except (TypeError, ValueError):
            ft = 1
        transcript_minimal.append(
            {
                "fidelity_tier": ft,
                "effective_provider": r[1],
                "input_tokens": int(r[2]) if r[2] is not None else None,
                "output_tokens": int(r[3]) if r[3] is not None else None,
            }
        )
    return build_run_economics_payload(
        transcript_minimal,
        total_input_tokens=tin_i,
        total_output_tokens=tout_i,
        llm_provider=llm_pv,
    )


async def get_merged_round_metrics(
    sqlite_path: str,
    *,
    simulation_id: str,
) -> dict[int, dict[str, Any]]:
    """Per-round global + outcome metrics for experiment comparison tables."""
    async with aiosqlite.connect(sqlite_path) as db:
        gcur = await db.execute(
            """
            SELECT round_number, implementation_readiness, alignment_index, convergence_delta
            FROM global_state_snapshots
            WHERE simulation_id = ?
            ORDER BY round_number ASC;
            """,
            (simulation_id,),
        )
        grows = await gcur.fetchall()
        ocur = await db.execute(
            """
            SELECT round_number, adoption_momentum, conflict_events, consistency_index
            FROM round_outcomes
            WHERE simulation_id = ?
            ORDER BY round_number ASC;
            """,
            (simulation_id,),
        )
        orows = await ocur.fetchall()

    by_round: dict[int, dict[str, Any]] = {}
    for row in grows:
        rn = int(row[0])
        gbucket: dict[str, Any] = {
            "implementation_readiness": float(row[1]),
            "alignment_index": float(row[2]),
        }
        if row[3] is not None:
            gbucket["convergence_delta"] = float(row[3])
        by_round[rn] = gbucket
    for row in orows:
        rn = int(row[0])
        bucket = by_round.setdefault(rn, {})
        bucket["adoption_momentum"] = float(row[1])
        bucket["conflict_events"] = int(row[2])
        bucket["consistency_index"] = float(row[3])
    return by_round


async def upsert_round_summary(
    sqlite_path: str,
    *,
    simulation_id: str,
    round_number: int,
    summary_text: str,
) -> None:
    async with aiosqlite.connect(sqlite_path) as db:
        await db.execute(
            """
            INSERT INTO round_summaries (simulation_id, round_number, summary_text)
            VALUES (?, ?, ?)
            ON CONFLICT (simulation_id, round_number) DO UPDATE SET summary_text = excluded.summary_text;
            """,
            (simulation_id, round_number, summary_text),
        )
        await db.commit()


async def get_round_summaries(
    sqlite_path: str,
    *,
    simulation_id: str,
    up_to_round: int | None = None,
) -> list[dict[str, Any]]:
    """Return summaries oldest-first, optionally capped at up_to_round (exclusive)."""
    async with aiosqlite.connect(sqlite_path) as db:
        if up_to_round is not None:
            cursor = await db.execute(
                """
                SELECT round_number, summary_text
                FROM round_summaries
                WHERE simulation_id = ? AND round_number < ?
                ORDER BY round_number ASC;
                """,
                (simulation_id, up_to_round),
            )
        else:
            cursor = await db.execute(
                """
                SELECT round_number, summary_text
                FROM round_summaries
                WHERE simulation_id = ?
                ORDER BY round_number ASC;
                """,
                (simulation_id,),
            )
        rows = await cursor.fetchall()
    return [{"round_number": int(r[0]), "summary_text": str(r[1])} for r in rows]


async def get_turns_for_round(
    sqlite_path: str,
    *,
    simulation_id: str,
    round_number: int,
) -> list[dict[str, Any]]:
    """Return all agent turns for a specific round, ordered by turn_index ascending."""
    async with aiosqlite.connect(sqlite_path) as db:
        cursor = await db.execute(
            """
            SELECT turn_index, agent_id, agent_name, agent_role,
                   interaction_type, target_agent_name, raw_response
            FROM agent_turns
            WHERE simulation_id = ? AND round_number = ?
            ORDER BY turn_index ASC;
            """,
            (simulation_id, round_number),
        )
        rows = await cursor.fetchall()
    return [
        {
            "turn_index": int(r[0]),
            "agent_id": str(r[1]),
            "agent_name": str(r[2]),
            "agent_role": str(r[3]),
            "interaction_type": str(r[4]),
            "target_agent_name": r[5] or "all",
            "raw_response": str(r[6]),
        }
        for r in rows
    ]

