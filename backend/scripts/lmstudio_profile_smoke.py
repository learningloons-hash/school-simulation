#!/usr/bin/env python3
"""
Optional live smoke test for local_lmstudio_default profile (senna-iter-39).

Requires LM Studio (or compatible server) at LMSTUDIO_BASE_URL / default 127.0.0.1:1234.

Usage (from backend/):
  uv run python scripts/lmstudio_profile_smoke.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from mirofish_backend.config import Settings
from mirofish_backend.llm.model_profiles import LOCAL_LMSTUDIO_DEFAULT_ID, local_lmstudio_default
from mirofish_backend.llm.router import llm_complete


async def main() -> int:
    settings = Settings()
    profile = local_lmstudio_default(settings)
    print(f"Profile: {profile.profile_id} ({LOCAL_LMSTUDIO_DEFAULT_ID})")
    print(f"Base URL: {profile.base_url}")
    print(f"Model: {profile.model_id}")

    completion = await llm_complete(
        provider="lmstudio",
        messages=[
            {
                "role": "system",
                "content": "Reply briefly. End with a <state> JSON block for support_level only.",
            },
            {"role": "user", "content": "Say hello in one sentence."},
        ],
        temperature=0.2,
        max_tokens=256,
        lmstudio_base_url=profile.base_url,
        lmstudio_model=profile.model_id,
        anthropic_api_key="",
        anthropic_model=settings.anthropic_model,
        openai_compatible_api_key="",
    )
    print("--- response ---")
    print(completion.text[:2000])
    if completion.input_tokens is not None:
        print(f"tokens in={completion.input_tokens} out={completion.output_tokens}")
    if "<state>" not in (completion.text or "").lower():
        print("WARN: no <state> block in response (local models often omit structured output)")
    return 0


if __name__ == "__main__":
    if os.environ.get("SKIP_LMSTUDIO_SMOKE") == "1":
        print("SKIP_LMSTUDIO_SMOKE=1 — exiting")
        sys.exit(0)
    raise SystemExit(asyncio.run(main()))
