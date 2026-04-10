# Review request — Iteration 4

**For:** Opus / architect (mirofish-code-reviewer or equivalent)  
**Repo folder:** `mirofish-mvp` (this project)  
**Iteration:** 4 (complete; includes follow-on hardening from LM Studio runs)

## Low-token retry (if the model hit usage limits)

Do **not** re-read the whole tree. In **one** reply, output **only**:

1. **Verdict:** `PASS` or `NEEDS_WORK` (one line).  
2. **Top 5 risks** (numbered, one sentence each).  
3. **Top 5 Iteration 5 actions** (numbered, specific).  
4. **One** methodological note on `<state>` JSON vs a second-pass extractor (≤ 3 sentences).

**Context:** paste or skim `docs/iterations/iteration-4-closeout.md` (sections *Original plan* and *Follow-on*) plus the short *Handoff summary* below. No need to open every test file.

---

## Handoff summary

Iteration 4 closed the Iteration 2 review gap list (structured state, tokens, Claude router, YAML scenarios, Python pin, tests, gitignore) and added operational fixes: LM Studio error surfacing, peer-context clipping for reasoning models and small `n_ctx`, prompt rules against chain-of-thought, and explicit cross-round dialogue feeding (round/turn labels, exclude self from “others,” evolution copy, policy defaults, wider interaction window on round openers).

## Please read first

1. `docs/SESSION_STATE.md` — current status and completed-work index  
2. `docs/iterations/iteration-4-closeout.md` — full file map and evidence  
3. `backend/src/mirofish_backend/simulation/orchestrator.py`  
4. `backend/src/mirofish_backend/llm/prompt_templates.py`  
5. `backend/src/mirofish_backend/llm/context_clip.py` + `state_parse.py`  
6. `backend/tests/` — all `test_*.py`

## Output

Create **`docs/reviews/review-iteration-4.md`** with your structured review (pass/needs work, prioritized findings, suggested Iteration 5 tasks).

## Focus questions

- Is `<state>` JSON + keyword fallback adequate for a thesis instrument, or is a dedicated extraction pass required?  
- Does clipping peer `raw_response` for prompts undermine auditability if full text remains only in DB/transcript?  
- Anthropic path: failure modes, empty API key, anything that should never appear in `config_snapshot`?  
- Does “exclude current agent from others block” + labels correctly address multi-round continuity?  
- Gaps vs long-term architecture (hybrid router, RAG, validity module)?
