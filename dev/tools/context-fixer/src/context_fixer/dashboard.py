from __future__ import annotations

import html
import json
from typing import Any


def build_dashboard_projection(report: dict[str, Any], history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    budget = report.get("budget") or {}
    diagnosis = report.get("diagnosis") or {}
    policy = report.get("context_policy") or {}
    return {
        "overview": {
            "product": "Context Fixer",
            "repo": report.get("repo"),
            "generated_at": report.get("generated_at"),
            "severity": diagnosis.get("severity"),
            "policy_status": policy.get("status"),
            "source_of_truth": diagnosis.get("source_of_truth"),
            "max_input_tokens": int(diagnosis.get("max_input_tokens") or 0),
            "max_context_pct": float(diagnosis.get("max_context_pct") or 0.0),
            "headroom_tokens": int(diagnosis.get("headroom_tokens") or 0),
        },
        "baseline": budget.get("baseline") or {},
        "session_growth": budget.get("session_growth") or {},
        "timeline": report.get("timeline") or {},
        "top_offenders": budget.get("top_offenders") or [],
        "recommendations": budget.get("recommendations") or report.get("compression", {}).get("recommendations") or [],
        "governance": report.get("governance") or {},
        "data_sources": report.get("data_sources") or {},
        "history": history or [],
        "privacy": {
            "local_only": True,
            "omitted_bodies": [
                "prompts",
                "messages",
                "tool arguments",
                "command output",
                "file contents",
                "trace payloads",
                "hook payloads",
            ],
        },
    }


def render_dashboard_html(projection: dict[str, Any]) -> str:
    data = html.escape(json.dumps(projection, ensure_ascii=False), quote=False)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Context Fixer Dashboard</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --surface: #ffffff;
      --text: #18202f;
      --muted: #647084;
      --border: #d8dee8;
      --accent: #0f766e;
      --warning: #b7791f;
      --danger: #b91c1c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-width: 320px;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
      line-height: 1.45;
    }}
    main {{ width: min(1200px, calc(100% - 32px)); margin: 0 auto; padding: 24px 0 40px; }}
    header {{ display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 18px; }}
    h1 {{ margin: 0; font-size: 28px; line-height: 1.1; letter-spacing: 0; }}
    h2 {{ margin: 0 0 12px; font-size: 17px; letter-spacing: 0; }}
    .repo {{ margin-top: 6px; color: var(--muted); font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; overflow-wrap: anywhere; }}
    .grid {{ display: grid; gap: 12px; }}
    .summary {{ grid-template-columns: repeat(5, minmax(0, 1fr)); margin-bottom: 14px; }}
    .layout {{ grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.9fr); align-items: start; }}
    .panel, .metric {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 14px;
    }}
    .metric-label {{ color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; }}
    .metric-value {{ margin-top: 7px; font-size: 22px; font-weight: 740; overflow-wrap: anywhere; }}
    .stack {{ display: grid; gap: 12px; }}
    .list {{ display: grid; gap: 8px; padding: 0; margin: 0; list-style: none; }}
    .item {{ border: 1px solid var(--border); border-radius: 8px; padding: 10px; background: #fbfcfe; }}
    .item-head {{ display: flex; justify-content: space-between; gap: 10px; align-items: center; }}
    .badge {{ border-radius: 999px; padding: 2px 8px; background: #edf2f7; font-size: 12px; font-weight: 700; }}
    .muted {{ color: var(--muted); font-size: 13px; overflow-wrap: anywhere; }}
    .bar {{ height: 10px; background: #edf2f7; border-radius: 999px; overflow: hidden; margin-top: 8px; }}
    .fill {{ height: 100%; background: var(--accent); }}
    @media (max-width: 900px) {{ .summary {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} .layout {{ grid-template-columns: 1fr; }} }}
    @media (max-width: 560px) {{ main {{ width: min(100% - 20px, 720px); }} .summary {{ grid-template-columns: 1fr; }} header {{ flex-direction: column; }} }}
  </style>
</head>
<body>
  <script id="context-fixer-data" type="application/json">{data}</script>
  <main>
    <header>
      <div>
        <h1>Context Fixer Dashboard</h1>
        <div class="repo" id="repo"></div>
      </div>
      <div class="muted" id="generated"></div>
    </header>
    <section class="grid summary" id="summary"></section>
    <section class="grid layout">
      <div class="stack">
        <section class="panel"><h2>Top Offenders</h2><ul class="list" id="offenders"></ul></section>
        <section class="panel"><h2>Timeline</h2><ul class="list" id="timeline"></ul></section>
        <section class="panel"><h2>Recommendations</h2><ul class="list" id="recommendations"></ul></section>
      </div>
      <aside class="stack">
        <section class="panel"><h2>Data Sources</h2><ul class="list" id="sources"></ul></section>
        <section class="panel"><h2>History</h2><ul class="list" id="history"></ul></section>
        <section class="panel"><h2>Privacy</h2><div class="muted" id="privacy"></div></section>
      </aside>
    </section>
  </main>
  <script>
    const data = JSON.parse(document.getElementById("context-fixer-data").textContent);
    const text = (value) => value === undefined || value === null || value === "" ? "unknown" : String(value);
    const fmt = (value) => Number(value || 0).toLocaleString();
    const pct = (value) => `${{(Number(value || 0) * 100).toFixed(1)}}%`;
    document.getElementById("repo").textContent = text(data.overview.repo);
    document.getElementById("generated").textContent = text(data.overview.generated_at);
    const metrics = [
      ["Severity", text(data.overview.severity)],
      ["Policy", text(data.overview.policy_status)],
      ["Peak", `${{fmt(data.overview.max_input_tokens)}} tokens`],
      ["Window", pct(data.overview.max_context_pct)],
      ["Headroom", fmt(data.overview.headroom_tokens)]
    ];
    document.getElementById("summary").innerHTML = metrics.map(([label, value]) => `<div class="metric"><div class="metric-label">${{label}}</div><div class="metric-value">${{value}}</div></div>`).join("");
    const item = (title, meta = "", badge = "") => `<li class="item"><div class="item-head"><strong>${{text(title)}}</strong><span class="badge">${{text(badge)}}</span></div><div class="muted">${{text(meta)}}</div></li>`;
    document.getElementById("offenders").innerHTML = (data.top_offenders || []).slice(0, 8).map((entry) => item(entry.label, entry.category, fmt(entry.estimated_tokens))).join("") || item("No offenders");
    const timeline = data.timeline || {{}};
    document.getElementById("timeline").innerHTML = [
      timeline.peak_event && item("Peak", timeline.peak_event.source, fmt(timeline.peak_event.input_tokens)),
      timeline.latest_valid_usage_event && item("Latest valid", timeline.latest_valid_usage_event.source, fmt(timeline.latest_valid_usage_event.input_tokens)),
      ...(timeline.growth_events || []).slice(0, 3).map((entry) => item("Growth", entry.path, `+${{fmt(entry.delta_input_tokens)}}`))
    ].filter(Boolean).join("") || item("No timeline events");
    document.getElementById("recommendations").innerHTML = (data.recommendations || []).slice(0, 8).map((entry) => item(entry.title, entry.action, entry.priority)).join("") || item("No recommendations");
    document.getElementById("sources").innerHTML = Object.entries(data.data_sources || {{}}).map(([key, value]) => item(key, value.precision, value.status)).join("") || item("No data sources");
    document.getElementById("history").innerHTML = (data.history || []).slice(0, 8).map((entry) => item(entry.id, entry.generated_at, entry.severity)).join("") || item("No saved snapshots");
    document.getElementById("privacy").textContent = `Local only. Omitted bodies: ${{(data.privacy.omitted_bodies || []).join(", ")}}.`;
  </script>
</body>
</html>
"""
