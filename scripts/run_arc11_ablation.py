#!/usr/bin/env python3
"""Arc 11 memory-mechanism ablation sweep (senna-iter-52).

**Local model requirement:** by default this sweep drives the simulation LLM
through LM Studio (``LMSTUDIO_BASE_URL``, default ``http://127.0.0.1:1234/v1``)
and, because ``fsbb_comparator`` has ``rag_enabled: true``, also needs a working
``/v1/embeddings`` endpoint on the same server. LM Studio serves chat and
embeddings as two independent model slots — **you must load two models**:

  1. A chat/LLM model (e.g. ``google/gemma-4-26b-a4b``) — set via ``LMSTUDIO_MODEL``.
  2. An embedding model (e.g. ``text-embedding-nomic-embed-text-v1.5``) — set via
     ``EMBEDDING_MODEL``. **MLX chat models do not serve ``/v1/embeddings``** —
     loading only the chat model will pass chat preflight and then fail every
     simulation with RAG on with ``HTTP 400: No models loaded``.

Run ``--interview-profile-id anthropic_default --judge-profile-id anthropic_default``
to route the post-run architectural interview through Claude instead, which is
useful when the local model is saturated after a long sweep.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "backend" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from run_arc10_diagnostics import run_arc10_diagnostics

from mirofish_backend.api.simulations import (
    SimulationRunRequest,
    queue_simulation_run,
    wait_for_simulation_terminal,
)
from mirofish_backend.config import get_settings
from mirofish_backend.db.repo import get_simulation_export_bundle
from mirofish_backend.db.schema import init_db as schema_init
from mirofish_backend.diagnostics.arc11_ablation import (
    ABLATION_CONDITIONS,
    DEFAULT_ABLATION_SEEDS,
    AblationRunProfile,
    AblationRunRecord,
    build_ablation_results_payload,
    build_network_csv_for_scenario,
    compute_deltas_vs_baseline,
    compute_dispersion_metrics,
    condition_memory_flags,
    extract_cost_metrics,
    extract_normalized_metrics,
    generate_ablation_markdown,
    load_measured_baseline_summary,
)
from mirofish_backend.llm.model_profiles import ANTHROPIC_DEFAULT_ID, LOCAL_LMSTUDIO_DEFAULT_ID
from mirofish_backend.llm.openai_compatible_client import chat_completion_openai_compatible
from mirofish_backend.rag.embeddings import embed_texts_openai_compatible

_DEFAULT_FIXTURES = _REPO_ROOT / "backend/tests/fixtures/membench"
_DEFAULT_BASELINE = _REPO_ROOT / "backend/tests/fixtures/arc11/measured_baseline_summary.json"
_DEFAULT_JSON_OUT = _REPO_ROOT / "docs/diagnostics/arc11_ablation_results.json"
_DEFAULT_MD_OUT = _REPO_ROOT / "docs/diagnostics/ARC11_ABLATION_RESULTS.md"
_DEFAULT_ENV_FILE = _REPO_ROOT / "backend" / ".env"


def load_dotenv_if_present(path: Path) -> bool:
    """
    Minimal ``.env`` loader (no new dependency): sets ``os.environ`` for any
    ``KEY=VALUE`` line not already set to a non-empty value in the
    environment, so real shell exports still win. A variable that's exported
    but empty (e.g. a stale entry in a shell profile) is treated the same as
    unset -- it almost never reflects deliberate intent, and silently letting
    it shadow a real value in .env produces exactly the kind of "valid key,
    still 401" failure this loader exists to prevent. Skips blank lines and
    ``#`` comments. Returns True if the file was found and read.
    """
    import os

    if not path.is_file():
        return False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and not os.environ.get(key):
            os.environ[key] = value
    print(f"[ablation] loaded env from {path}", flush=True)
    return True


def print_config_banner(settings) -> None:
    """Non-secret startup banner: resolved model/URL config actually in effect."""
    embedding_model = settings.embedding_model or settings.lmstudio_model
    print("[ablation] config:", flush=True)
    print(f"  LMSTUDIO_BASE_URL = {settings.lmstudio_base_url}", flush=True)
    print(f"  LMSTUDIO_MODEL    = {settings.lmstudio_model}", flush=True)
    print(
        f"  EMBEDDING_MODEL   = {embedding_model}"
        + ("" if settings.embedding_model else " (unset -> falling back to LMSTUDIO_MODEL)"),
        flush=True,
    )
    print(f"  LLM_PROVIDER      = {settings.llm_provider}", flush=True)


async def run_ablation_preflight(
    settings,
    *,
    check_embeddings: bool,
    check_lmstudio_chat: bool = True,
    interview_profile_id: str | None = None,
    judge_profile_id: str | None = None,
) -> None:
    """
    Fail fast, with actionable text, before queuing the full sweep. Probes
    ``GET /models``, one chat completion (if ``check_lmstudio_chat``), and one
    embedding call (if ``check_embeddings``) against the LM Studio server
    configured in ``settings``. If ``interview_profile_id``/``judge_profile_id``
    resolve to Anthropic (the default), also does one live Anthropic call so
    an invalid/expired API key surfaces here instead of ~10-20 minutes into
    the sweep, mid-interview.

    ``check_lmstudio_chat=False`` is for --llm-provider anthropic: the
    simulation itself won't touch LM Studio, so there's nothing to probe
    beyond /models (still checked, cheaply, in case check_embeddings needs
    it). ``check_embeddings=False`` is for --no-rag.
    """
    import httpx

    from mirofish_backend.llm.claude_client import chat_completion_anthropic
    from mirofish_backend.llm.model_profiles import get_builtin_profile

    base_url = settings.lmstudio_base_url
    lm_model = settings.lmstudio_model
    embedding_model = settings.embedding_model or settings.lmstudio_model

    if check_lmstudio_chat or check_embeddings:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{base_url.rstrip('/')}/models")
        except httpx.ConnectError as exc:
            raise RuntimeError(
                f"[preflight] cannot reach LM Studio at {base_url} ({exc}).\n"
                "  -> Is LM Studio running? Check the server toggle in LM Studio's Developer tab.\n"
                f"  -> curl {base_url.rstrip('/')}/models"
            ) from exc
        if resp.status_code != 200:
            raise RuntimeError(
                f"[preflight] GET {base_url}/models returned HTTP {resp.status_code}: {resp.text[:300]}"
            )

    if not check_lmstudio_chat:
        print(
            "[preflight] skipping LM Studio chat check (--llm-provider anthropic).",
            flush=True,
        )
    if check_lmstudio_chat:
        try:
            text, _, _ = await chat_completion_openai_compatible(
                base_url=base_url,
                model=lm_model,
                messages=[{"role": "user", "content": "Reply with the single word: OK"}],
                temperature=0.0,
                max_tokens=8,
                timeout_s=30.0,
            )
        except Exception as exc:
            raise RuntimeError(
                f"[preflight] chat completion against model={lm_model!r} failed: {exc}\n"
                f"  -> Load {lm_model!r} as the active chat model in LM Studio, or set LMSTUDIO_MODEL "
                "to a model you have loaded.\n"
                f"  -> curl {base_url.rstrip('/')}/chat/completions -H 'Content-Type: application/json' "
                f'-d \'{{"model": "{lm_model}", "messages": [{{"role": "user", "content": "hi"}}]}}\''
            ) from exc
        if not text:
            raise RuntimeError(f"[preflight] chat completion against {lm_model!r} returned empty content.")

    if check_embeddings:
        try:
            vectors = await embed_texts_openai_compatible(
                base_url=base_url,
                model=embedding_model,
                texts=["preflight probe"],
                timeout_s=30.0,
            )
        except Exception as exc:
            raise RuntimeError(
                f"[preflight] embedding call against model={embedding_model!r} failed: {exc}\n"
                "  -> fsbb_comparator has rag_enabled=True, so a loaded embedding model is required "
                "unless you pass --no-rag.\n"
                f"  -> Load an embedding model (e.g. text-embedding-nomic-embed-text-v1.5) in LM "
                "Studio's Developer tab, IN ADDITION to your chat model — MLX chat models do not "
                "serve /v1/embeddings.\n"
                "  -> Then set EMBEDDING_MODEL to that model's id (backend/.env or shell export).\n"
                f"  -> curl {base_url.rstrip('/')}/embeddings -H 'Content-Type: application/json' "
                f'-d \'{{"model": "{embedding_model}", "input": ["hi"]}}\''
            ) from exc
        if not vectors or not vectors[0]:
            raise RuntimeError(f"[preflight] embedding call against {embedding_model!r} returned no vector.")

    if check_lmstudio_chat or check_embeddings:
        checked = []
        if check_lmstudio_chat or check_embeddings:
            checked.append("/models")
        if check_lmstudio_chat:
            checked.append("chat completion")
        if check_embeddings:
            checked.append("embeddings")
        print(f"[preflight] OK — {', '.join(checked)} reachable.", flush=True)

    needs_anthropic = False
    for pid in (interview_profile_id, judge_profile_id):
        if not pid:
            continue
        profile = get_builtin_profile(pid, settings)
        if profile is not None and profile.provider_type == "anthropic":
            needs_anthropic = True

    if not needs_anthropic:
        return

    api_key = (settings.anthropic_api_key or "").strip() or __import__("os").environ.get(
        "ANTHROPIC_API_KEY", ""
    ).strip()
    if not api_key:
        raise RuntimeError(
            "[preflight] --interview-profile-id/--judge-profile-id resolve to Anthropic, but no "
            "ANTHROPIC_API_KEY is set.\n"
            "  -> Add ANTHROPIC_API_KEY=sk-ant-... to backend/.env, or export it in the shell."
        )

    try:
        text, _, _ = await chat_completion_anthropic(
            api_key=api_key,
            model=settings.anthropic_model,
            system_prompt="Reply with the single word: OK",
            user_prompt="ping",
            temperature=0.0,
            max_tokens=8,
            timeout_s=30.0,
        )
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        raise RuntimeError(
            f"[preflight] Anthropic call failed: HTTP {status} against model="
            f"{settings.anthropic_model!r}.\n"
            "  -> 401 with a key that looks right in backend/.env? Check your shell doesn't "
            "already have ANTHROPIC_API_KEY exported as EMPTY (e.g. a stale line in your shell "
            "profile) -- an empty exported var shadows the real one from .env. "
            "Try: echo \"[$ANTHROPIC_API_KEY]\" (before sourcing .env) -- [] means this is it.\n"
            "  -> Confirm the key itself works (must be double-quoted so $ANTHROPIC_API_KEY "
            "expands):\n"
            "       set -a; source backend/.env; set +a\n"
            "       curl https://api.anthropic.com/v1/messages \\\n"
            '         -H "x-api-key: $ANTHROPIC_API_KEY" \\\n'
            '         -H "anthropic-version: 2023-06-01" \\\n'
            '         -H "content-type: application/json" \\\n'
            f'         -d \'{{"model": "{settings.anthropic_model}", "max_tokens": 8, '
            '"messages": [{"role": "user", "content": "hi"}]}\'\n'
            "  -> Or run with --interview-profile-id local_lmstudio_default "
            "--judge-profile-id local_lmstudio_default to skip Anthropic entirely."
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"[preflight] Anthropic call failed: {exc}") from exc
    if not text:
        raise RuntimeError("[preflight] Anthropic call returned empty content.")

    print("[preflight] OK — Anthropic reachable and authorized.", flush=True)


def build_simulation_request(
    *,
    condition: str,
    seed: int,
    profile: AblationRunProfile,
    network_csv: str,
    llm_provider: str | None = None,
    model_profile_id: str | None = None,
    rag_enabled: bool | None = None,
) -> SimulationRunRequest:
    flags = condition_memory_flags(condition)
    return SimulationRunRequest(
        scenario_id=profile.scenario_id,
        agent_limit=profile.agent_limit,
        total_rounds=profile.total_rounds,
        random_seed=seed,
        visibility_policy=profile.visibility_policy,
        sampling_strategy=profile.sampling_strategy,
        network_csv=network_csv,
        llm_provider=llm_provider,
        model_profile_id=model_profile_id,
        rag_enabled=rag_enabled,
        importance_scoring_enabled=flags["importance_scoring_enabled"] or None,
        weighted_retrieval_enabled=flags["weighted_retrieval_enabled"] or None,
        reflection_enabled=flags["reflection_enabled"] or None,
        reflection_trigger_threshold=(
            profile.reflection_trigger_threshold if flags["reflection_enabled"] else None
        ),
    )


async def run_diagnostics_with_retry(
    *,
    settings,
    simulation_id: str,
    fixtures_dir: Path,
    seed: int,
    execute_interview: bool,
    interview_profile_id: str,
    judge_profile_id: str,
    max_attempts: int = 3,
    initial_backoff_s: float = 2.0,
):
    """
    Run Arc 10 diagnostics (incl. live architectural interview) with retry/backoff
    on transient connection failures — the interview step is the most exposed to a
    saturated or briefly-restarted local LM Studio server after a long sweep.

    ``simulation_id`` is always a freshly-queued simulation from this same ablation
    run (see ``run_ablation_via_api``), never a pre-existing one a human might care
    about -- so if attempt 1 fails partway through the interview (e.g. a
    ReadTimeout after writing some but not all agent/category response rows),
    any "already exists" rows found on a later attempt can only be our own
    partial write. Retries therefore pass ``force_interview=True`` from attempt 2
    onward so they cleanly replace that partial state instead of colliding with
    the uniqueness guard in ``run_architectural_interview_for_simulation``.
    """
    import httpx

    attempt = 0
    backoff = initial_backoff_s
    while True:
        attempt += 1
        try:
            return await run_arc10_diagnostics(
                sqlite_path=settings.sqlite_path,
                simulation_id=simulation_id,
                fixtures_dir=fixtures_dir,
                membench_seed=seed,
                membench_answer_mode="memory_match",
                execute_interview=execute_interview,
                interview_profile_id=interview_profile_id,
                judge_profile_id=judge_profile_id,
                force_interview=attempt > 1,
                interview_temperature=0.2,
                interview_max_tokens=1024,
            )
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
            if attempt >= max_attempts:
                raise RuntimeError(
                    f"[interview] gave up after {attempt} attempts against "
                    f"profile={interview_profile_id!r}: {type(exc).__name__}: {exc}\n"
                    "  -> Local model likely saturated/restarted after the sweep. Retry with "
                    "--interview-profile-id anthropic_default --judge-profile-id anthropic_default, "
                    "or re-run with --skip-interview and backfill later via "
                    "scripts/run_architectural_interview.py."
                ) from exc
            print(
                f"[interview] attempt {attempt}/{max_attempts} failed "
                f"({type(exc).__name__}: {exc}); retrying in {backoff:.0f}s",
                flush=True,
            )
            await asyncio.sleep(backoff)
            backoff *= 2


def check_transcript_for_llm_errors(
    bundle: dict, *, simulation_id: str, condition: str, seed: int
) -> None:
    """
    The orchestrator catches LLM call failures per-turn and substitutes
    ``"[LLM error] <ExceptionType>: <message>"`` as that turn's raw_response
    so a single bad turn doesn't crash a production run — but for an ablation
    sweep that means a run can "complete" while silently recording fabricated
    turns instead of real agent dialogue. Abort loudly rather than bank a
    condition's data point on a transcript full of error strings.
    """
    transcript = bundle.get("transcript") or []
    failed = [t for t in transcript if str(t.get("raw_response") or "").startswith("[LLM error]")]
    if not failed:
        return
    sample = failed[0].get("raw_response", "")[:200]
    raise RuntimeError(
        f"[ablation] {len(failed)}/{len(transcript)} turns in simulation {simulation_id} "
        f"(condition={condition!r}, seed={seed}) failed at the LLM call and were recorded as "
        f"error placeholders, not real agent turns. Sample: {sample!r}\n"
        "  -> This run's data is not usable for the sweep. Common cause: LM Studio's loaded "
        "context length for the chat model is too small for a RAG-enabled, multi-round "
        "simulation (context grows every round). Reload the chat model in LM Studio with a "
        "larger Context Length and re-run.\n"
        "  -> Aborting rather than continuing to bank corrupted runs into "
        "arc11_ablation_results.json."
    )


async def run_ablation_via_api(
    *,
    settings,
    condition: str,
    seed: int,
    profile: AblationRunProfile,
    network_csv: str,
    fixtures_dir: Path,
    baseline_metrics: dict,
    execute_interview: bool,
    interview_profile_id: str,
    judge_profile_id: str,
    llm_provider: str | None = None,
    model_profile_id: str | None = None,
    rag_enabled: bool | None = None,
) -> AblationRunRecord:
    req = build_simulation_request(
        condition=condition,
        seed=seed,
        profile=profile,
        network_csv=network_csv,
        llm_provider=llm_provider,
        model_profile_id=model_profile_id,
        rag_enabled=rag_enabled,
    )
    t0 = time.perf_counter()
    resp = await queue_simulation_run(
        settings,
        req,
        run_display_name=f"arc11-{condition}-s{seed}",
    )
    await wait_for_simulation_terminal(
        sqlite_path=settings.sqlite_path,
        simulation_id=resp.id,
        poll_interval=0.5,
        timeout_seconds=3600.0,
    )
    elapsed = time.perf_counter() - t0
    diag = await run_diagnostics_with_retry(
        settings=settings,
        simulation_id=resp.id,
        fixtures_dir=fixtures_dir,
        seed=seed,
        execute_interview=execute_interview,
        interview_profile_id=interview_profile_id,
        judge_profile_id=judge_profile_id,
    )
    bundle = await get_simulation_export_bundle(settings.sqlite_path, simulation_id=resp.id)
    if bundle is None:
        raise RuntimeError(f"missing export bundle for {resp.id}")
    check_transcript_for_llm_errors(bundle, simulation_id=resp.id, condition=condition, seed=seed)
    metrics = extract_normalized_metrics(diag)
    dispersion = compute_dispersion_metrics(export_bundle=bundle, diagnostics_summary=diag)
    cost = extract_cost_metrics(bundle, wall_clock_seconds=elapsed)
    deltas = compute_deltas_vs_baseline(metrics, baseline_metrics)
    return AblationRunRecord(
        condition=condition,
        seed=seed,
        simulation_id=resp.id,
        wall_clock_seconds=elapsed,
        diagnostics=diag,
        cost=cost,
        dispersion=dispersion,
        metrics=metrics,
        deltas_vs_baseline=deltas,
    )


def load_existing_records(json_out: Path) -> list[AblationRunRecord]:
    """
    Reconstruct AblationRunRecord objects from a previously written
    arc11_ablation_results.json so a crashed/interrupted sweep can resume
    without redoing already-completed (condition, seed) runs -- each local
    run costs several minutes, and losing 3 completed runs to one failed
    4th run (as happened on Mark's first two sweep attempts) is exactly the
    kind of avoidable cost this harness should not impose.

    ``diagnostics`` is not persisted in the JSON output (only its derived
    metrics/dispersion/cost/deltas are) and isn't needed again -- aggregation
    and markdown generation only read the derived fields.
    """
    if not json_out.is_file():
        return []
    try:
        payload = json.loads(json_out.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[ablation] could not read existing {json_out} ({exc}); starting fresh.", flush=True)
        return []
    records: list[AblationRunRecord] = []
    for r in payload.get("runs") or []:
        try:
            records.append(
                AblationRunRecord(
                    condition=r["condition"],
                    seed=r["seed"],
                    simulation_id=r["simulation_id"],
                    wall_clock_seconds=r.get("wall_clock_seconds") or 0.0,
                    diagnostics={},
                    cost=r.get("cost") or {},
                    dispersion=r.get("dispersion") or {},
                    metrics=r.get("metrics") or {},
                    deltas_vs_baseline=r.get("deltas_vs_baseline") or {},
                )
            )
        except KeyError:
            continue  # malformed entry -- skip rather than abort resume entirely
    return records


def write_ablation_artifacts(
    *,
    profile: AblationRunProfile,
    seeds: list[int],
    conditions: list[str],
    records: list[AblationRunRecord],
    baseline_ref: dict,
    command: str,
    json_out: Path,
    markdown_out: Path,
    provider_note: dict | None = None,
) -> dict:
    """Build the combined payload and write both artifacts. Called after every
    run (not just at the end) so progress survives a later crash.

    ``provider_note`` records llm_provider/model_profile_id/rag_enabled overrides
    (e.g. --llm-provider anthropic --no-rag) so anyone reading the results later
    knows this sweep may not be directly comparable to the RAG-on, LM-Studio-chat
    Arc 10 measured baseline -- not something that should have to be reconstructed
    from the --command string alone.
    """
    payload = build_ablation_results_payload(
        profile=profile,
        seeds=seeds,
        conditions=conditions,
        records=records,
        baseline_ref=baseline_ref,
        command=command,
    )
    if provider_note:
        payload["provider_override"] = provider_note
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = generate_ablation_markdown(payload)
    markdown_out.write_text(md, encoding="utf-8")
    return payload


_HELP_EPILOG = """\
LM Studio setup (required for the default local sweep):
  1. Load a chat/LLM model (e.g. google/gemma-4-26b-a4b) -> set LMSTUDIO_MODEL.
  2. Load an EMBEDDING model too (e.g. text-embedding-nomic-embed-text-v1.5) -> set
     EMBEDDING_MODEL. fsbb_comparator has rag_enabled=True, so this is not optional.
     MLX chat models do NOT serve /v1/embeddings -- loading only the chat model passes
     chat preflight and then fails every sim with "HTTP 400: No models loaded".
  3. Verify by hand if preflight ever seems wrong:
       curl http://127.0.0.1:1234/v1/models
       curl http://127.0.0.1:1234/v1/embeddings -d '{"model": "<EMBEDDING_MODEL>", "input": ["hi"]}'

If the local model is saturated after a long sweep, keep the sim on LM Studio but move the
post-run interview to Claude:
  python3 scripts/run_arc11_ablation.py --interview-profile-id anthropic_default \\
      --judge-profile-id anthropic_default
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Arc 11 memory ablation harness (senna-iter-52)",
        epilog=_HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--conditions",
        nargs="+",
        default=list(ABLATION_CONDITIONS),
        help="Subset of ablation conditions",
    )
    p.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=list(DEFAULT_ABLATION_SEEDS),
        help="Random seeds (default: 42 43 44)",
    )
    p.add_argument("--sqlite-path", default="", help="SQLite path (default: settings)")
    p.add_argument("--fixtures-dir", type=Path, default=_DEFAULT_FIXTURES)
    p.add_argument("--baseline-json", type=Path, default=_DEFAULT_BASELINE)
    p.add_argument("--json-out", type=Path, default=_DEFAULT_JSON_OUT)
    p.add_argument("--markdown-out", type=Path, default=_DEFAULT_MD_OUT)
    p.add_argument(
        "--skip-interview",
        action="store_true",
        help="Skip live architectural interview (not recommended for ablation)",
    )
    p.add_argument("--rounds", type=int, default=5, help="Total rounds (default 5)")
    p.add_argument(
        "--reflection-threshold",
        type=int,
        default=35,
        help="reflection_trigger_threshold when reflection arm is on (default 35 for 5-round profile)",
    )
    p.add_argument(
        "--interview-profile-id",
        default=ANTHROPIC_DEFAULT_ID,
        help=(
            "Model profile for the architectural interview + judge (default: anthropic_default). "
            f"Use {LOCAL_LMSTUDIO_DEFAULT_ID} to keep the interview on-device, but expect it to be "
            "the first thing to fail if LM Studio is saturated after a long sweep."
        ),
    )
    p.add_argument(
        "--judge-profile-id",
        default=ANTHROPIC_DEFAULT_ID,
        help="Model profile for judge scoring (default: anthropic_default).",
    )
    p.add_argument(
        "--llm-provider",
        default=None,
        choices=["lmstudio", "anthropic", "hybrid"],
        help=(
            "Provider for the SIMULATION itself (not the interview, which is controlled "
            "separately by --interview-profile-id). Default: server setting (lmstudio). Use "
            "anthropic to bypass local LM Studio entirely for chat -- note this still needs "
            "LM Studio for embeddings unless you also pass --no-rag, since Anthropic has no "
            "embeddings endpoint."
        ),
    )
    p.add_argument(
        "--model-profile-id",
        default=None,
        help="Explicit model profile for the simulation (e.g. anthropic_default). Overrides "
        "--llm-provider's default profile resolution if both are set.",
    )
    p.add_argument(
        "--no-rag",
        action="store_true",
        help=(
            "Force rag_enabled=False on the simulation, dropping the embeddings dependency "
            "entirely. Needed alongside --llm-provider anthropic to fully bypass LM Studio. "
            "Note: the Arc 10 measured baseline (21a6d94e...) ran with RAG on, so a --no-rag "
            "sweep is not directly comparable to it on that dimension -- record this explicitly "
            "when interpreting results, don't silently treat the numbers as equivalent."
        ),
    )
    p.add_argument(
        "--env-file",
        type=Path,
        default=_DEFAULT_ENV_FILE,
        help=f"Optional .env to load before running (default: {_DEFAULT_ENV_FILE}). "
        "Only fills vars not already set in the shell.",
    )
    p.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip the /models + chat + embeddings connectivity probe (not recommended).",
    )
    p.add_argument(
        "--fresh",
        action="store_true",
        help=(
            "Ignore any existing --json-out and redo every (condition, seed) run. Default "
            "resumes: (condition, seed) pairs already present in --json-out are skipped, and "
            "results are written after every run, not just at the end -- a crash or abort "
            "partway through no longer costs the runs that already succeeded."
        ),
    )
    return p


async def _main_async(args: argparse.Namespace) -> dict:
    settings = get_settings()
    print_config_banner(settings)
    # --llm-provider anthropic (or an explicit anthropic model profile) means the
    # simulation itself never touches LM Studio for chat. --no-rag drops the
    # embeddings dependency too. Preflight should only check what this run actually needs.
    sim_uses_anthropic = args.llm_provider == "anthropic" or args.model_profile_id == ANTHROPIC_DEFAULT_ID
    check_lmstudio_chat = not sim_uses_anthropic
    check_embeddings = not args.no_rag
    if args.no_rag:
        print(
            "[ablation] --no-rag set: this run is NOT comparable to the RAG-on Arc 10 measured "
            "baseline on that dimension. Record this explicitly when interpreting results.",
            flush=True,
        )
    if not args.skip_preflight:
        await run_ablation_preflight(
            settings,
            check_embeddings=check_embeddings,
            check_lmstudio_chat=check_lmstudio_chat,
            interview_profile_id=args.interview_profile_id,
            judge_profile_id=args.judge_profile_id,
        )
    provider_note: dict | None = None
    if args.llm_provider or args.model_profile_id or args.no_rag:
        provider_note = {
            "llm_provider": args.llm_provider,
            "model_profile_id": args.model_profile_id,
            "rag_enabled": (False if args.no_rag else None),
            "note": (
                "Simulation provider/RAG overridden from defaults -- may not be directly "
                "comparable to the RAG-on, LM-Studio-chat Arc 10 measured baseline "
                "(21a6d94e0af141de95da73fc3c41f759)."
            ),
        }
    sqlite_path = args.sqlite_path or settings.sqlite_path
    await schema_init(sqlite_path)
    profile = AblationRunProfile(
        total_rounds=args.rounds,
        reflection_trigger_threshold=args.reflection_threshold,
    )
    network_csv = build_network_csv_for_scenario(
        scenario_id=profile.scenario_id,
        agent_limit=profile.agent_limit,
    )
    baseline_ref = load_measured_baseline_summary(args.baseline_json.resolve())
    baseline_metrics = baseline_ref["metrics"]
    command = " ".join(sys.argv)

    records: list[AblationRunRecord] = [] if args.fresh else load_existing_records(args.json_out)
    done: set[tuple[str, int]] = {(r.condition, r.seed) for r in records}
    pending = [
        (condition, seed)
        for condition in args.conditions
        for seed in args.seeds
        if (condition, seed) not in done
    ]
    if records:
        print(
            f"[ablation] resuming from {args.json_out}: {len(records)} run(s) already complete, "
            f"{len(pending)} remaining. Use --fresh to ignore and redo everything.",
            flush=True,
        )

    for condition, seed in pending:
        rec = await run_ablation_via_api(
            settings=settings,
            condition=condition,
            seed=seed,
            profile=profile,
            network_csv=network_csv,
            fixtures_dir=args.fixtures_dir.resolve(),
            baseline_metrics=baseline_metrics,
            execute_interview=not args.skip_interview,
            interview_profile_id=args.interview_profile_id,
            judge_profile_id=args.judge_profile_id,
            llm_provider=args.llm_provider,
            model_profile_id=args.model_profile_id,
            rag_enabled=(False if args.no_rag else None),
        )
        records.append(rec)
        print(
            json.dumps(
                {
                    "condition": condition,
                    "seed": seed,
                    "simulation_id": rec.simulation_id,
                    "wall_clock_seconds": rec.cost.get("wall_clock_seconds"),
                }
            ),
            flush=True,
        )
        # Persist after every run, not just at the end -- a later crash shouldn't cost
        # runs that already succeeded.
        write_ablation_artifacts(
            profile=profile,
            seeds=list(args.seeds),
            conditions=list(args.conditions),
            records=records,
            baseline_ref=baseline_ref,
            command=command,
            json_out=args.json_out,
            markdown_out=args.markdown_out,
            provider_note=provider_note,
        )

    payload = write_ablation_artifacts(
        profile=profile,
        seeds=list(args.seeds),
        conditions=list(args.conditions),
        records=records,
        baseline_ref=baseline_ref,
        command=command,
        json_out=args.json_out,
        markdown_out=args.markdown_out,
        provider_note=provider_note,
    )
    payload["artifacts"] = {
        "json": str(args.json_out),
        "markdown": str(args.markdown_out),
    }
    return payload


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # Must run before get_settings() (inside _main_async) so pydantic-settings picks up
    # any vars this fills in. Real shell exports always take precedence.
    load_dotenv_if_present(args.env_file)
    try:
        payload = asyncio.run(_main_async(args))
    except (ValueError, RuntimeError) as exc:
        print(f"\n{exc}\n", file=sys.stderr)
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps({"status": "ok", "run_count": len(payload.get("runs") or [])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
