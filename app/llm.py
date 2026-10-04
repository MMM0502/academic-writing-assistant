from __future__ import annotations

import json
import time
import urllib.request

from .config import settings


def configured() -> bool:
    return bool(settings.llm_api_key and settings.llm_api_url)


def generate_review(prompt: str) -> dict | None:
    if not configured():
        return None
    start_time = time.time()
    payload = {
        "model": settings.llm_model,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": "你是严谨的学术写作助手。只根据提供的文献材料生成中文结构化综述，不捏造引用。每段论述后用[来源：文献 N]标注来源。",
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
        elapsed = time.time() - start_time
        return {
            "content": result["choices"][0]["message"]["content"].strip(),
            "model": settings.llm_model,
            "elapsed_seconds": round(elapsed, 2),
            "status": "success",
            "error": None,
        }
    except Exception as exc:
        elapsed = time.time() - start_time
        return {
            "content": None,
            "model": settings.llm_model,
            "elapsed_seconds": round(elapsed, 2),
            "status": "failed",
            "error": str(exc),
        }


def get_status() -> dict:
    return {
        "configured": configured(),
        "model": settings.llm_model if configured() else None,
        "api_url": settings.llm_api_url if configured() else None,
        "privacy_notice": "调用外部大模型时，文献内容将发送到外部服务，请注意数据合规。" if configured() else None,
    }
