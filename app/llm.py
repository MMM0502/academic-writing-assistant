from __future__ import annotations

import json
import os
import re
import time
import urllib.request

from .config import settings


_store = None


def bind_store(store) -> None:
    global _store
    _store = store


def _stored(name: str) -> str:
    if _store is None:
        return ""
    try:
        return (_store.get_setting(name) or "").strip()
    except Exception:
        return ""


def _resolve() -> tuple:
    key = os.getenv("LLM_API_KEY", "").strip() or _stored("llm_api_key") or settings.llm_api_key
    url = os.getenv("LLM_API_URL", "").strip() or _stored("llm_api_url") or settings.llm_api_url
    model = os.getenv("LLM_MODEL", "").strip() or _stored("llm_model") or settings.llm_model
    return key, url, model


def configured() -> bool:
    key, url, _model = _resolve()
    return bool(key and url)


def generate_review(prompt: str) -> dict | None:
    if not configured():
        return None
    key, url, model = _resolve()
    start_time = time.time()
    payload = {
        "model": model,
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
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
        elapsed = time.time() - start_time
        return {
            "content": result["choices"][0]["message"]["content"].strip(),
            "model": model,
            "elapsed_seconds": round(elapsed, 2),
            "status": "success",
            "error": None,
        }
    except Exception as exc:
        elapsed = time.time() - start_time
        return {
            "content": None,
            "model": model,
            "elapsed_seconds": round(elapsed, 2),
            "status": "failed",
            "error": str(exc),
        }


_REFERENCE_FIELDS = (
    "authors", "title", "source", "year", "volume", "issue", "pages",
    "doi", "url", "reference_type",
)


def normalize_references(references: list[dict], style: str = "gb7714") -> dict | None:
    """Ask an OpenAI-compatible model to repair reference metadata only.

    The model never renders the final citation and never receives the body. The
    deterministic citation engine remains responsible for ordering and output.
    """
    if not configured() or not references:
        return None
    key, url, model = _resolve()
    compact = []
    for ref in references:
        compact.append({
            "index": ref.get("index"),
            "raw": ref.get("raw", ""),
            **{key: ref.get(key, "") for key in _REFERENCE_FIELDS},
        })
    prompt = (
        "Repair the metadata of these academic references for citation style "
        f"{style}. Return JSON only as an array. Keep each index and preserve "
        "unknown values as empty strings. Do not invent DOI, pages, authors, "
        "or publication data. Do not return formatted citation text. Each item "
        "must contain index and these fields: "
        + ", ".join(_REFERENCE_FIELDS)
        + "\nReferences:\n"
        + json.dumps(compact, ensure_ascii=False)
    )
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": "You repair bibliographic metadata conservatively. Output valid JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    start_time = time.time()
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
        content = str(result["choices"][0]["message"]["content"]).strip()
        fenced = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", content, re.S)
        parsed = json.loads(fenced.group(1) if fenced else content)
        if not isinstance(parsed, list):
            raise ValueError("LLM response is not a JSON array")
        cleaned = []
        for item in parsed:
            if not isinstance(item, dict) or item.get("index") is None:
                continue
            clean = {"index": item["index"]}
            for key in _REFERENCE_FIELDS:
                value = item.get(key, "")
                clean[key] = str(value).strip() if value is not None else ""
            cleaned.append(clean)
        return {
            "references": cleaned,
            "model": model,
            "elapsed_seconds": round(time.time() - start_time, 2),
            "status": "success",
            "error": None,
        }
    except Exception as exc:
        return {
            "references": [],
            "model": model,
            "elapsed_seconds": round(time.time() - start_time, 2),
            "status": "failed",
            "error": str(exc),
        }


def get_status() -> dict:
    key, url, model = _resolve()
    is_ready = bool(key and url)
    source = "env" if os.getenv("LLM_API_KEY", "").strip() else ("settings" if _stored("llm_api_key") else "none")
    return {
        "configured": is_ready,
        "model": model if is_ready else None,
        "api_url": url if is_ready else None,
        "source": source,
        "privacy_notice": "调用外部大模型时，文献内容会发送到外部服务，请注意数据合规。" if is_ready else None,
    }
