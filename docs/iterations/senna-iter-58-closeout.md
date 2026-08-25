# senna-iter-58 — Pre-registration v2 and Platform Freeze

**Spec:** [`docs/handoffs/HANDOFF_SENNA_ARC12.md`](../handoffs/HANDOFF_SENNA_ARC12.md) §5
**Arc:** 12 — Freeze and Study Readiness
**Date:** 2026-08-25
**Status:** Iteration **CLOSED**. Pre-reg **signed** 2026-08-25 by Mark. **Arc 12 CLOSED.**

---

## What iter-58 delivered

Locks the RQ1 validity study configuration in writing before any substantive trial output. Replaces the closed Phase V pre-registration (v1.x) with a v2 instrument aligned to Arc 12 platform reality and GM-F scoring system v2.

| Part | Commit | Deliverable |
|------|--------|-------------|
| A — Pre-reg draft | `e3e74b9` | [`PREREG_SSTRF_RQ1_V2.md`](../research/PREREG_SSTRF_RQ1_V2.md) (unsigned) |
| B — Seeds + freeze | `66ea88e` | [`ARC12_STUDY_SEEDS.json`](../diagnostics/ARC12_STUDY_SEEDS.json), [`ARC12_PLATFORM_FREEZE.json`](../diagnostics/ARC12_PLATFORM_FREEZE.json), scoring v2 tracked in git, `test_senna_iter58_freeze.py` (5 tests), measures housekeeping |
| Handoff hygiene | `a20dfd4` | Architect report SHA update |

**Architect review:** Part A PASS (`e3e74b9`); Part B PASS (`66ea88e`).

---

## Part A — Pre-registration v2 draft (`e3e74b9`)

**Goal:** File the binding study protocol before validity trials — config, criterion by reference, exclusions, framing — with explicit **UNSIGNED** status until Mark signs.

**Shipped:**

- Platform record: code freeze point `da906c3` (iter-57 closeout; harness `177306a`)
- Fixture provenance from [`ciepss_school_b_provenance.json`](../diagnostics/ciepss_school_b_provenance.json) — study repo `47013659…`, not DB row
- Full simulation config (GM-F v2 §9): `ciepss_school_b`, 8 agents, **20 fixed rounds**, Haiku 4.5, network-bounded documented CSV, all mechanism flags **off**, Likert **off**, `convergence_threshold: null`
- Convergence τ=0.02 **calibrated but not applied** ([`ARC12_CONVERGENCE_CALIBRATION.md`](../diagnostics/ARC12_CONVERGENCE_CALIBRATION.md))
- Scoring criterion incorporated by reference — [`SSTRF_RQ1_SCORING_SYSTEM_V2.md`](../research/SSTRF_RQ1_SCORING_SYSTEM_V2.md) (propositions not rewritten in pre-reg)
- Phase V v1.x explicitly not reused; 1/10 prior pilot reported separately
- GM-F §3 framing verbatim (ten trials = repeated samples, not independent hypothesis tests)
- Signature block left blank

---

## Part B — Study seeds + freeze manifest (`66ea88e`)

**Goal:** Fix ten study seeds, write freeze manifest, close Part A architect follow-ups.

### Study seeds

[`ARC12_STUDY_SEEDS.json`](../diagnostics/ARC12_STUDY_SEEDS.json)

| Trial | Seed |
|-------|------|
| trial-A … trial-J | 500–509 |

**Rule:** first ten integers ≥ 500. **Excluded:** 42, 43, 44 (all seeds in Arc 9–12 diagnostic JSON).

### Platform freeze manifest

[`ARC12_PLATFORM_FREEZE.json`](../diagnostics/ARC12_PLATFORM_FREEZE.json)

| Field | Value |
|-------|-------|
| `platform_code_commit` | `da906c3` |
| `scoring_harness_commit` | `177306a` |
| `pre_reg_commit` | `e3e74b9` (Part A filing; §7 seeds updated in `66ea88e`) |
| `fixture_commit` | `47013659309c5ac047dbc53dcea3fd1441d74042` |
| `scoring_system` blob | `8130b7455422a1c474dd0cc1a647816b1fe593b8` |
| `signature_status` | **unsigned** |

### Also shipped

- `SSTRF_RQ1_SCORING_SYSTEM_V2.md` — gitignore allowlist + committed (reproducible hash)
- `PREREG_SSTRF_RQ1_V2.md` §7 — seeds table + freeze manifest links
- `ARC12_PLATFORM_MEASURES_STATEMENT.md` — §1 external-judge row, §6 harness on `main`, §7 await Mark signature
- `backend/tests/test_senna_iter58_freeze.py` — **5 passed**

---

## ARC12 §5 definition of done

| Item | Status | Evidence |
|------|--------|----------|
| Pre-registration v2 drafted (replaces v1.x) | ✓ | `PREREG_SSTRF_RQ1_V2.md` |
| Platform commit recorded | ✓ | `da906c3` in pre-reg §2 + freeze manifest |
| Fixture commit + repo recorded | ✓ | provenance manifest + freeze |
| Full config snapshot | ✓ | pre-reg §4 |
| Scoring system from iter-57 | ✓ | by reference + tracked blob |
| Ten study seeds, distinct from dev seeds | ✓ | 500–509 |
| **Mark signature before study output** | ✓ | Signed 2026-08-25 |

**ARC12 §5 Ops DoD: met pending signature.**

---

## What Mark signs (summary for PI)

Signing [`PREREG_SSTRF_RQ1_V2.md`](../research/PREREG_SSTRF_RQ1_V2.md) means:

1. **Lock the rules before seeing results** — how simulations run, how correspondence is scored, and what counts as pass/fail are fixed before any validity trial is executed or scored.
2. **Accept the frozen stack** — platform `da906c3`, CIEPSS School B fixture at study-repo `47013659…`, 10 seeds (500–509), 20 rounds, Haiku 4.5, mechanisms off.
3. **Accept the criterion** — GM-F v2 scoring (17 judgements/trial, study passes at ≥8/10); Phase V v1.x and Arc 9–12 rehearsal runs excluded from validity claims.
4. **Commit to freeze discipline** — no platform changes until all ten trials complete and are scored, or pre-reg is formally amended and re-signed **before** viewing outputs the amendment would affect.
5. **Not a promise of success** — signing does not assert the study will pass; it asserts the study will be run and reported under these rules regardless of outcome.

**How to sign:** Fill §Signature in `PREREG_SSTRF_RQ1_V2.md`; set `signature_status` to `signed` in `ARC12_PLATFORM_FREEZE.json` with date; commit both (or file signed PDF per institutional practice).

---

## Carried forward (outside iter-58 build)

| Item | Owner | Note |
|------|-------|------|
| **Mark signature** | Mark | Gates validity trials |
| **Practitioner panel** | Mark | GM-F §6 — longest lead; parallel to build |
| **RQ2** | Deferred | No criterion; Lee (2020) access outstanding |
| **Study-repo sync** | Ops | Harness on product `main`; study repo may need merge before live runs |
| **Independent review** | After Arc 12 close | Per project ritual |

---

## Commits

| Part | Commit |
|------|--------|
| A — Pre-reg draft | `e3e74b9` |
| B — Seeds + freeze | `66ea88e` |
| Closeout | *(this commit)* |

---

## iter-58 → study gate (ARC12 §8)

| Condition | Status |
|-----------|--------|
| Pre-reg v2 drafted | ✓ |
| Seeds + freeze manifest | ✓ |
| **Mark signed pre-reg v2** | ✓ 2026-08-25 |
| **Platform frozen** | ✓ binding on signature |

**Study gate: open.** Validity trials may proceed.

---

## Is iter-58 complete?

**Build scope: yes.** Pre-reg drafted, seeds fixed, freeze manifest written, tests pass, architect reviewed, this closeout written.

**Arc 12: CLOSED** (signed 2026-08-25). Execute ten validity trials under frozen config; no platform changes until complete or formally amended.
