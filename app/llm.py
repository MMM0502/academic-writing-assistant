from __future__ import annotations

import json
import urllib.request

from .config import settings


def configured() -> bool:
    return bool(settings.llm_api_key and settings.llm_api_url)


def generate_review(prompt: str) -> str | None:
    if not configured():
        return None
    payload = {
        "model": settings.llm_model,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": "你是严谨的学术写作助手。只根据提供的文献材料生成中文结构化综述，不捏造引用。",
            },
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(
        settings.llm_api_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.llm_api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
