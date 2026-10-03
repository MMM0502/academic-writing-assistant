from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, asdict
import re

from .llm import generate_review as _llm_generate_review
from .parsers import sentence_list, title_from_text


STOPWORDS = {
    "研究", "方法", "进行", "通过", "分析", "本文", "结果", "基于", "提出", "可以",
    "系统", "问题", "数据", "相关", "实现", "不同", "主要", "以及", "对于", "一种",
    "the", "and", "of", "with", "from", "study", "using",
}


@dataclass
class LiteratureItem:
    title: str
    year: str
    text: str
    keywords: list[str]


def _keywords(text: str, limit: int = 5) -> list[str]:
    tokens = re.findall(r"[\u4e00-\u9fff]{2,8}|[A-Za-z][A-Za-z-]{2,}", text.lower())
    counts = Counter(token for token in tokens if token not in STOPWORDS)
    return [token for token, _ in counts.most_common(limit)]


def build_item(text: str, filename: str) -> LiteratureItem:
    years = re.findall(r"\b(?:19|20)\d{2}\b", text)
    title = title_from_text(text, filename.rsplit(".", 1)[0])
    return LiteratureItem(title, years[0] if years else "未标注", text, _keywords(text))


def _theme_groups(items: list[LiteratureItem]) -> list[tuple[str, list[LiteratureItem]]]:
    groups: dict[str, list[LiteratureItem]] = {}
    for item in items:
        key = item.keywords[0] if item.keywords else "综合议题"
        groups.setdefault(key, []).append(item)
    return list(groups.items())[:5]


def generate_local_review(items: list[LiteratureItem], topic: str = "") -> dict:
    if not items:
        raise ValueError("至少上传一篇可读取的文献。")
    groups = _theme_groups(items)
    all_keywords = Counter(keyword for item in items for keyword in item.keywords)
    years = sorted({item.year for item in items if item.year != "未标注"})
    topic = topic.strip() or (all_keywords.most_common(1)[0][0] if all_keywords else "相关研究")
    overview = (
        f"围绕“{topic}”这一议题，现有研究主要从 {len(groups)} 个方向展开。"
        f"本次共整理 {len(items)} 篇文献，时间范围为 {years[0] + '—' + years[-1] if years else '未完整标注'}。"
        "从文献摘要与正文中的高频概念来看，研究重点集中在问题建模、方法设计和应用验证三个层面。"
    )
    sections = []
    for theme, members in groups:
        sources = "；".join(f"{item.title}（{item.year}）" for item in members[:3])
        sections.append(
            f"### {theme}方向\n"
            f"该方向包含 {len(members)} 篇文献，代表性材料包括：{sources}。"
            f"相关研究常见关键词为“{'、'.join(members[0].keywords[:4]) or '暂无'}”，"
            "整体上强调研究问题的清晰定义与方法可复现性。"
        )
    limitations = (
        "现有材料仍存在三点可继续讨论的空间：一是不同研究之间的评价指标尚未完全统一；"
        "二是部分方法依赖特定数据集，跨场景泛化能力需要进一步验证；"
        "三是理论分析与真实应用反馈之间仍可建立更紧密的闭环。"
    )
    body = "\n\n".join(sections)
    markdown = (
        f"# {topic}文献综述\n\n## 一、研究概述\n{overview}\n\n"
        f"## 二、研究主题与脉络\n{body}\n\n## 三、研究不足与展望\n{limitations}\n\n"
        "## 四、参考文献清单\n" + "\n".join(
            f"{index}. {item.title}，{item.year}。" for index, item in enumerate(items, start=1)
        )
    )
    return {
        "title": f"{topic}文献综述",
        "topic": topic,
        "markdown": markdown,
        "item_count": len(items),
        "keywords": [keyword for keyword, _ in all_keywords.most_common(12)],
        "themes": [{"name": name, "count": len(members)} for name, members in groups],
        "years": years,
        "engine": "local-rule-engine",
    }


def generate_review(items: list[LiteratureItem], topic: str = "") -> dict:
    local = generate_local_review(items, topic)
    prompt = (
        f"主题：{local['topic']}\n\n"
        + "\n\n".join(f"文献：{item.title}（{item.year}）\n{item.text[:5000]}" for item in items)
        + "\n\n请输出包含研究概述、主题脉络、观点比较、研究不足与展望、参考文献清单的 Markdown。"
    )
    enhanced = generate_review_with_llm(prompt)
    if enhanced:
        local["markdown"] = enhanced
        local["engine"] = "llm-enhanced"
    return local


def generate_review_with_llm(prompt: str) -> str | None:
    return _llm_generate_review(prompt)


def serialize_items(items: list[LiteratureItem]) -> list[dict]:
    return [asdict(item) for item in items]
