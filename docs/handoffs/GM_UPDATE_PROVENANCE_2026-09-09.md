# GM update — study artefact provenance and repo placement

**Date:** 2026-09-09  
**Source:** GM-F task (provenance fix before further runs)  
**Status:** CHECK list ruled by Mark 2026-09-09 — **Part C unblocked**

---

## Mark's CHECK list rulings (2026-09-09)

| # | Item | Ruling |
|---|------|--------|
| **1** | Calibration set public | **Approve.** Attributed paraphrases from freely-available NIE CIEPSS report, used methodologically. `SSTRF_RATER_CALIBRATION_SET.md` cites source page numbers; calibration **items** are paraphrased/invented passages (not verbatim report quotes). Ordinary scholarly practice for reproducibility. |
| **2** | sq_reading fixtures public | **Approve** on substance (pseudonyms Miss C/Miss L from published report). **Contradiction resolved:** authoritative copies are on **`school-simulation`** at `backend/src/mirofish_backend/scenarios/data/sq_reading_culture*.yaml` (from `c238fa9` + shock variants @ `befeaad`). `senna-sstrf-study` holds **non-authoritative mirrors** only (`437d72b`). Provenance JSON files updated accordingly. |
| **3** | Scoring manifest public | **Confirm.** It is the result; publishing it is the point. |
| **4** | RESULT narrative | **Publish on public repo.** A public 0/10 without explanation reads worse than either extreme. `SSTRF_RQ1_RESULT_V2.md` force-added alongside scoring manifest. Sensitive content is LLM-generated simulation output (quoted elicitation excerpts), not real persons. |
| **5** | Elicitation transcripts private | **Confirm.** Eighty LLM-output files; no reason to publish. Remain on `senna-sstrf-study` @ `437d72b`. |
| **6** | Shock fixtures | **Committed** to authoritative public repo: `sq_reading_culture_shock.yaml`, `sq_reading_culture_adverse_shock.yaml` + provenance JSON. |

---

## Executive summary

- **Public repo (`school-simulation`)** pushed earlier: `caedb22` → `72352e2`. Pre-reg signature `1b5ca4c` (2026-08-25) on remote with original date intact.
- **This commit** adds: RESULT narrative public, shock fixtures, provenance rulings doc, sq_reading provenance authority fix.
- **Private study repo (`senna-sstrf-study`)** @ `437d72b` — elicitation, scoring companions, **mirrors** of sq_reading fixtures (not authoritative).
- **Part C 2×2** (4 cells × 3 seeds) is **unblocked** pending Ops run brief.

---

## Fixture authority rule (resolves CHECK #2)

| Fixture family | Authoritative repo | Path pattern |
|----------------|-------------------|--------------|
| `sq_reading_culture*` (all 4 variants) | **`school-simulation`** | `backend/src/mirofish_backend/scenarios/data/sq_reading_culture*.yaml` |
| `ciepss_school_b` | **`senna-sstrf-study`** | `backend/.../ciepss_school_b.yaml` @ `47013659` |

Verifiers: use `docs/diagnostics/sq_reading_culture*_provenance.json` → `authoritative_repo` field.

---

## Step 1 — Inventory (final classification)

### PUBLIC-OK → `school-simulation`

| File | Notes |
|------|-------|
| `docs/research/PREREG_SSTRF_RQ1_V2.md` | Signed pre-reg |
| `docs/research/SSTRF_RQ1_SCORING_SYSTEM_V2.md` | Scoring system |
| `docs/research/SSTRF_RATER_CALIBRATION_SET.md` | Calibration set (paraphrases + citations) |
| `docs/research/runs/.../validity_v2_scoring_manifest.json` | Scores (`e5aa26b`) |
| `docs/research/runs/.../SSTRF_RQ1_RESULT_V2.md` | Result narrative (`befeaad`) |
| `backend/.../sq_reading_culture*.yaml` (4 files) | Utility fixtures — **authoritative** |
| `docs/diagnostics/*` (ARC manifests, trial manifest, provenance pointers) | Platform + study metadata |

### PRIVATE → `senna-sstrf-study` @ `437d72b`

| Material | Notes |
|----------|-------|
| `ciepss_school_b.yaml` + network CSV | Case fixture @ `47013659` |
| Validity v2 elicitation (80 JSON) | LLM output |
| Scoring companions (packets, worksheets, xlsx) | Human scoring artefacts |
| `SSTRF_RQ1_RESULT_V2.md` | **Mirror only** — public copy is authoritative |
| sq_reading YAML copies | **Mirror only** — public copy is authoritative |
| sq_reading run artefacts (tempsweep, analyst package) | Ops history |

### LOCAL ONLY (gitignored both repos)

| Material | Path |
|----------|------|
| Source PDFs | `docs/research/sources/*.pdf` |
| Proposal / MOE materials | `Proposal.*`, `simulation-study/` |

---

## Step 2 — Public push confirmation

| Check | Result |
|-------|--------|
| Remote updated (prior push) | `origin/main`: `caedb22` → `72352e2` |
| `1b5ca4c` on remote | ✅ Author date **2026-08-25 13:08:46 +0800** unchanged |
| No force-push / no rewrite | ✅ |

---

## Step 3 — Study repo sync

| Check | Result |
|-------|--------|
| Pushed | `4701365` → `437d72b` |
| Role | Private case material + **non-authoritative mirrors** |

---

## Artefact placement — verifier table

| Artefact | Authoritative repo | Commit / note | Path |
|----------|-------------------|---------------|------|
| Pre-reg (signed) | `school-simulation` | `1b5ca4c` | `docs/research/PREREG_SSTRF_RQ1_V2.md` |
| Scoring system | `school-simulation` | `177306a` | `docs/research/SSTRF_RQ1_SCORING_SYSTEM_V2.md` |
| Calibration set | `school-simulation` | `177306a` | `docs/research/SSTRF_RATER_CALIBRATION_SET.md` |
| Scoring manifest (0/10) | `school-simulation` | `e5aa26b` | `.../validity_v2_scoring_manifest.json` |
| **Result narrative** | `school-simulation` | `befeaad` | `.../SSTRF_RQ1_RESULT_V2.md` |
| sq_reading fixtures (×4) | `school-simulation` | `c238fa9` + `befeaad` | `backend/.../sq_reading_culture*.yaml` |
| CIEPSS fixture | `senna-sstrf-study` | `47013659` | `backend/.../ciepss_school_b.yaml` |
| Elicitation transcripts | `senna-sstrf-study` | `437d72b` | `.../validity_v2/elicitation/` |

**Confirmatory finding:** 0/10 trials pass — scores in public manifest; interpretation/limitations in public RESULT narrative.

---

## Part C readiness — 2×2 matrix

| | No shock | Shock |
|---|----------|-------|
| **Positive context** | `sq_reading_culture` | `sq_reading_culture_shock` |
| **Adverse context** | `sq_reading_culture_adverse` | `sq_reading_culture_adverse_shock` |

12 runs (3 seeds × 4 cells), ~US$4. Ops may proceed per GM-F corrected brief.

---

## Constraint compliance

| Constraint | Status |
|------------|--------|
| No rewrite of `1b5ca4c` or prior commits | ✅ |
| No force-push | ✅ |
| Public 0/10 has public explanation | ✅ (RESULT narrative) |
| Single authoritative pointer per fixture | ✅ |

---

*Last updated: 2026-09-09 after Mark CHECK rulings.*
