from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def parse_ccusage(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    findings: list[dict[str, Any]] = []
    if not text:
        return usage_summary("ccusage", path, findings=[{"level": "warning", "message": "ccusage artifact is empty or missing."}])
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return usage_summary("ccusage", path, findings=[{"level": "warning", "message": "ccusage artifact is not valid JSON."}])

    records = ccusage_records(data)
    totals = aggregate_usage(records)
    totals["records"] = len(records)
    return usage_summary("ccusage", path, findings=findings, **totals)


def ccusage_records(data: Any) -> list[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("sessions", "daily", "weekly", "monthly", "blocks"):
            value = data.get(key)
            if isinstance(value, list):
                return value
        return [data]
    return []


def parse_otel(path: Path) -> dict[str, Any]:
    totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_usd": 0.0}
    records = 0
    malformed = 0
    if not path.exists():
        return usage_summary("otel", path, findings=[{"level": "warning", "message": "OTel artifact is missing."}])
    with path.open(encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if not isinstance(data, dict):
                malformed += 1
                continue
            records += 1
            aggregate_into(totals, data)
            attributes = data.get("attributes")
            if isinstance(attributes, dict):
                aggregate_into(totals, attributes)
    findings = []
    if malformed:
        findings.append({"level": "warning", "message": f"Skipped {malformed} malformed OTel record(s)."})
    return usage_summary("otel", path, records=records, findings=findings, **totals)


def usage_summary(
    source: str,
    path: Path,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
    cost_usd: float = 0.0,
    records: int = 0,
    findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "source": source,
        "path": str(path),
        "records": records,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens or input_tokens + output_tokens,
        "cost_usd": round(float(cost_usd or 0.0), 6),
        "findings": findings or [],
    }


def aggregate_usage(records: list[Any]) -> dict[str, Any]:
    totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_usd": 0.0}
    for record in records:
        if isinstance(record, dict):
            aggregate_into(totals, record)
            for key in ("totals", "total", "usage", "summary"):
                nested = record.get(key)
                if isinstance(nested, dict):
                    aggregate_into(totals, nested)
    return totals


def aggregate_into(totals: dict[str, Any], data: dict[str, Any]) -> None:
    totals["input_tokens"] += first_int(data, "input_tokens", "inputTokens", "prompt_tokens", "promptTokens")
    totals["output_tokens"] += first_int(data, "output_tokens", "outputTokens", "completion_tokens", "completionTokens")
    totals["total_tokens"] += first_int(data, "total_tokens", "totalTokens", "tokens")
    totals["cost_usd"] += first_float(data, "cost_usd", "costUSD", "cost", "total_cost")


def first_int(data: dict[str, Any], *keys: str) -> int:
    for key in keys:
        try:
            value = int(data.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value:
            return value
    return 0


def first_float(data: dict[str, Any], *keys: str) -> float:
    for key in keys:
        try:
            value = float(data.get(key) or 0.0)
        except (TypeError, ValueError):
            value = 0.0
        if value:
            return value
    return 0.0
