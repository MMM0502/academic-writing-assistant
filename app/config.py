from dataclasses import dataclass, field
from pathlib import Path
import os


def _default_data_dir() -> Path:
    env = os.getenv("DATA_DIR")
    if env:
        return Path(env)
    return Path.home() / ".academic-assistant"


def _load_env_file() -> None:
    """读取项目根目录（以及 DATA_DIR）下的 .env；已存在的环境变量优先。"""
    candidates = [Path(__file__).resolve().parent.parent / ".env"]
    data_dir = os.getenv("DATA_DIR")
    if data_dir:
        candidates.append(Path(data_dir) / ".env")
    for path in candidates:
        try:
            if not path.is_file():
                continue
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
        except OSError:
            continue


_load_env_file()


@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8765"))
    data_dir: Path = field(default_factory=_default_data_dir)
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_MB", "12")) * 1024 * 1024
    llm_api_url: str = os.getenv("LLM_API_URL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    template_search_api_key: str = os.getenv("TAVILY_API_KEY", "")
    template_search_api_url: str = os.getenv("TAVILY_API_URL", "https://api.tavily.com/search")


settings = Settings()
try:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
except OSError as exc:
    raise SystemExit(
        f"无法创建数据目录 {settings.data_dir}：{exc}。"
        "请通过环境变量 DATA_DIR 指定一个可写的目录后重试。"
    ) from exc
