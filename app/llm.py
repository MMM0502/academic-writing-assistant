from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import settings


_last_error = ""


def configured() -> bool:
    return bool(settings.llm_api_key and settings.llm_api_url)


def status() -> dict[str, object]:
    return {
        "configured": configured(),
        "model": settings.llm_model,
        "api_url": settings.llm_api_url,
        "last_error": _last_error,
    }


def _content_from_response(result: dict) -> str:
    choices = result.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        content = message.get("content", "")
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        if content and isinstance(content, str):
            return content.strip()
    output_text = result.get("output_text")
    if isinstance(output_text, str):
        return output_text.strip()
    raise ValueError("API 返回中没有可用的文本内容")


def generate_review(prompt: str) -> str | None:
    global _last_error
    if not configured():
        _last_error = "未配置 LLM_API_KEY 或 OPENAI_API_KEY"
        return None
    payload = {
        "model": settings.llm_model,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是严谨的学术写作助手。只能根据提供的文献内容生成中文结构化综述， "
                    "必须区分原文证据和推断，不得编造作者、年份、期刊、DOI 或研究结论。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(
        settings.llm_api_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.llm_api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
        content = _content_from_response(result)
        _last_error = ""
        return content or None
    except urllib.error.HTTPError as exc:
        detail = exc.read(500).decode("utf-8", errors="replace")
        # Some gateways return an empty body for client errors. Preserve safe
        # response metadata so the user can distinguish provider errors from
        # proxy/gateway failures without exposing request headers or API keys.
        metadata = []
        headers = exc.headers
        if headers:
            for label, header in (
                ("server", "Server"),
                ("content-type", "Content-Type"),
                ("request-id", "X-Request-ID"),
            ):
                value = headers.get(header)
                if value:
                    metadata.append(f"{label}={value}")
        reason = str(exc.reason) if exc.reason else ""
        if reason:
            metadata.append(f"reason={reason}")
        message = detail.strip() or "响应正文为空"
        suffix = f" ({'; '.join(metadata)})" if metadata else ""
        _last_error = f"HTTP {exc.code}: {message}{suffix}"
    except Exception as exc:
        _last_error = f"{type(exc).__name__}: {exc}"
    return None
