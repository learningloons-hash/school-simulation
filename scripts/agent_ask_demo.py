#!/usr/bin/env python3
"""
One-liner demo for POST /agent/ask (Iteration 17).

Requires a running backend (default http://127.0.0.1:8100) and a working LLM.
Usage:
  export SENNA_BACKEND_URL=http://127.0.0.1:8100
  python3 scripts/agent_ask_demo.py "Run a short PSLE policy simulation and summarize stakeholder reactions."
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import warnings


def _backend_base_url() -> str:
    explicit = os.environ.get("SENNA_BACKEND_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    # Legacy env var (pre M-RENAME).
    legacy = os.environ.get("MIROFISH_BACKEND_URL", "").strip()
    if legacy:
        warnings.warn(
            "MIROFISH_BACKEND_URL is deprecated; use SENNA_BACKEND_URL",
            DeprecationWarning,
            stacklevel=2,
        )
        return legacy.rstrip("/")
    return "http://127.0.0.1:8100"


def main() -> None:
    base = _backend_base_url()
    q = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Run a short PSLE policy simulation and summarize stakeholder reactions."
    )
    body = json.dumps({"question": q}).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/agent/ask",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=3600) as resp:
            print(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.stderr.write(e.read().decode("utf-8", errors="replace"))
        raise SystemExit(e.code) from e


if __name__ == "__main__":
    main()
