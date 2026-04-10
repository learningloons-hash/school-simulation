from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    # Network
    host: str = "0.0.0.0"
    port: int = 8100
    cors_origins: list[str] = ["*"]

    # LM Studio (OpenAI compatible). Model id must match Local Server → loaded model identifier exactly.
    lmstudio_base_url: str = "http://127.0.0.1:1234/v1"
    lmstudio_model: str = "qwen/qwen3.5-9b"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 1024
    # lmstudio | anthropic | hybrid (hybrid: frontier on first turn of each round, local otherwise)
    llm_provider: str = "lmstudio"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-20241022"

    # DB
    sqlite_path: str = "./data/mirofish.sqlite"

    # Simulation defaults
    working_memory_last_k: int = 2
    prompt_version: str = "v1"
    # Per peer snippet when building cross-agent prompts (reasoning models can emit huge raw_response).
    peer_context_max_chars: int = 1200

    # RAG scaffold (Iteration 5): embeddings via LM Studio /v1/embeddings; effective if server or scenario enables.
    rag_enabled: bool = False
    # If empty, falls back to lmstudio_model for embedding calls.
    embedding_model: str = ""
    rag_top_k: int = 4
    rag_chunk_size: int = 400
    rag_chunk_overlap: int = 80
    rag_max_inject_chars: int = 2400

    # Iteration 6: reserved flag for future second-pass state audit (no LLM behavior when False).
    state_audit_enabled: bool = False

    # Iteration 19: max concurrent LLM calls within a single round (1 = sequential, default 4).
    llm_concurrency_cap: int = 4

    @field_validator("llm_provider", mode="before")
    @classmethod
    def _normalize_llm_provider(cls, v: object) -> str:
        if v is None:
            return "lmstudio"
        s = str(v).strip().lower()
        if s not in ("lmstudio", "anthropic", "hybrid"):
            return "lmstudio"
        return s


def get_settings() -> Settings:
    return Settings()

