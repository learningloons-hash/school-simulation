# Handoff to Builder

**Ritual:** Architect seeds this file before each Builder session. Builder implements **only** what is under **Active task** below. When finished (tests pass, commit), Builder fills [`handoff-to-architect.md`](./handoff-to-architect.md) and stops.

---

## Active task — `senna-iter-58` Part A (pre-registration v2 draft)

| Field | Value |
|-------|--------|
| **Arc** | 12 — Freeze and Study Readiness |
| **Spec** | [`HANDOFF_SENNA_ARC12.md`](./HANDOFF_SENNA_ARC12.md) §5 |
| **Scoring** | [`SSTRF_RQ1_SCORING_SYSTEM_V2.md`](../research/SSTRF_RQ1_SCORING_SYSTEM_V2.md) — incorporate by reference, do not rewrite propositions |
| **Branch** | `main` |
| **Base** | iter-57 closeout commit |
| **Commit** | One commit for Part A only |

### Goal

Draft **pre-registration v2** for RQ1. Documentation only — no live study runs, no scoring live trials. **Mark signs before any study output exists** — leave an explicit signature block; do not mark as signed.

### Required deliverable

**New file:** `docs/research/PREREG_SSTRF_RQ1_V2.md`

Follow ARC12 §5. Must record and resolve:

| Field | Source to cite |
|-------|----------------|
| Platform commit | `git rev-parse HEAD` at commit time |
| Fixture repo + commit | [`ciepss_school_b_provenance.json`](../diagnostics/ciepss_school_b_provenance.json) — **not** the DB row |
| Generator model + tier | GM-F v2 §9 — `claude-haiku-4-5-20251001`, Anthropic |
| Full config snapshot | GM-F v2 §9 table + mechanism flags all `false`, `likert_self_report_enabled: false`, `convergence_threshold: null`, `working_memory_last_k: 2`, `peer_context_max_chars: 1200`, `visibility_policy: network_bounded`, documented network CSV path |
| Scoring system | `SSTRF_RQ1_SCORING_SYSTEM_V2.md` at same commit (path + hash) |
| Study seeds | **Placeholder** — "fixed in Part B (`ARC12_STUDY_SEEDS.json`)" until Part B lands |
| Convergence | Record τ=0.02 from [`ARC12_CONVERGENCE_CALIBRATION.md`](../diagnostics/ARC12_CONVERGENCE_CALIBRATION.md) as **calibrated but not applied**; study uses fixed 20 rounds per GM-F §8 |
| Excluded development work | Arcs 9–12 rehearsal seeds 42/43/44; Phase C and Phase V prior pilots |
| Framing | GM-F v2 §3 verbatim — ten trials are repeated samples of one generative process, not independent hypothesis tests |

Include **Signature** section:

```markdown
## Signature
**Status:** UNSIGNED — Mark must sign before any study output exists.
**Signed by:** ___________________
**Date:** ___________________
```

State explicitly: old `PREREG_SSTRF_RQ1.md` v1.x governs closed Phase V and is **not** reused.

### Out of scope (Part A)

- Study seeds JSON (Part B)
- Freeze manifest (Part B)
- Mark's signature (Mark)
- Live study execution
- RQ2 pre-reg
- Changing GM-F proposition text or thresholds

### Verification

```bash
# No new tests required for Part A — doc-only
# Sanity: pre-reg file exists and references provenance manifest + scoring v2
test -f docs/research/PREREG_SSTRF_RQ1_V2.md
```

### Commit

`senna-iter-58` Part A (pre-reg v2 draft).

---

## Queued — `senna-iter-58` Part B (seeds + freeze manifest)

**Do not start until Part A is committed and Architect seeds Part B.**

| Deliverable | Purpose |
|-------------|---------|
| `docs/diagnostics/ARC12_STUDY_SEEDS.json` | Ten study seeds, fixed; **must not** include 42, 43, 44 or any seed listed in Arc 9–12 diagnostic JSON under `docs/diagnostics/` |
| `docs/diagnostics/ARC12_PLATFORM_FREEZE.json` | Platform commit, fixture provenance ref, scoring doc ref, seeds ref, `frozen_at` ISO timestamp |
| Update `PREREG_SSTRF_RQ1_V2.md` | Replace seeds placeholder with manifest path + seed list |
| `backend/tests/test_senna_iter58_freeze.py` | Assert seeds ∉ exclusion set; freeze JSON schema fields present |
| Housekeeping | `ARC12_PLATFORM_MEASURES_STATEMENT.md` §6 — Part B complete; §1 external-judge row → harness on `main` |

**Seed selection rule (document in JSON):** e.g. first ten integers ≥500 not in exclusion set, or SHA256-derived — must be deterministic and auditable. Label trials `trial-A` … `trial-J` in manifest.

**After Mark signs:** freeze is binding; no platform changes until study completes or pre-reg is formally amended.

---

## Completed (do not redo)

- `senna-iter-54`–`57` (incl. scoring harness `177306a`, Architect PASS)
