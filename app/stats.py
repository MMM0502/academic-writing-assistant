from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone, timedelta

from .storage import Store


def get_stats(store: Store, user_id: int | None = None) -> dict:
    jobs = store.get_all_jobs(limit=1000)
    if user_id is not None:
        jobs = [j for j in jobs if j.get("user_id") == user_id]

    total = len(jobs)
    format_jobs = [j for j in jobs if j["kind"] == "format"]
    review_jobs = [j for j in jobs if j["kind"] == "review"]

    style_counts = Counter()
    warning_count = 0
    duplicate_count = 0
    reference_count = 0
    llm_calls = 0
    llm_failures = 0
    llm_elapsed = []

    for job in jobs:
        payload = job["payload"]
        style = payload.get("style", "")
        if style:
            style_counts[style] += 1
        warnings = payload.get("warnings", [])
        warning_count += len(warnings)
        for w in warnings:
            if "重复" in w:
                duplicate_count += 1
        reference_count += payload.get("reference_count", 0)

        llm_status = payload.get("llm_status")
        engine = payload.get("engine", "")
        if engine == "llm-enhanced" or (llm_status and llm_status.get("configured")):
            llm_calls += 1
            if llm_status and llm_status.get("status") == "failed":
                llm_failures += 1
            if llm_status and llm_status.get("elapsed_seconds"):
                llm_elapsed.append(llm_status["elapsed_seconds"])

    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    recent_day = sum(1 for j in jobs if _parse_time(j["created_at"]) > day_ago)
    recent_week = sum(1 for j in jobs if _parse_time(j["created_at"]) > week_ago)

    avg_llm_time = round(sum(llm_elapsed) / len(llm_elapsed), 2) if llm_elapsed else 0
    llm_success_rate = round((llm_calls - llm_failures) / llm_calls * 100, 1) if llm_calls else 0

    return {
        "total_jobs": total,
        "format_jobs": len(format_jobs),
        "review_jobs": len(review_jobs),
        "recent_day": recent_day,
        "recent_week": recent_week,
        "total_references": reference_count,
        "total_warnings": warning_count,
        "duplicate_warnings": duplicate_count,
        "style_distribution": dict(style_counts),
        "llm_calls": llm_calls,
        "llm_failures": llm_failures,
        "llm_success_rate": llm_success_rate,
        "avg_llm_elapsed_seconds": avg_llm_time,
    }


def _parse_time(iso_str: str) -> datetime:
    try:
        return datetime.fromisoformat(iso_str)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)