from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, asdict, field
import re

from .llm import generate_review as _llm_generate_review, get_status as _llm_get_status
from .parsers import sentence_list, title_from_text


STOPWORDS = {
    "研究", "方法", "进行", "通过", "分析", "本文", "结果", "基于", "提出", "可以",
    "系统", "问题", "数据", "相关", "实现", "不同", "主要", "以及", "对于", "一种",
    "the", "and", "of", "with", "from", "study", "using",
}

QUESTION_PATTERNS = [
    r"(?:研究|探讨|关注|旨在|目的|为了)(?:的)?(?:问题|议题|目标|任务是?)[是为：:\s]*(.{10,80})",
    r"(?:本文|本研究|本论文)(?:研究|探讨|关注|旨在)[了]?(.{10,80})",
    r"(?:针对|面向)(.{5,40})(?:的|问题)",
]

METHOD_PATTERNS = [
    r"(?:方法|算法|模型|框架|技术|策略)[是为：:\s]*(.{10,80})",
    r"(?:采用|使用|基于|利用)(.{5,40})(?:方法|算法|模型|框架|技术|策略)",
    r"(?:提出|设计|构建)(?:了|一个)?(?:基于)?(.{5,40})(?:方法|算法|模型|框架)",
]

DATASET_PATTERNS = [
    r"(?:数据集|数据|语料|样本)[是为：:\s]*(.{5,60})",
    r"(?:在)(.{3,40})(?:上|数据集上)(?:进行|测试|评估|实验)",
]

CONCLUSION_PATTERNS = [
    r"(?:结果|结论|发现|表明|显示)[，：:\s]*(.{15,100})",
    r"(?:实验|评估)(?:结果)?(?:表明|显示|证明)[，：:\s]*(.{15,100})",
]

INNOVATION_PATTERNS = [
    r"(?:创新|贡献|新颖|首次|新)(?:之处|点|性)?[是为：:\s]*(.{10,80})",
    r"(?:本文|本研究)(?:的)?(?:主要)?(?:创新|贡献)[是为：:\s]*(.{10,80})",
]

LIMITATION_PATTERNS = [
    r"(?:局限|不足|缺点|缺陷|挑战)[是为：:\s]*(.{10,80})",
    r"(?:然而|但是|不过)(.{15,80})",
    r"(?:未来|后续)(?:工作|研究|方向)[是为：:\s]*(.{10,80})",
]


@dataclass
class LiteratureItem:
    title: str
    year: str
    text: str
    keywords: list[str]
    research_question: str = ""
    method: str = ""
    dataset: str = ""
    conclusion: str = ""
    innovation: str = ""
    limitation: str = ""
    source_index: int = 0


def _keywords(text: str, limit: int = 5) -> list[str]:
    tokens = re.findall(r"[\u4e00-\u9fff]{2,8}|[A-Za-z][A-Za-z-]{2,}", text.lower())
    counts = Counter(token for token in tokens if token not in STOPWORDS)
    return [token for token, _ in counts.most_common(limit)]


def _extract_field(text: str, patterns: list[str], max_len: int = 100) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            result = match.group(1).strip().rstrip("。.，,；;")
            if 5 <= len(result) <= max_len:
                return result
    return ""


def _extract_card_fields(text: str) -> dict:
    return {
        "research_question": _extract_field(text, QUESTION_PATTERNS),
        "method": _extract_field(text, METHOD_PATTERNS),
        "dataset": _extract_field(text, DATASET_PATTERNS),
        "conclusion": _extract_field(text, CONCLUSION_PATTERNS),
        "innovation": _extract_field(text, INNOVATION_PATTERNS),
        "limitation": _extract_field(text, LIMITATION_PATTERNS),
    }


def build_item(text: str, filename: str) -> LiteratureItem:
    years = re.findall(r"\b(?:19|20)\d{2}\b", text)
    title = title_from_text(text, filename.rsplit(".", 1)[0])
    card_fields = _extract_card_fields(text)
    return LiteratureItem(
        title=title,
        year=years[0] if years else "未标注",
        text=text,
        keywords=_keywords(text),
        **card_fields,
    )


def _theme_groups(items: list[LiteratureItem]) -> list[tuple[str, list[LiteratureItem]]]:
    groups: dict[str, list[LiteratureItem]] = {}
    for item in items:
        key = item.keywords[0] if item.keywords else "综合议题"
        groups.setdefault(key, []).append(item)
    return list(groups.items())[:5]


def _build_cards(items: list[LiteratureItem]) -> list[dict]:
    cards = []
    for i, item in enumerate(items, start=1):
        card = {
            "index": i,
            "title": item.title,
            "year": item.year,
            "keywords": item.keywords,
            "research_question": item.research_question or "未提取",
            "method": item.method or "未提取",
            "dataset": item.dataset or "未提取",
            "conclusion": item.conclusion or "未提取",
            "innovation": item.innovation or "未提取",
            "limitation": item.limitation or "未提取",
        }
        cards.append(card)
    return cards


def _compare_viewpoints(items: list[LiteratureItem]) -> list[dict]:
    comparisons = []
    for i, item in enumerate(items):
        if not item.conclusion:
            continue
        for j, other in enumerate(items):
            if j <= i or not other.conclusion:
                continue
            shared_keywords = set(item.keywords) & set(other.keywords)
            relation = "相关" if shared_keywords else "不同方向"
            if item.conclusion and other.conclusion:
                if any(kw in other.conclusion for kw in item.keywords[:2]):
                    relation = "支持/延伸"
                elif item.method and other.method and item.method != other.method:
                    relation = "方法差异"
            comparisons.append({
                "source_a": i + 1,
                "source_b": j + 1,
                "relation": relation,
                "shared_keywords": sorted(shared_keywords),
                "title_a": item.title,
                "title_b": other.title,
            })
    return comparisons


def generate_local_review(items: list[LiteratureItem], topic: str = "") -> dict:
    if not items:
        raise ValueError("至少上传一篇可读取的文献。")
    groups = _theme_groups(items)
    all_keywords = Counter(keyword for item in items for keyword in item.keywords)
    years = sorted({item.year for item in items if item.year != "未标注"})
    topic = topic.strip() or (all_keywords.most_common(1)[0][0] if all_keywords else "相关研究")
    overview = (
        f"围绕\u201c{topic}\u201d这一议题，现有研究主要从 {len(groups)} 个方向展开。"
        f"本次共整理 {len(items)} 篇文献，时间范围为 {years[0] + '\u2014' + years[-1] if years else '未完整标注'}。"
        "从文献摘要与正文中的高频概念来看，研究重点集中在问题建模、方法设计和应用验证三个层面。"
    )
    sections = []
    for theme, members in groups:
        sources = "；".join(f"{item.title}（{item.year}）[来源：文献 {idx}]" for idx, item in enumerate(members, start=1))
        section_text = (
            f"### {theme}方向\n"
            f"该方向包含 {len(members)} 篇文献，代表性材料包括：{sources}。"
            f"相关研究常见关键词为\u201c{'、'.join(members[0].keywords[:4]) or '暂无'}\u201d，"
        )
        if members[0].method:
            section_text += f"主要方法为{members[0].method}。"
        if members[0].conclusion:
            section_text += f"核心结论：{members[0].conclusion}[来源：文献 1]。"
        else:
            section_text += "整体上强调研究问题的清晰定义与方法可复现性。"
        sections.append(section_text)

    comparisons = _compare_viewpoints(items)
    if comparisons:
        compare_lines = []
        for cmp in comparisons[:8]:
            compare_lines.append(
                f"- 文献 {cmp['source_a']} 与文献 {cmp['source_b']}："
                f"关系为\u201c{cmp['relation']}\u201d"
                + (f"，共同关键词：{'、'.join(cmp['shared_keywords'])}" if cmp['shared_keywords'] else "")
            )
        comparison_section = "## 三、观点比较\n" + "\n".join(compare_lines)
    else:
        comparison_section = "## 三、观点比较\n暂未提取到足够的结论信息进行观点比较。"

    limitations = (
        "现有材料仍存在三点可继续讨论的空间：一是不同研究之间的评价指标尚未完全统一；"
        "二是部分方法依赖特定数据集，跨场景泛化能力需要进一步验证；"
        "三是理论分析与真实应用反馈之间仍可建立更紧密的闭环。"
    )
    body = "\n\n".join(sections)
    markdown = (
        f"# {topic}文献综述\n\n## 一、研究概述\n{overview}\n\n"
        f"## 二、研究主题与脉络\n{body}\n\n{comparison_section}\n\n"
        f"## 四、研究不足与展望\n{limitations}\n\n"
        "## 五、参考文献清单\n" + "\n".join(
            f"{index}. {item.title}，{item.year}。[来源：文献 {index}]" for index, item in enumerate(items, start=1)
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
        "cards": _build_cards(items),
        "comparisons": comparisons,
        "llm_status": None,
    }


def generate_review(items: list[LiteratureItem], topic: str = "") -> dict:
    local = generate_local_review(items, topic)
    llm_status = _llm_get_status()
    local["llm_status"] = llm_status

    if not llm_status["configured"]:
        return local

    prompt = (
        f"主题：{local['topic']}\n\n"
        + "\n\n".join(f"文献 {i}：{item.title}（{item.year}）\n{item.text[:5000]}" for i, item in enumerate(items, start=1))
        + "\n\n请输出包含研究概述、主题脉络、观点比较、研究不足与展望、参考文献清单的 Markdown。"
        + "每段论述后用[来源：文献 N]标注来源。"
    )
    result = _llm_generate_review(prompt)
    if result and result.get("content"):
        local["markdown"] = result["content"]
        local["engine"] = "llm-enhanced"
        local["llm_status"] = {
            **llm_status,
            "elapsed_seconds": result["elapsed_seconds"],
            "status": result["status"],
            "error": result["error"],
        }
    elif result and result.get("status") == "failed":
        local["llm_status"] = {
            **llm_status,
            "elapsed_seconds": result["elapsed_seconds"],
            "status": "failed",
            "error": result["error"],
        }
    return local


def generate_review_with_llm(prompt: str) -> str | None:
    result = _llm_generate_review(prompt)
    if result and result.get("content"):
        return result["content"]
    return None


def serialize_items(items: list[LiteratureItem]) -> list[dict]:
    return [asdict(item) for item in items]
