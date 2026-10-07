from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8765"))
    data_dir: Path = Path(os.getenv("DATA_DIR", "data"))
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_MB", "12")) * 1024 * 1024
    llm_api_url: str = os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
    llm_api_key: str = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
