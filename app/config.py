from dataclasses import dataclass, field
from pathlib import Path
import os


def _default_data_dir() -> Path:
    env = os.getenv("DATA_DIR")
    if env:
        return Path(env)
    return Path.home() / ".academic-assistant"


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8765"))
    data_dir: Path = field(default_factory=_default_data_dir)
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_MB", "12")) * 1024 * 1024
    llm_api_url: str = os.getenv("LLM_API_URL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")


settings = Settings()
try:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
except OSError as exc:
    raise SystemExit(
        f"无法创建数据目录 {settings.data_dir}：{exc}。"
        "请通过环境变量 DATA_DIR 指定一个可写的目录后重试。"
    ) from exc
