from __future__ import annotations

from urllib.parse import urlparse
from urllib.request import Request, urlopen
import json
import os
import re

from .config import settings
from .storage import Store


DEGREE_LABELS = {
    "associate": "专科",
    "undergraduate": "本科",
    "graduate": "研究生",
    "doctoral": "博士生",
}

# 正向结果缓存 30 天；负向结果（确实没搜到）只缓存 1 天，避免反复调用付费接口。
POSITIVE_TTL_SECONDS = 30 * 24 * 3600
NEGATIVE_TTL_SECONDS = 24 * 3600


def _domain(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def _looks_like_education_domain(domain: str) -> bool:
    return domain.endswith((".edu.cn", ".edu", ".ac.uk", ".ac.jp", ".edu.au"))


def _normalize(text: str) -> str:
    """查询归一化：抹掉空格、标点、大小写差异，让同一所学校走同一条缓存。"""
    return re.sub(r"[\s·•\-_/（）()]+", "", (text or "").strip().lower())


def _cache_key(degree: str, school: str, college: str) -> str:
    return f"{degree}|{_normalize(school)}|{_normalize(college)}"


def resolve_api_key(store: Store) -> tuple[str, str]:
    """环境变量优先，其次是页面里保存到本机数据库的 Key。"""
    env_key = os.getenv("TAVILY_API_KEY", "").strip() or getattr(settings, "template_search_api_key", "").strip()
    if env_key:
        return env_key, "env"
    stored = (store.get_setting("tavily_api_key") or "").strip()
    if stored:
        return stored, "settings"
    return "", "none"


def _tavily_search(api_key: str, school: str, college: str, degree_label: str) -> dict:
    scope = f" {college}" if college else ""
    query = f'"{school}"{scope} {degree_label} 学位论文 格式规范 模板 site:edu.cn OR site:edu'
    body = json.dumps({
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced",
        "max_results": 10,
        "include_answer": False,
        "include_raw_content": False,
    }).encode("utf-8")
    request = Request(
        settings.template_search_api_url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=12) as response:
            return json.loads(response.read(2_000_000).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - 把原始原因原样带给用户
        raise ValueError(f"联网搜索失败：{exc}") from exc


def _rank(candidates: list[dict]) -> list[dict]:
    """官方域名优先，其次标题里带“模板 / 格式 / 学位论文”的；同一域名只留最相关的一条。"""
    for item in candidates:
        title = item.get("title", "")
        score = 0
        if item.get("official_domain_hint"):
            score += 3
        if "模板" in title:
            score += 2
        if "格式" in title:
            score += 1
        if "学位论文" in title or "毕业论文" in title:
            score += 1
        if item.get("url", "").lower().endswith(".pdf"):
            score += 1
        item["relevance"] = score
        item["confidence"] = "high" if score >= 4 else ("medium" if score >= 2 else "low")
    candidates.sort(key=lambda row: row["relevance"], reverse=True)
    picked: list[dict] = []
    seen: set[str] = set()
    for item in candidates:
        domain = item.get("domain", "")
        if domain in seen:
            continue
        seen.add(domain)
        picked.append(item)
    return picked


def search_templates(store: Store, degree: str, school: str, college: str = "", refresh: bool = False) -> dict:
    degree = degree.strip()
    school = school.strip()
    college = college.strip()
    if degree not in DEGREE_LABELS:
        raise ValueError("学历层次无效。")
    if not school:
        raise ValueError("请输入学校名称。")

    api_key, key_source = resolve_api_key(store)
    cache_key = _cache_key(degree, school, college)

    # 第一层：本地模板库。搜过、或人工确认过的候选直接命中，不再联网。
    if not refresh:
        library = store.list_school_templates(degree, school, college)
        if library:
            return {
                "cached": True,
                "configured": bool(api_key),
                "negative": False,
                "results": library,
                "message": f"命中本地模板库（{len(library)} 条已入库来源），本次没有联网。",
                "source": "library",
            }

    if not refresh:
        cached = store.get_search_cache(cache_key)
        if cached:
            negative = cached["status"] == "empty"
            return {
                "cached": True,
                "configured": bool(api_key),
                "negative": negative,
                "results": [] if negative else cached["payload"],
                "message": (
                    "上次检索没有找到候选来源，已缓存 24 小时。可以补充学院名称，或直接用自定义格式。"
                    if negative
                    else "命中本地缓存，本次没有产生联网请求。"
                ),
                "expires_at": cached["expires_at"],
                "source": key_source,
            }

    if not api_key:
        return {
            "cached": False,
            "configured": False,
            "negative": False,
            "results": [],
            "message": "尚未配置 TAVILY_API_KEY。填入后即可联网检索学校与学院的论文模板来源。",
            "source": "none",
        }

    payload = _tavily_search(api_key, school, college, DEGREE_LABELS[degree])

    candidates: list[dict] = []
    for result in payload.get("results", []):
        url = str(result.get("url", ""))
        domain = _domain(url)
        if urlparse(url).scheme not in {"http", "https"} or not domain:
            continue
        candidates.append({
            "degree": degree,
            "school": school,
            "college": college,
            "title": str(result.get("title", "官方论文格式资料"))[:300],
            "url": url,
            "domain": domain,
            "published_date": str(result.get("published_date") or ""),
            "snippet": str(result.get("content", ""))[:1200],
            "official_domain_hint": _looks_like_education_domain(domain),
            "status": "待人工核验",
        })

    ranked = _rank(candidates)
    for item in ranked:
        item["id"] = store.save_school_template(item)

    status = "ok" if ranked else "empty"
    store.put_search_cache(
        cache_key,
        degree,
        school,
        college,
        status,
        ranked,
        POSITIVE_TTL_SECONDS if ranked else NEGATIVE_TTL_SECONDS,
    )

    return {
        "cached": False,
        "configured": True,
        "negative": not ranked,
        "results": ranked,
        "message": (
            "已按官方域名与标题相关度排序，结果缓存 30 天；使用前请核对发布部门、适用学院和版本。"
            if ranked
            else "没有检索到候选来源。可以补充学院名称重试，或直接用自定义格式。"
        ),
        "source": key_source,
    }


def cache_candidate(store: Store, item: dict) -> dict:
    degree = str(item.get("degree", ""))
    if degree not in DEGREE_LABELS:
        raise ValueError("学历层次无效。")
    school = str(item.get("school", "")).strip()
    title = str(item.get("title", "")).strip()
    url = str(item.get("url", "")).strip()
    domain = _domain(url)
    if not school or not title or not domain or urlparse(url).scheme not in {"http", "https"}:
        raise ValueError("模板来源信息不完整。")
    entry = {
        "degree": degree,
        "school": school[:200],
        "college": str(item.get("college", "")).strip()[:200],
        "title": title[:300],
        "url": url[:2000],
        "domain": domain,
        "published_date": str(item.get("published_date", ""))[:40],
        "snippet": str(item.get("snippet", ""))[:1200],
    }
    entry["id"] = store.save_school_template(entry)
    entry["status"] = "待人工核验"
    return entry
