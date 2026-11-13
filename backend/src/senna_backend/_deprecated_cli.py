"""Legacy console entrypoint for the pre-rename CLI name."""

from __future__ import annotations

import warnings

from senna_backend.main import run_dev


def run_dev_deprecated() -> None:
    warnings.warn(
        "mirofish-backend is deprecated; use: uv run senna-backend",
        DeprecationWarning,
        stacklevel=1,
    )
    run_dev()
