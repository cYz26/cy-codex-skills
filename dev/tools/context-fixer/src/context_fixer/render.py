from __future__ import annotations

import html
import json


def render_text(report: dict) -> str:
    diagnosis = report["diagnosis"]
    lines = [
        "Context Fixer",
        f"Repo: {report.get('repo') or '(not provided)'}",
        f"Severity: {diagnosis['severity']}",
        f"Source of truth: {diagnosis.get('source_of_truth', 'unknown')}",
        f"Policy status: {report.get('context_policy', {}).get('status', 'unknown')}",
        f"Peak context: {diagnosis['max_input_tokens']} tokens ({diagnosis['max_context_pct']:.1%})",
        f"Context headroom: {diagnosis.get('headroom_tokens', 0)} tokens",
        f"Latest cache hit: {diagnosis['cache_hit_pct']:.1%}",
        f"Latest valid usage: {format_int(diagnosis.get('latest_valid_input_tokens', 0))} tokens ({diagnosis.get('latest_valid_source', 'none')})",
        f"Compactions seen: {diagnosis['compact_events']}",
        f"Request trace events: {diagnosis.get('request_trace_events', 0)}",
        "",
        "Timeline:",
        *render_text_timeline(report.get("timeline", {})),
        "",
        "Capability activity:",
        *render_text_activity(report.get("activity", {})),
        "",
        "Top contributors:",
    ]
    for item in report["attribution"]["top_contributors"][:10]:
        path = f" [{item['path']}]" if item.get("path") else ""
        confidence = f" ({item['confidence']})" if item.get("confidence") else ""
        lines.append(f"- {item['estimated_tokens']:>7} tokens  {item['label']}{path}{confidence}")
    chain = report.get("config_audit", {}).get("instruction_chain", {})
    if chain:
        lines.extend(["", "Instruction chain:"])
        global_instruction = chain.get("global")
        if global_instruction:
            lines.append(f"- global: {global_instruction}")
        project_chain = chain.get("project") or []
        if project_chain:
            for item in project_chain:
                lines.append(f"- project: {item['path']} ({item['status']}, {item['estimated_tokens']} est. tokens)")
        elif not global_instruction:
            lines.append("- No instruction files discovered.")
    lines.extend(["", "Findings:"])
    findings = report["diagnosis"]["findings"] + report["config_audit"]["findings"]
    if not findings:
        lines.append("- No significant findings.")
    for item in findings:
        lines.append(f"- [{item['level']}] {item['message']}")
    lines.extend(["", "Recommendations:"])
    for item in report["compression"]["recommendations"] or [{"priority": "-", "title": "No compaction changes needed", "action": ""}]:
        action = f" {item['action']}" if item.get("action") else ""
        lines.append(f"- [{item['priority']}] {item['title']}.{action}")
    lines.append("")
    lines.append("Note: attribution is estimated from local files and session event sizes; token_count events are exact Codex telemetry.")
    return "\n".join(lines)


def render_html(report: dict) -> str:
    diagnosis = report["diagnosis"]
    top = report["attribution"]["top_contributors"]
    findings = report["diagnosis"]["findings"] + report["config_audit"]["findings"]
    recommendations = report["compression"]["recommendations"]
    inventory = report["config_audit"]["inventory"]
    severity = str(diagnosis["severity"])
    max_tokens = max((int(item["estimated_tokens"]) for item in top), default=1)
    generated_at = escape(str(report.get("generated_at") or ""))
    repo = escape(str(report.get("repo") or "(not provided)"))
    raw_json = escape(json.dumps(report, ensure_ascii=False, indent=2))

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Context Fixer</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fb;
      --surface: #ffffff;
      --surface-2: #eef2f7;
      --text: #18202f;
      --muted: #637083;
      --border: #d9e0ea;
      --accent: #0f766e;
      --accent-2: #2563eb;
      --critical: #b91c1c;
      --high: #c2410c;
      --medium: #b7791f;
      --low: #15803d;
      --shadow: 0 12px 32px rgba(24, 32, 47, 0.08);
    }}

    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-width: 320px;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 15px;
      line-height: 1.5;
      overflow-x: hidden;
    }}

    main {{
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 40px;
    }}

    .topbar {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 20px;
      margin-bottom: 18px;
    }}

    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }}

    .brand-icon {{
      flex: 0 0 auto;
      width: 52px;
      height: 52px;
      border-radius: 8px;
      box-shadow: 0 10px 24px rgba(16, 19, 24, 0.14);
      image-rendering: pixelated;
    }}

    .brand-copy {{
      min-width: 0;
    }}

    h1 {{
      margin: 0;
      font-size: 30px;
      line-height: 1.12;
      font-weight: 760;
      letter-spacing: 0;
    }}

    .repo {{
      margin-top: 8px;
      color: var(--muted);
      overflow-wrap: anywhere;
      word-break: break-word;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 13px;
    }}

    .generated {{
      color: var(--muted);
      font-size: 13px;
      text-align: right;
      white-space: nowrap;
    }}

    .grid {{
      display: grid;
      gap: 14px;
    }}

    .summary {{
      grid-template-columns: repeat(5, minmax(0, 1fr));
      margin-bottom: 16px;
    }}

    .card, .panel {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }}

    .card {{
      min-height: 104px;
      padding: 16px;
    }}

    .label {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 680;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}

    .value {{
      margin-top: 8px;
      font-size: 25px;
      line-height: 1.15;
      font-weight: 740;
      overflow-wrap: anywhere;
    }}

    .hint {{
      margin-top: 7px;
      color: var(--muted);
      font-size: 13px;
    }}

    .severity {{
      color: var(--severity-color);
    }}

    .severity-chip {{
      display: inline-flex;
      align-items: center;
      height: 28px;
      padding: 0 10px;
      border-radius: 999px;
      color: #fff;
      background: var(--severity-color);
      font-size: 13px;
      font-weight: 720;
      text-transform: capitalize;
    }}

    .content {{
      grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.9fr);
      align-items: start;
    }}

    .panel {{
      padding: 18px;
    }}

    .panel h2 {{
      margin: 0 0 14px;
      font-size: 18px;
      line-height: 1.2;
      font-weight: 740;
      letter-spacing: 0;
    }}

    .bars {{
      display: grid;
      gap: 10px;
      min-width: 0;
    }}

    .bar-row {{
      display: grid;
      grid-template-columns: minmax(170px, 1fr) minmax(130px, 42%);
      gap: 12px;
      align-items: center;
      min-height: 38px;
    }}

    .bar-label {{
      min-width: 0;
    }}

    .bar-title {{
      font-weight: 660;
      overflow-wrap: anywhere;
    }}

    .bar-meta {{
      color: var(--muted);
      font-size: 12px;
      overflow-wrap: anywhere;
    }}

    .bar-track {{
      height: 26px;
      border-radius: 6px;
      background: var(--surface-2);
      overflow: hidden;
      position: relative;
      border: 1px solid #dfe5ef;
      min-width: 0;
    }}

    .bar-fill {{
      height: 100%;
      min-width: 2px;
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
    }}

    .bar-count {{
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: flex-end;
      padding-right: 8px;
      color: #0f172a;
      font-size: 12px;
      font-weight: 720;
      text-shadow: 0 1px 0 rgba(255, 255, 255, 0.7);
    }}

    .list {{
      display: grid;
      gap: 10px;
      margin: 0;
      padding: 0;
      list-style: none;
    }}

    .item {{
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      background: #fbfcfe;
    }}

    .item-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 5px;
    }}

    .badge {{
      flex: 0 0 auto;
      border-radius: 999px;
      padding: 3px 8px;
      background: var(--surface-2);
      color: #334155;
      font-size: 12px;
      font-weight: 720;
    }}

    .item-title {{
      font-weight: 710;
      overflow-wrap: anywhere;
    }}

    .item-body {{
      color: var(--muted);
      font-size: 13px;
      overflow-wrap: anywhere;
    }}

    .section-stack {{
      display: grid;
      gap: 14px;
    }}

    .chain {{
      display: grid;
      gap: 8px;
    }}

    .chain-row {{
      display: grid;
      grid-template-columns: 76px minmax(0, 1fr) auto;
      gap: 10px;
      align-items: center;
      padding: 9px 0;
      border-bottom: 1px solid var(--border);
    }}

    .chain-row:last-child {{
      border-bottom: 0;
    }}

    .scope {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 720;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}

    .path {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 13px;
      overflow-wrap: anywhere;
    }}

    .status {{
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }}

    .inventory {{
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}

    .kv {{
      padding: 12px;
      border-radius: 8px;
      background: #fbfcfe;
      border: 1px solid var(--border);
      min-width: 0;
    }}

    .kv .value {{
      font-size: 18px;
      line-height: 1.25;
    }}

    details {{
      margin-top: 14px;
      border-top: 1px solid var(--border);
      padding-top: 14px;
    }}

    summary {{
      cursor: pointer;
      font-weight: 700;
    }}

    pre {{
      margin: 12px 0 0;
      max-height: 420px;
      overflow: auto;
      padding: 14px;
      border-radius: 8px;
      background: #101827;
      color: #dbeafe;
      font-size: 12px;
      line-height: 1.45;
    }}

    @media (max-width: 960px) {{
      main {{ width: min(100% - 24px, 760px); padding-top: 20px; }}
      .summary {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .content {{ grid-template-columns: 1fr; }}
      .generated {{ text-align: left; white-space: normal; }}
      .topbar {{ flex-direction: column; }}
    }}

    @media (max-width: 620px) {{
      h1 {{ font-size: 24px; }}
      .summary, .inventory {{ grid-template-columns: 1fr; }}
      .bar-row {{ grid-template-columns: 1fr; }}
      .chain-row {{ grid-template-columns: 1fr; gap: 3px; }}
      .status {{ white-space: normal; }}
    }}
  </style>
</head>
<body style="--severity-color: {severity_color(severity)};">
  <main>
    <header class="topbar">
      <div class="brand">
        {brand_icon()}
        <div class="brand-copy">
        <h1>Context Fixer</h1>
        <div class="repo">{repo}</div>
        </div>
      </div>
      <div class="generated">Generated<br>{generated_at}</div>
    </header>

    <section class="grid summary" aria-label="Context summary">
      {summary_card("Severity", f'<span class="severity-chip">{escape(severity)}</span>', "Current pressure tier")}
      {summary_card("Peak Context", format_pct(diagnosis["max_context_pct"]), f'{format_int(diagnosis["max_input_tokens"])} input tokens')}
      {summary_card("Headroom", format_int(diagnosis.get("headroom_tokens", 0)), "Tokens before context window")}
      {summary_card("Cache Hit", format_pct(diagnosis["cache_hit_pct"]), "Latest token event")}
      {summary_card("Compactions", format_int(diagnosis["compact_events"]), "Events found in sessions")}
    </section>

    <section class="grid content">
      <div class="section-stack">
        <section class="panel">
          <h2>Top Contributors</h2>
          <div class="bars">
            {render_contributor_bars(top, max_tokens)}
          </div>
        </section>

        <section class="panel">
          <h2>Instruction Chain</h2>
          <div class="chain">
            {render_instruction_chain(report)}
          </div>
        </section>

        <section class="panel">
          <h2>Configuration Inventory</h2>
          <div class="grid inventory">
            {inventory_card("Global Plugins", inventory.get("enabled_global_plugins", 0), ", ".join(inventory.get("enabled_global_plugin_keys") or []) or "None")}
            {inventory_card("Global Skills", inventory.get("global_skills", 0), "Metadata only until a skill is loaded")}
            {inventory_card("MCP Servers", inventory.get("mcp_servers", 0), ", ".join(inventory.get("mcp_server_keys") or []) or "None")}
            {inventory_card("Project Skills", inventory.get("project_skills", 0), "Project-local .codex/skills")}
            {inventory_card("Project MCP", inventory.get("project_mcp_servers", 0), "From project .codex/config.toml")}
            {inventory_card("Workflow Signals", workflow_summary(inventory), "Planning and OpenSpec files")}
          </div>
        </section>
      </div>

      <aside class="section-stack">
        <section class="panel">
          <h2>Data Sources</h2>
          <div class="grid inventory">
            {render_data_sources(report.get("data_sources", {}))}
          </div>
        </section>

        <section class="panel">
          <h2>Policy Status</h2>
          <div class="grid inventory">
            {render_policy(report.get("context_policy", {}))}
          </div>
        </section>

        <section class="panel">
          <h2>Timeline</h2>
          {render_timeline(report.get("timeline", {}))}
        </section>

        <section class="panel">
          <h2>Capability Activity</h2>
          {render_activity(report.get("activity", {}))}
        </section>

        <section class="panel">
          <h2>Recommendations</h2>
          <ul class="list">
            {render_recommendations(recommendations)}
          </ul>
        </section>

        <section class="panel">
          <h2>Findings</h2>
          <ul class="list">
            {render_findings(findings)}
          </ul>
        </section>

        <section class="panel">
          <h2>Session Telemetry</h2>
          <div class="grid inventory">
            {inventory_card("Token Events", diagnosis.get("token_events", 0), "Exact Codex telemetry")}
            {inventory_card("Total Input", diagnosis.get("max_total_input_tokens", 0), "Largest accumulated input total")}
            {inventory_card("Output", diagnosis.get("last_output_tokens", 0), "Latest output tokens")}
            {inventory_card("Reasoning", diagnosis.get("last_reasoning_output_tokens", 0), "Latest reasoning output")}
          </div>
          <details>
            <summary>Sanitized JSON</summary>
            <pre>{raw_json}</pre>
          </details>
        </section>
      </aside>
    </section>
  </main>
</body>
</html>
"""


def render_contributor_bars(items: list[dict], max_tokens: int) -> str:
    if not items:
        return '<div class="item-body">No contributors found.</div>'
    rows = []
    for item in items[:12]:
        tokens = int(item.get("estimated_tokens") or 0)
        width = max(2, round(tokens / max_tokens * 100)) if max_tokens else 2
        path = f"<div class=\"bar-meta\">{escape(str(item.get('path')))}</div>" if item.get("path") else ""
        rows.append(
            f"""<div class="bar-row">
  <div class="bar-label">
    <div class="bar-title">{escape(str(item.get("label") or ""))}</div>
    <div class="bar-meta">{escape(str(item.get("kind") or ""))} · {escape(str(item.get("confidence") or ""))}</div>
    {path}
  </div>
  <div class="bar-track" aria-label="{escape(str(item.get("label") or ""))}: {format_int(tokens)} estimated tokens">
    <div class="bar-fill" style="width: {width}%"></div>
    <div class="bar-count">{format_int(tokens)}</div>
  </div>
</div>"""
        )
    return "\n".join(rows)


def brand_icon() -> str:
    return """<svg class="brand-icon" xmlns="http://www.w3.org/2000/svg" width="52" height="52" viewBox="0 0 64 64" role="img" aria-labelledby="context-fixer-icon-title context-fixer-icon-desc" shape-rendering="crispEdges">
  <title id="context-fixer-icon-title">Context Fixer icon</title>
  <desc id="context-fixer-icon-desc">Original pixel icon for a Codex context audit and cleanup tool.</desc>
  <rect width="64" height="64" fill="#101318"/>
  <rect x="4" y="4" width="56" height="56" fill="#171c23"/>
  <rect x="8" y="8" width="48" height="48" fill="#202630"/>
  <rect x="10" y="10" width="44" height="44" fill="#141920"/>
  <g fill="#27313c">
    <rect x="12" y="12" width="8" height="4"/>
    <rect x="24" y="12" width="4" height="4"/>
    <rect x="34" y="12" width="12" height="4"/>
    <rect x="12" y="20" width="4" height="4"/>
    <rect x="20" y="20" width="12" height="4"/>
    <rect x="42" y="20" width="8" height="4"/>
    <rect x="14" y="28" width="10" height="4"/>
    <rect x="40" y="28" width="12" height="4"/>
    <rect x="14" y="46" width="8" height="4"/>
    <rect x="42" y="46" width="8" height="4"/>
  </g>
  <g fill="#3dd7b6">
    <rect x="16" y="14" width="2" height="2"/>
    <rect x="24" y="22" width="2" height="2"/>
    <rect x="46" y="22" width="2" height="2"/>
    <rect x="16" y="48" width="2" height="2"/>
  </g>
  <g fill="#efe26b">
    <rect x="49" y="11" width="2" height="2"/>
    <rect x="47" y="13" width="2" height="2"/>
    <rect x="51" y="13" width="2" height="2"/>
    <rect x="49" y="15" width="2" height="2"/>
    <rect x="12" y="39" width="2" height="2"/>
    <rect x="10" y="41" width="2" height="2"/>
    <rect x="14" y="41" width="2" height="2"/>
    <rect x="12" y="43" width="2" height="2"/>
  </g>
  <g>
    <rect x="24" y="18" width="16" height="4" fill="#2a201d"/>
    <rect x="20" y="22" width="24" height="4" fill="#2a201d"/>
    <rect x="18" y="26" width="8" height="14" fill="#2a201d"/>
    <rect x="38" y="26" width="8" height="14" fill="#2a201d"/>
    <rect x="24" y="22" width="16" height="18" fill="#c28a62"/>
    <rect x="28" y="18" width="8" height="4" fill="#3a2a25"/>
    <rect x="22" y="30" width="4" height="8" fill="#6f4a39"/>
    <rect x="38" y="30" width="4" height="8" fill="#6f4a39"/>
    <rect x="28" y="28" width="3" height="3" fill="#101318"/>
    <rect x="35" y="28" width="3" height="3" fill="#101318"/>
    <rect x="31" y="36" width="4" height="2" fill="#7c3a36"/>
    <rect x="40" y="34" width="4" height="6" fill="#e7d8c3"/>
    <rect x="18" y="36" width="4" height="6" fill="#e7d8c3"/>
  </g>
  <g>
    <rect x="16" y="42" width="32" height="4" fill="#11151b"/>
    <rect x="14" y="46" width="36" height="10" fill="#1d252f"/>
    <rect x="18" y="46" width="6" height="10" fill="#27313c"/>
    <rect x="38" y="46" width="8" height="10" fill="#0e1217"/>
    <rect x="29" y="42" width="6" height="14" fill="#d8e1de"/>
    <rect x="31" y="46" width="2" height="10" fill="#3dd7b6"/>
  </g>
  <g>
    <rect x="42" y="36" width="4" height="18" fill="#a98f55"/>
    <rect x="38" y="52" width="12" height="4" fill="#d6c16b"/>
    <rect x="36" y="56" width="16" height="4" fill="#efe26b"/>
    <rect x="40" y="34" width="8" height="4" fill="#d8e1de"/>
    <rect x="20" y="50" width="8" height="8" fill="#0d1117"/>
    <rect x="18" y="54" width="12" height="4" fill="#0b0f14"/>
    <rect x="22" y="48" width="4" height="2" fill="#3dd7b6"/>
  </g>
  <g fill="#06080b">
    <rect x="4" y="4" width="56" height="4"/>
    <rect x="4" y="56" width="56" height="4"/>
    <rect x="4" y="4" width="4" height="56"/>
    <rect x="56" y="4" width="4" height="56"/>
  </g>
  <rect x="8" y="8" width="48" height="2" fill="#3dd7b6"/>
</svg>"""


def render_instruction_chain(report: dict) -> str:
    chain = report.get("config_audit", {}).get("instruction_chain", {})
    rows = []
    global_item = chain.get("global")
    if global_item:
        rows.append(chain_row("global", str(global_item), "loaded"))
    for item in chain.get("project") or []:
        status = f"{item.get('status', 'loaded')} · {format_int(item.get('estimated_tokens', 0))} est. tokens"
        rows.append(chain_row("project", str(item.get("path") or ""), status))
    if not rows:
        return '<div class="item-body">No instruction files discovered for this repo and cwd.</div>'
    return "\n".join(rows)


def render_recommendations(items: list[dict]) -> str:
    if not items:
        return '<li class="item"><div class="item-title">No compaction changes needed</div></li>'
    return "\n".join(
        f"""<li class="item">
  <div class="item-head"><div class="item-title">{escape(str(item.get("title") or ""))}</div><span class="badge">{escape(str(item.get("priority") or "-"))}</span></div>
  <div class="item-body">{escape(str(item.get("reason") or ""))}</div>
  <div class="item-body">{escape(str(item.get("action") or ""))}</div>
</li>"""
        for item in items
    )


def render_findings(items: list[dict]) -> str:
    if not items:
        return '<li class="item"><div class="item-title">No significant findings</div></li>'
    return "\n".join(
        f"""<li class="item">
  <div class="item-head"><div class="item-title">{escape(str(item.get("message") or ""))}</div><span class="badge">{escape(str(item.get("level") or "info"))}</span></div>
</li>"""
        for item in items
    )


def render_data_sources(data_sources: dict) -> str:
    session = data_sources.get("session_parser") or {}
    trace = data_sources.get("request_trace") or {}
    return "\n".join(
        [
            inventory_card(
                "Session Parser",
                session.get("status", "missing"),
                f"{format_int(session.get('files', 0))} files, {format_int(session.get('token_events', 0))} token events",
            ),
            inventory_card(
                "Request Trace",
                trace.get("status", "not_provided"),
                f"{format_int(trace.get('events', 0))} events, {format_int(trace.get('exact_usage_events', 0))} exact usage events",
            ),
        ]
    )


def render_policy(policy: dict) -> str:
    compact_range = policy.get("compact_range_tokens") or []
    compact_text = (
        f"{format_int(compact_range[0])}-{format_int(compact_range[1])}"
        if len(compact_range) == 2
        else "unknown"
    )


def render_text_timeline(timeline: dict) -> list[str]:
    if not timeline:
        return ["- No timeline events available."]
    lines = []
    peak = timeline.get("peak_event") or {}
    latest = timeline.get("latest_valid_usage_event") or {}
    growth = timeline.get("growth_events") or []
    compactions = timeline.get("compaction_events") or []
    anomalies = timeline.get("anomalies") or []
    if peak:
        lines.append(f"- Peak: {format_int(peak.get('input_tokens', 0))} tokens from {peak.get('source', 'unknown')} {peak.get('timestamp', '')}".rstrip())
    if latest:
        lines.append(
            f"- Latest valid: {format_int(latest.get('input_tokens', 0))} tokens from {latest.get('source', 'unknown')} {latest.get('timestamp', '')}".rstrip()
        )
    if growth:
        jump = growth[0]
        lines.append(
            f"- Largest jump: +{format_int(jump.get('delta_input_tokens', 0))} input tokens in {short_path(jump.get('path'))}"
        )
    lines.append(f"- Compaction events: {format_int(len(compactions))}")
    if anomalies:
        lines.append(f"- Anomalies: {format_int(len(anomalies))}")
    return lines or ["- No timeline events available."]


def render_timeline(timeline: dict) -> str:
    if not timeline:
        return '<div class="item-body">No timeline events available.</div>'
    summary = timeline.get("summary") or {}
    peak = timeline.get("peak_event") or {}
    latest = timeline.get("latest_valid_usage_event") or {}
    growth = timeline.get("growth_events") or []
    compactions = timeline.get("compaction_events") or []
    anomalies = timeline.get("anomalies") or []
    cards = [
        inventory_card("Events", summary.get("total_events", 0), "Sanitized chronological records"),
        inventory_card("Usage Events", summary.get("usage_events", 0), "Token telemetry events"),
        inventory_card("Trace Events", summary.get("request_events", 0), "Request-level records"),
        inventory_card("Anomalies", summary.get("anomaly_events", 0), "Zero usage or request errors"),
    ]
    blocks = [
        f'<div class="grid inventory">{"".join(cards)}</div>',
        timeline_item("Peak", peak, "input_tokens"),
        timeline_item("Latest Valid", latest, "input_tokens"),
    ]
    if growth:
        jump = growth[0]
        blocks.append(
            f"""<div class="item">
  <div class="item-head"><div class="item-title">Largest Growth Jump</div><span class="badge">+{escape(format_int(jump.get("delta_input_tokens", 0)))}</span></div>
  <div class="item-body">{escape(short_path(jump.get("path")))} · {escape(str(jump.get("timestamp") or ""))}</div>
</div>"""
        )
    if compactions:
        blocks.append(timeline_list("Compactions", compactions[:3], "input_tokens_before"))
    if anomalies:
        blocks.append(timeline_list("Anomalies", anomalies[:3], "anomaly_type"))
    return "\n".join(block for block in blocks if block)


def render_text_activity(activity: dict) -> list[str]:
    if not activity:
        return ["- No capability activity available."]
    summary = activity.get("summary") or {}
    lines = [
        f"- Observed tool calls: {format_int(summary.get('observed_tool_calls', 0))}",
        f"- Request activity events: {format_int(summary.get('request_activity_events', 0))}",
        f"- Available/request tools: {format_int(summary.get('available_tools', 0))}",
        f"- Configured plugins: {format_int(summary.get('enabled_global_plugins', 0))}; skills: {format_int(summary.get('global_skills', 0) + summary.get('project_skills', 0))}; MCP servers: {format_int(summary.get('mcp_servers', 0))}",
    ]
    for item in (activity.get("observed_calls") or [])[:5]:
        lines.append(
            f"- {item.get('name', 'unknown')}: {format_int(item.get('call_count', 0))} calls, {format_int(item.get('result_count', 0))} results"
        )
    return lines


def render_activity(activity: dict) -> str:
    if not activity:
        return '<div class="item-body">No capability activity available.</div>'
    summary = activity.get("summary") or {}
    inventory = activity.get("activation_inventory") or {}
    cards = [
        inventory_card("Observed Calls", summary.get("observed_tool_calls", 0), "Session tool call events"),
        inventory_card("Request Activity", summary.get("request_activity_events", 0), "Trace network/request records"),
        inventory_card("Available Tools", summary.get("available_tools", 0), "Session and request tool inventories"),
        inventory_card("Configured Plugins", inventory.get("enabled_global_plugins", 0), "Inventory, not observed calls"),
    ]
    blocks = [f'<div class="grid inventory">{"".join(cards)}</div>']
    observed = activity.get("observed_calls") or []
    if observed:
        rows = []
        for item in observed[:6]:
            detail = (
                f"{format_int(item.get('call_count', 0))} calls, "
                f"{format_int(item.get('result_count', 0))} results, "
                f"{format_int(item.get('output_estimated_tokens', 0))} output est. tokens"
            )
            rows.append(
                f"""<li class="item">
  <div class="item-head"><div class="item-title">{escape(str(item.get("name") or "unknown"))}</div><span class="badge">observed</span></div>
  <div class="item-body">{escape(detail)}</div>
</li>"""
            )
        blocks.append(f"<h2>Observed Calls</h2><ul class=\"list\">{''.join(rows)}</ul>")
    request_activity = activity.get("request_activity") or []
    if request_activity:
        rows = []
        for event in request_activity[:6]:
            detail = " · ".join(
                bit
                for bit in [
                    str(event.get("method") or ""),
                    str(event.get("path") or ""),
                    str(event.get("model") or ""),
                    f"status {event.get('status')}" if event.get("status") else "",
                ]
                if bit
            )
            rows.append(
                f"""<li class="item">
  <div class="item-head"><div class="item-title">{escape(str(event.get("category") or "request"))}</div><span class="badge">{escape(str(event.get("source") or ""))}</span></div>
  <div class="item-body">{escape(detail)}</div>
</li>"""
            )
        blocks.append(f"<h2>Request Activity</h2><ul class=\"list\">{''.join(rows)}</ul>")
    tools = activity.get("available_tools") or []
    if tools:
        blocks.append(
            f"""<div class="item">
  <div class="item-head"><div class="item-title">Available Tool Names</div><span class="badge">{format_int(len(tools))}</span></div>
  <div class="item-body">{escape(", ".join(str(tool) for tool in tools[:30]))}</div>
</div>"""
        )
    plugin_keys = inventory.get("enabled_global_plugin_keys") or []
    mcp_keys = inventory.get("mcp_server_keys") or []
    blocks.append(
        f"""<div class="item">
  <div class="item-head"><div class="item-title">Configured Inventory</div><span class="badge">not calls</span></div>
  <div class="item-body">Plugins: {escape(", ".join(plugin_keys[:20]) or "None")}</div>
  <div class="item-body">MCP: {escape(", ".join(mcp_keys[:20]) or "None")}</div>
</div>"""
    )
    return "\n".join(blocks)


def timeline_item(title: str, event: dict, token_key: str) -> str:
    if not event:
        return ""
    badge = format_int(event.get(token_key, 0))
    detail_bits = [
        str(event.get("source") or "unknown"),
        str(event.get("timestamp") or ""),
        short_path(event.get("path") or event.get("file")),
    ]
    detail = " · ".join(bit for bit in detail_bits if bit)
    return f"""<div class="item">
  <div class="item-head"><div class="item-title">{escape(title)}</div><span class="badge">{escape(badge)}</span></div>
  <div class="item-body">{escape(detail)}</div>
</div>"""


def timeline_list(title: str, events: list[dict], badge_key: str) -> str:
    rows = []
    for event in events:
        badge = event.get(badge_key, "")
        if isinstance(badge, int):
            badge = format_int(badge)
        label = event.get("message") or event.get("kind") or event.get("source") or "event"
        detail = " · ".join(
            bit
            for bit in [
                str(event.get("timestamp") or ""),
                short_path(event.get("path") or event.get("file")),
            ]
            if bit
        )
        rows.append(
            f"""<li class="item">
  <div class="item-head"><div class="item-title">{escape(str(label))}</div><span class="badge">{escape(str(badge))}</span></div>
  <div class="item-body">{escape(detail)}</div>
</li>"""
        )
    return f"<h2>{escape(title)}</h2><ul class=\"list\">{''.join(rows)}</ul>"


def short_path(value: object) -> str:
    text = str(value or "")
    if len(text) <= 96:
        return text
    return "..." + text[-93:]
    return "\n".join(
        [
            inventory_card("Status", policy.get("status", "unknown"), "Green, yellow, orange, or red"),
            inventory_card("Profile", policy.get("profile", "standard_coding"), "Context policy profile"),
            inventory_card("Compact At", compact_text, "Recommended token band"),
            inventory_card("Tool Output Limit", policy.get("tool_output_token_limit", 0), "Per-output guidance"),
        ]
    )


def summary_card(label: str, value_html: str, hint: str) -> str:
    return f"""<div class="card">
  <div class="label">{escape(label)}</div>
  <div class="value">{value_html}</div>
  <div class="hint">{escape(hint)}</div>
</div>"""


def inventory_card(label: str, value: object, hint: str) -> str:
    return f"""<div class="kv">
  <div class="label">{escape(label)}</div>
  <div class="value">{escape(format_value(value))}</div>
  <div class="hint">{escape(hint)}</div>
</div>"""


def chain_row(scope: str, path: str, status: str) -> str:
    return f"""<div class="chain-row">
  <div class="scope">{escape(scope)}</div>
  <div class="path">{escape(path)}</div>
  <div class="status">{escape(status)}</div>
</div>"""


def workflow_summary(inventory: dict) -> str:
    values = []
    if inventory.get("has_planning_state"):
        values.append("planning")
    if inventory.get("has_openspec"):
        values.append("openspec")
    return ", ".join(values) if values else "none"


def severity_color(severity: str) -> str:
    return {
        "critical": "#b91c1c",
        "high": "#c2410c",
        "medium": "#b7791f",
        "low": "#15803d",
    }.get(severity, "#475569")


def format_pct(value: float) -> str:
    return f"{value:.1%}"


def format_int(value: object) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def format_value(value: object) -> str:
    if isinstance(value, int):
        return format_int(value)
    return str(value)


def escape(value: str) -> str:
    return html.escape(value, quote=True)
