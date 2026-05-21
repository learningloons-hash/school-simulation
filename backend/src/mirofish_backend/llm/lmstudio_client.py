"""LM Studio compatibility shim — delegates to the generic OpenAI-compatible client."""

from mirofish_backend.llm.openai_compatible_client import (
    _format_openai_compatible_error_body as _format_lm_studio_error_body,
    chat_completion_openai_compatible,
)

__all__ = [
    "_format_lm_studio_error_body",
    "chat_completion_openai_compatible",
]
