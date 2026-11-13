#!/usr/bin/env python3
"""Verify backend/.env Anthropic key loads and passes a one-turn API ping."""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "backend" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from run_arc11_ablation import load_backend_env_for_live_runs  # noqa: E402

from mirofish_backend.config import get_settings  # noqa: E402
from mirofish_backend.llm.router import llm_complete  # noqa: E402


async def main() -> int:
    env_file = _REPO_ROOT / "backend" / ".env"
    load_backend_env_for_live_runs(env_file)
    settings = get_settings()
    key = (settings.anthropic_api_key or "").strip()
    model = settings.anthropic_model

    if not key:
        print("FAIL: ANTHROPIC_API_KEY missing after loading backend/.env", file=sys.stderr)
        return 1

    shape_ok = key.startswith("sk-ant-") and bool(re.match(r"^sk-ant-api[0-9]{2}-", key))
    print(f"key_len={len(key)} sk-ant-apiNN-prefix={shape_ok} model={model}")

    try:
        completion = await llm_complete(
            provider="anthropic",
            messages=[
                {"role": "system", "content": "Reply OK"},
                {"role": "user", "content": "ping"},
            ],
            temperature=0.0,
            max_tokens=8,
            lmstudio_base_url=settings.lmstudio_base_url,
            lmstudio_model=settings.lmstudio_model,
            anthropic_api_key=key,
            anthropic_model=model,
            settings=settings,
            llm_call_site="anthropic_key_ping",
        )
        text = completion.text
    except RuntimeError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        if "404" in str(exc) or "not_found" in str(exc).lower():
            print(
                "  → Update ANTHROPIC_MODEL in backend/.env (retired ids return 404).",
                file=sys.stderr,
            )
        if "401" in str(exc):
            print(
                "  → Create a new key at console.anthropic.com and update backend/.env",
                file=sys.stderr,
            )
        return 1
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print(f"OK: Anthropic accepted key (reply={text[:20]!r})")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
