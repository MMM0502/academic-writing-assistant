# -*- coding: utf-8 -*-
"""格式规则 Schema v2：按“文档部位”分组，并提供与旧扁平规则的互转。

设计目标：
- 旧规则（v1 扁平字典，20 个键）不用迁移就能继续工作；
- 新规则按 page / body / headings / captions / references / header_footer 分组；
- 所有消费方（渲染器、应用器）只读 `to_flat()` 的输出，避免各处重复解析。
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

SCHEMA_VERSION = 2

GROUP_KEYS = ("page", "body", "headings", "title", "captions", "references", "header_footer")

DEFAULTS: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "page": {
        "size": "A4",
        "margins": {"top": "2.54", "bottom": "2.54", "left": "3.18", "right": "3.18"},
    },
    "body": {
        "font_cn": "SimSun",
        "font_en": "Calibri",
        "size": "12pt",
        "line_spacing": {"type": "multiple", "value": "1.5"},
        "space_before": "0pt",
        "space_after": "0pt",
        "first_line_indent": {"chars": 2},
        "alignment": "both",
    },
    "headings": {
        "1": {"font_cn": "SimHei", "size": "22pt", "bold": True, "align": "center", "before": "12pt", "after": "6pt"},
        "2": {"font_cn": "SimHei", "size": "16pt", "bold": True, "align": "left", "before": "12pt", "after": "6pt"},
        "3": {"font_cn": "SimHei", "size": "16pt", "bold": True, "align": "left", "before": "6pt", "after": "6pt"},
    },
    "title": {"size": "22pt", "align": "center"},
    "captions": {
        "figure": {"position": "below", "size": "10.5pt", "align": "center"},
        "table": {"position": "above", "size": "10.5pt", "align": "center"},
    },
    "references": {"font_cn": "SimSun", "size": "10.5pt", "hanging_indent": 2, "numbering": "bracket"},
    "header_footer": {"header_text": "", "page_number": {"position": "center", "format": "arabic", "start": 1}},
}

# v1 扁平键 -> v2 路径
FLAT_TO_PATH: dict[str, tuple[str, ...]] = {
    "page_size": ("page", "size"),
    "margin_top": ("page", "margins", "top"),
    "margin_bottom": ("page", "margins", "bottom"),
    "margin_left": ("page", "margins", "left"),
    "margin_right": ("page", "margins", "right"),
    "font_family": ("body", "font_cn"),
    "font_size": ("body", "size"),
    "body_alignment": ("body", "alignment"),
    "heading1_font": ("headings", "1", "font_cn"),
    "heading2_font": ("headings", "2", "font_cn"),
    "heading3_font": ("headings", "3", "font_cn"),
    "heading1_size": ("headings", "1", "size"),
    "heading2_size": ("headings", "2", "size"),
    "heading3_size": ("headings", "3", "size"),
    "ref_font": ("references", "font_cn"),
    "ref_size": ("references", "size"),
    "page_header": ("header_footer", "header_text"),
    "page_number_pos": ("header_footer", "page_number", "position"),
    "figure_caption": ("captions", "figure", "position"),
}


def _set(tree: dict, path: tuple[str, ...], value: Any) -> None:
    node = tree
    for key in path[:-1]:
        node = node.setdefault(key, {})
    node[path[-1]] = value


def _deep_update(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
    return base


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def to_v2(rules: dict | None) -> dict[str, Any]:
    """把任意版本的规则规范成 v2 结构。"""
    if not isinstance(rules, dict):
        return deepcopy(DEFAULTS)
    tree = deepcopy(DEFAULTS)

    # 1) 旧扁平键
    for key, path in FLAT_TO_PATH.items():
        if key in rules:
            _set(tree, path, rules[key])
    if rules.get("line_spacing_pt"):
        tree["body"]["line_spacing"] = {"type": "exact", "value": str(rules["line_spacing_pt"])}
    elif rules.get("line_spacing"):
        tree["body"]["line_spacing"] = {"type": "multiple", "value": str(rules["line_spacing"])}
    if rules.get("first_line_indent") is not None:
        chars = 2 if str(rules["first_line_indent"]) == "2chars" else 0
        tree["body"]["first_line_indent"] = {"chars": chars}

    # 2) 新分组键覆盖旧值
    nested = {key: rules[key] for key in GROUP_KEYS if isinstance(rules.get(key), dict)}
    if nested:
        _deep_update(tree, nested)

    # 3) 规范化
    tree["schema_version"] = SCHEMA_VERSION
    for level in ("1", "2", "3"):
        heading = tree["headings"].setdefault(level, {})
        heading["bold"] = _as_bool(heading.get("bold", True))
    for group in ("figure", "table"):
        tree["captions"].setdefault(group, {})
    tree["references"]["hanging_indent"] = int(float(tree["references"].get("hanging_indent", 2) or 0))
    tree["body"]["first_line_indent"]["chars"] = int(float(tree["body"]["first_line_indent"].get("chars", 2) or 0))
    return tree


def _pt_to_twips(value: Any, default_pt: float = 0.0) -> int:
    try:
        raw = str(value).replace("pt", "").strip()
        return int(round(float(raw) * 20))
    except (TypeError, ValueError):
        return int(round(default_pt * 20))


def to_flat(rules: dict | None) -> dict[str, Any]:
    """转成渲染器/应用器直接消费的扁平键（同时兼容旧键名）。"""
    tree = to_v2(rules)
    page, body = tree["page"], tree["body"]
    headings, references = tree["headings"], tree["references"]
    captions, header = tree["captions"], tree["header_footer"]

    chars = int(body["first_line_indent"].get("chars", 2) or 0)
    # 首行缩进按“字符数 × 字号”换算成 twips（1pt = 20 twips）
    try:
        body_pt = float(str(body.get("size", "12pt")).replace("pt", ""))
    except (TypeError, ValueError):
        body_pt = 12.0
    flat: dict[str, Any] = {
        "page_size": page.get("size", "A4"),
        "margin_top": str(page["margins"].get("top", "2.54")),
        "margin_bottom": str(page["margins"].get("bottom", "2.54")),
        "margin_left": str(page["margins"].get("left", "3.18")),
        "margin_right": str(page["margins"].get("right", "3.18")),
        "font_family": body.get("font_cn", "SimSun"),
        "font_en": body.get("font_en", "Calibri"),
        "font_size": str(body.get("size", "12pt")),
        "body_alignment": body.get("alignment", "both"),
        "first_line_chars": chars,
        "first_line_indent": "2chars" if chars >= 1 else "none",
        "first_line_indent_twips": int(round(chars * body_pt * 20)),
        "space_before": _pt_to_twips(body.get("space_before", "0pt")),
        "space_after": _pt_to_twips(body.get("space_after", "0pt")),
        "ref_font": references.get("font_cn", "SimSun"),
        "ref_size": str(references.get("size", "10.5pt")),
        "ref_numbering": references.get("numbering", "bracket"),
        "ref_hanging_chars": int(references.get("hanging_indent", 2) or 0),
        "page_header": header.get("header_text", ""),
        "page_number_pos": header.get("page_number", {}).get("position", "center"),
        "figure_caption": captions.get("figure", {}).get("position", "below"),
        "caption_size": str(captions.get("figure", {}).get("size", "10.5pt")),
        "caption_align": captions.get("figure", {}).get("align", "center"),
        "title_size": str(tree["title"].get("size", "22pt")),
    }

    spacing = body.get("line_spacing", {})
    if str(spacing.get("type", "multiple")) == "exact":
        flat["line_spacing_pt"] = str(spacing.get("value", "20"))
    else:
        flat["line_spacing"] = str(spacing.get("value", "1.5"))

    for level in ("1", "2", "3"):
        heading = headings.get(level, {})
        flat[f"heading{level}_font"] = heading.get("font_cn", "SimHei")
        flat[f"heading{level}_size"] = str(heading.get("size", "16pt"))
        flat[f"heading{level}_bold"] = _as_bool(heading.get("bold", True))
        flat[f"heading{level}_align"] = heading.get("align", "left")
        flat[f"heading{level}_before"] = _pt_to_twips(heading.get("before", "12pt"), 12)
        flat[f"heading{level}_after"] = _pt_to_twips(heading.get("after", "6pt"), 6)

    try:
        ref_pt = float(str(flat["ref_size"]).replace("pt", ""))
    except (TypeError, ValueError):
        ref_pt = 10.5
    flat["ref_hanging_twips"] = int(round(flat["ref_hanging_chars"] * ref_pt * 20))
    return flat


def _layer(rules: dict | None) -> dict:
    """只取出这一层显式写下的值（不补默认），用于叠加。"""
    if not isinstance(rules, dict):
        return {}
    tree: dict[str, Any] = {}
    for key, path in FLAT_TO_PATH.items():
        if key in rules:
            _set(tree, path, rules[key])
    if rules.get("line_spacing_pt"):
        _set(tree, ("body", "line_spacing"), {"type": "exact", "value": str(rules["line_spacing_pt"])})
    elif rules.get("line_spacing"):
        _set(tree, ("body", "line_spacing"), {"type": "multiple", "value": str(rules["line_spacing"])})
    if rules.get("first_line_indent") is not None:
        _set(tree, ("body", "first_line_indent", "chars"),
             2 if str(rules["first_line_indent"]) == "2chars" else 0)
    nested = {key: rules[key] for key in GROUP_KEYS if isinstance(rules.get(key), dict)}
    _deep_update(tree, nested)
    return tree


def merge_rules(*layers: dict | None) -> dict[str, Any]:
    """按顺序叠加：默认值 ← 学校模板 ← 用户微调。"""
    tree = deepcopy(DEFAULTS)
    for layer in layers:
        if layer:
            _deep_update(tree, _layer(layer))
    tree["schema_version"] = SCHEMA_VERSION
    return tree


def diff_rules(base: dict | None, override: dict | None) -> dict[str, Any]:
    """返回 override 相对 base 的差异，只保留被改动过的字段。"""
    normalized_base, normalized_override = to_v2(base), to_v2(override)

    def walk(base_node: dict, override_node: dict) -> dict:
        out: dict[str, Any] = {}
        for key, value in override_node.items():
            if key == "schema_version":
                continue
            if isinstance(value, dict) and isinstance(base_node.get(key), dict):
                child = walk(base_node[key], value)
                if child:
                    out[key] = child
            elif value != base_node.get(key):
                out[key] = value
        return out

    return walk(normalized_base, normalized_override)


def count_overrides(overrides: dict | None) -> int:
    """统计差异里的叶子字段数量，用于界面上的“已改 N 项”。"""
    if not isinstance(overrides, dict):
        return 0
    total = 0
    stack = [overrides]
    while stack:
        node = stack.pop()
        for value in node.values():
            if isinstance(value, dict):
                stack.append(value)
            else:
                total += 1
    return total


def validate(rules: dict | None) -> list[str]:
    """返回面向用户的可读告警，不阻止保存。"""
    tree = to_v2(rules)
    warnings: list[str] = []
    try:
        if not 1.0 <= float(tree["page"]["margins"]["top"]) <= 6.0:
            warnings.append("上边距超出常见范围（1–6 cm）。")
    except (TypeError, ValueError, KeyError):
        warnings.append("上边距不是有效数字。")
    spacing = tree["body"]["line_spacing"]
    if str(spacing.get("type")) == "exact" and str(spacing.get("value")) in ("", "0"):
        warnings.append("固定行距缺少具体磅值。")
    if tree["body"]["first_line_indent"].get("chars", 0) not in range(0, 7):
        warnings.append("首行缩进建议在 0–6 字符之间。")
    return warnings
