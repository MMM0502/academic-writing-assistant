from __future__ import annotations

from urllib.parse import urlparse
from urllib.request import Request, urlopen
import json

from .config import settings
from .storage import Store


DEGREE_LABELS = {
    "associate": "专科",
    "undergraduate": "本科",
    "graduate": "研究生",
    "doctoral": "博士生",
}


def _domain(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def _looks_like_education_domain(domain: str) -> bool:
    return domain.endswith((".edu.cn", ".edu", ".ac.uk", ".ac.jp", ".edu.au"))


def search_templates(store: Store, degree: str, school: str, college: str = "") -> dict:
    degree = degree.strip()
    school = school.strip()
    college = college.strip()
    if degree not in DEGREE_LABELS:
        raise ValueError("学历层次无效。")
    if not school:
        raise ValueError("请输入学校名称。")

    cached = store.list_school_templates(degree, school, college)
    if cached:
        return {"cached": True, "configured": bool(settings.template_search_api_key), "results": cached}
    if not settings.template_search_api_key:
        return {"cached": False, "configured": False, "results": [], "message": "模板缓存未命中。配置 TAVILY_API_KEY 后可搜索网页候选。"}

    degree_label = DEGREE_LABELS[degree]
    scope = f" {college}" if college else ""
    query = f'"{school}"{scope} {degree_label} 学位论文 格式规范 模板 site:edu.cn OR site:edu'
    body = json.dumps({
        "api_key": settings.template_search_api_key,
        "query": query,
        "search_depth": "advanced",
        "max_results": 10,
        "include_answer": False,
        "include_raw_content": False,
    }).encode("utf-8")
    request = Request(settings.template_search_api_url, data=body, headers={"Content-Type": "application/json", "Accept": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=12) as response:
            payload = json.loads(response.read(2_000_000).decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"联网搜索失败：{exc}") from exc

    results = []
    for result in payload.get("results", []):
        url = str(result.get("url", ""))
        domain = _domain(url)
        if urlparse(url).scheme not in {"http", "https"} or not domain:
            continue
        results.append({
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
    for result in results:
        result["id"] = store.save_school_template(result)
    return {"cached": False, "configured": True, "results": results, "message": "搜索结果已缓存为候选来源，使用前请确认发布单位、适用范围和版本。"}


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
