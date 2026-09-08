"""Runtime configuration, read from the environment (and an optional .env file)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CACHE_DIR = ROOT / "llm_cache"
UPLOAD_DIR = DATA_DIR / "uploads"


def _load_dotenv() -> None:
    """Minimal .env loader so we don't take a dependency for four lines of parsing."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


_load_dotenv()

# Default model per provider. All are cheap, high-throughput models with a large
# context window, which is what this workload wants: many medium-sized prompts.
DEFAULT_MODELS = {
    "gemini": "gemini-3.6-flash",
    "anthropic": "claude-sonnet-5",
    "openai": "gpt-4.1-mini",
    "replay": "replay",
}

API_KEY_ENV = {
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}


@dataclass
class Settings:
    provider: str = field(default_factory=lambda: os.getenv("FACTLAYER_PROVIDER", "gemini").lower())
    model: str = field(default_factory=lambda: os.getenv("FACTLAYER_MODEL", ""))
    db_path: Path = field(default_factory=lambda: Path(os.getenv("FACTLAYER_DB", str(DATA_DIR / "factlayer.db"))))
    cache_dir: Path = field(default_factory=lambda: Path(os.getenv("FACTLAYER_CACHE", str(CACHE_DIR))))
    upload_dir: Path = field(default_factory=lambda: Path(os.getenv("FACTLAYER_UPLOADS", str(UPLOAD_DIR))))

    # Ingestion tuning.
    max_concurrency: int = field(default_factory=lambda: int(os.getenv("FACTLAYER_MAX_CONCURRENCY", "4")))
    pages_per_chunk: int = field(default_factory=lambda: int(os.getenv("FACTLAYER_PAGES_PER_CHUNK", "4")))
    chunk_char_budget: int = field(default_factory=lambda: int(os.getenv("FACTLAYER_CHUNK_CHARS", "14000")))

    # Linking tuning.
    candidate_top_k: int = field(default_factory=lambda: int(os.getenv("FACTLAYER_TOP_K", "12")))
    metric_sim_threshold: float = field(default_factory=lambda: float(os.getenv("FACTLAYER_METRIC_SIM", "0.42")))
    numeric_tolerance: float = field(default_factory=lambda: float(os.getenv("FACTLAYER_NUM_TOL", "0.01")))

    # When true, never call a live API; only replay from the on-disk cache.
    offline: bool = field(default_factory=lambda: os.getenv("FACTLAYER_OFFLINE", "").lower() in {"1", "true", "yes"})

    def __post_init__(self) -> None:
        if self.provider == "replay":
            self.offline = True
        if not self.model:
            self.model = DEFAULT_MODELS.get(self.provider, DEFAULT_MODELS["gemini"])
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    @property
    def api_key(self) -> str:
        return os.getenv(API_KEY_ENV.get(self.provider, ""), "")

    @property
    def has_live_llm(self) -> bool:
        return bool(self.api_key) and not self.offline


_settings: Settings | None = None


def get_settings(refresh: bool = False) -> Settings:
    global _settings
    if _settings is None or refresh:
        _settings = Settings()
    return _settings
