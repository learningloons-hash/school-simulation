# Handoff to Builder

**Ritual:** Architect seeds this file before each Builder session. Builder implements **only** what is under **Active task** below. When finished (tests pass, commit), Builder fills [`handoff-to-architect.md`](./handoff-to-architect.md) and stops.

---

## Active task — `senna-iter-58` Part B (seeds + freeze manifest)

| Field | Value |
|-------|--------|
| **Arc** | 12 — Freeze and Study Readiness |
| **Spec** | [`HANDOFF_SENNA_ARC12.md`](./HANDOFF_SENNA_ARC12.md) §5 |
| **Pre-reg** | [`PREREG_SSTRF_RQ1_V2.md`](../research/PREREG_SSTRF_RQ1_V2.md) (Part A, Architect PASS `e3e74b9`) |
| **Branch** | `main` |
| **Base** | `e3e74b9` (Part A) |
| **Commit** | One commit for Part B only |

### Goal

Fix ten study seeds, write the platform freeze manifest, patch the pre-reg seeds section, and close Part A architect follow-ups. **No live validity trials.** Mark signature remains out of scope.

### Required deliverables

#### 1. `docs/diagnostics/ARC12_STUDY_SEEDS.json`

Ten trials, labels `trial-A` … `trial-J`, each with `random_seed`.

**Exclusion set (must not use any of these):** all `"seed"` values in `docs/diagnostics/*.json` — today **42, 43, 44** only (Arc 11 ablation, iter-54 confound, iter-55 rehearsal).

**Selection rule (document in JSON):** deterministic and auditable. Recommended:

> First ten integers ≥ 500 not in the exclusion set → **500–509**.

Record `selection_rule`, `excluded_seeds`, `trials` array, `drafted_at` ISO timestamp.

#### 2. `docs/diagnostics/ARC12_PLATFORM_FREEZE.json`

Binding record for Mark to sign against. Minimum fields:

| Field | Value / source |
|-------|----------------|
| `platform_code_commit` | `da906c3` — iter-57 platform closeout (harness `177306a`); simulation code freeze point |
| `pre_reg_commit` | `e3e74b9` (or current HEAD if Part B adds only manifests) |
| `pre_reg_path` | `docs/research/PREREG_SSTRF_RQ1_V2.md` |
| `fixture_provenance` | copy/ref [`ciepss_school_b_provenance.json`](../diagnostics/ciepss_school_b_provenance.json) |
| `scoring_system` | path + `git hash-object` blob hash for `SSTRF_RQ1_SCORING_SYSTEM_V2.md` |
| `study_seeds` | path `docs/diagnostics/ARC12_STUDY_SEEDS.json` |
| `export_version` | 14 |
| `frozen_at` | ISO timestamp at commit time |
| `signature_status` | `unsigned` |

#### 3. Track scoring system v2 in git (Architect follow-up from Part A)

`SSTRF_RQ1_SCORING_SYSTEM_V2.md` exists locally but is **not** tracked. Add `.gitignore` allowlist and **commit the file** so freeze hash is reproducible from git.

#### 4. Update `PREREG_SSTRF_RQ1_V2.md` §7

Replace placeholder with seed list + manifest path. Keep **UNSIGNED**. Do not change proposition text or thresholds.

#### 5. `backend/tests/test_senna_iter58_freeze.py`

- Load `ARC12_STUDY_SEEDS.json` — exactly 10 trials, labels A–J, seeds ∉ exclusion set
- Load `ARC12_PLATFORM_FREEZE.json` — required keys present; `signature_status == "unsigned"`
- Scoring blob hash in freeze matches `git hash-object` on committed scoring doc

#### 6. Housekeeping — `ARC12_PLATFORM_MEASURES_STATEMENT.md`

- **§6:** iter-57 Part B complete; harness on product `main` (`177306a`, 56 tests)
- **§1** external-judge row: harness implements GM-F v2 scoring (not orchestrator output)
- **§7** ops next step: iter-58 freeze (not “await GM-F”)

### Out of scope

- Mark's signature (Mark fills §Signature after review)
- Live validity trial execution or scoring
- iter-58 closeout doc (Architect after Part B PASS)
- RQ2 seeds / criterion
- Platform code changes beyond allowlist + tests

### Verification

```bash
cd backend && uv run pytest tests/test_senna_iter58_freeze.py -q
```

### Commit

`senna-iter-58` Part B (study seeds + freeze manifest).

---

## Completed (do not redo)

- `senna-iter-54`–`57`
- `senna-iter-58` Part A (`e3e74b9`, Architect PASS)
